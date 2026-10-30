from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.models import (
    TreasuryWallet, OrganizationMember, MemberRole, User, TreasurySigner
)
from app.schemas.schemas import TreasuryCreate, TreasuryResponse, TreasurySignerInfo, FundTreasuryRequest
from app.services.treasury_service import treasury_service

router = APIRouter(prefix="/treasury", tags=["Treasury"])

def serialize_wallet(w: TreasuryWallet) -> TreasuryResponse:
    signers_info = []
    for ts in w.signers:
        s = ts.signer
        signers_info.append(TreasurySignerInfo(
            signer_id=s.id,
            label=s.label,
            public_key=s.public_key,
            user_name=s.user.full_name if s.user else "Unknown"
        ))

    return TreasuryResponse(
        id=w.id,
        organization_id=w.organization_id,
        wallet_name=w.wallet_name,
        address=w.address,
        threshold=w.threshold,
        total_signers=w.total_signers,
        descriptor=w.descriptor,
        redeem_script=w.redeem_script,
        balance_satoshis=w.balance_satoshis,
        balance_btc=round(w.balance_satoshis / 100_000_000, 8),
        network=w.network,
        status=w.status,
        created_at=w.created_at,
        signers=signers_info
    )

@router.get("", response_model=List[TreasuryResponse])
def get_treasury_wallets(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    membership = db.query(OrganizationMember).filter(OrganizationMember.user_id == current_user.id).first()
    if not membership:
        raise HTTPException(status_code=404, detail="No organization associated with this user")

    wallets = db.query(TreasuryWallet).filter(TreasuryWallet.organization_id == membership.organization_id).all()
    # Auto sync balances
    results = []
    for w in wallets:
        try:
            treasury_service.sync_treasury_balance(db, w.id)
        except Exception:
            pass
        results.append(serialize_wallet(w))
    return results

@router.get("/{wallet_id}", response_model=TreasuryResponse)
def get_treasury_wallet(wallet_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    w = db.query(TreasuryWallet).filter(TreasuryWallet.id == wallet_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Treasury wallet not found")

    try:
        treasury_service.sync_treasury_balance(db, w.id)
    except Exception:
        pass

    return serialize_wallet(w)

@router.post("", response_model=TreasuryResponse)
def create_treasury(
    treasury_in: TreasuryCreate,
    current_user: User = Depends(get_current_user),
    _ = Depends(require_role([MemberRole.ORG_ADMIN, MemberRole.FINANCE_MANAGER])),
    db: Session = Depends(get_db)
):
    membership = db.query(OrganizationMember).filter(OrganizationMember.user_id == current_user.id).first()
    try:
        wallet = treasury_service.create_treasury_wallet(
            db=db,
            organization_id=membership.organization_id,
            wallet_name=treasury_in.wallet_name,
            threshold=treasury_in.threshold,
            signer_ids=treasury_in.signer_ids,
            actor_id=current_user.id
        )
        return serialize_wallet(wallet)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{wallet_id}/fund")
def fund_treasury_wallet(
    wallet_id: int,
    fund_in: FundTreasuryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        res = treasury_service.fund_treasury(
            db=db,
            wallet_id=wallet_id,
            amount_btc=fund_in.amount_btc,
            actor_id=current_user.id
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{wallet_id}/sync")
def sync_treasury(wallet_id: int, db: Session = Depends(get_db)):
    try:
        sats = treasury_service.sync_treasury_balance(db, wallet_id)
        return {"wallet_id": wallet_id, "balance_satoshis": sats, "balance_btc": sats / 100_000_000}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
