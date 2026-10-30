import json
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from app.models.models import AuditEvent, User

GENESIS_HASH = "0" * 64

class AuditService:
    @staticmethod
    def _compute_event_hash(
        prev_hash: str,
        organization_id: int,
        actor_id: Optional[int],
        event_type: str,
        reference_type: Optional[str],
        reference_id: Optional[str],
        details: Dict[str, Any]
    ) -> str:
        """Computes SHA-256 hash linking the prior hash to all immutable event fields."""
        serialized_details = json.dumps(details or {}, sort_keys=True)
        payload = f"{prev_hash}|{organization_id}|{actor_id}|{event_type}|{reference_type}|{reference_id}|{serialized_details}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def record_event(
        db: Session,
        organization_id: int,
        event_type: str,
        actor_id: Optional[int] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> AuditEvent:
        clean_details = details or {}

        # 1. Fetch latest event for this organization to link the hash chain
        latest_event = (
            db.query(AuditEvent)
            .filter(AuditEvent.organization_id == organization_id)
            .order_by(AuditEvent.id.desc())
            .first()
        )
        prev_hash = latest_event.curr_hash if (latest_event and latest_event.curr_hash) else GENESIS_HASH

        # 2. Compute current event's cryptographic hash
        curr_hash = AuditService._compute_event_hash(
            prev_hash=prev_hash,
            organization_id=organization_id,
            actor_id=actor_id,
            event_type=event_type,
            reference_type=reference_type,
            reference_id=reference_id,
            details=clean_details
        )

        event = AuditEvent(
            organization_id=organization_id,
            actor_id=actor_id,
            event_type=event_type,
            reference_type=reference_type,
            reference_id=reference_id,
            details=clean_details,
            ip_address=ip_address,
            prev_hash=prev_hash,
            curr_hash=curr_hash
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def verify_audit_chain(db: Session, organization_id: int) -> Dict[str, Any]:
        """
        Cryptographically verifies the immutable hash-chain across all historical audit records.
        Returns validation status, total block count, and identifies any tampered records.
        """
        events = (
            db.query(AuditEvent)
            .filter(AuditEvent.organization_id == organization_id)
            .order_by(AuditEvent.id.asc())
            .all()
        )

        if not events:
            return {
                "is_valid": True,
                "total_records": 0,
                "latest_hash": GENESIS_HASH,
                "message": "Audit chain empty - genesis state intact"
            }

        expected_prev_hash = GENESIS_HASH
        for i, event in enumerate(events):
            # Check prev_hash link
            if event.prev_hash and event.prev_hash != expected_prev_hash:
                return {
                    "is_valid": False,
                    "total_records": len(events),
                    "broken_at_id": event.id,
                    "error": f"Hash chain broken at event #{event.id}: prev_hash mismatch (expected {expected_prev_hash[:16]}..., got {event.prev_hash[:16]}...)"
                }

            # Recalculate event hash
            calculated_hash = AuditService._compute_event_hash(
                prev_hash=expected_prev_hash,
                organization_id=event.organization_id,
                actor_id=event.actor_id,
                event_type=event.event_type,
                reference_type=event.reference_type,
                reference_id=event.reference_id,
                details=event.details or {}
            )

            if event.curr_hash and event.curr_hash != calculated_hash:
                return {
                    "is_valid": False,
                    "total_records": len(events),
                    "broken_at_id": event.id,
                    "error": f"Content tampering detected at event #{event.id}: curr_hash mismatch"
                }

            expected_prev_hash = event.curr_hash or calculated_hash

        return {
            "is_valid": True,
            "total_records": len(events),
            "latest_hash": expected_prev_hash,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "message": "Cryptographic hash chain 100% verified. Zero tampering detected."
        }

    @staticmethod
    def get_events(
        db: Session,
        organization_id: int,
        skip: int = 0,
        limit: int = 100,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query = db.query(AuditEvent).filter(AuditEvent.organization_id == organization_id)
        if event_type:
            query = query.filter(AuditEvent.event_type == event_type)
        
        events = query.order_by(AuditEvent.created_at.desc()).offset(skip).limit(limit).all()
        
        results = []
        for e in events:
            actor_name = e.actor.full_name if e.actor else "System"
            results.append({
                "id": e.id,
                "organization_id": e.organization_id,
                "actor_id": e.actor_id,
                "actor_name": actor_name,
                "event_type": e.event_type,
                "reference_type": e.reference_type,
                "reference_id": e.reference_id,
                "details": e.details,
                "ip_address": e.ip_address,
                "prev_hash": e.prev_hash,
                "curr_hash": e.curr_hash,
                "created_at": e.created_at
            })
        return results

audit_service = AuditService()
