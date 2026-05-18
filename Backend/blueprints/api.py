from flask import Blueprint, current_app, jsonify, request, session

from database import get_db
from utils import login_required

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _auth_api():
    token = request.headers.get("X-API-Token") or request.args.get("api_token")
    if current_app.config.get("API_TOKEN") and token == current_app.config["API_TOKEN"]:
        return True
    return "user_id" in session


@api_bp.route("/tasks")
def list_tasks():
    if not _auth_api():
        return jsonify({"error": "Unauthorized"}), 401
    db = get_db()
    cursor = db.cursor(dictionary=True)
    user_id = session.get("user_id")
    role = session.get("role")
    if role == "user" and user_id:
        cursor.execute(
            """
            SELECT t.id, t.task, t.priority, t.status, t.due_date, t.created_at
            FROM tasks t WHERE t.user_id = %s
            """,
            (user_id,),
        )
    else:
        cursor.execute(
            """
            SELECT t.id, t.task, t.priority, t.status, t.due_date,
                   u.username AS assignee, t.created_at
            FROM tasks t JOIN users u ON t.user_id = u.id
            """
        )
    rows = cursor.fetchall()
    for r in rows:
        for k, v in r.items():
            if hasattr(v, "isoformat"):
                r[k] = v.isoformat()
    cursor.close()
    return jsonify({"tasks": rows})


@api_bp.route("/tasks/<int:task_id>")
def get_task(task_id):
    if not _auth_api():
        return jsonify({"error": "Unauthorized"}), 401
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT t.*, u.username FROM tasks t
        JOIN users u ON t.user_id = u.id WHERE t.id = %s
        """,
        (task_id,),
    )
    task = cursor.fetchone()
    cursor.close()
    if not task:
        return jsonify({"error": "Not found"}), 404
    if session.get("role") == "user" and task["user_id"] != session.get("user_id"):
        return jsonify({"error": "Forbidden"}), 403
    return jsonify(task)


@api_bp.route("/analytics")
def analytics_summary():
    if not _auth_api() or session.get("role") not in ("admin", "manager"):
        if not (
            current_app.config.get("API_TOKEN")
            and request.headers.get("X-API-Token") == current_app.config["API_TOKEN"]
        ):
            return jsonify({"error": "Forbidden"}), 403
    from task_helpers import get_analytics

    return jsonify(get_analytics())
