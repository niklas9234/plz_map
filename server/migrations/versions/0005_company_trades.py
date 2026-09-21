"""Allow companies to be assigned to multiple trades without losing data."""

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    company_columns = {column["name"] for column in inspector.get_columns("companies")}
    # An unversioned database may already have been created from the current
    # ORM metadata and then adopted by Alembic.
    if "company_trades" in inspector.get_table_names() and "trade_id" not in company_columns:
        return
    op.rename_table("territories", "territories_legacy")
    op.create_table(
        "company_trades",
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("trade_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trade_id"], ["trades.id"]),
        sa.PrimaryKeyConstraint("company_id", "trade_id"),
    )
    op.execute(sa.text(
        "INSERT INTO company_trades (company_id, trade_id) "
        "SELECT id, trade_id FROM companies"
    ))
    op.create_table(
        "territories",
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("trade_id", sa.String(36), nullable=False),
        sa.Column("postal_code", sa.String(3), nullable=False),
        sa.Column("role", sa.String(11), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id", "trade_id"],
            ["company_trades.company_id", "company_trades.trade_id"],
            name="fk_territories_company_trade", ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("company_id", "trade_id", "postal_code"),
        sa.CheckConstraint("role IN ('primary', 'alternative')", name="ck_territories_role"),
    )
    op.execute(sa.text(
        "INSERT INTO territories (company_id, trade_id, postal_code, role) "
        "SELECT company_id, trade_id, postal_code, role FROM territories_legacy"
    ))
    op.drop_table("territories_legacy")
    op.create_index(
        "uq_territories_primary_trade_postal_code", "territories",
        ["trade_id", "postal_code"], unique=True,
        sqlite_where=sa.text("role = 'primary'"),
        postgresql_where=sa.text("role = 'primary'"),
    )
    naming = {"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"}
    with op.batch_alter_table("companies", naming_convention=naming) as batch:
        batch.drop_constraint("uq_companies_id_trade_id", type_="unique")
        batch.drop_constraint("uq_companies_pps_number_trade_id", type_="unique")
        batch.drop_constraint("fk_companies_trade_id_trades", type_="foreignkey")
        batch.drop_column("trade_id")
        batch.create_unique_constraint("uq_companies_pps_number", ["pps_number"])


def downgrade():
    with op.batch_alter_table("companies") as batch:
        batch.drop_constraint("uq_companies_pps_number", type_="unique")
        batch.add_column(sa.Column("trade_id", sa.String(36), nullable=True))
    op.execute(sa.text(
        "UPDATE companies SET trade_id = (SELECT MIN(trade_id) FROM company_trades "
        "WHERE company_trades.company_id = companies.id)"
    ))
    op.drop_index("uq_territories_primary_trade_postal_code", table_name="territories")
    op.drop_table("territories")
    with op.batch_alter_table("companies") as batch:
        batch.alter_column("trade_id", nullable=False)
        batch.create_foreign_key("fk_companies_trade_id_trades", "trades", ["trade_id"], ["id"])
        batch.create_unique_constraint("uq_companies_id_trade_id", ["id", "trade_id"])
        batch.create_unique_constraint(
            "uq_companies_pps_number_trade_id", ["pps_number", "trade_id"]
        )
    op.drop_table("company_trades")
