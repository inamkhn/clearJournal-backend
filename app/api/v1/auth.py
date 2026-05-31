from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api import deps
from app.models.users import User, UserCreate, UserPublic, UserUpdate, Message, Token
from app.core.exceptions import (
    UserAlreadyExistsException,
    UserNotFoundException,
    InvalidTokenException,
    InvalidCredentialsException
)
from app.services.auth.auth_service import AuthService

router = APIRouter()

@router.post("/signup", response_model=UserPublic)
def signup(
    user: UserCreate,
    auth_service: AuthService = Depends()
):
    """
    Register a new user account.
    """
    try:
        return auth_service.register(user)
    except UserAlreadyExistsException as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends()
):
    """
    Log in with email and password (Sign In)
    """
    user = auth_service.login(form_data.username, form_data.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    access_token = auth_service.create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token, token_type="bearer")

@router.post("/verification-codes", response_model=Message)
def resend_verification_code(
    email: str = Query(..., description="The user email to resend verification code for"),
    auth_service: AuthService = Depends()
):
    """
    Resend verification code to the registered email address.
    """
    try:
        return auth_service.resend_verification_code(email)
    except UserNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/verify-email", response_model=Message)
def verify_email(
    email: str = Query(..., description="Email address to verify"),
    code: str = Query(..., description="Verification code sent to the email"),
    auth_service: AuthService = Depends()
):
    """
    Verify the user's email address using the received verification code.
    """
    try:
        return auth_service.verify_email(email, code)
    except UserNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidTokenException as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/users/me", response_model=UserPublic)
def read_users_me(
    current_user: User = Depends(deps.get_current_user),
    auth_service: AuthService = Depends()
):
    """
    Get profile information of the currently authenticated user.
    """
    return auth_service.user_repo.map_to_public(current_user)

@router.patch("/users/me", response_model=UserPublic)
def update_user(
    schema: UserUpdate,
    current_user: User = Depends(deps.get_current_user),
    auth_service: AuthService = Depends()
):
    """
    Update the authenticated user's profile information.
    """
    try:
        return auth_service.update_user(current_user.id, schema)
    except UserNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidCredentialsException as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/password-reset")
def initiate_password_reset(
    email: str = Query(..., description="Email associated with the account"),
    auth_service: AuthService = Depends()
):
    """
    Initiate password recovery process by generating reset token.
    """
    try:
        return auth_service.initiate_password_reset(email)
    except UserNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/password-reset/confirm")
def confirm_password_reset(
    token: str = Query(..., description="Password reset token"),
    new_password: str = Query(..., description="New password"),
    auth_service: AuthService = Depends()
):
    """
    Confirm password reset and register new password.
    """
    try:
        return auth_service.confirm_password_reset(token, new_password)
    except InvalidTokenException as e:
        raise HTTPException(status_code=400, detail=str(e))

