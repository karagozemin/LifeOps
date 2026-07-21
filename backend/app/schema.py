"""
LifeOps - Guaranteed JSON output schema.
The heart of the product: NO free text. Every output conforms to this schema.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    drivers_license = "drivers_license"
    passport = "passport"
    visa = "visa"
    warranty = "warranty"
    subscription = "subscription"
    bill = "bill"
    appointment = "appointment"
    multi = "multi"
    unknown = "unknown"


class Obligation(BaseModel):
    title: str = Field(..., description="Short title of the obligation")
    due_date: str = Field(..., description="ISO date (YYYY-MM-DD) - the deadline")
    start_action_by: str = Field(..., description="ISO date - when to start acting")
    risk_if_missed: str = Field(..., description="What happens if missed")
    money_at_risk_usd: float = Field(..., description="Estimated money lost if missed (USD)")
    days_remaining: int = Field(..., description="Days from today until due_date")
    steps: List[str] = Field(default_factory=list, description="Step-by-step action plan")


class Entities(BaseModel):
    expiry_date: Optional[str] = None
    holder: Optional[str] = None
    provider: Optional[str] = None
    amount_usd: Optional[float] = None
    reference: Optional[str] = None


class LifeOpsResult(BaseModel):
    document_type: DocumentType
    entities: Entities
    obligations: List[Obligation]
    reminders: List[str] = Field(default_factory=list, description="ISO reminder dates")
    total_money_at_risk_usd: float = 0.0
    ics_base64: str = ""
    confidence: float = Field(..., ge=0.0, le=1.0)
    documents_scanned: int = Field(default=1, description="Number of documents parsed (multi_audit)")


class ScanRequest(BaseModel):
    text: str = Field(..., description="Document/message text or JSON payload")
    service: str = Field(default="full_action_pack", description="scan | full_action_pack | multi_audit")
    caller: str = Field(default="human", description="human | agent - caller identity")
