from sqlalchemy import String, Text, Integer, ForeignKey, Enum as SQLEnum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum, uuid
from app.db.base import Base, TimestampMixin

class DocumentType(str, enum.Enum):
    LAW = "law"
    RULING = "ruling"
    CONTRACT = "contract"
    MEMO = "memo"
    CLAIM = "claim"
    DEFENSE = "defense"
    EVIDENCE = "evidence"
    OTHER = "other"

class Document(Base, TimestampMixin):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    doc_type: Mapped[DocumentType] = mapped_column(SQLEnum(DocumentType))
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ocr_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    case_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("cases.id"), nullable=True)
    uploaded_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    case = relationship("Case", back_populates="documents")
    uploaded_by_user = relationship("User", back_populates="documents")
