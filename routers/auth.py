# app/routers/auth_router.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database_connection import get_db
from auth.jwt import authenticate_user, create_access_token
from crud.user import get_user_by_email, create_user
from utils.password_validation import validate_password_strength, get_password_requirements
from schemas.user import UserCreate, UserOut, LoginResponse
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
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Incorrect email or password",
                            headers={"WWW-Authenticate": "Bearer"})
    access_token = create_access_token(data={"sub": user.email})
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
