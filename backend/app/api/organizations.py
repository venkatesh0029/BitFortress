from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.models import Organization, OrganizationMember, User, MemberRole
from app.schemas.schemas import OrganizationResponse, MemberAdd, MemberResponse, UserResponse
from app.services.audit_service import audit_service

router = APIRouter(prefix="/organizations", tags=["Organizations"])

@router.get("/current", response_model=OrganizationResponse)
def get_current_organization(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    membership = db.query(OrganizationMember).filter(OrganizationMember.user_id == current_user.id).first()
    if not membership:
        raise HTTPException(status_code=404, detail="No organization associated with this user")
    
    org = db.query(Organization).filter(Organization.id == membership.organization_id).first()
    return org

@router.get("/members", response_model=List[MemberResponse])
def get_organization_members(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    membership = db.query(OrganizationMember).filter(OrganizationMember.user_id == current_user.id).first()
    if not membership:
        raise HTTPException(status_code=404, detail="No organization associated with this user")
    
    members = db.query(OrganizationMember).filter(OrganizationMember.organization_id == membership.organization_id).all()
    results = []
    for m in members:
        results.append(MemberResponse(
            id=m.id,
            organization_id=m.organization_id,
            user_id=m.user_id,
            role=m.role,
            user=UserResponse(
                id=m.user.id,
                email=m.user.email,
                full_name=m.user.full_name,
                status=m.user.status,
                created_at=m.user.created_at,
                role=m.role,
                organization_id=m.organization_id
            ),
            created_at=m.created_at
        ))
    return results

@router.post("/members", response_model=MemberResponse)
def add_organization_member(
    member_in: MemberAdd,
    current_user: User = Depends(get_current_user),
    _ = Depends(require_role([MemberRole.ORG_ADMIN])),
    db: Session = Depends(get_db)
):
    membership = db.query(OrganizationMember).filter(OrganizationMember.user_id == current_user.id).first()
    user = db.query(User).filter(User.email == member_in.email.lower()).first()
    if not user:
        raise HTTPException(status_code=404, detail="User with this email does not exist")

    existing_mem = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == membership.organization_id,
        OrganizationMember.user_id == user.id
    ).first()
    if existing_mem:
        raise HTTPException(status_code=400, detail="User is already a member of this organization")

    new_mem = OrganizationMember(
        organization_id=membership.organization_id,
        user_id=user.id,
        role=member_in.role
    )
    db.add(new_mem)
    db.commit()
    db.refresh(new_mem)

    audit_service.record_event(
        db=db,
        organization_id=membership.organization_id,
        actor_id=current_user.id,
        event_type="MEMBER_ADDED",
        details={"user_email": user.email, "role": member_in.role}
    )

    return MemberResponse(
        id=new_mem.id,
        organization_id=new_mem.organization_id,
        user_id=new_mem.user_id,
        role=new_mem.role,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            status=user.status,
            created_at=user.created_at,
            role=new_mem.role,
            organization_id=new_mem.organization_id
        ),
        created_at=new_mem.created_at
    )
