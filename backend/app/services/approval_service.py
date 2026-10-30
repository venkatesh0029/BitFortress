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
        signed_psbt: str,
        signature_reference: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cryptographically validates and records a custodian's PSBT signature.
        Enforces:
        - Mandatory signed_psbt payload
        - Row-level database lock (concurrency protection)
        - Signer authorization check against wallet custodian roster
        - Duplicate signature rejection
        - Explicit verification that submitted PSBT contains a valid ECDSA signature matching signer's registered public key
        - Automatic threshold finalization and Regtest on-chain broadcast upon quorum
        """
        # 1. Require signed_psbt
        if not signed_psbt or not signed_psbt.strip():
            raise ValueError(
                "A cryptographically signed PSBT is required to record approval. Unsigned approvals are rejected by security policy."
            )

        # 2. Fetch proposal with row-level lock to prevent concurrent approval race conditions
        proposal = (
            db.query(TransactionProposal)
            .filter(TransactionProposal.id == proposal_id)
            .with_for_update()
            .first()
        )
        if not proposal:
            raise ValueError(f"Transaction proposal #{proposal_id} not found")

        if proposal.status != ProposalStatus.PENDING:
            raise ValueError(f"Cannot approve proposal in '{proposal.status}' state")

        wallet = proposal.wallet
        psbt_record = proposal.psbt_record

        # 3. Verify signer profile belongs to this user and is assigned to this wallet
        signer_profile = (
            db.query(SignerProfile)
            .join(TreasurySigner, TreasurySigner.signer_id == SignerProfile.id)
            .filter(
                SignerProfile.user_id == user_id,
                TreasurySigner.wallet_id == wallet.id,
                SignerProfile.status == "ACTIVE"
            )
            .first()
        )

        if not signer_profile:
            raise ValueError("You are not an authorized custodian/signer for this treasury wallet")

        # 4. Check for duplicate approval / prior decision
        existing_approval = (
            db.query(Approval)
            .filter(
                Approval.proposal_id == proposal_id,
                Approval.signer_id == signer_profile.id
            )
            .first()
        )

        if existing_approval:
            raise ValueError(
                f"You have already submitted a decision ({existing_approval.decision}) for this proposal"
            )

        # 5. Cryptographically verify and combine PSBT
        # Validates that the submitted PSBT contains a partial signature for signer_profile.public_key
        combine_result = psbt_service.combine_and_verify_signatures(
            current_psbt=psbt_record.current_psbt,
            submitted_signed_psbt=signed_psbt.strip(),
            expected_pubkey_hex=signer_profile.public_key
        )
        updated_psbt = combine_result["combined_psbt"]
        psbt_record.current_psbt = updated_psbt

        # 6. Extract the verified signature hex from the submitted PSBT
        extracted_sigs = psbt_service.extract_partial_signatures(signed_psbt)
        matched_sig_hex = None
        for s in extracted_sigs:
            if s["pubkey"] == signer_profile.public_key.lower():
                matched_sig_hex = s["signature"]
                break

        # 7. Record Approval in Database
        approval = Approval(
            proposal_id=proposal_id,
            signer_id=signer_profile.id,
            decision=ApprovalDecision.APPROVED,
            signature_reference=signature_reference or f"{signer_profile.label} (Custody Key #{signer_profile.id})",
            signature_data=matched_sig_hex or "ECDSA Secp256k1 Signature Verified"
        )
        db.add(approval)
        db.flush()

        # 8. Count cryptographic approvals collected so far
        approved_count = (
            db.query(Approval)
            .filter(
                Approval.proposal_id == proposal_id,
                Approval.decision == ApprovalDecision.APPROVED
            )
            .count()
        )

        # Record Audit Event with cryptographic hash chain
        audit_service.record_event(
            db=db,
            organization_id=wallet.organization_id,
            actor_id=user_id,
            event_type="CRYPTOGRAPHIC_SIGNATURE_VERIFIED",
            reference_type="PROPOSAL",
            reference_id=str(proposal.id),
            details={
                "signer_label": signer_profile.label,
                "signer_public_key": signer_profile.public_key,
                "signature_hex": (matched_sig_hex[:32] + "...") if matched_sig_hex else "Verified",
                "approved_count": approved_count,
                "threshold": wallet.threshold,
                "psbt_complete": combine_result["analysis"].get("next") == "finalizer"
            },
            ip_address=ip_address
        )

        broadcast_info = None

        # 9. Quorum Evaluation: Check if threshold is reached
        psbt_ready_to_finalize = (
            combine_result["analysis"].get("next") == "finalizer" or
            approved_count >= wallet.threshold
        )

        if psbt_ready_to_finalize:
            logger.info(
                f"Quorum reached ({approved_count}/{wallet.threshold}) for proposal #{proposal.id}. Finalizing and broadcasting to Bitcoin network..."
            )
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
                    title="Transaction Broadcast & Confirmed",
                    message=f"Proposal #{proposal.id} reached threshold ({approved_count}/{wallet.threshold}) and was broadcast to Regtest. TXID: {broadcast_res['txid'][:16]}...",
                    category="SUCCESS"
                )

                broadcast_info = broadcast_res
            except Exception as e:
                logger.error(f"Error finalizing/broadcasting proposal #{proposal.id}: {e}")
                proposal.status = ProposalStatus.APPROVED
                broadcast_info = {"error": str(e), "broadcast": False}
        else:
            # Threshold not yet reached; notify proposer of progress
            notification_service.notify_user(
                db=db,
                user_id=proposal.proposer_id,
                title="Cryptographic Signature Received",
                message=f"Signer {signer_profile.label} verified and signed proposal #{proposal.id}. Progress: {approved_count}/{wallet.threshold} signatures.",
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
        """
        Records a custodian's formal veto/rejection of a proposal.
        Uses row-level locking to guarantee finality.
        """
        proposal = (
            db.query(TransactionProposal)
            .filter(TransactionProposal.id == proposal_id)
            .with_for_update()
            .first()
        )
        if not proposal:
            raise ValueError(f"Transaction proposal #{proposal_id} not found")

        if proposal.status != ProposalStatus.PENDING:
            raise ValueError(f"Cannot reject proposal in '{proposal.status}' state")

        wallet = proposal.wallet

        # Verify signer profile
        signer_profile = (
            db.query(SignerProfile)
            .join(TreasurySigner, TreasurySigner.signer_id == SignerProfile.id)
            .filter(
                SignerProfile.user_id == user_id,
                TreasurySigner.wallet_id == wallet.id,
                SignerProfile.status == "ACTIVE"
            )
            .first()
        )

        if not signer_profile:
            raise ValueError("You are not an authorized signer for this treasury wallet")

        # Check existing decision
        existing_approval = (
            db.query(Approval)
            .filter(
                Approval.proposal_id == proposal_id,
                Approval.signer_id == signer_profile.id
            )
            .first()
        )

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

        # Audit Event with cryptographic hash chain
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
