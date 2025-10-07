# Multi-tenant Real Estate Management (Flask)

This project implements a real estate management system.

## Key Concepts
- Master DB (bind `master`) stores companies and branding.
- Tenant DB: each company has its own database (SQLite by default; can be PostgreSQL/MySQL by providing a DB URI).
- On login, users select a company. The app binds the SQLAlchemy default engine to that company for the request lifecycle.
- Theming: `g.company_theme` is injected with colors and font.

## Structure
- `app/models.py`: Tenant models and `Company` (bound to `master`).
- `app/tenant_manager.py`: Utilities for per-company DB creation, export, deletion.
- `app/cli.py`: `flask tenant-create|tenant-export|tenant-delete` commands.

## Setup
1. Create env: `python -m venv venv && source venv/bin/activate`
2. Install deps: `pip install -r requirements.txt`
3. Set env: `cp .env.example .env` and update `MASTER_DATABASE_URI` etc.
4. Init DBs: `python create_db.py` (creates default tenant), then `flask seed-data`.

## Multi-tenancy
- Create a company: `flask tenant-create --name "Acme" --subdomain acme`
- Log in: select the company on login screen.
- Export: `flask tenant-export --subdomain acme --out backups/acme.db`
- Delete: `flask tenant-delete --subdomain acme`

## Notes
- For PostgreSQL/MySQL, set `--db-uri` when creating the tenant and use native tools for export/backup.
