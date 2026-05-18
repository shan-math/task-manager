from datetime import date, datetime
from functools import wraps

from flask import flash, redirect, session, url_for
from werkzeug.security import check_password_hash

DATE_DISPLAY_FMT = "%d-%m-%Y"
DATE_INPUT_FMTS = ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d")


def parse_date_input(value):
    """Parse user-facing date string to date object."""
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    for fmt in DATE_INPUT_FMTS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def format_date_display(value):
    """Format date for UI display (dd-mm-yyyy)."""
    if not value:
        return ""
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.strftime(DATE_DISPLAY_FMT)
    parsed = parse_date_input(value)
    return parsed.strftime(DATE_DISPLAY_FMT) if parsed else str(value)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return decorated


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("auth.login"))
            if session.get("role") not in roles:
                flash("Access denied.", "error")
                return redirect(url_for("main.index"))
            return f(*args, **kwargs)

        return decorated

    return decorator


admin_required = role_required("admin")
manager_required = role_required("admin", "manager")
staff_required = role_required("admin", "manager")


def verify_password(stored_hash, password):
    return check_password_hash(stored_hash, password)


def due_label(due_date, status):
    if not due_date or status == "Complete":
        return ""
    d = parse_date_input(due_date)
    if not d:
        return ""
    today = date.today()
    if d < today:
        return "overdue"
    if d == today:
        return "today"
    from datetime import timedelta

    if d <= today + timedelta(days=7):
        return "week"
    return ""


def paginate(total, page, per_page):
    pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, pages))
    offset = (page - 1) * per_page
    return page, pages, offset
