import csv
import io
import os
from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)
from fpdf import FPDF
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from database import get_db
from forms import CategoryForm, TaskForm, UserAdminForm
from services.audit import log_action
from task_helpers import (
    apply_task_filters,
    create_task,
    get_analytics,
    get_assignable_users,
    get_categories,
    get_tags,
    get_task_tags,
    list_tasks_filtered,
    update_task,
)
from utils import admin_required, format_date_display

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    page = request.args.get("page", 1, type=int)
    filters = apply_task_filters(request.args)
    tasks, total, page, pages = list_tasks_filtered(filters, page=page)
    return render_template(
        "admin_dashboard.html",
        tasks=tasks,
        page=page,
        pages=pages,
        total=total,
        filters=request.args,
    )


@admin_bp.route("/analytics")
@admin_required
def analytics():
    data = get_analytics()
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT a.*, u.username FROM audit_log a
        LEFT JOIN users u ON a.user_id = u.id
        ORDER BY a.created_at DESC LIMIT 50
        """
    )
    audit = cursor.fetchall()
    cursor.close()
    return render_template("admin_analytics.html", analytics=data, audit=audit)


@admin_bp.route("/kanban")
@admin_required
def kanban():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT t.id, t.task, t.priority, t.status, t.due_date, u.username
        FROM tasks t JOIN users u ON t.user_id = u.id
        ORDER BY t.priority DESC
        """
    )
    all_tasks = cursor.fetchall()
    cursor.close()
    columns = {"Incomplete": [], "In Progress": [], "Complete": []}
    for t in all_tasks:
        columns.setdefault(t["status"], []).append(t)
    return render_template("kanban.html", columns=columns, board_title="Admin Kanban")


@admin_bp.route("/add_task", methods=["GET", "POST"])
@admin_required
def add_task():
    form = TaskForm()
    form.user_id.choices = [(u["id"], u["username"]) for u in get_assignable_users("admin")]
    form.category_id.choices = [(0, "— None —")] + [
        (c["id"], c["name"]) for c in get_categories()
    ]
    tags = get_tags()
    form.tags.choices = [(t["id"], t["name"]) for t in tags]
    if form.validate_on_submit():
        create_task(
            {
                "user_id": form.user_id.data,
                "task": form.task.data,
                "description": form.description.data,
                "priority": form.priority.data,
                "status": form.status.data,
                "category_id": form.category_id.data or None,
                "due_date": form.due_date.data or None,
                "tags": form.tags.data,
            },
            session["user_id"],
        )
        flash("Task added successfully.", "success")
        return redirect(url_for("admin.dashboard"))
    return render_template("add_task.html", form=form, tags=tags)


