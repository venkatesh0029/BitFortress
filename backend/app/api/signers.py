from typing import List, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, get_current_org_membership, require_role
from app.core.config import settings
from app.models.models import SignerProfile, User, OrganizationMember, MemberRole
from app.schemas.schemas import SignerProfileCreate, SignerProfileResponse
from app.bitcoin.keys import generate_keypair
from app.services.signer_device_service import signer_device_service
from app.services.audit_service import audit_service

router = APIRouter(prefix="/signers", tags=["Signers"])

class DeviceSignRequest(BaseModel):
    psbt_base64: str

@router.get("", response_model=List[SignerProfileResponse])
def list_signers(
    membership: OrganizationMember = Depends(get_current_org_membership),
    db: Session = Depends(get_db)
):
    """
    Returns signer profiles associated with members of the caller's active organization.
    Enforces multi-tenant isolation so organizations cannot view each other's signer profiles.
    """
    profiles = (
        db.query(SignerProfile)
        .join(User, User.id == SignerProfile.user_id)
        .join(OrganizationMember, OrganizationMember.user_id == User.id)
        .filter(
            OrganizationMember.organization_id == membership.organization_id,
            SignerProfile.status == "ACTIVE"
        )
        .all()
    )
    results = []
    for p in profiles:
        results.append(SignerProfileResponse(
            id=p.id,
            user_id=p.user_id,
            label=p.label,
            public_key=p.public_key,
            fingerprint=p.fingerprint,
            derivation_path=p.derivation_path,
            status=p.status,
            created_at=p.created_at,
            user_name=p.user.full_name if p.user else "Unknown"
        ))
    return results

@router.post("", response_model=SignerProfileResponse)
def register_signer(
    profile_in: SignerProfileCreate,
    membership: OrganizationMember = Depends(get_current_org_membership),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Registers a new public key profile for the authenticated custodian within their organization.
    """
    # Verify public key format (compressed 33 bytes = 66 hex chars)
    pk_clean = profile_in.public_key.strip().lower()
    if len(pk_clean) not in [66, 130]:
        raise HTTPException(
            status_code=400,
            detail="Invalid public key format. Expected 66 hex characters for compressed secp256k1 key"
        )

    profile = SignerProfile(
        user_id=current_user.id,
        label=profile_in.label,
        public_key=pk_clean,
        fingerprint=profile_in.fingerprint,
        derivation_path=profile_in.derivation_path or "m/48'/1'/0'/2'",
        status="ACTIVE"
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    audit_service.record_event(
        db=db,
        organization_id=membership.organization_id,
        actor_id=current_user.id,
        event_type="SIGNER_PROFILE_REGISTERED",
        reference_type="SIGNER_PROFILE",
        reference_id=str(profile.id),
        details={
            "label": profile.label,
            "public_key": profile.public_key,
            "fingerprint": profile.fingerprint
        }
    )

    return SignerProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        label=profile.label,
        public_key=profile.public_key,
        fingerprint=profile.fingerprint,
        derivation_path=profile.derivation_path,
        status=profile.status,
        created_at=profile.created_at,
        user_name=current_user.full_name
    )

@router.post("/generate-keypair")
def generate_secp256k1_keypair(
    membership: OrganizationMember = Depends(require_role([MemberRole.ORG_ADMIN])),
):
    """
    Generates a secp256k1 keypair for development or testing (Admin only).
    Disabled in production mode where keys must be generated offline or on hardware devices.
    """
    if settings.ENVIRONMENT.lower() == "production":
        raise HTTPException(
            status_code=403,
            detail="Server-side keypair generation is strictly disabled in production. Use tools/signer_cli.py or a hardware signer."
        )
    return generate_keypair()

@router.post("/{signer_id}/device-sign")
def sign_with_custodian_device(
    signer_id: int,
    req: DeviceSignRequest,
    membership: OrganizationMember = Depends(get_current_org_membership),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Communicates with the custodian's simulated hardware signing device / HSM on Bitcoin Core Regtest.
    The simulated device signs the PSBT with its private key and returns the signed PSBT.
    The main treasury coordinator never touches or stores the private key.
    """
    profile = db.query(SignerProfile).filter(SignerProfile.id == signer_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Signer profile not found")

    # Verify authorization: user must own the signer profile or be an admin of the SAME organization
    if profile.user_id != current_user.id and membership.role != MemberRole.ORG_ADMIN:
        raise HTTPException(status_code=403, detail="You can only trigger signing on your own custodian hardware device.")

    # Multi-tenant check: ensure profile user belongs to the caller's organization
    profile_org_mem = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.user_id == profile.user_id,
            OrganizationMember.organization_id == membership.organization_id
        )
        .first()
    )
    if not profile_org_mem:
        raise HTTPException(status_code=403, detail="Signer does not belong to your active organization.")

    try:
        sign_result = signer_device_service.sign_psbt_with_device(
            signer_id=signer_id,
            psbt_base64=req.psbt_base64
        )
        return sign_result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
