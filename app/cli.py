from datetime import date, timedelta
import click
from flask import Flask
from .extensions import db
from .models import User, Property, Contract, Payment, Account
import subprocess
import sys


def register_cli(app: Flask) -> None:
    @app.cli.command("compile-translations")
    def compile_translations():
        try:
            subprocess.check_call([sys.executable, "-m", "babel.messages.frontend", "compile_catalog", "-d", "app/translations"])  # type: ignore
        except Exception:
            subprocess.check_call(["pybabel", "compile", "-d", "app/translations"])  # type: ignore
    @app.cli.command("create-admin")
    @click.option("--username", prompt=True)
    @click.option("--email", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(username: str, email: str, password: str):
        if User.query.filter((User.username == username) | (User.email == email)).first():
            click.echo("User with same username or email already exists")
            return
        user = User(username=username, email=email, role="admin")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo("Admin created")

    @app.cli.command("migrate-remove-superadmin")
    def migrate_remove_superadmin():
        """Migrate existing users with role 'superadmin' to 'admin'."""
        updated = 0
        try:
            updated = User.query.filter_by(role="superadmin").update({User.role: "admin"})
            db.session.commit()
        except Exception:
            db.session.rollback()
            click.echo("Migration failed; database rolled back")
            return
        click.echo(f"Updated {updated} users from superadmin to admin")

    @app.cli.command("seed-data")
    def seed_data():
        # Basic roles users
        if not User.query.filter_by(username="employee").first():
            u = User(username="employee", email="employee@example.com", role="employee")
            u.set_password("password")
            db.session.add(u)
        if not User.query.filter_by(username="tenant").first():
            t = User(username="tenant", email="tenant@example.com", role="tenant")
            t.set_password("password")
            db.session.add(t)
        if not User.query.filter_by(username="accountant").first():
            a = User(username="accountant", email="accountant@example.com", role="accountant")
            a.set_password("password")
            db.session.add(a)

        # Properties
        if Property.query.count() == 0:
            p1 = Property(title="Apartment A", description="Sea view", price=800.00, status="available")
            p2 = Property(title="Villa B", description="Garden", price=2500.00, status="available")
            db.session.add_all([p1, p2])
            db.session.flush()

        db.session.commit()

        # Seed minimal chart of accounts
        def _get_or_create_account(code: str, name: str, acc_type: str) -> Account:
            acc = Account.query.filter_by(code=code).first()
            if not acc:
                acc = Account(code=code, name=name, type=acc_type)
                db.session.add(acc)
                db.session.commit()
            return acc

        _get_or_create_account("1000", "Cash", "asset")
        _get_or_create_account("1100", "Accounts Receivable", "asset")
        _get_or_create_account("4000", "Rental Income", "income")
        _get_or_create_account("5000", "General Expenses", "expense")

        # Contracts and payments
        tenant = User.query.filter_by(role="tenant").first()
        prop = Property.query.first()
        if tenant and prop and not Contract.query.first():
            contract = Contract(
                property_id=prop.id,
                tenant_id=tenant.id,
                start_date=date.today(),
                end_date=date.today() + timedelta(days=365),
                rent_amount=prop.price,
                status="active",
            )
            db.session.add(contract)
            db.session.flush()
            for i in range(1, 4):
                payment = Payment(
                    contract_id=contract.id,
                    amount=prop.price,
                    due_date=date.today() + timedelta(days=30 * i),
                    status="unpaid",
                )
                db.session.add(payment)
            db.session.commit()
        click.echo("Seed data inserted")

    # Single-tenant: removed tenant management CLI commands

