from datetime import timedelta
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import (
    verify_password, get_password_hash, create_access_token, get_current_user
)
from app.models.models import User, Organization, OrganizationMember, MemberRole, SignerProfile
from app.schemas.schemas import UserCreate, UserLogin, Token, UserResponse
from app.services.audit_service import audit_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=Token)
def register(user_in: UserCreate, org_name: str = "Acme Treasury Holdings", db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="A user with this email already exists")

    # Create Organization
    org = Organization(name=org_name, status="ACTIVE")
    db.add(org)
    db.flush()

    # Create User
    user = User(
        email=user_in.email.lower(),
        full_name=user_in.full_name,
        password_hash=get_password_hash(user_in.password),
        status="ACTIVE"
    )
    db.add(user)
    db.flush()

    # Add as ORG_ADMIN
    membership = OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role=MemberRole.ORG_ADMIN
    )
    db.add(membership)
    db.commit()
    db.refresh(user)

    audit_service.record_event(
        db=db,
        organization_id=org.id,
        actor_id=user.id,
        event_type="ORGANIZATION_INITIALIZED",
        details={"org_name": org_name, "admin_email": user.email}
    )

    access_token = create_access_token(data={"sub": str(user.id), "email": user.email, "role": MemberRole.ORG_ADMIN})
    user_resp = UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        status=user.status,
        created_at=user.created_at,
        role=MemberRole.ORG_ADMIN,
        organization_id=org.id
    )

    return Token(access_token=access_token, user=user_resp)

@router.post("/login", response_model=Token)
def login(login_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_in.email.lower()).first()
    if not user or not verify_password(login_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status != "ACTIVE":
        raise HTTPException(status_code=403, detail="Account is deactivated")

    membership = db.query(OrganizationMember).filter(OrganizationMember.user_id == user.id).first()
    role = membership.role if membership else MemberRole.SIGNER
    org_id = membership.organization_id if membership else None

    access_token = create_access_token(data={"sub": str(user.id), "email": user.email, "role": role})
    user_resp = UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        status=user.status,
        created_at=user.created_at,
        role=role,
        organization_id=org_id,
        must_change_password=getattr(user, "must_change_password", False)
    )

    return Token(access_token=access_token, user=user_resp)

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    membership = db.query(OrganizationMember).filter(OrganizationMember.user_id == current_user.id).first()
    role = membership.role if membership else "SIGNER"
    org_id = membership.organization_id if membership else None

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        status=current_user.status,
        created_at=current_user.created_at,
        role=role,
        organization_id=org_id,
        must_change_password=getattr(current_user, "must_change_password", False)
    )

@router.post("/change-password")
def change_password(
    req: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Allows authenticated users to change their password, clearing default credential flags."""
    if not verify_password(req.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password incorrect")

    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters long")

    if req.new_password == "password123":
        raise HTTPException(status_code=400, detail="Cannot choose default demonstration password")

    current_user.password_hash = get_password_hash(req.new_password)
    current_user.must_change_password = False
    db.commit()

    return {"status": "success", "message": "Password changed successfully"}

@router.get("/demo-users")
def get_demo_users(db: Session = Depends(get_db)):
    """Returns quick-switch profiles for seamless demonstration testing."""
    users = db.query(User).all()
    demo_list = []
    for u in users:
        membership = db.query(OrganizationMember).filter(OrganizationMember.user_id == u.id).first()
        role = membership.role if membership else "SIGNER"
        signer = db.query(SignerProfile).filter(SignerProfile.user_id == u.id).first()
        demo_list.append({
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": role,
            "has_signer_key": signer is not None,
            "signer_label": signer.label if signer else None,
            "public_key": signer.public_key if signer else None,
            "must_change_password": getattr(u, "must_change_password", False)
        })
    return demo_list
