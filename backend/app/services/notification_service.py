from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.models import Notification, OrganizationMember

class NotificationService:
    @staticmethod
    def notify_user(
        db: Session,
        user_id: int,
        title: str,
        message: str,
        category: str = "INFO"
    ) -> Notification:
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            category=category,
            read_status=False
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        return notif

    @staticmethod
    def notify_organization_role(
        db: Session,
        organization_id: int,
        role: str,
        title: str,
        message: str,
        category: str = "INFO"
    ) -> List[Notification]:
        members = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.role == role
        ).all()
        
        notifications = []
        for m in members:
            notif = Notification(
                user_id=m.user_id,
                title=title,
                message=message,
                category=category,
                read_status=False
            )
            db.add(notif)
            notifications.append(notif)
        
        if notifications:
            db.commit()
        return notifications

    @staticmethod
    def get_user_notifications(db: Session, user_id: int, limit: int = 50) -> List[Notification]:
        return db.query(Notification).filter(
            Notification.user_id == user_id
        ).order_by(Notification.created_at.desc()).limit(limit).all()

    @staticmethod
    def mark_as_read(db: Session, notification_id: int, user_id: int) -> bool:
        notif = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()
        if notif:
            notif.read_status = True
            db.commit()
            return True
        return False

    @staticmethod
    def mark_all_as_read(db: Session, user_id: int) -> int:
        count = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.read_status == False
        ).update({"read_status": True})
        db.commit()
        return count

notification_service = NotificationService()
