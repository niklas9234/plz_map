"""SQLAlchemy models shared by SQLite and PostgreSQL."""

from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, Index, String, UniqueConstraint, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'inactive')", name="ck_trades_status"),
        UniqueConstraint("color", name="uq_trades_color"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(8), nullable=False)
    color: Mapped[str | None] = mapped_column(String(7))
    created_at: Mapped[str] = mapped_column(String(35), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(35), nullable=False)


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'inactive')", name="ck_companies_status"),
        UniqueConstraint("pps_number", name="uq_companies_pps_number"),
        UniqueConstraint("id", "trade_id", name="uq_companies_id_trade_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    pps_number: Mapped[str] = mapped_column(String(255), nullable=False)
    trade_id: Mapped[str] = mapped_column(ForeignKey("trades.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(8), nullable=False)
    created_at: Mapped[str] = mapped_column(String(35), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(35), nullable=False)
    territories: Mapped[list["Territory"]] = relationship(cascade="all, delete-orphan")
    information: Mapped[list["CompanyInformation"]] = relationship(cascade="all, delete-orphan")


class Territory(Base):
    __tablename__ = "territories"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "trade_id"], ["companies.id", "companies.trade_id"],
            name="fk_territories_company_trade", ondelete="CASCADE",
        ),
        CheckConstraint("role IN ('primary', 'alternative')", name="ck_territories_role"),
    )

    company_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    postal_code: Mapped[str] = mapped_column(String(3), primary_key=True)
    trade_id: Mapped[str] = mapped_column(String(36), nullable=False)
    role: Mapped[str] = mapped_column(String(11), nullable=False)


class CompanyInformation(Base):
    __tablename__ = "company_information"
    __table_args__ = (
        CheckConstraint("category IN ('address', 'phone', 'contact', 'other')", name="ck_information_category"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True)
    position: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(7), nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)


Index("uq_trades_name_case_insensitive", func.lower(Trade.name), unique=True)

# SQLAlchemy renders the filtered index using each dialect's syntax. The
# predicate is the same standard comparison on both databases.
Index(
    "uq_territories_primary_trade_postal_code",
    Territory.trade_id,
    Territory.postal_code,
    unique=True,
    sqlite_where=text("role = 'primary'"),
    postgresql_where=text("role = 'primary'"),
)
