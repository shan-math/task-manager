from datetime import datetime

from flask import current_app, session

from database import get_db
from services.audit import log_action
from services.email_service import notify_task_assigned, notify_task_completed
from utils import format_date_display, parse_date_input


def _filter_clause(args, prefix=""):
    p = f"{prefix}" if prefix else ""
    clauses = []
    params = []
    if args.get("q"):
        clauses.append(f"({p}task LIKE %s OR {p}description LIKE %s)")
        q = f"%{args['q']}%"
        params.extend([q, q])
    if args.get("status"):
        clauses.append(f"{p}status = %s")
        params.append(args["status"])
    if args.get("priority"):
        clauses.append(f"{p}priority = %s")
        params.append(args["priority"])
    if args.get("category_id"):
        clauses.append(f"{p}category_id = %s")
        params.append(args["category_id"])
    if args.get("assignee_id"):
        clauses.append(f"{p}user_id = %s")
        params.append(args["assignee_id"])
    if args.get("due_from"):
        due_from = parse_date_input(args["due_from"])
        if due_from:
            clauses.append(f"{p}due_date >= %s")
            params.append(due_from)
    if args.get("due_to"):
        due_to = parse_date_input(args["due_to"])
        if due_to:
            clauses.append(f"{p}due_date <= %s")
            params.append(due_to)
    if args.get("overdue") == "1":
        clauses.append(
            f"{p}due_date < CURDATE() AND {p}status != 'Complete'"
        )
    return clauses, params


def fetch_tasks_list(where_extra="", params=None, page=1, order="t.created_at DESC"):
    params = list(params or [])
    per_page = current_app.config["ITEMS_PER_PAGE"]
    db = get_db()
    cursor = db.cursor(dictionary=True)
    base = """
        FROM tasks t
        JOIN users u ON t.user_id = u.id
        LEFT JOIN categories c ON t.category_id = c.id
    """
    where = " WHERE 1=1 "
    if where_extra:
        where += f" AND {where_extra}"
    filter_clauses, filter_params = _filter_clause(
        {k: session.get(f"filter_{k}") for k in ("q", "status", "priority")}
        if False
        else {},
    )
    cursor.execute(f"SELECT COUNT(*) AS cnt {base} {where}", params)
    total = cursor.fetchone()["cnt"]
    from utils import paginate

    page, pages, offset = paginate(total, page, per_page)
    cursor.execute(
        f"""
        SELECT t.*, u.username, c.name AS category_name
        {base} {where}
        ORDER BY {order}
        LIMIT %s OFFSET %s
        """,
        params + [per_page, offset],
    )
    tasks = cursor.fetchall()
    for task in tasks:
        task["tags"] = get_task_tags(task["id"])
    cursor.close()
    return tasks, total, page, pages