@admin_bp.route("/edit_task/<int:task_id>", methods=["GET", "POST"])
@admin_required
def edit_task(task_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
    task = cursor.fetchone()
    cursor.close()
    if not task:
        flash("Task not found.", "error")
        return redirect(url_for("admin.dashboard"))
    form = TaskForm()
    form.user_id.choices = [(u["id"], u["username"]) for u in get_assignable_users("admin")]
    form.category_id.choices = [(0, "— None —")] + [
        (c["id"], c["name"]) for c in get_categories()
    ]
    tags = get_tags()
    form.tags.choices = [(t["id"], t["name"]) for t in tags]
    if form.validate_on_submit():
        update_task(
            task_id,
            {
                "user_id": form.user_id.data,
                "task": form.task.data,
                "description": form.description.data,
                "priority": form.priority.data,
                "status": form.status.data,
                "category_id": form.category_id.data or None,
                "due_date": form.due_date.data or None,
                "tags": form.tags.data,
            },
            notify_complete=True,
        )
        flash("Task updated.", "success")
        return redirect(url_for("admin.dashboard"))
    if request.method == "GET":
        form.task.data = task["task"]
        form.description.data = task.get("description")
        form.priority.data = task["priority"]
        form.status.data = task["status"]
        form.user_id.data = task["user_id"]
        form.category_id.data = task.get("category_id") or 0
        form.due_date.data = format_date_display(task.get("due_date"))
        form.tags.data = [t["id"] for t in get_task_tags(task_id)]
    return render_template(
        "edit_task.html",
        form=form,
        task=task,
        task_id=task_id,
        tags=tags,
    )


@admin_bp.route("/delete_task/<int:task_id>", methods=["POST"])
@admin_required
def delete_task(task_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    db.commit()
    cursor.close()
    log_action("delete", "task", task_id)
    flash("Task deleted.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/bulk", methods=["POST"])
@admin_required
def bulk_action():
    form = BulkActionForm()
    if not form.validate_on_submit():
        flash("Invalid bulk action.", "error")
        return redirect(url_for("admin.dashboard"))
    ids = request.form.getlist("task_ids")
    if not ids:
        flash("No tasks selected.", "warning")
        return redirect(url_for("admin.dashboard"))
    db = get_db()
    cursor = db.cursor()
    placeholders = ",".join(["%s"] * len(ids))
    action = form.action.data
    if action == "delete":
        cursor.execute(f"DELETE FROM tasks WHERE id IN ({placeholders})", ids)
    elif action == "status_incomplete":
        cursor.execute(
            f"UPDATE tasks SET status='Incomplete', completed_at=NULL WHERE id IN ({placeholders})",
            ids,
        )
    elif action == "status_progress":
        cursor.execute(
            f"UPDATE tasks SET status='In Progress', completed_at=NULL WHERE id IN ({placeholders})",
            ids,
        )
    elif action == "status_complete":
        cursor.execute(
            f"UPDATE tasks SET status='Complete', completed_at=NOW() WHERE id IN ({placeholders})",
            ids,
        )
    db.commit()
    cursor.close()
    log_action("bulk", "task", details=f"{action}:{','.join(ids)}")
    flash(f"Bulk action applied to {len(ids)} task(s).", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/task/<int:task_id>", methods=["GET", "POST"])
@admin_required
def task_detail(task_id):
    from forms import CommentForm

    form = CommentForm()
    if form.validate_on_submit():
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO comments (task_id, user_id, body) VALUES (%s, %s, %s)",
            (task_id, session["user_id"], form.body.data),
        )
        db.commit()
        cursor.close()
        log_action("comment", "task", task_id)
        flash("Comment added.", "success")
        return redirect(url_for("admin.task_detail", task_id=task_id))
    return _task_detail(task_id, "admin.dashboard", form)


@admin_bp.route("/task/<int:task_id>/upload", methods=["POST"])
@admin_required
def upload_attachment(task_id):
    file = request.files.get("file")
    if not file or not file.filename:
        flash("No file selected.", "warning")
        return redirect(url_for("admin.task_detail", task_id=task_id))
    filename = secure_filename(file.filename)
    upload_dir = current_app.config["UPLOAD_FOLDER_ABS"]
    os.makedirs(upload_dir, exist_ok=True)
    stored = f"{task_id}_{session['user_id']}_{filename}"
    path = os.path.join(upload_dir, stored)
    file.save(path)
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        INSERT INTO attachments (task_id, filename, stored_path, uploaded_by)
        VALUES (%s, %s, %s, %s)
        """,
        (task_id, filename, stored, session["user_id"]),
    )
    db.commit()
    cursor.close()
    flash("File uploaded.", "success")
    return redirect(url_for("admin.task_detail", task_id=task_id))


@admin_bp.route("/attachments/<path:filename>")
@admin_required
def download_attachment(filename):
    upload_dir = current_app.config["UPLOAD_FOLDER_ABS"]
    return send_from_directory(upload_dir, filename, as_attachment=True)


@admin_bp.route("/api/kanban/status", methods=["POST"])
@admin_required
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
        WHERE id=%s
        """,
        (status, status, task_id),
    )
    db.commit()
    cursor.close()
    return {"ok": True}


@admin_bp.route("/users", methods=["GET", "POST"])
@admin_required
def manage_users():
    form = UserAdminForm()
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, name FROM teams ORDER BY name")
    teams = cursor.fetchall()
    form.team_id.choices = [(0, "— None —")] + [(t["id"], t["name"]) for t in teams]
    if form.validate_on_submit() and request.method == "POST":
        pw = form.password.data
        pw_hash = generate_password_hash(pw) if pw else None
        team = form.team_id.data or None
        if team == 0:
            team = None
        try:
            if pw_hash:
                cursor.execute(
                    """
                    INSERT INTO users (username, email, password_hash, role, team_id)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (form.username.data, form.email.data, pw_hash, form.role.data, team),
                )
            else:
                flash("Password required for new users.", "error")
                raise ValueError("password")
            db.commit()
            flash("User created.", "success")
        except Exception:
            db.rollback()
            flash("Could not create user.", "error")
    cursor.execute(
        """
        SELECT u.id, u.username, u.email, u.role, t.name AS team_name
        FROM users u LEFT JOIN teams t ON u.team_id = t.id
        ORDER BY u.username
        """
    )
    users = cursor.fetchall()
    cursor.close()
    return render_template("admin_users.html", users=users, form=form, teams=teams)


@admin_bp.route("/categories", methods=["GET", "POST"])
@admin_required
def categories():
    form = CategoryForm()
    if form.validate_on_submit():
        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute(
                "INSERT INTO categories (name) VALUES (%s)", (form.name.data,)
            )
            db.commit()
            flash("Category added.", "success")
        except Exception:
            flash("Category already exists.", "error")
        cursor.close()
    cats = get_categories()
    return render_template("admin_categories.html", categories=cats, form=form)


@admin_bp.route("/export/csv")
@admin_required
def export_csv():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT t.id, u.username, t.task, t.priority, t.status, t.due_date,
               c.name AS category, t.created_at, t.completed_at
        FROM tasks t
        JOIN users u ON t.user_id = u.id
        LEFT JOIN categories c ON t.category_id = c.id
        ORDER BY t.id
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "id",
            "username",
            "task",
            "priority",
            "status",
            "due_date",
            "category",
            "created_at",
            "completed_at",
        ],
    )
    writer.writeheader()
    for r in rows:
        writer.writerow(
            {k: (r.get(k) if r.get(k) is not None else "") for k in writer.fieldnames}
        )
    mem = io.BytesIO()
    mem.write(output.getvalue().encode("utf-8"))
    mem.seek(0)
    return send_file(
        mem,
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"tasks_{datetime.now().strftime('%Y%m%d')}.csv",
    )


@admin_bp.route("/export/pdf")
@admin_required
def export_pdf():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT t.task, u.username, t.priority, t.status, t.due_date
        FROM tasks t JOIN users u ON t.user_id = u.id
        ORDER BY t.id LIMIT 200
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "Task Export Report", ln=True)
    for r in rows:
        line = f"{r['task'][:60]} | {r['username']} | {r['priority']} | {r['status']}"
        pdf.cell(0, 8, line[:120], ln=True)
    mem = io.BytesIO(pdf.output())
    mem.seek(0)
    return send_file(
        mem,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"tasks_{datetime.now().strftime('%Y%m%d')}.pdf",
    )


def _task_detail(task_id, back_endpoint, comment_form=None):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT t.*, u.username, c.name AS category_name
        FROM tasks t
        JOIN users u ON t.user_id = u.id
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.id = %s
        """,
        (task_id,),
    )
    task = cursor.fetchone()
    if not task:
        flash("Task not found.", "error")
        return redirect(url_for("admin.dashboard"))
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
        """
        SELECT a.*, u.username FROM attachments a
        JOIN users u ON a.uploaded_by = u.id
        WHERE a.task_id = %s
        """,
        (task_id,),
    )
    attachments = cursor.fetchall()
    cursor.close()
    from forms import CommentForm

    return render_template(
        "task_detail.html",
        task=task,
        comments=comments,
        attachments=attachments,
        comment_form=comment_form or CommentForm(),
        back_url=url_for(back_endpoint),
        task_id=task_id,
        tags=get_task_tags(task_id),
        upload_endpoint="admin.upload_attachment",
    )
