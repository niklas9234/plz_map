"""Add the marker table used by versioned initial imports."""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    # Some desktop databases received this internal table through the legacy
    # create_all startup path before Alembic managed it. Keep the migration
    # safe for those databases while still creating it on clean installations.
    if "application_metadata" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "application_metadata",
            sa.Column("key", sa.String(255), primary_key=True),
            sa.Column("value", sa.String(255), nullable=False),
            sa.Column("created_at", sa.String(35), nullable=False),
        )


def downgrade():
    if "application_metadata" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("application_metadata")
