"""002 change pk columns from bigint to integer

Revision ID: 002
Revises: 001
Create Date: 2025-01-02 00:00:00

Changes primary keys and foreign keys from BIGINT → INTEGER across
all four tables to match the SQLAlchemy model definitions.
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop FK constraints that reference the PKs we're changing
    op.drop_constraint("posting_history_user_id_fkey", "posting_history", type_="foreignkey")
    op.drop_constraint("posting_history_video_id_fkey", "posting_history", type_="foreignkey")
    op.drop_constraint("videos_category_id_fkey", "videos", type_="foreignkey")

    # Alter primary keys
    op.alter_column("users",           "id", type_=sa.Integer(), existing_nullable=False)
    op.alter_column("categories",      "id", type_=sa.Integer(), existing_nullable=False)
    op.alter_column("videos",          "id", type_=sa.Integer(), existing_nullable=False)
    op.alter_column("posting_history", "id", type_=sa.Integer(), existing_nullable=False)

    # Alter foreign key columns
    op.alter_column("videos",          "category_id", type_=sa.Integer(), existing_nullable=True)
    op.alter_column("posting_history", "user_id",     type_=sa.Integer(), existing_nullable=False)
    op.alter_column("posting_history", "video_id",    type_=sa.Integer(), existing_nullable=False)

    # Recreate FK constraints
    op.create_foreign_key(
        "videos_category_id_fkey", "videos", "categories",
        ["category_id"], ["id"], ondelete="SET NULL",
    )
    op.create_foreign_key(
        "posting_history_user_id_fkey", "posting_history", "users",
        ["user_id"], ["id"], ondelete="CASCADE",
    )
    op.create_foreign_key(
        "posting_history_video_id_fkey", "posting_history", "videos",
        ["video_id"], ["id"], ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("posting_history_user_id_fkey", "posting_history", type_="foreignkey")
    op.drop_constraint("posting_history_video_id_fkey", "posting_history", type_="foreignkey")
    op.drop_constraint("videos_category_id_fkey", "videos", type_="foreignkey")

    op.alter_column("users",           "id", type_=sa.BigInteger(), existing_nullable=False)
    op.alter_column("categories",      "id", type_=sa.BigInteger(), existing_nullable=False)
    op.alter_column("videos",          "id", type_=sa.BigInteger(), existing_nullable=False)
    op.alter_column("posting_history", "id", type_=sa.BigInteger(), existing_nullable=False)

    op.alter_column("videos",          "category_id", type_=sa.BigInteger(), existing_nullable=True)
    op.alter_column("posting_history", "user_id",     type_=sa.BigInteger(), existing_nullable=False)
    op.alter_column("posting_history", "video_id",    type_=sa.BigInteger(), existing_nullable=False)

    op.create_foreign_key(
        "videos_category_id_fkey", "videos", "categories",
        ["category_id"], ["id"], ondelete="SET NULL",
    )
    op.create_foreign_key(
        "posting_history_user_id_fkey", "posting_history", "users",
        ["user_id"], ["id"], ondelete="CASCADE",
    )
    op.create_foreign_key(
        "posting_history_video_id_fkey", "posting_history", "videos",
        ["video_id"], ["id"], ondelete="RESTRICT",
    )
