from sqlalchemy import String, Text, Integer, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
import uuid
from app.db.base import Base, TimestampMixin

class Law(Base, TimestampMixin):
    __tablename__ = "laws"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(500))
    law_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    category: Mapped[str | None] = mapped_column(String(200), nullable=True)
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    articles: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
