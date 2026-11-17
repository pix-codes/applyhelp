from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OutreachMessageBase(BaseModel):
    company_id: UUID
    job_id: UUID | None = None
    contact_id: UUID | None = None
    template_type: str = "General Introduction"
    subject: str
    body: str
    status: str = "Draft Generated"
    follow_up_date: datetime | None = None
    notes: str | None = None


class OutreachMessageCreate(OutreachMessageBase):
    pass


class OutreachMessageUpdate(BaseModel):
    subject: str | None = None
    body: str | None = None
    status: str | None = None
    follow_up_date: datetime | None = None
    notes: str | None = None
    gmail_draft_id: str | None = None


class OutreachMessageOut(OutreachMessageBase):
    id: UUID
    gmail_draft_id: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
