"""Make company PPS numbers unique per trade instead of globally."""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    constraints = {
        constraint["name"]
        for constraint in sa.inspect(op.get_bind()).get_unique_constraints("companies")
    }
    # An unversioned database may already have been created from the current
    # ORM metadata before Alembic adopts it.
    if "uq_companies_pps_number_trade_id" in constraints:
        return
    # Batch mode recreates the table on SQLite and issues regular ALTER TABLE
    # statements on PostgreSQL.
    with op.batch_alter_table("companies") as batch_op:
        if "uq_companies_pps_number" in constraints:
            batch_op.drop_constraint("uq_companies_pps_number", type_="unique")
        batch_op.create_unique_constraint(
            "uq_companies_pps_number_trade_id", ["pps_number", "trade_id"]
        )


def downgrade():
    constraints = {
        constraint["name"]
        for constraint in sa.inspect(op.get_bind()).get_unique_constraints("companies")
    }
    if "uq_companies_pps_number" in constraints:
        return
    with op.batch_alter_table("companies") as batch_op:
        if "uq_companies_pps_number_trade_id" in constraints:
            batch_op.drop_constraint("uq_companies_pps_number_trade_id", type_="unique")
        batch_op.create_unique_constraint("uq_companies_pps_number", ["pps_number"])
