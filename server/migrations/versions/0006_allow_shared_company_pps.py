"""Allow a PPS number to be reused by companies in different trades."""

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    constraints = {
        constraint["name"]
        for constraint in sa.inspect(op.get_bind()).get_unique_constraints("companies")
    }
    if "uq_companies_pps_number" in constraints:
        with op.batch_alter_table("companies") as batch:
            batch.drop_constraint("uq_companies_pps_number", type_="unique")


def downgrade():
    with op.batch_alter_table("companies") as batch:
        batch.create_unique_constraint("uq_companies_pps_number", ["pps_number"])
