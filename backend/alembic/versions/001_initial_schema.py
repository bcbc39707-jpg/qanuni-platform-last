"""initial schema

Revision ID: 001
Revises: 
Create Date: 2026-05-29
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")

    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, index=True, nullable=False),
        sa.Column("phone", sa.String(20), unique=True, nullable=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("admin", "lawyer", "client", "reviewer", name="userrole"), nullable=False, server_default="client"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "cases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("case_number", sa.String(100), nullable=True),
        sa.Column("case_type", sa.Enum("civil", "criminal", "commercial", "family", "administrative", "labor", name="casetype"), nullable=False),
        sa.Column("status", sa.Enum("open", "in_progress", "closed", "archived", name="casestatus"), nullable=False, server_default="open"),
        sa.Column("court_name", sa.String(255), nullable=True),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("lawyer_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("plan", sa.Enum("free", "professional", "enterprise", name="plantype"), nullable=False, server_default="free"),
        sa.Column("status", sa.Enum("active", "expired", "cancelled", name="subscriptionstatus"), nullable=False, server_default="active"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("search_quota", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("analysis_quota", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("drafting_quota", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("searches_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("analyses_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("drafts_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("subscription_id", sa.String(36), sa.ForeignKey("subscriptions.id"), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="YER"),
        sa.Column("provider", sa.Enum("jeep", "easy", "jawali", "alkuraimi", "manual", name="paymentprovider"), nullable=False),
        sa.Column("status", sa.Enum("pending", "completed", "failed", "refunded", name="paymentstatus"), nullable=False, server_default="pending"),
        sa.Column("provider_txn_id", sa.String(255), nullable=True),
        sa.Column("provider_response", sa.String(2000), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("doc_type", sa.Enum("law", "ruling", "contract", "memo", "claim", "defense", "evidence", "other", name="documenttype"), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("ocr_processed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.id"), nullable=True),
        sa.Column("uploaded_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "laws",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("law_number", sa.String(100), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(200), nullable=True),
        sa.Column("full_text", sa.Text(), nullable=True),
        sa.Column("articles", JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "rulings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("ruling_number", sa.String(100), nullable=True),
        sa.Column("court_name", sa.String(255), nullable=False),
        sa.Column("ruling_date", sa.Date(), nullable=True),
        sa.Column("case_type", sa.String(100), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("full_text", sa.Text(), nullable=True),
        sa.Column("legal_principles", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_documents_search_vector", "documents", [sa.text("to_tsvector('arabic', coalesce(title, '') || ' ' || coalesce(content, ''))")], postgresql_using="gin")
    op.create_index("ix_laws_search_vector", "laws", [sa.text("to_tsvector('arabic', coalesce(title, '') || ' ' || coalesce(full_text, ''))")], postgresql_using="gin")
    op.create_index("ix_rulings_search_vector", "rulings", [sa.text("to_tsvector('arabic', coalesce(title, '') || ' ' || coalesce(full_text, ''))")], postgresql_using="gin")

def downgrade() -> None:
    op.drop_index("ix_documents_search_vector", table_name="documents")
    op.drop_index("ix_laws_search_vector", table_name="laws")
    op.drop_index("ix_rulings_search_vector", table_name="rulings")
    op.drop_table("rulings")
    op.drop_table("laws")
    op.drop_table("documents")
    op.drop_table("payments")
    op.drop_table("subscriptions")
    op.drop_table("cases")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS casetype")
    op.execute("DROP TYPE IF EXISTS casestatus")
    op.execute("DROP TYPE IF EXISTS plantype")
    op.execute("DROP TYPE IF EXISTS subscriptionstatus")
    op.execute("DROP TYPE IF EXISTS paymentprovider")
    op.execute("DROP TYPE IF EXISTS paymentstatus")
    op.execute("DROP TYPE IF EXISTS documenttype")
