from flask import current_app, render_template
from flask_mail import Message

from extensions import mail


def send_email(subject, recipients, template, **kwargs):
    if not recipients:
        return False
    if current_app.config.get("MAIL_SUPPRESS_SEND"):
        current_app.logger.info(
            "Mail suppressed: %s -> %s", subject, recipients
        )
        return True
    try:
        html = render_template(f"email/{template}.html", **kwargs)
        msg = Message(
            subject=subject,
            recipients=recipients,
            html=html,
        )
        mail.send(msg)
        return True
    except Exception as exc:
        current_app.logger.warning("Email failed: %s", exc)
        return False


def notify_task_assigned(user_email, username, task_title, due_date=None):
    return send_email(
        f"New task assigned: {task_title}",
        [user_email],
        "task_assigned",
        username=username,
        task_title=task_title,
        due_date=due_date,
    )


def notify_task_completed(admin_email, task_title, username):
    return send_email(
        f"Task completed: {task_title}",
        [admin_email],
        "task_completed",
        task_title=task_title,
        username=username,
    )


def notify_due_reminder(user_email, username, tasks):
    return send_email(
        "Task due date reminder",
        [user_email],
        "due_reminder",
        username=username,
        tasks=tasks,
    )
