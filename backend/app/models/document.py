from sqlalchemy import String, Text, Integer, Float, ForeignKey, Enum as SQLEnum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum, uuid
from app.db.base import Base, TimestampMixin

_enum_values = lambda x: [e.value for e in x]

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
    doc_type: Mapped[DocumentType] = mapped_column(SQLEnum(DocumentType, values_callable=_enum_values))
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ocr_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ocr_method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    case_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("cases.id"), nullable=True)
    uploaded_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    case = relationship("Case", back_populates="documents")
    uploaded_by_user = relationship("User", back_populates="documents")
