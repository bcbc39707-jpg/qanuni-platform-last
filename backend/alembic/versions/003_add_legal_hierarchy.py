"""add legal hierarchy tables (divisions, parts, chapters, articles, tree)

Revision ID: 003
Revises: 002
Create Date: 2026-06-09
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # legal_divisions - Level 1 categories
    op.create_table(
        "legal_divisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("slug", sa.String(200), nullable=True, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("color", sa.String(50), nullable=True),
        sa.Column("parent_id", sa.String(36), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # legal_parts - Level 3 (أبواب)
    op.create_table(
        "legal_parts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("law_id", sa.String(36), sa.ForeignKey("laws.id", ondelete="CASCADE"), nullable=False),
        sa.Column("part_number", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # legal_chapters - Level 4 (فصول)
    op.create_table(
        "legal_chapters",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("part_id", sa.String(36), sa.ForeignKey("legal_parts.id", ondelete="CASCADE"), nullable=True),
        sa.Column("law_id", sa.String(36), sa.ForeignKey("laws.id", ondelete="CASCADE"), nullable=True),
        sa.Column("chapter_number", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # legal_articles - Level 5 (مواد)
    op.create_table(
        "legal_articles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("law_id", sa.String(36), sa.ForeignKey("laws.id", ondelete="CASCADE"), nullable=False),
        sa.Column("part_id", sa.String(36), sa.ForeignKey("legal_parts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("chapter_id", sa.String(36), sa.ForeignKey("legal_chapters.id", ondelete="SET NULL"), nullable=True),
        sa.Column("article_number", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("keywords", sa.Text(), nullable=True),
        sa.Column("legal_topics", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # legal_tree_nodes - generic tree for non-law items
    op.create_table(
        "legal_tree_nodes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("legal_tree_nodes.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("slug", sa.String(200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("node_type", sa.String(100), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("color", sa.String(50), nullable=True),
        sa.Column("ref_table", sa.String(50), nullable=True),
        sa.Column("ref_id", sa.String(36), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("meta_data", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Add new columns to laws table
    op.add_column("laws", sa.Column("division_id", sa.String(36), sa.ForeignKey("legal_divisions.id", ondelete="SET NULL"), nullable=True))
    op.add_column("laws", sa.Column("slug", sa.String(200), nullable=True))
    op.add_column("laws", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("laws", sa.Column("total_articles_count", sa.Integer(), nullable=False, server_default="0"))

    # Add GIN index on legal_articles content + title for FTS
    op.create_index(
        "ix_legal_articles_search_vector",
        "legal_articles",
        [sa.text("to_tsvector('arabic', coalesce(title, '') || ' ' || coalesce(content, ''))")],
        postgresql_using="gin"
    )

    # Add index on legal_tree_nodes for faster tree traversal
    op.create_index("ix_legal_tree_nodes_parent", "legal_tree_nodes", ["parent_id"])
    op.create_index("ix_legal_tree_nodes_type", "legal_tree_nodes", ["node_type"])

    # Index for article lookups
    op.create_index("ix_legal_articles_law_article", "legal_articles", ["law_id", "article_number"])
    op.create_index("ix_legal_parts_law", "legal_parts", ["law_id"])
    op.create_index("ix_legal_chapters_part", "legal_chapters", ["part_id"])


def downgrade() -> None:
    op.drop_index("ix_legal_articles_search_vector", table_name="legal_articles")
    op.drop_index("ix_legal_tree_nodes_parent", table_name="legal_tree_nodes")
    op.drop_index("ix_legal_tree_nodes_type", table_name="legal_tree_nodes")
    op.drop_index("ix_legal_articles_law_article", table_name="legal_articles")
    op.drop_index("ix_legal_parts_law", table_name="legal_parts")
    op.drop_index("ix_legal_chapters_part", table_name="legal_chapters")

    op.drop_column("laws", "division_id")
    op.drop_column("laws", "slug")
    op.drop_column("laws", "description")
    op.drop_column("laws", "total_articles_count")

    op.drop_table("legal_articles")
    op.drop_table("legal_chapters")
    op.drop_table("legal_parts")
    op.drop_table("legal_tree_nodes")
    op.drop_table("legal_divisions")
