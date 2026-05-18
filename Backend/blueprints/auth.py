from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash

from database import get_db
from forms import LoginForm, SignupForm
from services.audit import log_action
from services.reminders import get_due_banners
from utils import verify_password

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, username, email, password_hash, role, team_id FROM users WHERE username = %s",
            (form.username.data,),
        )
        user = cursor.fetchone()
        cursor.close()
        if user and verify_password(user["password_hash"], form.password.data):
            session.clear()
            session.permanent = True
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            session["team_id"] = user["team_id"]
            log_action("login", "user", user["id"])
            flash("Welcome back!", "success")
            return _redirect_for_role(user["role"])
        flash("Invalid credentials.", "error")
    return render_template("login.html", form=form)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO users (username, email, password_hash, role)
                VALUES (%s, %s, %s, 'user')
                """,
                (
                    form.username.data,
                    form.email.data,
                    generate_password_hash(form.password.data),
                ),
            )
            db.commit()
            log_action("signup", "user", cursor.lastrowid, form.username.data)
            flash("Account created. Please log in.", "success")
            return redirect(url_for("auth.login"))
        except Exception:
            db.rollback()
            flash("Username or email already exists.", "error")
        finally:
            cursor.close()
    return render_template("signup.html", form=form)


@auth_bp.route("/logout")
def logout():
    log_action("logout", "user", session.get("user_id"))
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


def _redirect_for_role(role):
    if role == "admin":
        return redirect(url_for("admin.dashboard"))
    if role == "manager":
        return redirect(url_for("manager.dashboard"))
    return redirect(url_for("user.dashboard"))


def store_session_banners():
    if session.get("role") == "user" and session.get("user_id"):
        overdue, upcoming = get_due_banners(session["user_id"])
        session["due_overdue"] = overdue
        session["due_upcoming"] = upcoming
