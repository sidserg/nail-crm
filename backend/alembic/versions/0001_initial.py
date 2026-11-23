"""Initial schema: users, clients, services, appointments, expenses, settings.

On PostgreSQL an EXCLUDE constraint additionally guarantees at the database
level that two active appointments can never overlap in time.

Revision ID: 0001
Revises:
Create Date: 2026-11-23
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("login", sa.String(64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "clients",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False, unique=True),
        sa.Column("birth_date", sa.Date, nullable=True),
        sa.Column("notes", sa.Text, nullable=False, server_default=""),
        sa.Column("telegram_chat_id", sa.String(32), nullable=True),
        sa.Column("tg_token", sa.String(32), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_clients_name", "clients", ["name"])

    op.create_table(
        "services",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("duration_min", sa.Integer, nullable=False),
        sa.Column("price", sa.Float, nullable=False, server_default="0"),
        sa.Column("color", sa.String(9), nullable=False, server_default="#d6336c"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("service_id", sa.Integer, sa.ForeignKey("services.id"), nullable=False),
        sa.Column("start_at", sa.DateTime, nullable=False),
        sa.Column("end_at", sa.DateTime, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="confirmed"),
        sa.Column("price", sa.Float, nullable=True),
        sa.Column("comment", sa.Text, nullable=False, server_default=""),
        sa.Column("source", sa.String(8), nullable=False, server_default="owner"),
        sa.Column("client_confirmed", sa.Boolean, nullable=True),
        sa.Column("reminder_24h_sent", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("reminder_2h_sent", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_appointments_start", "appointments", ["start_at"])
    op.create_index("ix_appointments_status", "appointments", ["status"])

    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("category", sa.String(60), nullable=False, server_default="Материалы"),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("comment", sa.Text, nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "settings",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", sa.String(255), nullable=False),
    )

    # PostgreSQL: DB-level guarantee against double booking
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            ALTER TABLE appointments
            ADD CONSTRAINT appointments_no_overlap
            EXCLUDE USING gist (tsrange(start_at, end_at) WITH &&)
            WHERE (status IN ('confirmed', 'completed'))
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE appointments DROP CONSTRAINT IF EXISTS appointments_no_overlap")
    op.drop_table("settings")
    op.drop_table("expenses")
    op.drop_index("ix_appointments_status", table_name="appointments")
    op.drop_index("ix_appointments_start", table_name="appointments")
    op.drop_table("appointments")
    op.drop_table("services")
    op.drop_index("ix_clients_name", table_name="clients")
    op.drop_table("clients")
    op.drop_table("users")
