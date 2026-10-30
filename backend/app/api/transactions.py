from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.models import (
    TransactionProposal, PSBTRecord, Approval, User, MemberRole, ApprovalDecision,
    TreasuryWallet, TreasurySigner
)
from app.schemas.schemas import (
    ProposalCreate, ProposalResponse, ProposalDetailResponse, ApprovalResponse,
    TreasurySignerInfo
)
from app.services.transaction_service import transaction_service

router = APIRouter(prefix="/transactions", tags=["Transactions"])

def serialize_proposal(p: TransactionProposal, db: Session) -> ProposalResponse:
    approvals = db.query(Approval).filter(Approval.proposal_id == p.id).all()
    approved_count = sum(1 for a in approvals if a.decision == ApprovalDecision.APPROVED)
    rejected_count = sum(1 for a in approvals if a.decision == ApprovalDecision.REJECTED)

    return ProposalResponse(
        id=p.id,
        wallet_id=p.wallet_id,
        wallet_name=p.wallet.wallet_name if p.wallet else "Treasury",
        proposer_id=p.proposer_id,
        proposer_name=p.proposer.full_name if p.proposer else "Unknown",
        destination=p.destination,
        amount_satoshis=p.amount,
        amount_btc=round(p.amount / 100_000_000, 8),
        fee_satoshis=p.fee_satoshis,
        description=p.description,
        status=p.status,
        txid=p.txid,
        broadcast_at=p.broadcast_at,
        confirmations=p.confirmations,
        threshold=p.wallet.threshold if p.wallet else 2,
        approvals_count=approved_count,
        rejections_count=rejected_count,
        created_at=p.created_at,
        updated_at=p.updated_at
    )

@router.get("", response_model=List[ProposalResponse])
def get_transactions(
    wallet_id: Optional[int] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(TransactionProposal)
    if wallet_id:
        query = query.filter(TransactionProposal.wallet_id == wallet_id)
    if status:
        query = query.filter(TransactionProposal.status == status)

    proposals = query.order_by(TransactionProposal.created_at.desc()).all()
    return [serialize_proposal(p, db) for p in proposals]

@router.get("/{proposal_id}", response_model=ProposalDetailResponse)
def get_transaction_detail(proposal_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.query(TransactionProposal).filter(TransactionProposal.id == proposal_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")

    base = serialize_proposal(p, db)
    psbt_rec = p.psbt_record

    approvals = db.query(Approval).filter(Approval.proposal_id == p.id).all()
    app_responses = []
    for a in approvals:
        signer = a.signer
        app_responses.append(ApprovalResponse(
            id=a.id,
            signer_id=a.signer_id,
            signer_name=signer.user.full_name if signer and signer.user else "Signer",
            signer_label=signer.label if signer else "Signer",
            public_key=signer.public_key if signer else "",
            decision=a.decision,
            signature_reference=a.signature_reference,
            rejection_reason=a.rejection_reason,
            created_at=a.created_at
        ))

    # Assigned signers for this wallet
    signers_info = []
    for ts in p.wallet.signers:
        s = ts.signer
        signers_info.append(TreasurySignerInfo(
            signer_id=s.id,
            label=s.label,
            public_key=s.public_key,
            user_name=s.user.full_name if s.user else "Signer"
        ))

    return ProposalDetailResponse(
        **base.dict(),
        unsigned_psbt=psbt_rec.unsigned_psbt if psbt_rec else None,
        current_psbt=psbt_rec.current_psbt if psbt_rec else None,
        finalized_tx_hex=psbt_rec.finalized_tx_hex if psbt_rec else None,
        approvals=app_responses,
        signers=signers_info
    )

@router.post("", response_model=ProposalResponse)
def propose_transaction(
    proposal_in: ProposalCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    _ = Depends(require_role([MemberRole.ORG_ADMIN, MemberRole.FINANCE_MANAGER])),
    db: Session = Depends(get_db)
):
    ip_addr = request.client.host if request.client else "127.0.0.1"
    try:
        proposal = transaction_service.propose_transaction(
            db=db,
            wallet_id=proposal_in.wallet_id,
            proposer_id=current_user.id,
            destination=proposal_in.destination.strip(),
            amount_satoshis=proposal_in.amount_satoshis,
            fee_satoshis=proposal_in.fee_satoshis or 1000,
            description=proposal_in.description.strip(),
            ip_address=ip_addr
        )
        return serialize_proposal(proposal, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
