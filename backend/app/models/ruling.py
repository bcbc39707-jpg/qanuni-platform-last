from sqlalchemy import String, Text, Integer, Date
from sqlalchemy.orm import Mapped, mapped_column
from datetime import date
import uuid
from app.db.base import Base, TimestampMixin

class Ruling(Base, TimestampMixin):
    __tablename__ = "rulings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(500))
    ruling_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    court_name: Mapped[str] = mapped_column(String(255))
    ruling_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    case_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    legal_principles: Mapped[str | None] = mapped_column(Text, nullable=True)
