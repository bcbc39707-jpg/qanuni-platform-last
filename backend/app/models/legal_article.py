from sqlalchemy import String, Text, Integer, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from app.db.base import Base, TimestampMixin

class LegalArticle(Base, TimestampMixin):
    __tablename__ = "legal_articles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    law_id: Mapped[str] = mapped_column(String(36), ForeignKey("laws.id", ondelete="CASCADE"))
    part_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("legal_parts.id", ondelete="SET NULL"), nullable=True)
    chapter_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("legal_chapters.id", ondelete="SET NULL"), nullable=True)
    article_number: Mapped[str] = mapped_column(String(50))
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    keywords: Mapped[str | None] = mapped_column(Text, nullable=True)
    legal_topics: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    law: Mapped["Law"] = relationship("Law", back_populates="articles_rel", lazy="selectin")
    part: Mapped["LegalPart | None"] = relationship("LegalPart", back_populates="articles", lazy="selectin")
    chapter: Mapped["LegalChapter | None"] = relationship("LegalChapter", back_populates="articles", lazy="selectin")
