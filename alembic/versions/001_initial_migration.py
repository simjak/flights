"""Initial migration

Revision ID: 001
Create Date: 2024-01-20 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute(
        "CREATE TYPE job_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled')"
    )
    op.execute("CREATE TYPE price_indicator AS ENUM ('low', 'typical', 'high')")

    # Create jobs table
    op.create_table(
        "jobs",
        sa.Column("job_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("departure_airports", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column(
            "destination_airports", postgresql.ARRAY(sa.String()), nullable=False
        ),
        sa.Column("outbound_dates", postgresql.ARRAY(sa.DateTime()), nullable=False),
        sa.Column("return_dates", postgresql.ARRAY(sa.DateTime()), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "running",
                "completed",
                "failed",
                "cancelled",
                name="job_status",
            ),
            nullable=False,
        ),
        sa.Column("total_combinations", sa.Integer(), nullable=False, default=0),
        sa.Column("processed_combinations", sa.Integer(), nullable=False, default=0),
        sa.Column("progress", sa.Float(), nullable=False, default=0.0),
        sa.Column("last_checkpoint", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            onupdate=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    # Create flight_results table
    op.create_table(
        "flight_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("departure_airport", sa.String(3), nullable=False),
        sa.Column("destination_airport", sa.String(3), nullable=False),
        sa.Column("outbound_date", sa.DateTime(), nullable=False),
        sa.Column("return_date", sa.DateTime(), nullable=True),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("airline", sa.String(100), nullable=False),
        sa.Column("stops", sa.Integer(), nullable=False),
        sa.Column("duration", sa.String(20), nullable=False),
        sa.Column(
            "current_price_indicator",
            sa.Enum("low", "typical", "high", name="price_indicator"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.job_id"], ondelete="CASCADE"),
        sa.Index("ix_flight_results_job_id", "job_id"),
        sa.Index("ix_flight_results_price", "price"),
    )


def downgrade() -> None:
    # Drop tables
    op.drop_table("flight_results")
    op.drop_table("jobs")

    # Drop enum types
    op.execute("DROP TYPE price_indicator")
    op.execute("DROP TYPE job_status")
