from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User, OrganizationMember
from app.schemas.schemas import AuditEventResponse
from app.services.audit_service import audit_service

router = APIRouter(prefix="/audit", tags=["Audit"])

@router.get("", response_model=List[AuditEventResponse])
def get_audit_trail(
    event_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    mem = db.query(OrganizationMember).filter(OrganizationMember.user_id == current_user.id).first()
    if not mem:
        raise HTTPException(status_code=404, detail="No organization associated with this user")

    events = audit_service.get_events(
        db=db,
        organization_id=mem.organization_id,
        limit=limit,
        event_type=event_type
    )
    return events

@router.get("/verify")
def verify_audit_trail(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Cryptographically verifies the SHA-256 hash chain of the organization's audit log."""
    mem = db.query(OrganizationMember).filter(OrganizationMember.user_id == current_user.id).first()
    if not mem:
        raise HTTPException(status_code=404, detail="No organization associated with this user")

    verification = audit_service.verify_audit_chain(db=db, organization_id=mem.organization_id)
    return verification
