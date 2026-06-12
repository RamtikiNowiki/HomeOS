from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db
from ..models import User
from . import auth_bp


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    users = User.query.order_by(User.id).all()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash("Invalid credentials — access denied.", "error")
            return redirect(url_for("auth.login"))
        login_user(user, remember=True)
        return redirect(request.args.get("next") or url_for("main.dashboard"))

    return render_template("auth/login.html", users=users)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Signed out. See you at the next session.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/switch", methods=["POST"])
@login_required
def switch_profile():
    """Log out and return to profile selection — quick profile switching."""
    logout_user()
    return redirect(url_for("auth.login"))
