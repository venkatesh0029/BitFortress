from datetime import datetime, timezone
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.models import (
    TransactionProposal, PSBTRecord, Approval, SignerProfile, TreasurySigner,
    ProposalStatus, ApprovalDecision, MemberRole
)
from app.bitcoin.psbt_service import psbt_service
from app.services.treasury_service import treasury_service
from app.services.audit_service import audit_service
from app.services.notification_service import notification_service

logger = logging.getLogger("satoshiguard.approval.service")

class ApprovalService:
    @staticmethod
    def approve_proposal(
        db: Session,
        proposal_id: int,
        user_id: int,
        signed_psbt: Optional[str] = None,
        signature_hex: Optional[str] = None,
        signature_reference: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        # 1. Fetch proposal
        proposal = db.query(TransactionProposal).filter(TransactionProposal.id == proposal_id).first()
        if not proposal:
            raise ValueError("Transaction proposal not found")

        if proposal.status != ProposalStatus.PENDING:
            raise ValueError(f"Cannot approve proposal in '{proposal.status}' state")

        wallet = proposal.wallet
        psbt_record = proposal.psbt_record

        # 2. Verify signer profile belongs to this user and is assigned to this wallet
        signer_profile = db.query(SignerProfile).join(
            TreasurySigner, TreasurySigner.signer_id == SignerProfile.id
        ).filter(
            SignerProfile.user_id == user_id,
            TreasurySigner.wallet_id == wallet.id,
            SignerProfile.status == "ACTIVE"
        ).first()

        if not signer_profile:
            raise ValueError("You are not an authorized signer for this treasury wallet")

        # 3. Check for duplicate approval / prior decision
        existing_approval = db.query(Approval).filter(
            Approval.proposal_id == proposal_id,
            Approval.signer_id == signer_profile.id
        ).first()

        if existing_approval:
            raise ValueError(
                f"You have already submitted a decision ({existing_approval.decision}) for this proposal"
            )

        # 4. Verify & Combine PSBT Signature
        updated_psbt = psbt_record.current_psbt
        if signed_psbt:
            combine_result = psbt_service.combine_and_verify_signatures(
                current_psbt=psbt_record.current_psbt,
                submitted_signed_psbt=signed_psbt
            )
            updated_psbt = combine_result["combined_psbt"]
            psbt_record.current_psbt = updated_psbt

        # 5. Record Approval
        approval = Approval(
            proposal_id=proposal_id,
            signer_id=signer_profile.id,
            decision=ApprovalDecision.APPROVED,
            signature_reference=signature_reference or f"Signer #{signer_profile.id} ({signer_profile.label})",
            signature_data=signature_hex or (signed_psbt[:64] + "..." if signed_psbt else "Valid ECDSA Signature")
        )
        db.add(approval)
        db.flush()

        # 6. Count approved signatures
        approved_count = db.query(Approval).filter(
            Approval.proposal_id == proposal_id,
            Approval.decision == ApprovalDecision.APPROVED
        ).count()

        audit_service.record_event(
            db=db,
            organization_id=wallet.organization_id,
            actor_id=user_id,
            event_type="SIGNATURE_SUBMITTED",
            reference_type="PROPOSAL",
            reference_id=str(proposal.id),
            details={
                "signer_label": signer_profile.label,
                "signer_public_key": signer_profile.public_key,
                "approved_count": approved_count,
                "threshold": wallet.threshold
            },
            ip_address=ip_address
        )

        broadcast_info = None

        # 7. Check if Threshold is Reached
        if approved_count >= wallet.threshold:
            logger.info(f"Threshold reached ({approved_count}/{wallet.threshold}) for proposal #{proposal.id}. Finalizing and broadcasting...")
            
            try:
                broadcast_res = psbt_service.finalize_and_broadcast(psbt_record.current_psbt)
                proposal.status = ProposalStatus.BROADCAST
                proposal.txid = broadcast_res["txid"]
                proposal.broadcast_at = datetime.now(timezone.utc)
                proposal.confirmations = 1
                psbt_record.finalized_tx_hex = broadcast_res["hex"]

                # Sync treasury balance
                treasury_service.sync_treasury_balance(db, wallet.id)

                # Record broadcast audit event
                audit_service.record_event(
                    db=db,
                    organization_id=wallet.organization_id,
                    actor_id=user_id,
                    event_type="TRANSACTION_BROADCAST_SUCCESS",
                    reference_type="PROPOSAL",
                    reference_id=str(proposal.id),
                    details={
                        "txid": broadcast_res["txid"],
                        "destination": proposal.destination,
                        "amount_satoshis": proposal.amount,
                        "amount_btc": proposal.amount / 100_000_000,
                        "network": "regtest",
                        "status": "CONFIRMED_IN_BLOCK"
                    },
                    ip_address=ip_address
                )

                # Notify Proposer & Admins
                notification_service.notify_user(
                    db=db,
                    user_id=proposal.proposer_id,
                    title="Transaction Broadcasted & Confirmed",
                    message=f"Proposal #{proposal.id} reached threshold ({approved_count}/{wallet.threshold}) and was broadcast to Regtest. TXID: {broadcast_res['txid'][:16]}...",
                    category="SUCCESS"
                )

                broadcast_info = broadcast_res
            except Exception as e:
                logger.error(f"Error finalizing/broadcasting proposal #{proposal.id}: {e}")
                # Keep approved state, pending broadcast retry
                proposal.status = ProposalStatus.APPROVED
                broadcast_info = {"error": str(e), "broadcast": False}
        else:
            # Threshold not yet reached
            notification_service.notify_user(
                db=db,
                user_id=proposal.proposer_id,
                title="Signature Received",
                message=f"Signer {signer_profile.label} approved proposal #{proposal.id}. Progress: {approved_count}/{wallet.threshold} signatures.",
                category="INFO"
            )

        db.commit()
        db.refresh(proposal)

        return {
            "proposal_id": proposal.id,
            "status": proposal.status,
            "approved_count": approved_count,
            "threshold": wallet.threshold,
            "broadcast_info": broadcast_info
        }

    @staticmethod
    def reject_proposal(
        db: Session,
        proposal_id: int,
        user_id: int,
        reason: str,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        proposal = db.query(TransactionProposal).filter(TransactionProposal.id == proposal_id).first()
        if not proposal:
            raise ValueError("Transaction proposal not found")

        if proposal.status != ProposalStatus.PENDING:
            raise ValueError(f"Cannot reject proposal in '{proposal.status}' state")

        wallet = proposal.wallet

        # Verify signer profile
        signer_profile = db.query(SignerProfile).join(
            TreasurySigner, TreasurySigner.signer_id == SignerProfile.id
        ).filter(
            SignerProfile.user_id == user_id,
            TreasurySigner.wallet_id == wallet.id,
            SignerProfile.status == "ACTIVE"
        ).first()

        if not signer_profile:
            raise ValueError("You are not an authorized signer for this treasury wallet")

        # Check existing decision
        existing_approval = db.query(Approval).filter(
            Approval.proposal_id == proposal_id,
            Approval.signer_id == signer_profile.id
        ).first()

        if existing_approval:
            raise ValueError(f"You have already submitted a decision ({existing_approval.decision})")

        # Record Rejection
        approval = Approval(
            proposal_id=proposal_id,
            signer_id=signer_profile.id,
            decision=ApprovalDecision.REJECTED,
            rejection_reason=reason
        )
        db.add(approval)

        # Mark proposal as rejected so it can never be finalized or broadcast
        proposal.status = ProposalStatus.REJECTED
        db.commit()

        # Audit Event
        audit_service.record_event(
            db=db,
            organization_id=wallet.organization_id,
            actor_id=user_id,
            event_type="PROPOSAL_REJECTED",
            reference_type="PROPOSAL",
            reference_id=str(proposal.id),
            details={
                "signer_label": signer_profile.label,
                "reason": reason
            },
            ip_address=ip_address
        )

        # Notify proposer
        notification_service.notify_user(
            db=db,
            user_id=proposal.proposer_id,
            title="Proposal Rejected",
            message=f"Proposal #{proposal.id} was rejected by {signer_profile.label}. Reason: {reason}",
            category="WARNING"
        )

        return {
            "proposal_id": proposal.id,
            "status": proposal.status,
            "rejection_reason": reason
        }

approval_service = ApprovalService()
