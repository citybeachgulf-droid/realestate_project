from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, abort
from flask_login import login_user, logout_user, login_required
from flask_babel import gettext as _
from ..extensions import db
from ..models import User
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash(_("Welcome back, %(user)s", user=user.username), "success")
            return redirect(url_for("index"))

        flash(_("Invalid credentials"), "danger")

    return render_template("auth/login.html")



@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash(_("You have been logged out"), "info")
    return redirect(url_for("auth.login"))


def _get_company_setup_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config.get("SECRET_KEY"), salt="company-setup")

# Single-tenant: company setup flow removed

