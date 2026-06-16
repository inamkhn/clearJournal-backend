"""User agent instruction service — CRUD with versioning and activation."""
from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select, update

from app.db.session import get_session
from app.models.user_instructions import UserAgentInstruction
from app.schemas.user_instruction import (
    UserInstructionCreate,
    UserInstructionUpdate,
    UserInstructionRead,
)


class UserInstructionService:
    def __init__(self, session: Session = Depends(get_session)):
        self.session = session

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _to_read(self, instruction: UserAgentInstruction) -> UserInstructionRead:
        return UserInstructionRead(
            id=instruction.id,
            user_id=instruction.user_id,
            name=instruction.name,
            content=instruction.content,
            version=instruction.version,
            is_active=instruction.is_active,
            created_at=instruction.created_at,
            updated_at=instruction.updated_at,
        )

    def _get_or_404(self, instruction_id: int, user_id: int) -> UserAgentInstruction:
        """Fetch an instruction by ID, verify ownership, or raise 404."""
        instruction = self.session.exec(
            select(UserAgentInstruction).where(
                UserAgentInstruction.id == instruction_id,
                UserAgentInstruction.user_id == user_id,
            )
        ).first()
        if not instruction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User instruction not found",
            )
        return instruction

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def list_instructions(self, user_id: int) -> list[UserInstructionRead]:
        instructions = self.session.exec(
            select(UserAgentInstruction)
            .where(UserAgentInstruction.user_id == user_id)
            .order_by(UserAgentInstruction.created_at.desc())
        ).all()
        return [self._to_read(i) for i in instructions]

    def create_instruction(
        self, user_id: int, payload: UserInstructionCreate
    ) -> UserInstructionRead:
        instruction = UserAgentInstruction(
            user_id=user_id,
            name=payload.name,
            content=payload.content,
            version=1,
            is_active=False,
        )
        self.session.add(instruction)
        self.session.commit()
        self.session.refresh(instruction)
        return self._to_read(instruction)

    def get_instruction(self, instruction_id: int, user_id: int) -> UserInstructionRead:
        instruction = self._get_or_404(instruction_id, user_id)
        return self._to_read(instruction)

    def update_instruction(
        self, instruction_id: int, user_id: int, payload: UserInstructionUpdate
    ) -> UserInstructionRead:
        instruction = self._get_or_404(instruction_id, user_id)
        if payload.name is not None:
            instruction.name = payload.name
        if payload.content is not None:
            instruction.content = payload.content
            instruction.version += 1  # Auto-increment version on content change
        self.session.add(instruction)
        self.session.commit()
        self.session.refresh(instruction)
        return self._to_read(instruction)

    def delete_instruction(self, instruction_id: int, user_id: int) -> None:
        instruction = self._get_or_404(instruction_id, user_id)
        self.session.delete(instruction)
        self.session.commit()

    def activate_instruction(self, instruction_id: int, user_id: int) -> UserInstructionRead:
        """Activate this instruction and deactivate all others for the user."""
        instruction = self._get_or_404(instruction_id, user_id)

        # Deactivate all user's instructions
        self.session.exec(
            update(UserAgentInstruction)
            .where(
                UserAgentInstruction.user_id == user_id,
                UserAgentInstruction.is_active == True,
            )
            .values(is_active=False)
        )

        # Activate the target instruction
        instruction.is_active = True
        self.session.add(instruction)
        self.session.commit()
        self.session.refresh(instruction)
        return self._to_read(instruction)

    def deactivate_instruction(self, instruction_id: int, user_id: int) -> UserInstructionRead:
        instruction = self._get_or_404(instruction_id, user_id)
        instruction.is_active = False
        self.session.add(instruction)
        self.session.commit()
        self.session.refresh(instruction)
        return self._to_read(instruction)
