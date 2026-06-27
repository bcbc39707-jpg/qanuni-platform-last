from sqlalchemy import String, Boolean, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum, uuid
from app.db.base import Base, TimestampMixin

_enum_values = lambda x: [e.value for e in x]

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    LAWYER = "lawyer"
    CLIENT = "client"
    REVIEWER = "reviewer"

class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole, values_callable=_enum_values), default=UserRole.CLIENT)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    cases = relationship("Case", back_populates="owner", foreign_keys="Case.owner_id")
    documents = relationship("Document", back_populates="uploaded_by_user")
