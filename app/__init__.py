import os
from flask import Flask, request, redirect, url_for, session, render_template, send_from_directory, abort
from flask_babel import get_locale as babel_get_locale
from .config import Config
from .extensions import db, migrate, login_manager, babel
from itsdangerous import URLSafeSerializer, BadSignature

def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(config_class)

    # Ensure uploads directory exists
    os.makedirs(app.config.get("UPLOAD_FOLDER", "uploads"), exist_ok=True)

    # --- Initialize Extensions (single-tenant) ---
    app.config.setdefault("SQLALCHEMY_DATABASE_URI", config_class.SQLALCHEMY_DATABASE_URI)
    # Ensure on-disk SQLite directory exists for the default URI
    def _ensure_sqlite_dir(uri: str) -> None:
        if isinstance(uri, str) and uri.startswith("sqlite///"):
            # Handle accidental schema like 'sqlite///' (rare)
            path = uri.replace("sqlite///", "", 1)
        elif isinstance(uri, str) and uri.startswith("sqlite:///"):
            path = uri.replace("sqlite:///", "", 1)
        else:
            return
        import os as _os
        _os.makedirs(_os.path.dirname(path), exist_ok=True)

    _ensure_sqlite_dir(app.config["SQLALCHEMY_DATABASE_URI"])

    db.init_app(app)
    # Single database
    migrate.init_app(app, db)
    login_manager.init_app(app)
    babel.init_app(app, locale_selector=select_locale)

    # Login Manager
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    # --- Import Models after db init ---
    from .models import User  # noqa: WPS433

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.query.get(int(user_id))

    # --- Blueprints ---
    from .auth.routes import auth_bp
    from .admin.routes import admin_bp
    from .employee.routes import employee_bp
    from .tenant.routes import tenant_bp
    from .accountant.routes import accountant_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(employee_bp, url_prefix="/employee")
    app.register_blueprint(tenant_bp, url_prefix="/tenant")
    app.register_blueprint(accountant_bp, url_prefix="/accountant")

    # CLI commands
    from .cli import register_cli
    register_cli(app)

    # --- Context Processor ---
    @app.context_processor
    def inject_get_locale():
        return {"get_locale": lambda: str(babel_get_locale())}

    # Single-tenant: no company theming injection

    # --- Routes ---
    @app.route("/")
    def index():
        from flask_login import current_user

        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        role_redirect = {
            "admin": "admin.dashboard",
            "employee": "employee.dashboard",
            "tenant": "tenant.dashboard",
            "accountant": "accountant.dashboard",
        }
        return redirect(url_for(role_redirect.get(current_user.role, "auth.login")))

    # Single-tenant: no per-request tenant DB binding

    @app.route("/set-lang/<lang_code>")
    def set_language(lang_code: str):
        if lang_code in app.config.get("LANGUAGES", {}):
            session["lang"] = lang_code
        return redirect(request.referrer or url_for("index"))

    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename: str):
        upload_folder = app.config.get("UPLOAD_FOLDER", "uploads")
        return send_from_directory(upload_folder, filename, as_attachment=False)

    # --- Initialize database schema on first run ---
    with app.app_context():
        try:
            db.create_all()
        except Exception:
            pass

    # --- Public Share Route for Property Details ---
    def _get_property_share_serializer() -> URLSafeSerializer:
        secret_key = app.config.get("SECRET_KEY")
        return URLSafeSerializer(secret_key, salt="property-share")

    @app.route("/p/<token>")
    def public_property_view(token: str):
        try:
            serializer = _get_property_share_serializer()
            property_id = serializer.loads(token)
        except BadSignature:
            return abort(404)

        from .models import Property  # local import to avoid circulars

        prop = Property.query.get_or_404(int(property_id))

        # Prepare images list from stored comma-separated paths
        images = []
        if prop.images:
            images = [p.strip() for p in prop.images.split(",") if p.strip()]

        return render_template(
            "public/property_view.html",
            prop=prop,
            images=images,
        )

    # --- Error Handlers ---
    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("403.html"), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("404.html"), 404

    return app


# --- Helper Functions ---
def select_locale():
    """Return the selected locale from session or default."""
    from flask import session, request
    lang = session.get("lang")
    if lang:
        return lang
    return request.accept_languages.best_match(Config.LANGUAGES.keys())
