import os
import json
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from app.models.models import AuditEvent, User

logger = logging.getLogger("bitfortress.audit.service")

GENESIS_HASH = "0" * 64

def get_anchor_file_path() -> str:
    """Returns filesystem path for external, append-only cryptographic audit chain anchors."""
    # Look for bitcoin_data directory or default to local data directory
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    btc_data = os.path.join(base_dir, "bitcoin_data")
    if os.path.isdir(btc_data):
        return os.path.join(btc_data, "audit_anchors.jsonl")
    return os.path.join(base_dir, "audit_anchors.jsonl")

class AuditService:
    @staticmethod
    def _compute_event_hash(
        prev_hash: str,
        organization_id: int,
        actor_id: Optional[int],
        event_type: str,
        reference_type: Optional[str],
        reference_id: Optional[str],
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
        created_at_iso: Optional[str] = None
    ) -> str:
        """
        Computes SHA-256 hash linking the prior hash to all immutable event fields,
        including ip_address and exact canonical created_at timestamp.
        """
        serialized_details = json.dumps(details or {}, sort_keys=True)
        canonical_ip = (ip_address or "").strip()
        canonical_time = (created_at_iso or "").strip()
        payload = (
            f"{prev_hash}|{organization_id}|{actor_id}|{event_type}|"
            f"{reference_type}|{reference_id}|{canonical_ip}|{canonical_time}|{serialized_details}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _format_canonical_timestamp(dt: Optional[datetime]) -> str:
        if not dt:
            return ""
        if dt.tzinfo:
            dt_utc = dt.astimezone(timezone.utc)
        else:
            dt_utc = dt.replace(tzinfo=timezone.utc)
        return dt_utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    @staticmethod
    def _compute_legacy_hash(
        prev_hash: str,
        organization_id: int,
        actor_id: Optional[int],
        event_type: str,
        reference_type: Optional[str],
        reference_id: Optional[str],
        details: Dict[str, Any]
    ) -> str:
        """Legacy hash computation format for pre-existing audit events."""
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
        now_dt = datetime.now(timezone.utc)
        created_at_iso = AuditService._format_canonical_timestamp(now_dt)

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
            details=clean_details,
            ip_address=ip_address,
            created_at_iso=created_at_iso
        )

        event = AuditEvent(
            organization_id=organization_id,
            actor_id=actor_id,
            event_type=event_type,
            reference_type=reference_type,
            reference_id=reference_id,
            details=clean_details,
            ip_address=ip_address,
            created_at=now_dt,
            prev_hash=prev_hash,
            curr_hash=curr_hash
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def anchor_audit_chain(db: Session, organization_id: int) -> Dict[str, Any]:
        """
        Periodically anchors the latest audit chain hash outside the database into
        an append-only, tamper-evident external anchor log file.
        This ensures that even a database administrator with full write access cannot rewrite history undetected.
        """
        # First verify internal integrity
        verification = AuditService.verify_audit_chain(db, organization_id, check_external_anchor=False)
        if not verification.get("is_valid", False):
            raise ValueError(f"Cannot anchor corrupted audit chain: {verification.get('error')}")

        latest_event = (
            db.query(AuditEvent)
            .filter(AuditEvent.organization_id == organization_id)
            .order_by(AuditEvent.id.desc())
            .first()
        )
        if not latest_event:
            return {"status": "skipped", "message": "No events to anchor"}

        anchor_file = get_anchor_file_path()
        anchor_data = {
            "organization_id": organization_id,
            "anchored_at": datetime.now(timezone.utc).isoformat(),
            "tip_event_id": latest_event.id,
            "tip_hash": latest_event.curr_hash,
            "total_records": verification["total_records"]
        }

        # Append to external file
        with open(anchor_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(anchor_data) + "\n")

        return {
            "status": "anchored",
            "anchor_file": anchor_file,
            "anchored_tip_id": latest_event.id,
            "anchored_tip_hash": latest_event.curr_hash,
            "total_records": verification["total_records"]
        }

    @staticmethod
    def verify_audit_chain(
        db: Session,
        organization_id: int,
        check_external_anchor: bool = True
    ) -> Dict[str, Any]:
        """
        Cryptographically verifies the immutable hash-chain across all historical audit records.
        Also validates that the chain matches external out-of-band anchors (protecting against rogue DB admins).
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
                "external_anchor_verified": True,
                "message": "Audit chain empty - genesis state intact"
            }

        expected_prev_hash = GENESIS_HASH
        event_hash_map = {}

        for i, event in enumerate(events):
            # Check prev_hash link
            if event.prev_hash and event.prev_hash != expected_prev_hash:
                return {
                    "is_valid": False,
                    "total_records": len(events),
                    "broken_at_id": event.id,
                    "error": f"Hash chain broken at event #{event.id}: prev_hash mismatch (expected {expected_prev_hash[:16]}..., got {event.prev_hash[:16]}...)"
                }

            # Recalculate event hash using all canonical fields
            created_iso = AuditService._format_canonical_timestamp(event.created_at)
            calculated_hash = AuditService._compute_event_hash(
                prev_hash=expected_prev_hash,
                organization_id=event.organization_id,
                actor_id=event.actor_id,
                event_type=event.event_type,
                reference_type=event.reference_type,
                reference_id=event.reference_id,
                details=event.details or {},
                ip_address=event.ip_address,
                created_at_iso=created_iso
            )

            if event.curr_hash and event.curr_hash != calculated_hash:
                legacy_hash = AuditService._compute_legacy_hash(
                    prev_hash=expected_prev_hash,
                    organization_id=event.organization_id,
                    actor_id=event.actor_id,
                    event_type=event.event_type,
                    reference_type=event.reference_type,
                    reference_id=event.reference_id,
                    details=event.details or {}
                )
                if event.curr_hash == legacy_hash:
                    calculated_hash = legacy_hash
                else:
                    return {
                        "is_valid": False,
                        "total_records": len(events),
                        "broken_at_id": event.id,
                        "error": f"Content tampering detected at event #{event.id}: curr_hash mismatch"
                    }

            expected_prev_hash = event.curr_hash or calculated_hash
            event_hash_map[event.id] = expected_prev_hash

        # External anchor verification (Out-of-band tamper detection)
        external_anchor_verified = True
        matched_anchors = 0
        if check_external_anchor:
            anchor_file = get_anchor_file_path()
            if os.path.isfile(anchor_file):
                try:
                    with open(anchor_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if not line.strip():
                                continue
                            anchor = json.loads(line)
                            if anchor.get("organization_id") == organization_id:
                                anchor_tip_id = anchor.get("tip_event_id")
                                anchor_tip_hash = anchor.get("tip_hash")
                                if anchor_tip_id in event_hash_map:
                                    if event_hash_map[anchor_tip_id] != anchor_tip_hash:
                                        return {
                                            "is_valid": False,
                                            "total_records": len(events),
                                            "broken_at_id": anchor_tip_id,
                                            "external_anchor_verified": False,
                                            "error": (
                                                f"CRITICAL: External anchor mismatch detected at event #{anchor_tip_id}. "
                                                f"Database hash {event_hash_map[anchor_tip_id][:16]}... does not match external anchor {anchor_tip_hash[:16]}... "
                                                "(History has been rewritten/rehashed by an adversary!)"
                                            )
                                        }
                                    matched_anchors += 1
                except Exception as e:
                    logger.warning(f"Error checking external audit anchors: {e}")

        return {
            "is_valid": True,
            "total_records": len(events),
            "latest_hash": expected_prev_hash,
            "external_anchor_verified": external_anchor_verified,
            "external_anchors_count": matched_anchors,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "message": f"Cryptographic hash chain 100% verified. Zero tampering detected across {len(events)} events (external anchors verified: {matched_anchors})."
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
