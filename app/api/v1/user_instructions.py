from typing import List
from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.deps import get_current_user
from app.models.users import User
from app.schemas.user_instruction import (
    UserInstructionCreate,
    UserInstructionUpdate,
    UserInstructionRead,
)
from app.services.user_instruction_service import UserInstructionService

router = APIRouter(tags=["user-instructions"])


# ── List User Instructions ────────────────────────────────────────────────────

@router.get("/", response_model=List[UserInstructionRead])
def list_instructions(
    user_instruction_service: UserInstructionService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """List all AI instructions for the current user."""
    return user_instruction_service.list_instructions(user_id=current_user.id)


# ── Create User Instruction ──────────────────────────────────────────────────

@router.post("/", response_model=UserInstructionRead, status_code=201)
def create_instruction(
    payload: UserInstructionCreate,
    user_instruction_service: UserInstructionService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Create a new AI instruction."""
    return user_instruction_service.create_instruction(user_id=current_user.id, payload=payload)


# ── Get User Instruction ─────────────────────────────────────────────────────

@router.get("/{instruction_id}", response_model=UserInstructionRead)
def get_instruction(
    instruction_id: int,
    user_instruction_service: UserInstructionService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Get a single instruction by ID."""
    return user_instruction_service.get_instruction(
        instruction_id=instruction_id, user_id=current_user.id
    )


# ── Update User Instruction ──────────────────────────────────────────────────

@router.patch("/{instruction_id}", response_model=UserInstructionRead)
def update_instruction(
    instruction_id: int,
    payload: UserInstructionUpdate,
    user_instruction_service: UserInstructionService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Update an instruction. Auto-increments version on content change."""
    return user_instruction_service.update_instruction(
        instruction_id=instruction_id, user_id=current_user.id, payload=payload
    )


# ── Delete User Instruction ──────────────────────────────────────────────────

@router.delete("/{instruction_id}", status_code=204)
def delete_instruction(
    instruction_id: int,
    user_instruction_service: UserInstructionService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Delete an instruction."""
    user_instruction_service.delete_instruction(
        instruction_id=instruction_id, user_id=current_user.id
    )
    return Response(status_code=204)


# ── Activate User Instruction ────────────────────────────────────────────────

@router.patch("/{instruction_id}/activate/", response_model=UserInstructionRead)
def activate_instruction(
    instruction_id: int,
    user_instruction_service: UserInstructionService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Activate this instruction and deactivate all others."""
    return user_instruction_service.activate_instruction(
        instruction_id=instruction_id, user_id=current_user.id
    )


# ── Deactivate User Instruction ──────────────────────────────────────────────

@router.patch("/{instruction_id}/deactivate/", response_model=UserInstructionRead)
def deactivate_instruction(
    instruction_id: int,
    user_instruction_service: UserInstructionService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Deactivate this instruction."""
    return user_instruction_service.deactivate_instruction(
        instruction_id=instruction_id, user_id=current_user.id
    )
