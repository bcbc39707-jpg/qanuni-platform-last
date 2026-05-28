from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, Enum as SQLEnum, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import enum, uuid
from app.db.base import Base, TimestampMixin

class PlanType(str, enum.Enum):
    FREE = "free"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"

class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    plan: Mapped[PlanType] = mapped_column(SQLEnum(PlanType), default=PlanType.FREE)
    status: Mapped[SubscriptionStatus] = mapped_column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    search_quota: Mapped[int] = mapped_column(Integer, default=10)
    analysis_quota: Mapped[int] = mapped_column(Integer, default=0)
    drafting_quota: Mapped[int] = mapped_column(Integer, default=0)
    searches_used: Mapped[int] = mapped_column(Integer, default=0)
    analyses_used: Mapped[int] = mapped_column(Integer, default=0)
    drafts_used: Mapped[int] = mapped_column(Integer, default=0)
