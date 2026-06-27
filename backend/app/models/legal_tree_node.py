from sqlalchemy import String, Text, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from app.db.base import Base, TimestampMixin

class LegalTreeNode(Base, TimestampMixin):
    __tablename__ = "legal_tree_nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    parent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("legal_tree_nodes.id", ondelete="CASCADE"), nullable=True)
    name: Mapped[str] = mapped_column(String(500))
    slug: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    node_type: Mapped[str] = mapped_column(String(100))
    level: Mapped[int] = mapped_column(Integer, default=1)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ref_table: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ref_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    meta_data: Mapped[str | None] = mapped_column(Text, nullable=True)

    children: Mapped[list["LegalTreeNode"]] = relationship(
        "LegalTreeNode", back_populates="parent",
        lazy="selectin", cascade="all, delete-orphan",
        remote_side="LegalTreeNode.parent_id"
    )
    parent: Mapped["LegalTreeNode | None"] = relationship(
        "LegalTreeNode", back_populates="children",
        lazy="selectin", remote_side="LegalTreeNode.id"
    )
