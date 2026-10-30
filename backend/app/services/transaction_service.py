import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.models import (
    TransactionProposal, PSBTRecord, TreasuryWallet, ProposalStatus, User,
    TreasurySigner, MemberRole
)
from app.bitcoin.psbt_service import psbt_service
from app.services.treasury_service import treasury_service
from app.services.policy_service import policy_service
from app.services.audit_service import audit_service
from app.services.notification_service import notification_service

logger = logging.getLogger("satoshiguard.transaction.service")

class TransactionService:
    @staticmethod
    def propose_transaction(
        db: Session,
        wallet_id: int,
        proposer_id: int,
        destination: str,
        amount_satoshis: int,
        fee_satoshis: int = 1000,
        description: str = "",
        ip_address: Optional[str] = None
    ) -> TransactionProposal:
        # 1. Fetch wallet
        wallet = db.query(TreasuryWallet).filter(TreasuryWallet.id == wallet_id).first()
        if not wallet:
            raise ValueError("Treasury wallet not found")

        # 2. Check Spending Policy Limits
        is_allowed, violation_reason = policy_service.validate_proposal_against_policies(
            db=db,
            organization_id=wallet.organization_id,
            amount_satoshis=amount_satoshis
        )
        if not is_allowed:
            # Record security/policy audit event
            audit_service.record_event(
                db=db,
                organization_id=wallet.organization_id,
                actor_id=proposer_id,
                event_type="POLICY_VIOLATION_BLOCKED",
                reference_type="SPENDING_POLICY",
                reference_id=str(wallet.id),
                details={
                    "attempted_amount_satoshis": amount_satoshis,
                    "attempted_amount_btc": amount_satoshis / 100_000_000,
                    "destination": destination,
                    "reason": violation_reason
                },
                ip_address=ip_address
            )
            # Notify admins of policy breach attempt
            notification_service.notify_organization_role(
                db=db,
                organization_id=wallet.organization_id,
                role=MemberRole.ORG_ADMIN,
                title="Spending Policy Violation Blocked",
                message=f"A transaction proposal of {amount_satoshis/100_000_000:.4f} BTC was blocked by corporate spending limits.",
                category="WARNING"
            )
            raise ValueError(violation_reason)

        # 3. Refresh & sync on-chain balance
        treasury_service.sync_treasury_balance(db, wallet.id)
        if wallet.balance_satoshis < (amount_satoshis + fee_satoshis):
            raise ValueError(
                f"Treasury balance ({wallet.balance_satoshis:,} sats) is insufficient to fund "
                f"{amount_satoshis:,} sats + {fee_satoshis:,} sats fee."
            )

        # 4. Generate PSBT through Bitcoin Core
        psbt_data = psbt_service.create_multisig_psbt(
            multisig_address=wallet.address,
            redeem_script=wallet.redeem_script or "",
            descriptor=wallet.descriptor or "",
            destination_address=destination,
            amount_satoshis=amount_satoshis,
            fee_satoshis=fee_satoshis
        )

        unsigned_psbt = psbt_data["psbt_base64"]

        # 5. Persist TransactionProposal
        proposal = TransactionProposal(
            wallet_id=wallet_id,
            proposer_id=proposer_id,
            destination=destination,
            amount=amount_satoshis,
            fee_satoshis=fee_satoshis,
            description=description,
            status=ProposalStatus.PENDING
        )
        db.add(proposal)
        db.flush()

        # 6. Persist PSBTRecord
        psbt_record = PSBTRecord(
            proposal_id=proposal.id,
            unsigned_psbt=unsigned_psbt,
            current_psbt=unsigned_psbt
        )
        db.add(psbt_record)
        db.commit()
        db.refresh(proposal)

        # 7. Audit Event
        audit_service.record_event(
            db=db,
            organization_id=wallet.organization_id,
            actor_id=proposer_id,
            event_type="TRANSACTION_PROPOSED",
            reference_type="PROPOSAL",
            reference_id=str(proposal.id),
            details={
                "amount_satoshis": amount_satoshis,
                "amount_btc": amount_satoshis / 100_000_000,
                "destination": destination,
                "description": description,
                "required_threshold": wallet.threshold,
                "total_signers": wallet.total_signers
            },
            ip_address=ip_address
        )

        # 8. Notify assigned signers
        assigned_signers = db.query(TreasurySigner).filter(TreasurySigner.wallet_id == wallet.id).all()
        for ts in assigned_signers:
            if ts.signer and ts.signer.user_id != proposer_id:
                notification_service.notify_user(
                    db=db,
                    user_id=ts.signer.user_id,
                    title="Signature Required",
                    message=f"New treasury transfer proposal #{proposal.id} for {amount_satoshis/100_000_000:.4f} BTC awaits your review and signature.",
                    category="ACTION_REQUIRED"
                )

        return proposal

transaction_service = TransactionService()
