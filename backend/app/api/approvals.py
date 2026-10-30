from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.models import (
    TransactionProposal, SignerProfile, TreasurySigner, Approval, User,
    ProposalStatus, MemberRole
)
from app.schemas.schemas import SignApprovalRequest, RejectApprovalRequest, ProposalResponse
from app.services.approval_service import approval_service
from app.api.transactions import serialize_proposal

router = APIRouter(prefix="/approvals", tags=["Approvals"])

@router.get("/pending", response_model=List[ProposalResponse])
def get_pending_approvals(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Find all signer profiles for this user
    signer_profiles = db.query(SignerProfile).filter(SignerProfile.user_id == current_user.id).all()
    signer_ids = [s.id for s in signer_profiles]

    # Find treasury wallets assigned to these signers
    assigned_wallets = db.query(TreasurySigner.wallet_id).filter(
        TreasurySigner.signer_id.in_(signer_ids)
    ).subquery()

    # Find pending proposals in these wallets that have NOT yet been decided by this signer
    pending_proposals = db.query(TransactionProposal).filter(
        TransactionProposal.wallet_id.in_(assigned_wallets),
        TransactionProposal.status == ProposalStatus.PENDING
    ).all()

    results = []
    for p in pending_proposals:
        # Check if already decided
        already_decided = db.query(Approval).filter(
            Approval.proposal_id == p.id,
            Approval.signer_id.in_(signer_ids)
        ).first()

        if not already_decided:
            results.append(serialize_proposal(p, db))

    return results

@router.post("/sign")
def sign_proposal(
    req: SignApprovalRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip_addr = request.client.host if request.client else "127.0.0.1"
    try:
        res = approval_service.approve_proposal(
            db=db,
            proposal_id=req.proposal_id,
            user_id=current_user.id,
            signed_psbt=req.signed_psbt,
            signature_reference=req.signature_reference,
            ip_address=ip_addr
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/reject")
def reject_proposal(
    req: RejectApprovalRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not req.reason or len(req.reason.strip()) < 3:
        raise HTTPException(status_code=400, detail="A valid business reason for rejection is required")

    ip_addr = request.client.host if request.client else "127.0.0.1"
    try:
        res = approval_service.reject_proposal(
            db=db,
            proposal_id=req.proposal_id,
            user_id=current_user.id,
            reason=req.reason.strip(),
            ip_address=ip_addr
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
