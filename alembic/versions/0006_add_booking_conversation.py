"""Add conversation_id to consultation_bookings

Revision ID: 0006_add_booking_conversation
Revises: 0005_add_booking_status
Create Date: 2025-11-26
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0006_add_booking_conversation"
down_revision = "0005_add_booking_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("consultation_bookings", sa.Column("conversation_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_consultation_bookings_conversation_id",
        "consultation_bookings",
        "conversations",
        ["conversation_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_consultation_bookings_conversation_id", "consultation_bookings", type_="foreignkey")
    op.drop_column("consultation_bookings", "conversation_id")
