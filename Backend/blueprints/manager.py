from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from database import get_db
from forms import TaskForm
from task_helpers import (
    apply_task_filters,
    create_task,
    get_assignable_users,
    get_categories,
    get_tags,
    get_task_tags,
    list_tasks_filtered,
    update_task,
)
from utils import manager_required

manager_bp = Blueprint("manager", __name__, url_prefix="/manager")


def _team_user_ids():
    db = get_db()
    cursor = db.cursor()
    team_id = session.get("team_id")
    if not team_id:
        cursor.close()
        return []
    cursor.execute(
        "SELECT id FROM users WHERE team_id = %s AND role = 'user'", (team_id,)
    )
    ids = [r[0] for r in cursor.fetchall()]
    cursor.close()
    return ids


@manager_bp.route("/dashboard")
@manager_required
def dashboard():
    page = request.args.get("page", 1, type=int)
    filters = apply_task_filters(request.args)
    tasks, total, page, pages = list_tasks_filtered(
        filters, team_user_ids=_team_user_ids(), page=page
    )
    return render_template(
        "manager_dashboard.html",
        tasks=tasks,
        page=page,
        pages=pages,
        total=total,
        filters=request.args,
    )


@manager_bp.route("/add_task", methods=["GET", "POST"])
@manager_required
def add_task():
    form = TaskForm()
    users = get_assignable_users("manager", session.get("team_id"))
    form.user_id.choices = [(u["id"], u["username"]) for u in users]
    form.category_id.choices = [(0, "— None —")] + [
        (c["id"], c["name"]) for c in get_categories()
    ]
    tags = get_tags()
    form.tags.choices = [(t["id"], t["name"]) for t in tags]
    if request.method == "POST":
        form.status.data = "Incomplete"
    if form.validate_on_submit():
        if form.user_id.data not in [u["id"] for u in users]:
            flash("Cannot assign outside your team.", "error")
            return redirect(url_for("manager.add_task"))
        create_task(
            {
                "user_id": form.user_id.data,
                "task": form.task.data,
                "description": form.description.data,
                "priority": form.priority.data,
                "status": "Incomplete",
                "category_id": form.category_id.data or None,
                "due_date": form.due_date.data,
                "tags": form.tags.data,
            },
            session["user_id"],
        )
        flash("Task assigned to team member.", "success")
        return redirect(url_for("manager.dashboard"))
    return render_template("add_task.html", form=form, tags=tags, manager=True)


@manager_bp.route("/kanban")
@manager_required
def kanban():
    ids = _team_user_ids()
    if not ids:
        columns = {"Incomplete": [], "In Progress": [], "Complete": []}
        return render_template(
            "kanban.html", columns=columns, board_title="Team Kanban"
        )
    db = get_db()
    cursor = db.cursor(dictionary=True)
    placeholders = ",".join(["%s"] * len(ids))
    cursor.execute(
        f"""
        SELECT t.id, t.task, t.priority, t.status, t.due_date, u.username
        FROM tasks t JOIN users u ON t.user_id = u.id
        WHERE t.user_id IN ({placeholders})
        """,
        ids,
    )
    all_tasks = cursor.fetchall()
    cursor.close()
    columns = {"Incomplete": [], "In Progress": [], "Complete": []}
    for t in all_tasks:
        columns.setdefault(t["status"], []).append(t)
    return render_template("kanban.html", columns=columns, board_title="Team Kanban")


@manager_bp.route("/api/kanban/status", methods=["POST"])
@manager_required
def kanban_update_status():
    data = request.get_json(silent=True) or {}
    task_id = data.get("task_id")
    status = data.get("status")
    if status not in ("Incomplete", "In Progress", "Complete"):
        return {"ok": False}, 400
    ids = _team_user_ids()
    if not ids:
        return {"ok": False}, 403
    db = get_db()
    cursor = db.cursor()
    placeholders = ",".join(["%s"] * len(ids))
    cursor.execute(
        f"""
        UPDATE tasks SET status=%s,
            completed_at = CASE WHEN %s = 'Complete' THEN COALESCE(completed_at, NOW()) ELSE NULL END
        WHERE id=%s AND user_id IN ({placeholders})
        """,
        (status, status, task_id, *ids),
    )
    db.commit()
    cursor.close()
    return {"ok": True}
