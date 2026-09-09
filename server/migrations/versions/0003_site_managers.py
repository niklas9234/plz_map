"""Add site managers and their postal-code territories."""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    # Desktop databases may already contain tables created through create_all
    # before Alembic adopts the unversioned schema.
    if "site_managers" not in existing:
        op.create_table(
            "site_managers",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("status", sa.String(8), nullable=False),
            sa.Column("created_at", sa.String(35), nullable=False),
            sa.Column("updated_at", sa.String(35), nullable=False),
            sa.CheckConstraint("status IN ('active', 'inactive')", name="ck_site_managers_status"),
        )
    if "site_manager_territories" not in existing:
        op.create_table(
            "site_manager_territories",
            sa.Column("site_manager_id", sa.String(36), nullable=False),
            sa.Column("postal_code", sa.String(3), nullable=False),
            sa.ForeignKeyConstraint(["site_manager_id"], ["site_managers.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("site_manager_id", "postal_code"),
        )


def downgrade():
    op.drop_table("site_manager_territories")
    op.drop_table("site_managers")
