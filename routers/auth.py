# app/routers/auth_router.py
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database_connection import get_db

from auth.jwt import authenticate_user, create_access_token
from crud.user import get_user_by_email, create_user, create_google_user
from utils.password_validation import validate_password_strength, get_password_requirements
from utils.email_service import send_account_created_login_email
from schemas.user import UserCreate, UserOut, LoginResponse, GoogleAuthRequest
router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    # Lowercase email
    email = user_in.email.lower()
    if get_user_by_email(db, email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    # create
    user = create_user(db, user_in)
    return user

@router.post("/login", response_model=LoginResponse)
def login(
    background_tasks: BackgroundTasks,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Incorrect email or password",
                            headers={"WWW-Authenticate": "Bearer"})
    access_token = create_access_token(data={"sub": user.email})
    background_tasks.add_task(send_account_created_login_email, user.email, user.full_name)
    return {
        "access_token": access_token,
        "user": UserOut.from_orm(user),
        "message": f"Welcome back, {user.full_name}!"
    }

@router.post("/validate-password")
def validate_password(request: dict):
    password = request.get("password", "")
    valid, errors = validate_password_strength(password)
    return {"is_valid": valid, "errors": errors}

@router.get("/password-requirements")
def password_requirements():
    return get_password_requirements()


@router.post("/google", response_model=LoginResponse)
def google_auth(payload: GoogleAuthRequest, db: Session = Depends(get_db)):
    try:
        google_payload = verify_google_id_token(payload.id_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    email = google_payload.get("email", "").lower()
    full_name = google_payload.get("name") or email.split("@")[0]

    user = get_user_by_email(db, email)
    if not user:
        user = create_google_user(db, email=email, full_name=full_name)

    access_token = create_access_token(data={"sub": user.email})
    return {
        "access_token": access_token,
        "user": UserOut.from_orm(user),
        "message": f"Welcome, {user.full_name}!"
    }
