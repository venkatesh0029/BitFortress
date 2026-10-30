import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.models import (
    TreasuryWallet, TreasurySigner, SignerProfile, Organization, AuditEvent
)
from app.bitcoin.wallet_service import wallet_service
from app.services.audit_service import audit_service

logger = logging.getLogger("satoshiguard.treasury.service")

class TreasuryService:
    @staticmethod
    def create_treasury_wallet(
        db: Session,
        organization_id: int,
        wallet_name: str,
        threshold: int,
        signer_ids: List[int],
        actor_id: Optional[int] = None
    ) -> TreasuryWallet:
        # Validate unique signers
        if len(set(signer_ids)) != len(signer_ids):
            raise ValueError("All signer profiles assigned to a treasury must be distinct")

        if threshold < 1 or threshold > len(signer_ids):
            raise ValueError(f"Threshold must be between 1 and total signers ({len(signer_ids)})")

        # Fetch signers and their public keys
        signers = db.query(SignerProfile).filter(SignerProfile.id.in_(signer_ids)).all()
        if len(signers) != len(signer_ids):
            raise ValueError("One or more specified signer profiles do not exist")

        pubkeys = [s.public_key for s in signers]

        # Call Bitcoin Core to generate multisig address & redeem script
        multisig_config = wallet_service.create_multisig_config(threshold, pubkeys)

        treasury = TreasuryWallet(
            organization_id=organization_id,
            wallet_name=wallet_name,
            address=multisig_config["address"],
            redeem_script=multisig_config["redeem_script"],
            descriptor=multisig_config["descriptor"],
            threshold=threshold,
            total_signers=len(signer_ids),
            balance_satoshis=0,
            network="regtest",
            status="ACTIVE"
        )
        db.add(treasury)
        db.flush()

        for idx, signer_id in enumerate(signer_ids):
            ts = TreasurySigner(
                wallet_id=treasury.id,
                signer_id=signer_id,
                signer_order=idx
            )
            db.add(ts)

        db.commit()
        db.refresh(treasury)

        # Audit event
        audit_service.record_event(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            event_type="TREASURY_WALLET_CREATED",
            reference_type="TREASURY_WALLET",
            reference_id=str(treasury.id),
            details={
                "wallet_name": wallet_name,
                "address": treasury.address,
                "threshold": threshold,
                "total_signers": len(signer_ids),
                "policy": f"{threshold}-of-{len(signer_ids)}"
            }
        )

        return treasury

    @staticmethod
    def sync_treasury_balance(db: Session, wallet_id: int) -> int:
        treasury = db.query(TreasuryWallet).filter(TreasuryWallet.id == wallet_id).first()
        if not treasury:
            raise ValueError("Treasury wallet not found")

        sats, _ = wallet_service.get_address_balance_satoshis(treasury.address)
        treasury.balance_satoshis = sats
        db.commit()
        db.refresh(treasury)
        return sats

    @staticmethod
    def fund_treasury(db: Session, wallet_id: int, amount_btc: float = 5.0, actor_id: Optional[int] = None) -> Dict[str, Any]:
        treasury = db.query(TreasuryWallet).filter(TreasuryWallet.id == wallet_id).first()
        if not treasury:
            raise ValueError("Treasury wallet not found")

        fund_res = wallet_service.fund_address(treasury.address, amount_btc)
        
        # Sync balance
        TreasuryService.sync_treasury_balance(db, wallet_id)

        # Audit event
        audit_service.record_event(
            db=db,
            organization_id=treasury.organization_id,
            actor_id=actor_id,
            event_type="TREASURY_WALLET_FUNDED",
            reference_type="TREASURY_WALLET",
            reference_id=str(treasury.id),
            details={
                "txid": fund_res["txid"],
                "amount_btc": amount_btc,
                "amount_satoshis": fund_res["amount_satoshis"],
                "address": treasury.address
            }
        )

        return fund_res

treasury_service = TreasuryService()
