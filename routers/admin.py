from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from auth.jwt import get_current_admin
from crud.admin import get_admin_dashboard_data, get_admin_posts
from database_connection import get_db
from schemas.admin import AdminDashboardResponse, AdminPostListItem


router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard", response_model=AdminDashboardResponse, status_code=status.HTTP_200_OK)
def admin_dashboard(
    recent_limit: int = Query(8, ge=1, le=50),
    db: Session = Depends(get_db),
    _current_admin=Depends(get_current_admin),
):
    # Access is enforced via get_current_admin, which validates JWT and role.
    return get_admin_dashboard_data(db, recent_limit=recent_limit)


@router.get("/posts", response_model=List[AdminPostListItem], status_code=status.HTTP_200_OK)
def admin_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=300),
    search: Optional[str] = Query(None),
    owner_role: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _current_admin=Depends(get_current_admin),
):
    return get_admin_posts(
        db,
        skip=skip,
        limit=limit,
        search=search,
        owner_role=owner_role,
    )
