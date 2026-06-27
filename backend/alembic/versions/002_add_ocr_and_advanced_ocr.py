"""add ocr confidence + advanced ocr quota

Revision ID: 002
Revises: 001
Create Date: 2026-05-29
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column("documents", sa.Column("ocr_confidence", sa.Float(), nullable=True))
    op.add_column("documents", sa.Column("ocr_method", sa.String(20), nullable=True))
    op.add_column("subscriptions", sa.Column("advanced_ocr_quota", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("subscriptions", sa.Column("advanced_ocr_used", sa.Integer(), nullable=False, server_default="0"))

def downgrade() -> None:
    op.drop_column("documents", "ocr_confidence")
    op.drop_column("documents", "ocr_method")
    op.drop_column("subscriptions", "advanced_ocr_quota")
    op.drop_column("subscriptions", "advanced_ocr_used")
