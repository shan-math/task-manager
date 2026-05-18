from flask import session

from database import get_db


def log_action(action, entity_type, entity_id=None, details=None):
    db = get_db()
    cursor = db.cursor()
    user_id = session.get("user_id")
    username = session.get("username")
    cursor.execute(
        """
        INSERT INTO audit_log (user_id, username, action, entity_type, entity_id, details)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (user_id, username, action, entity_type, entity_id, details),
    )
    db.commit()
    cursor.close()
