from sqlalchemy import String, Text, Integer, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from app.db.base import Base, TimestampMixin

class LegalPart(Base, TimestampMixin):
    __tablename__ = "legal_parts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    law_id: Mapped[str] = mapped_column(String(36), ForeignKey("laws.id", ondelete="CASCADE"))
    part_number: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    law: Mapped["Law"] = relationship("Law", back_populates="parts", lazy="selectin")
    chapters: Mapped[list["LegalChapter"]] = relationship("LegalChapter", back_populates="part", lazy="selectin", cascade="all, delete-orphan")
    articles: Mapped[list["LegalArticle"]] = relationship("LegalArticle", back_populates="part", lazy="selectin", cascade="all, delete-orphan")
