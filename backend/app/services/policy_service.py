from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.models import SpendingPolicy, TransactionProposal, ProposalStatus

class PolicyService:
    @staticmethod
    def get_or_create_policy(db: Session, organization_id: int) -> SpendingPolicy:
        policy = db.query(SpendingPolicy).filter(SpendingPolicy.organization_id == organization_id).first()
        if not policy:
            # Default: 0.5 BTC per transaction (50,000,000 sats), 2.0 BTC daily (200,000,000 sats)
            policy = SpendingPolicy(
                organization_id=organization_id,
                per_transaction_limit=50_000_000,
                daily_limit=200_000_000,
                require_admin_override=True,
                is_active=True
            )
            db.add(policy)
            db.commit()
            db.refresh(policy)
        return policy

    @staticmethod
    def validate_proposal_against_policies(
        db: Session,
        organization_id: int,
        amount_satoshis: int
    ) -> Tuple[bool, Optional[str]]:
        policy = PolicyService.get_or_create_policy(db, organization_id)
        if not policy.is_active:
            return True, None

        # 1. Per-transaction limit check
        if amount_satoshis > policy.per_transaction_limit:
            limit_btc = policy.per_transaction_limit / 100_000_000
            req_btc = amount_satoshis / 100_000_000
            return False, f"Proposed amount ({req_btc:.4f} BTC) exceeds per-transaction spending limit of {limit_btc:.4f} BTC ({policy.per_transaction_limit:,} sats)."

        # 2. Daily spending limit check (proposals in past 24 hours that are pending, approved, or broadcast)
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        daily_spent_query = db.query(func.coalesce(func.sum(TransactionProposal.amount), 0)).join(
            TransactionProposal.wallet
        ).filter(
            TransactionProposal.created_at >= since,
            TransactionProposal.status.in_([
                ProposalStatus.PENDING,
                ProposalStatus.APPROVED,
                ProposalStatus.FINALIZED,
                ProposalStatus.BROADCAST,
                ProposalStatus.CONFIRMED
            ])
        ).scalar()

        total_daily_would_be = (daily_spent_query or 0) + amount_satoshis
        if total_daily_would_be > policy.daily_limit:
            limit_btc = policy.daily_limit / 100_000_000
            current_btc = (daily_spent_query or 0) / 100_000_000
            would_be_btc = total_daily_would_be / 100_000_000
            return False, (
                f"Proposed transaction would breach the 24-hour daily volume limit of {limit_btc:.4f} BTC. "
                f"Already committed in past 24h: {current_btc:.4f} BTC; New total would be: {would_be_btc:.4f} BTC."
            )

        return True, None

policy_service = PolicyService()
