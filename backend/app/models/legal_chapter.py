from sqlalchemy import String, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from app.db.base import Base, TimestampMixin

class LegalChapter(Base, TimestampMixin):
    __tablename__ = "legal_chapters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    part_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("legal_parts.id", ondelete="CASCADE"), nullable=True)
    law_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("laws.id", ondelete="CASCADE"), nullable=True)
    chapter_number: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    part: Mapped["LegalPart | None"] = relationship("LegalPart", back_populates="chapters", lazy="selectin")
    law: Mapped["Law | None"] = relationship("Law", back_populates="chapters", lazy="selectin")
    articles: Mapped[list["LegalArticle"]] = relationship("LegalArticle", back_populates="chapter", lazy="selectin", cascade="all, delete-orphan")
