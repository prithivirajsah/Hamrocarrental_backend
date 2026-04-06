# app/routers/auth_router.py
import json
import os
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status, BackgroundTasks, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile as StarletteUploadFile
from starlette.requests import ClientDisconnect

from database_connection import get_db

from auth.jwt import authenticate_user, create_access_token, get_current_user
from crud.user import get_user_by_email, create_user
from crud.driver_license import create_driver_license
from crud.driver_license import get_driver_license_by_user_id
from utils.password_validation import validate_password_strength, get_password_requirements
from utils.email_service import send_account_created_login_email
from schemas.user import UserCreate, UserOut, LoginResponse
router = APIRouter(prefix="/auth", tags=["auth"])

LICENSE_UPLOAD_DIR = "static/uploads/licenses"
os.makedirs(LICENSE_UPLOAD_DIR, exist_ok=True)
ALLOWED_LICENSE_TYPES = {"application/pdf", "image/jpeg", "image/jpg", "image/png", "image/webp"}


async def _save_license_document(file: UploadFile) -> Dict[str, Any]:
    if file.content_type not in ALLOWED_LICENSE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported license document type: {file.content_type}",
        )

    extension = os.path.splitext(file.filename or "")[1].lower()
    if not extension:
        extension_map = {
            "application/pdf": ".pdf",
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
        }
        extension = extension_map.get(file.content_type, ".bin")

    file_name = f"{uuid.uuid4().hex}{extension}"
    file_path = os.path.join(LICENSE_UPLOAD_DIR, file_name)

    data = await file.read()
    with open(file_path, "wb") as output:
        output.write(data)

    return {
        "url": f"/static/uploads/licenses/{file_name}",
        "path": file_path,
        "data": data,
        "content_type": file.content_type,
        "filename": file.filename or file_name,
    }


async def _parse_driver_registration_payload(request: Request) -> Dict[str, Any]:
    content_type = request.headers.get("content-type", "").lower()

    if "multipart/form-data" in content_type:
        try:
            form = await request.form()
        except ClientDisconnect:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Client disconnected before completing upload.",
            )

        payload: Dict[str, Any] = {
            "full_name": (form.get("full_name") or "").strip(),
            "email": (form.get("email") or "").strip().lower(),
            "password": form.get("password") or "",
            "confirm_password": form.get("confirm_password") or "",
            "license_number": (form.get("license_number") or "").strip(),
            "license_expiry": (form.get("license_expiry") or form.get("license_expiry_date") or "").strip(),
            "license_document": form.get("license_document"),
        }
        return payload

    try:
        body = await request.json()
    except ClientDisconnect:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client disconnected before completing request body.",
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request payload. Send JSON or multipart/form-data.",
        )

    if not isinstance(body, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request payload must be an object.",
        )

    return {
        "full_name": str(body.get("full_name") or "").strip(),
        "email": str(body.get("email") or "").strip().lower(),
        "password": body.get("password") or "",
        "confirm_password": body.get("confirm_password") or "",
        "license_number": str(body.get("license_number") or "").strip(),
        "license_expiry": str(body.get("license_expiry") or body.get("license_expiry_date") or "").strip(),
        "license_document": None,
    }


async def _parse_login_payload(request: Request) -> Dict[str, str]:
    content_type = request.headers.get("content-type", "").lower()

    if "application/json" in content_type:
        try:
            payload = await request.json()
        except ClientDisconnect:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Client disconnected before completing request body.",
            )
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload.",
            )

        if not isinstance(payload, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request payload must be an object.",
            )

        email = (payload.get("email") or payload.get("username") or "").strip()
        password = payload.get("password") or ""
        return {"email": email, "password": password}

    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        try:
            form = await request.form()
        except ClientDisconnect:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Client disconnected before completing request body.",
            )
        email = (form.get("username") or form.get("email") or "").strip()
        password = form.get("password") or ""
        return {"email": email, "password": password}

    # Unknown/empty content type. Let endpoint validation return a clean 422.
    return {"email": "", "password": ""}

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    # Lowercase email
    email = user_in.email.lower()
    if get_user_by_email(db, email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    # create
    user_data = user_in.model_copy(update={"role": "user"})
    user = create_user(db, user_data)
    return user


@router.post("/register-driver", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register_driver(request: Request, db: Session = Depends(get_db)):
    payload = await _parse_driver_registration_payload(request)

    try:
        user_in = UserCreate(
            full_name=payload.get("full_name"),
            email=payload.get("email"),
            password=payload.get("password"),
            confirm_password=payload.get("confirm_password"),
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors())

    email = user_in.email.lower()
    if get_user_by_email(db, email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    license_number = str(payload.get("license_number") or "").strip()
    license_expiry = str(payload.get("license_expiry") or "").strip()
    if not license_number or not license_expiry:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="license_number and license_expiry are required for driver registration",
        )

    uploaded_doc = payload.get("license_document")
    if not isinstance(uploaded_doc, (UploadFile, StarletteUploadFile)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="license_document upload is required for driver registration",
        )

    saved_document = await _save_license_document(uploaded_doc)

    try:
        user_data = user_in.model_copy(update={"role": "driver"})
        user = create_user(db, user_data, commit=False)
        create_driver_license(
            db,
            user_id=user.id,
            license_number=license_number,
            license_image_url=saved_document["url"],
            license_expiry_date=license_expiry,
            license_image_data=saved_document["data"],
            license_image_content_type=saved_document["content_type"],
            license_image_filename=saved_document["filename"],
            commit=False,
        )
        db.commit()
        db.refresh(user)
    except HTTPException:
        db.rollback()
        try:
            os.remove(saved_document["path"])
        except OSError:
            pass
        raise
    except Exception:
        db.rollback()
        try:
            os.remove(saved_document["path"])
        except OSError:
            pass
        raise

    return user

@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    credentials = await _parse_login_payload(request)
    email = credentials["email"]
    password = credentials["password"]

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email/username and password are required",
        )

    user = authenticate_user(db, email, password)
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


@router.post("/driver-login", response_model=LoginResponse)
async def driver_login(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    credentials = await _parse_login_payload(request)
    email = credentials["email"]
    password = credentials["password"]

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email/username and password are required",
        )

    user = authenticate_user(db, email, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Backfill legacy accounts: if a license exists, this user should be treated as a driver.
    if user.role != "driver":
        existing_license = get_driver_license_by_user_id(db, user.id)
        if existing_license:
            user.role = "driver"
            db.commit()
            db.refresh(user)

    if user.role != "driver":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Driver account required",
        )

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


@router.get("/session")
def get_auth_session(current_user=Depends(get_current_user)):
    return {
        "authenticated": True,
        "user": UserOut.from_orm(current_user),
    }
