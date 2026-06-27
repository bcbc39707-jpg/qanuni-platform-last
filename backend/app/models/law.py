from sqlalchemy import String, Text, Integer, JSON, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
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
    division_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("legal_divisions.id", ondelete="SET NULL"), nullable=True)
    slug: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_articles_count: Mapped[int | None] = mapped_column(Integer, default=0)

    division: Mapped["LegalDivision | None"] = relationship("LegalDivision", back_populates="laws", lazy="selectin")
    parts: Mapped[list["LegalPart"]] = relationship("LegalPart", back_populates="law", lazy="selectin", cascade="all, delete-orphan")
    chapters: Mapped[list["LegalChapter"]] = relationship("LegalChapter", back_populates="law", lazy="selectin", cascade="all, delete-orphan")
    articles_rel: Mapped[list["LegalArticle"]] = relationship("LegalArticle", back_populates="law", lazy="selectin", cascade="all, delete-orphan")
