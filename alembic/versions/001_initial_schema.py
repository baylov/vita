"""Initial database schema.

Revision ID: 001_initial_schema
Revises: 
Create Date: 2024-11-13 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "specialist",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("specialty", sa.String(length=100), nullable=False),
        sa.Column("telegram_id", sa.String(length=50), nullable=True),
        sa.Column("whatsapp", sa.String(length=50), nullable=True),
        sa.Column("instagram", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_specialist_telegram_id", "specialist", ["telegram_id"], unique=True)
    op.create_index("ix_specialist_whatsapp", "specialist", ["whatsapp"], unique=True)
    op.create_index("ix_specialist_instagram", "specialist", ["instagram"], unique=True)

    op.create_table(
        "schedule",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("specialist_id", sa.Integer(), nullable=False),
        sa.Column("day_of_week", sa.String(length=10), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("appointment_duration", sa.Integer(), nullable=False),
        sa.Column("max_patients", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["specialist_id"], ["specialist.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_schedule_specialist_id", "schedule", ["specialist_id"], unique=False)

    op.create_table(
        "day_off",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("specialist_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["specialist_id"], ["specialist.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_day_off_specialist_id", "day_off", ["specialist_id"], unique=False)

    op.create_table(
        "booking",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("specialist_id", sa.Integer(), nullable=False),
        sa.Column("user_name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("booking_date", sa.Date(), nullable=False),
        sa.Column("booking_time", sa.Time(), nullable=False),
        sa.Column("problem_summary", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["specialist_id"], ["specialist.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_booking_specialist_id", "booking", ["specialist_id"], unique=False)
    op.create_index("ix_booking_phone", "booking", ["phone"], unique=False)

    op.create_table(
        "user_session",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column(
            "language",
            sa.String(length=5),
            nullable=False,
            server_default=sa.text("'ru'"),
        ),
        sa.Column("current_state", sa.String(length=100), nullable=True),
        sa.Column("context_data", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_session_user_id", "user_session", ["user_id"], unique=True)

    op.create_table(
        "admin_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("admin_id", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_log_admin_id", "admin_log", ["admin_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_admin_log_admin_id", table_name="admin_log")
    op.drop_table("admin_log")
    op.drop_index("ix_user_session_user_id", table_name="user_session")
    op.drop_table("user_session")
    op.drop_index("ix_booking_phone", table_name="booking")
    op.drop_index("ix_booking_specialist_id", table_name="booking")
    op.drop_table("booking")
    op.drop_index("ix_day_off_specialist_id", table_name="day_off")
    op.drop_table("day_off")
    op.drop_index("ix_schedule_specialist_id", table_name="schedule")
    op.drop_table("schedule")
    op.drop_index("ix_specialist_instagram", table_name="specialist")
    op.drop_index("ix_specialist_whatsapp", table_name="specialist")
    op.drop_index("ix_specialist_telegram_id", table_name="specialist")
    op.drop_table("specialist")
