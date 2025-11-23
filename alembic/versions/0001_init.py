"""initial schema

Revision ID: 0001_init
Revises: 
Create Date: 2025-11-23
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # Skip if the initial schema already exists to allow idempotent local runs.
    if "users" in existing_tables:
        return

    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("external_id", sa.String(), nullable=True),
        sa.Column("nickname", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "company_profiles",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("company_name", sa.String(), nullable=True),
        sa.Column("industry", sa.String(), nullable=True),
        sa.Column("employees_range", sa.String(), nullable=True),
        sa.Column("annual_sales_range", sa.String(), nullable=True),
        sa.Column("location_prefecture", sa.String(), nullable=True),
        sa.Column("years_in_business", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "conversations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("main_concern", sa.Text(), nullable=True),
        sa.Column("channel", sa.String(), nullable=True),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("conversation_id", sa.String(), sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "memories",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("current_concerns", sa.Text(), nullable=True),
        sa.Column("important_points", sa.Text(), nullable=True),
        sa.Column("remembered_facts", sa.Text(), nullable=True),
        sa.Column("last_updated_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "consultation_memos",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("conversation_id", sa.String(), sa.ForeignKey("conversations.id"), nullable=False, unique=True),
        sa.Column("current_points", sa.Text(), nullable=True),
        sa.Column("important_points", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "experts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("avatar_url", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("organization", sa.String(), nullable=True),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("review_count", sa.Integer(), nullable=True),
        sa.Column("location_prefecture", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
    )

    op.create_table(
        "expert_availabilities",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("expert_id", sa.String(), sa.ForeignKey("experts.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("slots_json", sa.Text(), nullable=False),
    )

    op.create_table(
        "consultation_bookings",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("expert_id", sa.String(), sa.ForeignKey("experts.id"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("time_slot", sa.String(), nullable=False),
        sa.Column("channel", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("documents")
    op.drop_table("consultation_bookings")
    op.drop_table("expert_availabilities")
    op.drop_table("experts")
    op.drop_table("consultation_memos")
    op.drop_table("memories")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("company_profiles")
    op.drop_table("users")
