from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, get_current_org_membership, require_role
from app.models.models import User, OrganizationMember, MemberRole
from app.schemas.schemas import AuditEventResponse
from app.services.audit_service import audit_service

router = APIRouter(prefix="/audit", tags=["Audit"])

@router.get("", response_model=List[AuditEventResponse])
def get_audit_trail(
    event_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    membership: OrganizationMember = Depends(get_current_org_membership),
    db: Session = Depends(get_db)
):
    events = audit_service.get_events(
        db=db,
        organization_id=membership.organization_id,
        limit=limit,
        event_type=event_type
    )
    return events

@router.get("/verify")
def verify_audit_trail(
    membership: OrganizationMember = Depends(get_current_org_membership),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Cryptographically verifies the SHA-256 hash chain and external anchor of the organization's audit log."""
    verification = audit_service.verify_audit_chain(db=db, organization_id=membership.organization_id)
    return verification

@router.post("/anchor")
def anchor_audit_trail(
    membership: OrganizationMember = Depends(require_role([MemberRole.ORG_ADMIN, MemberRole.AUDITOR])),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Anchors the current latest tip of the organization's audit log to an external append-only log file.
    This creates an immutable out-of-band anchor that cannot be forged even by a database administrator.
    """
    try:
        res = audit_service.anchor_audit_chain(db=db, organization_id=membership.organization_id)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
