"""add meeting link fields to consultation_bookings

Revision ID: 0007_add_meeting_links
Revises: 0006_add_booking_conversation
Create Date: 2025-11-27 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0007_add_meeting_links"
down_revision = "0006_add_booking_conversation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("consultation_bookings", sa.Column("meeting_url", sa.String(length=512), nullable=True))
    op.add_column("consultation_bookings", sa.Column("line_contact", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("consultation_bookings", "line_contact")
    op.drop_column("consultation_bookings", "meeting_url")
