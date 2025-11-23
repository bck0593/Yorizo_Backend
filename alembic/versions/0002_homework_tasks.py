"""add homework tasks table

Revision ID: 0002_homework_tasks
Revises: 0001_init
Create Date: 2025-11-24
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_homework_tasks"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "homework_tasks" in existing_tables:
        return

    op.create_table(
        "homework_tasks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("conversation_id", sa.String(), sa.ForeignKey("conversations.id"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_homework_tasks_user_id", "homework_tasks", ["user_id"])
    op.create_index("ix_homework_tasks_conversation_id", "homework_tasks", ["conversation_id"])


def downgrade() -> None:
    op.drop_index("ix_homework_tasks_conversation_id", table_name="homework_tasks")
    op.drop_index("ix_homework_tasks_user_id", table_name="homework_tasks")
    op.drop_table("homework_tasks")
