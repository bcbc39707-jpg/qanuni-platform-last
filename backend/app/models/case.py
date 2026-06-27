from sqlalchemy import String, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum, uuid
from app.db.base import Base, TimestampMixin

_enum_values = lambda x: [e.value for e in x]

class CaseStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"
    ARCHIVED = "archived"

class CaseType(str, enum.Enum):
    CIVIL = "civil"
    CRIMINAL = "criminal"
    COMMERCIAL = "commercial"
    FAMILY = "family"
    ADMINISTRATIVE = "administrative"
    LABOR = "labor"

class Case(Base, TimestampMixin):
    __tablename__ = "cases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    case_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    case_type: Mapped[CaseType] = mapped_column(SQLEnum(CaseType, values_callable=_enum_values))
    status: Mapped[CaseStatus] = mapped_column(SQLEnum(CaseStatus, values_callable=_enum_values), default=CaseStatus.OPEN)
    court_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    lawyer_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    owner = relationship("User", back_populates="cases", foreign_keys=[owner_id])
    documents = relationship("Document", back_populates="case")
