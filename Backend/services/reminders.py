from datetime import date, timedelta

from database import get_db
from services.email_service import notify_due_reminder


def process_due_reminders(app):
    with app.app_context():
        db = get_db()
        cursor = db.cursor(dictionary=True)
        tomorrow = date.today() + timedelta(days=1)
        cursor.execute(
            """
            SELECT u.id AS user_id, u.username, u.email,
                   t.id, t.task, t.due_date, t.status
            FROM tasks t
            JOIN users u ON t.user_id = u.id
            WHERE t.due_date = %s
              AND t.status != 'Complete'
              AND t.reminder_sent = 0
            """,
            (tomorrow,),
        )
        rows = cursor.fetchall()
        by_user = {}
        for row in rows:
            by_user.setdefault(row["user_id"], {"user": row, "tasks": []})
            by_user[row["user_id"]]["tasks"].append(row)

        for data in by_user.values():
            user = data["user"]
            notify_due_reminder(
                user["email"],
                user["username"],
                data["tasks"],
            )
            for t in data["tasks"]:
                cursor.execute(
                    "UPDATE tasks SET reminder_sent = 1 WHERE id = %s",
                    (t["id"],),
                )
        db.commit()
        cursor.close()


def get_due_banners(user_id):
    """In-app reminders on login."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    today = date.today()
    cursor.execute(
        """
        SELECT id, task, due_date, status, priority
        FROM tasks
        WHERE user_id = %s AND status != 'Complete'
          AND due_date IS NOT NULL
          AND due_date <= %s
        ORDER BY due_date ASC
        LIMIT 10
        """,
        (user_id, today),
    )
    overdue = cursor.fetchall()
    week_end = today + timedelta(days=7)
    cursor.execute(
        """
        SELECT id, task, due_date, status, priority
        FROM tasks
        WHERE user_id = %s AND status != 'Complete'
          AND due_date > %s AND due_date <= %s
        ORDER BY due_date ASC
        LIMIT 10
        """,
        (user_id, today, week_end),
    )
    upcoming = cursor.fetchall()
    cursor.close()
    return overdue, upcoming
