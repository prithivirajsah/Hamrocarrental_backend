# app/routers/user_router.py

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database_connection import get_db
from schemas.user import UserOut, UserProfileUpdate, UserRole
from crud.user import (
    get_all_drivers,
    get_user_by_id,
    get_users_by_role,
    get_all_drivers,
    count_users_by_role,
    update_user_profile,
    update_user_role
)
from auth.jwt import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])

# Role-based feature lists
def get_role_features(role: str):
    features = {
        "admin": {
            "user_management": "Manage users and roles",
            "system_statistics": "View system analytics",
            "content_moderation": "Moderate listings and reviews",
        },
        "driver": {
            "my_vehicles": "Manage your vehicle listings",
            "earnings": "Track your earnings",
            "availability": "Update your availability status",
            "rental_requests": "View rental requests",
        },
        "user": {
            "favorites": "Your favorite vehicles",
            "reviews": "Rate and review your rentals",
            "notifications": "View notifications",
        },
    }
    return features.get(role, features["user"])

# Get current logged-in user
@router.get("/me", response_model=UserOut)
def read_current_user(current_user=Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserOut)
def update_current_user(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return update_user_profile(db, current_user, payload)

# Home Page for logged-in users
@router.get("/home")
def home_page(current_user=Depends(get_current_user)):
    return {
        "message": f"Welcome to HamroRental, {current_user.full_name}!",
        "user_role": current_user.role,
        "user_id": current_user.id,
        "features": {
            "browse_vehicles": "Browse available vehicles",
            "my_bookings": "View your booking history",
            "profile": "Edit profile",
            "support": "Get customer support",
        },
        "role_specific_features": get_role_features(current_user.role),
    }

# Admin: Get users by role
@router.get("/by-role/{role}", response_model=List[UserOut])
def get_users_by_role_endpoint(
    role: UserRole,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view users by role",
        )

    return get_users_by_role(db, role.value, skip, limit)

# Get all drivers (drivers only)
@router.get("/drivers", response_model=List[UserOut])
def get_drivers(
    skip: int = Query(0),
    limit: int = Query(100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return get_all_drivers(db, skip, limit)


# -------------------------------------------------
# Admin: Count users by role
# -------------------------------------------------
@router.get("/stats/roles")
def get_role_statistics(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view statistics",
        )

    return count_users_by_role(db)


# -------------------------------------------------
# Admin: Update a user's role
# -------------------------------------------------
@router.put("/{user_id}/role", response_model=UserOut)
def update_user_role_endpoint(
    user_id: int,
    new_role: UserRole,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update roles",
        )

    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role",
        )

    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    updated_user = update_user_role(db, user_id, new_role.value)
    return updated_user
