from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.models import User, MemberRole, OrganizationMember, SpendingPolicy
from app.schemas.schemas import SpendingPolicyCreate, SpendingPolicyResponse
from app.services.policy_service import policy_service
from app.services.audit_service import audit_service

router = APIRouter(prefix="/policies", tags=["Policies"])

@router.get("", response_model=SpendingPolicyResponse)
def get_policy(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    mem = db.query(OrganizationMember).filter(OrganizationMember.user_id == current_user.id).first()
    if not mem:
        raise HTTPException(status_code=404, detail="No organization found")

    p = policy_service.get_or_create_policy(db, mem.organization_id)
    return SpendingPolicyResponse(
        id=p.id,
        organization_id=p.organization_id,
        per_transaction_limit=p.per_transaction_limit,
        daily_limit=p.daily_limit,
        per_tx_btc=p.per_transaction_limit / 100_000_000,
        daily_btc=p.daily_limit / 100_000_000,
        require_admin_override=p.require_admin_override,
        is_active=p.is_active,
        created_at=p.created_at
    )

@router.put("", response_model=SpendingPolicyResponse)
def update_policy(
    policy_in: SpendingPolicyCreate,
    current_user: User = Depends(get_current_user),
    _ = Depends(require_role([MemberRole.ORG_ADMIN])),
    db: Session = Depends(get_db)
):
    mem = db.query(OrganizationMember).filter(OrganizationMember.user_id == current_user.id).first()
    p = policy_service.get_or_create_policy(db, mem.organization_id)

    old_per_tx = p.per_transaction_limit
    old_daily = p.daily_limit

    p.per_transaction_limit = policy_in.per_transaction_limit
    p.daily_limit = policy_in.daily_limit
    p.require_admin_override = policy_in.require_admin_override
    db.commit()
    db.refresh(p)

    audit_service.record_event(
        db=db,
        organization_id=mem.organization_id,
        actor_id=current_user.id,
        event_type="SPENDING_POLICY_UPDATED",
        reference_type="SPENDING_POLICY",
        reference_id=str(p.id),
        details={
            "old_per_tx_sats": old_per_tx,
            "new_per_tx_sats": p.per_transaction_limit,
            "old_daily_sats": old_daily,
            "new_daily_sats": p.daily_limit
        }
    )

    return SpendingPolicyResponse(
        id=p.id,
        organization_id=p.organization_id,
        per_transaction_limit=p.per_transaction_limit,
        daily_limit=p.daily_limit,
        per_tx_btc=p.per_transaction_limit / 100_000_000,
        daily_btc=p.daily_limit / 100_000_000,
        require_admin_override=p.require_admin_override,
        is_active=p.is_active,
        created_at=p.created_at
    )
