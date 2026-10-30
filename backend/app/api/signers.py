from typing import List, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import SignerProfile, User
from app.schemas.schemas import SignerProfileCreate, SignerProfileResponse
from app.bitcoin.keys import generate_keypair
from app.services.signer_device_service import signer_device_service
from app.services.audit_service import audit_service

router = APIRouter(prefix="/signers", tags=["Signers"])

class DeviceSignRequest(BaseModel):
    psbt_base64: str

@router.get("", response_model=List[SignerProfileResponse])
def list_signers(db: Session = Depends(get_db)):
    profiles = db.query(SignerProfile).filter(SignerProfile.status == "ACTIVE").all()
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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
def generate_secp256k1_keypair():
    """Generates a secp256k1 keypair for development, demo, or testing."""
    kp = generate_keypair()
    return kp

@router.post("/{signer_id}/device-sign")
def sign_with_custodian_device(
    signer_id: int,
    req: DeviceSignRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Communicates with the custodian's isolated hardware signing device / HSM.
    The hardware device signs the PSBT with its private key and returns the signed PSBT.
    The main treasury coordinator never touches or stores the private key.
    """
    profile = db.query(SignerProfile).filter(SignerProfile.id == signer_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Signer profile not found")

    # Verify authorization: user must own the signer profile or be an admin
    if profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only trigger signing on your own custodian hardware device.")

    try:
        sign_result = signer_device_service.sign_psbt_with_device(
            signer_id=signer_id,
            psbt_base64=req.psbt_base64
        )
        return sign_result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
