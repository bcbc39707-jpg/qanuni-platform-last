from sqlalchemy import String, Integer, Float, ForeignKey, Enum as SQLEnum, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import enum, uuid
from app.db.base import Base, TimestampMixin

_enum_values = lambda x: [e.value for e in x]

class PaymentProvider(str, enum.Enum):
    JEEP = "jeep"
    EASY = "easy"
    JAWALI = "jawali"
    ALKURAIMI = "alkuraimi"
    MANUAL = "manual"

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

class Payment(Base, TimestampMixin):
    __tablename__ = "payments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    subscription_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("subscriptions.id"), nullable=True)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="YER")
    provider: Mapped[PaymentProvider] = mapped_column(SQLEnum(PaymentProvider, values_callable=_enum_values))
    status: Mapped[PaymentStatus] = mapped_column(SQLEnum(PaymentStatus, values_callable=_enum_values), default=PaymentStatus.PENDING)
    provider_txn_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_response: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