def get_task_tags(task_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT tg.id, tg.name FROM tags tg
        JOIN task_tags tt ON tt.tag_id = tg.id
        WHERE tt.task_id = %s
        """,
        (task_id,),
    )
    tags = cursor.fetchall()
    cursor.close()
    return tags


def set_task_tags(task_id, tag_ids):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM task_tags WHERE task_id = %s", (task_id,))
    for tid in tag_ids or []:
        if tid:
            cursor.execute(
                "INSERT IGNORE INTO task_tags (task_id, tag_id) VALUES (%s, %s)",
                (task_id, int(tid)),
            )
    db.commit()
    cursor.close()


def apply_task_filters(request_args):
    return _filter_clause(dict(request_args))


def build_task_query(filters, team_user_ids=None):
    clauses, params = filters
    if team_user_ids is not None:
        if not team_user_ids:
            clauses.append("1=0")
        else:
            placeholders = ",".join(["%s"] * len(team_user_ids))
            clauses.append(f"t.user_id IN ({placeholders})")
            params.extend(team_user_ids)
    where = " AND ".join(clauses) if clauses else "1=1"
    return where, params


def list_tasks_filtered(filters, team_user_ids=None, page=1, order="t.due_date IS NULL, t.due_date ASC, t.created_at DESC"):
    clauses, params = filters
    where, params = build_task_query((clauses, params), team_user_ids)
    per_page = current_app.config["ITEMS_PER_PAGE"]
    db = get_db()
    cursor = db.cursor(dictionary=True)
    base = """
        FROM tasks t
        JOIN users u ON t.user_id = u.id
        LEFT JOIN categories c ON t.category_id = c.id
    """
    cursor.execute(f"SELECT COUNT(*) AS cnt {base} WHERE {where}", params)
    total = cursor.fetchone()["cnt"]
    from utils import paginate

    page, pages, offset = paginate(total, page, per_page)
    cursor.execute(
        f"""
        SELECT t.*, u.username, c.name AS category_name
        {base}
        WHERE {where}
        ORDER BY {order}
        LIMIT %s OFFSET %s
        """,
        params + [per_page, offset],
    )
    tasks = cursor.fetchall()
    for task in tasks:
        task["tags"] = get_task_tags(task["id"])
    cursor.close()
    return tasks, total, page, pages


def get_assignable_users(role, team_id=None):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    if role == "admin":
        cursor.execute(
            "SELECT id, username FROM users WHERE role IN ('user', 'manager') ORDER BY username"
        )
    else:
        cursor.execute(
            """
            SELECT id, username FROM users
            WHERE role = 'user' AND team_id = %s
            ORDER BY username
            """,
            (team_id,),
        )
    users = cursor.fetchall()
    cursor.close()
    return users


def get_categories():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, name FROM categories ORDER BY name")
    cats = cursor.fetchall()
    cursor.close()
    return cats


def get_tags():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, name FROM tags ORDER BY name")
    tags = cursor.fetchall()
    cursor.close()
    return tags


def ensure_tag(name):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT IGNORE INTO tags (name) VALUES (%s)", (name.strip(),))
    db.commit()
    cursor.execute("SELECT id FROM tags WHERE name = %s", (name.strip(),))
    row = cursor.fetchone()
    cursor.close()
    return row[0] if row else None


def create_task(data, actor_id, send_mail=True):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        INSERT INTO tasks (user_id, task, description, priority, status, category_id, due_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            data["user_id"],
            data["task"],
            data.get("description"),
            data["priority"],
            data.get("status", "Incomplete"),
            data.get("category_id") or None,
            parse_date_input(data.get("due_date")) or None,
        ),
    )
    task_id = cursor.lastrowid
    set_task_tags(task_id, data.get("tags"))
    db.commit()
    cursor.execute(
        "SELECT email, username FROM users WHERE id = %s", (data["user_id"],)
    )
    assignee = cursor.fetchone()
    cursor.close()
    log_action("create", "task", task_id, data["task"])
    if send_mail and assignee:
        notify_task_assigned(
            assignee["email"],
            assignee["username"],
            data["task"],
            format_date_display(data.get("due_date")) if data.get("due_date") else None,
        )
    return task_id


def update_task(task_id, data, notify_complete=False):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    completed_at = None
    if data.get("status") == "Complete":
        completed_at = datetime.utcnow()
    cursor.execute(
        """
        UPDATE tasks SET task=%s, description=%s, priority=%s, status=%s,
            category_id=%s, due_date=%s, user_id=%s,
            completed_at = CASE WHEN %s = 'Complete' THEN COALESCE(completed_at, %s) ELSE NULL END
        WHERE id=%s
        """,
        (
            data["task"],
            data.get("description"),
            data["priority"],
            data["status"],
            data.get("category_id") or None,
            parse_date_input(data.get("due_date")) or None,
            data["user_id"],
            data["status"],
            completed_at,
            completed_at,
            task_id,
        ),
    )
    set_task_tags(task_id, data.get("tags"))
    db.commit()
    if notify_complete and data.get("status") == "Complete":
        cursor.execute(
            "SELECT email FROM users WHERE role = 'admin' LIMIT 1"
        )
        admin = cursor.fetchone()
        cursor.execute("SELECT username FROM users WHERE id = %s", (data["user_id"],))
        user = cursor.fetchone()
        if admin:
            notify_task_completed(
                admin["email"], data["task"], user["username"] if user else ""
            )
    cursor.close()
    log_action("update", "task", task_id, data["task"])


def get_analytics():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    analytics = {}
    cursor.execute(
        """
        SELECT status, COUNT(*) AS count FROM tasks GROUP BY status
        """
    )
    analytics["by_status"] = cursor.fetchall()
    cursor.execute(
        """
        SELECT priority, COUNT(*) AS count FROM tasks GROUP BY priority
        """
    )
    analytics["by_priority"] = cursor.fetchall()
    cursor.execute(
        """
        SELECT COUNT(*) AS count FROM tasks
        WHERE due_date < CURDATE() AND status != 'Complete'
        """
    )
    analytics["overdue"] = cursor.fetchone()["count"]
    cursor.execute(
        """
        SELECT u.username, COUNT(*) AS open_count
        FROM tasks t JOIN users u ON t.user_id = u.id
        WHERE t.status != 'Complete'
        GROUP BY u.id, u.username
        ORDER BY open_count DESC LIMIT 5
        """
    )
    analytics["workload"] = cursor.fetchall()
    cursor.execute(
        """
        SELECT DATE(completed_at) AS day, COUNT(*) AS completed
        FROM tasks
        WHERE completed_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        GROUP BY DATE(completed_at)
        ORDER BY day
        """
    )
    analytics["completions_30d"] = cursor.fetchall()
    cursor.execute(
        """
        SELECT AVG(TIMESTAMPDIFF(HOUR, created_at, completed_at)) AS avg_hours
        FROM tasks WHERE completed_at IS NOT NULL
        """
    )
    row = cursor.fetchone()
    analytics["avg_completion_hours"] = round(row["avg_hours"] or 0, 1)
    cursor.execute("SELECT COUNT(*) AS total FROM tasks")
    analytics["total_tasks"] = cursor.fetchone()["total"]
    cursor.execute(
        """
        SELECT COUNT(*) AS c FROM tasks WHERE status = 'Complete'
        """
    )
    done = cursor.fetchone()["c"]
    total = analytics["total_tasks"] or 1
    analytics["completion_rate"] = round(100 * done / total, 1)
    cursor.close()
    return analytics
