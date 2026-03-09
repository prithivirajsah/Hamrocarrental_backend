from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from auth.jwt import get_current_admin
from crud.admin import get_admin_dashboard_data
from database_connection import get_db
from schemas.admin import AdminDashboardResponse


router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard", response_model=AdminDashboardResponse, status_code=status.HTTP_200_OK)
def admin_dashboard(
    recent_limit: int = Query(8, ge=1, le=50),
    db: Session = Depends(get_db),
    _current_admin=Depends(get_current_admin),
):
    # Access is enforced via get_current_admin, which validates JWT and role.
    return get_admin_dashboard_data(db, recent_limit=recent_limit)
