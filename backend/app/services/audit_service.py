from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.models.models import AuditEvent, User

class AuditService:
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
        event = AuditEvent(
            organization_id=organization_id,
            actor_id=actor_id,
            event_type=event_type,
            reference_type=reference_type,
            reference_id=reference_id,
            details=details or {},
            ip_address=ip_address
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

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
                "created_at": e.created_at
            })
        return results

audit_service = AuditService()
