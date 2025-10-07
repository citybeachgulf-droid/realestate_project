from datetime import datetime, date
from typing import Optional
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(UserMixin, db.Model, TimestampMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=True)
    # Mobile phone for tenants; optional for other roles
    phone = db.Column(db.String(32), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(32), nullable=False, index=True)

    contracts = db.relationship("Contract", back_populates="tenant", lazy="dynamic")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    

    @property
    def is_employee(self) -> bool:
        return self.role == "employee"

    @property
    def is_tenant(self) -> bool:
        return self.role == "tenant"

    @property
    def is_accountant(self) -> bool:
        return self.role == "accountant"


class Property(db.Model, TimestampMixin):
    __tablename__ = "properties"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    status = db.Column(db.String(50), nullable=False, default="available")
    # property_type distinguishes standalone apartment vs building that contains apartments
    # allowed values: 'building', 'apartment'
    property_type = db.Column(db.String(20), nullable=False, default="building", index=True)
    images = db.Column(db.Text)  # store comma-separated file names or JSON
    # Apartment-specific metadata for standalone apartments
    number = db.Column(db.String(50), nullable=True)
    floor = db.Column(db.Integer, nullable=True)
    area_sqm = db.Column(db.Numeric(10, 2), nullable=True)
    bedrooms = db.Column(db.Integer, nullable=True)
    bathrooms = db.Column(db.Integer, nullable=True)
    # Building-related metadata
    num_apartments = db.Column(db.Integer, nullable=True)
    num_floors = db.Column(db.Integer, nullable=True)

    contracts = db.relationship("Contract", back_populates="property", lazy="dynamic")
    apartments = db.relationship(
        "Apartment",
        back_populates="building",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )


class Apartment(db.Model, TimestampMixin):
    __tablename__ = "apartments"

    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(
        db.Integer,
        db.ForeignKey("properties.id"),
        nullable=False,
        index=True,
    )
    number = db.Column(db.String(50), nullable=True)  # e.g., 12A
    floor = db.Column(db.Integer, nullable=True)
    area_sqm = db.Column(db.Numeric(10, 2), nullable=True)
    bedrooms = db.Column(db.Integer, nullable=True)
    bathrooms = db.Column(db.Integer, nullable=True)
    rent_price = db.Column(db.Numeric(12, 2), nullable=True)
    status = db.Column(db.String(50), nullable=False, default="available")
    images = db.Column(db.Text)  # comma-separated relative paths

    building = db.relationship("Property", back_populates="apartments")


class Contract(db.Model, TimestampMixin):
    __tablename__ = "contracts"

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.id"), nullable=False, index=True)
    # Optional apartment reference if the property is a building
    apartment_id = db.Column(db.Integer, db.ForeignKey("apartments.id"), nullable=True, index=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    rent_amount = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.String(50), nullable=False, default="active")
    document_path = db.Column(db.String(500))

    property = db.relationship("Property", back_populates="contracts")
    apartment = db.relationship("Apartment")
    tenant = db.relationship("User", back_populates="contracts")
    payments = db.relationship("Payment", back_populates="contract", lazy="dynamic")


class Payment(db.Model, TimestampMixin):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("contracts.id"), nullable=False, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    paid_date = db.Column(db.Date)
    method = db.Column(db.String(50))  # cash, card, transfer
    status = db.Column(db.String(50), nullable=False, default="unpaid")

    contract = db.relationship("Contract", back_populates="payments")
    invoice = db.relationship("Invoice", back_populates="payment", uselist=False)


class Invoice(db.Model, TimestampMixin):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey("payments.id"), nullable=False, unique=True)
    file_path = db.Column(db.String(500), nullable=False)

    payment = db.relationship("Payment", back_populates="invoice")


# --- Service and Support domain ---


class MaintenanceRequest(db.Model, TimestampMixin):
    __tablename__ = "maintenance_requests"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.id"), nullable=True, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), nullable=False, default="new")  # new, in_progress, resolved, closed
    notes = db.Column(db.Text)


# --- Accounting domain ---


class Account(db.Model, TimestampMixin):
    __tablename__ = "accounts"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    # One of: asset, liability, equity, income, expense
    type = db.Column(db.String(20), nullable=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=True)

    parent = db.relationship("Account", remote_side=[id], backref="children")

    def is_debit_normal(self) -> bool:
        return self.type in {"asset", "expense"}


class JournalEntry(db.Model, TimestampMixin):
    __tablename__ = "journal_entries"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=date.today)
    memo = db.Column(db.String(255))
    # Optional linkage to a source object (e.g., payment)
    source = db.Column(db.String(50))
    source_id = db.Column(db.Integer)

    lines = db.relationship(
        "JournalLine",
        back_populates="entry",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )


class JournalLine(db.Model, TimestampMixin):
    __tablename__ = "journal_lines"

    id = db.Column(db.Integer, primary_key=True)
    entry_id = db.Column(db.Integer, db.ForeignKey("journal_entries.id"), nullable=False, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False, index=True)
    debit = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    credit = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    entry = db.relationship("JournalEntry", back_populates="lines")
    account = db.relationship("Account")


class Expense(db.Model, TimestampMixin):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    category = db.Column(db.String(100))
    vendor = db.Column(db.String(100))
    spent_at = db.Column(db.Date, nullable=False, default=date.today)


class Complaint(db.Model, TimestampMixin):
    __tablename__ = "complaints"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    subject = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), nullable=False, default="new")  # new, reviewing, resolved, closed
    notes = db.Column(db.Text)


# Single-tenant: removed Company and master bind usage
