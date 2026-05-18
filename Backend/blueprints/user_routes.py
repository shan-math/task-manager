import os

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

from database import get_db
from forms import CommentForm
from services.audit import log_action
from services.email_service import notify_task_completed
from services.reminders import get_due_banners
from task_helpers import apply_task_filters, get_task_tags, list_tasks_filtered
from utils import login_required

user_bp = Blueprint("user", __name__)


@user_bp.route("/dashboard")
@login_required
def dashboard():
    if session.get("role") != "user":
        return redirect(url_for("main.index"))
    page = request.args.get("page", 1, type=int)
    clauses, params = apply_task_filters(request.args)
    clauses.append("t.user_id = %s")
    params.append(session["user_id"])
    filters = (clauses, params)
    tasks, total, page, pages = list_tasks_filtered(filters, page=page)
    overdue, upcoming = get_due_banners(session["user_id"])
    return render_template(
        "user_dashboard.html",
        tasks=tasks,
        page=page,
        pages=pages,
        total=total,
        filters=request.args,
        overdue=overdue,
        upcoming=upcoming,
        username=session.get("username"),
    )


@user_bp.route("/kanban")
@login_required
def kanban():
    if session.get("role") != "user":
        return redirect(url_for("main.index"))
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id, task, priority, status, due_date
        FROM tasks WHERE user_id = %s
        """,
        (session["user_id"],),
    )
    all_tasks = cursor.fetchall()
    cursor.close()
    columns = {"Incomplete": [], "In Progress": [], "Complete": []}
    for t in all_tasks:
        columns.setdefault(t["status"], []).append(t)
    return render_template(
        "kanban.html", columns=columns, board_title="My Kanban", user_board=True
    )


@user_bp.route("/update_progress/<int:task_id>", methods=["POST"])
@login_required
def update_progress(task_id):
    status = request.form.get("status")
    db = get_db()
    cursor = db.cursor(dictionary=True)
    completed_at = "NOW()" if status == "Complete" else "NULL"
    cursor.execute(
        f"""
        UPDATE tasks SET status=%s,
            completed_at = CASE WHEN %s = 'Complete' THEN COALESCE(completed_at, NOW()) ELSE NULL END
        WHERE id=%s AND user_id=%s
        """,
        (status, status, task_id, session["user_id"]),
    )
    db.commit()
    if status == "Complete":
        cursor.execute("SELECT task FROM tasks WHERE id = %s", (task_id,))
        t = cursor.fetchone()
        cursor.execute("SELECT email FROM users WHERE role = 'admin' LIMIT 1")
        admin = cursor.fetchone()
        if admin and t:
            notify_task_completed(admin["email"], t["task"], session.get("username"))
    cursor.close()
    log_action("status_update", "task", task_id, status)
    flash("Status updated.", "success")
    return redirect(url_for("user.dashboard"))


@user_bp.route("/task/<int:task_id>", methods=["GET", "POST"])
@login_required
def task_detail(task_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM tasks WHERE id = %s AND user_id = %s",
        (task_id, session["user_id"]),
    )
    task = cursor.fetchone()
    if not task:
        flash("Task not found.", "error")
        return redirect(url_for("user.dashboard"))
    form = CommentForm()
    if form.validate_on_submit():
        cursor.execute(
            "INSERT INTO comments (task_id, user_id, body) VALUES (%s, %s, %s)",
            (task_id, session["user_id"], form.body.data),
        )
        db.commit()
        log_action("comment", "task", task_id)
        flash("Comment added.", "success")
        return redirect(url_for("user.task_detail", task_id=task_id))
    cursor.execute(
        """
        SELECT c.*, u.username FROM comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.task_id = %s ORDER BY c.created_at
        """,
        (task_id,),
    )
    comments = cursor.fetchall()
    cursor.execute(
        "SELECT * FROM attachments WHERE task_id = %s", (task_id,)
    )
    attachments = cursor.fetchall()
    cursor.close()
    return render_template(
        "task_detail.html",
        task=task,
        comments=comments,
        attachments=attachments,
        comment_form=form,
        back_url=url_for("user.dashboard"),
        task_id=task_id,
        tags=get_task_tags(task_id),
        upload_endpoint="user.upload_attachment",
    )


@user_bp.route("/task/<int:task_id>/upload", methods=["POST"])
@login_required
def upload_attachment(task_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT id FROM tasks WHERE id = %s AND user_id = %s",
        (task_id, session["user_id"]),
    )
    if not cursor.fetchone():
        flash("Task not found.", "error")
        return redirect(url_for("user.dashboard"))
    file = request.files.get("file")
    if not file or not file.filename:
        flash("No file selected.", "warning")
        return redirect(url_for("user.task_detail", task_id=task_id))
    filename = secure_filename(file.filename)
    upload_dir = current_app.config["UPLOAD_FOLDER_ABS"]
    os.makedirs(upload_dir, exist_ok=True)
    stored = f"{task_id}_{session['user_id']}_{filename}"
    path = os.path.join(upload_dir, stored)
    file.save(path)
    cursor.execute(
        """
        INSERT INTO attachments (task_id, filename, stored_path, uploaded_by)
        VALUES (%s, %s, %s, %s)
        """,
        (task_id, filename, stored, session["user_id"]),
    )
    db.commit()
    cursor.close()
    log_action("upload", "attachment", task_id, filename)
    flash("File uploaded.", "success")
    return redirect(url_for("user.task_detail", task_id=task_id))


@user_bp.route("/attachments/<path:filename>")
@login_required
def download_attachment(filename):
    upload_dir = current_app.config["UPLOAD_FOLDER_ABS"]
    return send_from_directory(upload_dir, filename, as_attachment=True)


@user_bp.route("/api/kanban/status", methods=["POST"])
@login_required
def kanban_update_status():
    data = request.get_json(silent=True) or {}
    task_id = data.get("task_id")
    status = data.get("status")
    if status not in ("Incomplete", "In Progress", "Complete"):
        return {"ok": False}, 400
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        UPDATE tasks SET status=%s,
            completed_at = CASE WHEN %s = 'Complete' THEN COALESCE(completed_at, NOW()) ELSE NULL END
        WHERE id=%s AND user_id=%s
        """,
        (status, status, task_id, session["user_id"]),
    )
    db.commit()
    cursor.close()
    return {"ok": True}
