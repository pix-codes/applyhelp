from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import OutreachEvent, OutreachMessage
from app.schemas.outreach import OutreachMessageCreate, OutreachMessageUpdate


class OutreachRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, message_id: UUID) -> OutreachMessage | None:
        stmt = (
            select(OutreachMessage)
            .options(selectinload(OutreachMessage.events))
            .where(OutreachMessage.id == message_id)
        )
        return self.db.execute(stmt).scalars().first()

    def create(self, msg_in: OutreachMessageCreate) -> OutreachMessage:
        msg = OutreachMessage(**msg_in.model_dump())
        self.db.add(msg)
        self.db.flush()

        event = OutreachEvent(
            outreach_id=msg.id,
            event_type="Created",
            details=f"Draft generated with template: {msg.template_type}",
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def update(self, message_id: UUID, updates: OutreachMessageUpdate) -> OutreachMessage:
        msg = self.db.get(OutreachMessage, message_id)
        if not msg:
            raise ValueError(f"OutreachMessage {message_id} not found")

        data = updates.model_dump(exclude_unset=True)
        old_status = msg.status
        for k, v in data.items():
            setattr(msg, k, v)

        msg.updated_at = datetime.utcnow()

        if "status" in data and data["status"] != old_status:
            event = OutreachEvent(
                outreach_id=msg.id,
                event_type="Status Changed",
                details=f"Status changed from {old_status} to {data['status']}",
            )
            self.db.add(event)

        self.db.commit()
        self.db.refresh(msg)
        return msg

    def record_event(self, message_id: UUID, event_type: str, details: str) -> None:
        event = OutreachEvent(
            outreach_id=message_id,
            event_type=event_type,
            details=details,
        )
        self.db.add(event)
        self.db.commit()

    def list_messages(self, status: str | None = None, limit: int = 100) -> list[OutreachMessage]:
        stmt = select(OutreachMessage).options(selectinload(OutreachMessage.events))
        if status:
            stmt = stmt.where(OutreachMessage.status == status)
        stmt = stmt.order_by(OutreachMessage.updated_at.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars().all())
