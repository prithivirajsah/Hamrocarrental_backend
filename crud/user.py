# app/crud.py

from sqlalchemy import func
from typing import List, Optional

from sqlalchemy.orm import Session

from models.user import User
from schemas.user import UserCreate, UserProfileUpdate
from utils.password_validation import get_password_hash

# Get user by email
def get_user_by_email(db: Session, email: str) -> Optional[User]:
    normalized_email = (email or "").strip().lower()
    return db.query(User).filter(func.lower(User.email) == normalized_email).first()

# Get user by ID
def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

# Create new user
def create_user(db: Session, user_in: UserCreate) -> User:
    hashed_pw = get_password_hash(user_in.password)

    db_user = User(
        full_name=user_in.full_name,
        email=user_in.email.lower(),
        hashed_password=hashed_pw,
        role=user_in.role,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user
# Get users by specific role
def get_users_by_role(db: Session, role: str, skip: int = 0, limit: int = 100) -> List[User]:
    return (
        db.query(User)
        .filter(User.role == role)
        .offset(skip)
        .limit(limit)
        .all()
    )

# Get all drivers easily
def get_all_drivers(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return get_users_by_role(db, "driver", skip, limit)

# Count users grouped by role
def count_users_by_role(db: Session):
    results = db.query(User.role, func.count(User.id)).group_by(User.role).all()
    return {role: count for role, count in results}

# Update user role
def update_user_role(db: Session, user_id: int, new_role: str) -> User:
    db_user = get_user_by_id(db, user_id)

    if not db_user:
        raise ValueError("User not found")

    db_user.role = new_role

    db.commit()
    db.refresh(db_user)

    return db_user


def update_user_profile(db: Session, user: User, payload: UserProfileUpdate) -> User:
    user.full_name = payload.full_name
    user.phone = payload.phone
    user.location = payload.location
    user.country = payload.country
    user.date_of_birth = payload.date_of_birth

    db.commit()
    db.refresh(user)

    return user


def update_user_profile_image(db: Session, user: User, image_url: Optional[str]) -> User:
    user.profile_image_url = image_url
    db.commit()
    db.refresh(user)
    return user
