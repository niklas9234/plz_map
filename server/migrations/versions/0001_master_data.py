"""Create the portable master-data schema and its domain constraints."""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("trades",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(8), nullable=False),
        sa.Column("color", sa.String(7)), sa.Column("created_at", sa.String(35), nullable=False),
        sa.Column("updated_at", sa.String(35), nullable=False),
        sa.CheckConstraint("status IN ('active', 'inactive')", name="ck_trades_status"),
        sa.UniqueConstraint("color", name="uq_trades_color"))
    op.create_index("uq_trades_name_case_insensitive", "trades", [sa.text("lower(name)")], unique=True)
    op.create_table("companies",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("name", sa.String(255), nullable=False),
        sa.Column("pps_number", sa.String(255), nullable=False), sa.Column("trade_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(8), nullable=False), sa.Column("created_at", sa.String(35), nullable=False),
        sa.Column("updated_at", sa.String(35), nullable=False),
        sa.ForeignKeyConstraint(["trade_id"], ["trades.id"]),
        sa.UniqueConstraint("pps_number", name="uq_companies_pps_number"),
        sa.UniqueConstraint("id", "trade_id", name="uq_companies_id_trade_id"),
        sa.CheckConstraint("status IN ('active', 'inactive')", name="ck_companies_status"))
    op.create_table("territories",
        sa.Column("company_id", sa.String(36), primary_key=True), sa.Column("postal_code", sa.String(3), primary_key=True),
        sa.Column("trade_id", sa.String(36), nullable=False), sa.Column("role", sa.String(11), nullable=False),
        sa.ForeignKeyConstraint(["company_id", "trade_id"], ["companies.id", "companies.trade_id"], name="fk_territories_company_trade", ondelete="CASCADE"),
        sa.CheckConstraint("role IN ('primary', 'alternative')", name="ck_territories_role"))
    op.create_index("uq_territories_primary_trade_postal_code", "territories", ["trade_id", "postal_code"], unique=True,
                    sqlite_where=sa.text("role = 'primary'"), postgresql_where=sa.text("role = 'primary'"))
    op.create_table("company_information",
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("position", sa.Integer, primary_key=True), sa.Column("category", sa.String(7), nullable=False),
        sa.Column("value", sa.String, nullable=False),
        sa.CheckConstraint("category IN ('address', 'phone', 'contact', 'other')", name="ck_information_category"))


def downgrade():
    op.drop_table("company_information")
    op.drop_index("uq_territories_primary_trade_postal_code", table_name="territories")
    op.drop_table("territories")
    op.drop_table("companies")
    op.drop_index("uq_trades_name_case_insensitive", table_name="trades")
    op.drop_table("trades")
