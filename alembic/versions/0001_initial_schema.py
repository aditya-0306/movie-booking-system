"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    user_role = sa.Enum("admin", "customer", name="userrole")
    seat_type = sa.Enum("regular", "premium", name="seattype")
    booking_status = sa.Enum("pending", "confirmed", "cancelled", name="bookingstatus")
    payment_status = sa.Enum("pending", "success", "failed", name="paymentstatus")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(150), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False, server_default="customer"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)

    op.create_table(
        "movies",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("genre", sa.String(100), nullable=False),
        sa.Column("language", sa.String(50), nullable=False),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("rating", sa.Float(), server_default="0.0"),
        sa.Column("poster_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_movies_title", "movies", ["title"])
    op.create_index("ix_movies_genre", "movies", ["genre"])
    op.create_index("ix_movies_language", "movies", ["language"])

    op.create_table(
        "theatres",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("address", sa.String(300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_theatres_city", "theatres", ["city"])

    op.create_table(
        "screens",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("theatre_id", sa.Integer(), sa.ForeignKey("theatres.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("total_seats", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_screens_theatre_id", "screens", ["theatre_id"])

    op.create_table(
        "seats",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("screen_id", sa.Integer(), sa.ForeignKey("screens.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seat_number", sa.String(10), nullable=False),
        sa.Column("seat_type", seat_type, nullable=False, server_default="regular"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("screen_id", "seat_number", name="uq_screen_seat_number"),
    )
    op.create_index("ix_seats_screen_id", "seats", ["screen_id"])

    op.create_table(
        "shows",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("movie_id", sa.Integer(), sa.ForeignKey("movies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("screen_id", sa.Integer(), sa.ForeignKey("screens.id", ondelete="CASCADE"), nullable=False),
        sa.Column("show_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_shows_movie_id", "shows", ["movie_id"])
    op.create_index("ix_shows_screen_id", "shows", ["screen_id"])
    op.create_index("ix_shows_show_time", "shows", ["show_time"])

    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("show_id", sa.Integer(), sa.ForeignKey("shows.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seat_id", sa.Integer(), sa.ForeignKey("seats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", booking_status, nullable=False, server_default="pending"),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("booked_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_bookings_user_id", "bookings", ["user_id"])
    op.create_index("ix_bookings_show_id", "bookings", ["show_id"])
    op.create_index("ix_bookings_seat_id", "bookings", ["seat_id"])

    # THE critical constraint: only one active (non-cancelled) booking is
    # allowed per (show_id, seat_id) combination. This is what makes seat
    # reservation safe under concurrent requests -- see BookingRepository
    # for the full explanation of why this beats a plain SELECT FOR UPDATE.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_active_booking_per_seat_per_show
        ON bookings (show_id, seat_id)
        WHERE status != 'cancelled'
        """
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", payment_status, nullable=False, server_default="pending"),
        sa.Column("transaction_ref", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("booking_id", name="uq_payment_booking_id"),
    )


def downgrade() -> None:
    op.drop_table("payments")
    op.execute("DROP INDEX IF EXISTS uq_active_booking_per_seat_per_show")
    op.drop_table("bookings")
    op.drop_table("shows")
    op.drop_table("seats")
    op.drop_table("screens")
    op.drop_table("theatres")
    op.drop_table("movies")
    op.drop_table("refresh_tokens")
    op.drop_table("users")

    sa.Enum(name="paymentstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="bookingstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="seattype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=True)
