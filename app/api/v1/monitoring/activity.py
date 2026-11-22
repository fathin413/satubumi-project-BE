from fastapi import (
    APIRouter,
    Depends,
    Query,
)

from sqlalchemy.orm import Session

from typing import List, Optional

from app.core.database import get_db

from app.core.dependencies import require_super_admin, get_project_or_404
from app.api.v1.auth import get_current_user

from app.models.user import User

from app.models.activity_log import ActivityLog
from app.models.monitor import ProjectMember

from app.schemas.activity_log import (
    ActivityLogResponse,
    ActivityLogMyResponse,
)




router = APIRouter(
    prefix="/activity",
    tags=["Activity Log"]
)



@router.get(
    "/all",
    response_model=List[ActivityLogResponse]
)
def get_all_logs(
    db: Session = Depends(get_db),
    user: User = Depends(require_super_admin)
):

    logs = (
        db.query(
            ActivityLog,
            User.full_name.label("user_name"),
            User.email.label("user_email"),
        )
        .outerjoin(
            User,
            ActivityLog.user_id == User.id
        )
        .order_by(
            ActivityLog.created_at.desc()
        )
        .all()
    )


    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "user_name": user_name,
            "user_email": user_email,
            "action": log.action,
            "module": log.module,
            "target_id": log.target_id,
            "target_name": log.target_name,
            "description": log.description,
            "created_at": log.created_at,
        }
        for log, user_name, user_email in logs
        
    ]

@router.get(
    "/me",
    response_model=List[ActivityLogMyResponse]
)
def get_my_logs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):

    return (
        db.query(ActivityLog)
        .filter(
            ActivityLog.user_id == user.id
        )
        .order_by(
            ActivityLog.created_at.desc()
        )
        .all()
    )


@router.get(
    "/project/{project_id}",
    response_model=List[ActivityLogResponse]
)
def get_project_team_logs(
    project_id: int,
    user_id: Optional[int] = Query(None, description="Filter log untuk anggota tim tertentu"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Project Manager / Admin / Anggota dapat melacak log aktivitas tim di dalam proyek.
    Mendukung filter berdasarkan user_id spesifik.
    """
    get_project_or_404(project_id, db, current_user)

    member_user_ids = [
        m.user_id for m in db.query(ProjectMember.user_id).filter(ProjectMember.project_id == project_id).all()
    ]

    if not member_user_ids:
        return []

    query = (
        db.query(
            ActivityLog,
            User.full_name.label("user_name"),
            User.email.label("user_email"),
        )
        .outerjoin(
            User,
            ActivityLog.user_id == User.id
        )
        .filter(
            ActivityLog.user_id.in_(member_user_ids)
        )
    )

    if user_id:
        query = query.filter(ActivityLog.user_id == user_id)

    logs = query.order_by(ActivityLog.created_at.desc()).limit(100).all()

    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "user_name": user_name,
            "user_email": user_email,
            "action": log.action,
            "module": log.module,
            "target_id": log.target_id,
            "target_name": log.target_name,
            "description": log.description,
            "created_at": log.created_at,
        }
        for log, user_name, user_email in logs
    ]


