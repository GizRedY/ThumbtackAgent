from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class LeadStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUOTED = "quoted"
    BOOKED = "booked"
    COMPLETED = "completed"
    DECLINED = "declined"


class MessageType(str, Enum):
    LEAD = "lead"
    MESSAGE = "message"
    QUOTE_REQUEST = "quote_request"
    BOOKING_CONFIRMATION = "booking_confirmation"


class Lead(BaseModel):
    """Модель лида от Thumbtack"""
    id: str
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    service_category: str
    description: str
    budget_range: Optional[tuple[float, float]] = None
    preferred_date: Optional[datetime] = None
    location: Optional[str] = None
    status: LeadStatus = LeadStatus.NEW
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Message(BaseModel):
    """Модель сообщения"""
    id: str
    lead_id: str
    sender: str  # "customer" or "business"
    content: str
    message_type: MessageType = MessageType.MESSAGE
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Quote(BaseModel):
    """Модель ценового предложения"""
    lead_id: str
    price: float
    description: str
    valid_until: datetime
    terms_and_conditions: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


class CalendarEvent(BaseModel):
    """Модель события календаря"""
    id: Optional[str] = None
    lead_id: str
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    attendees: list[str] = Field(default_factory=list)


class GPTAnalysis(BaseModel):
    """Результат анализа GPT"""
    sentiment: str  # "positive", "neutral", "negative"
    intent: str  # "quote_request", "scheduling", "question", etc.
    urgency: str  # "high", "medium", "low"
    suggested_price: Optional[float] = None
    key_requirements: list[str] = Field(default_factory=list)
    suggested_response: str
    confidence_score: float = Field(ge=0.0, le=1.0)