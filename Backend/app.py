import os

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask

from blueprints.admin import admin_bp
from blueprints.api import api_bp
from blueprints.auth import auth_bp
from blueprints.main import main_bp
from blueprints.manager import manager_bp
from blueprints.user_routes import user_bp
from config import Config, BACKEND_DIR, FRONTEND_DIR
from database import close_db, init_db
from extensions import csrf, mail
from services.reminders import process_due_reminders


def create_app(config_class=Config):
    app = Flask(
        __name__,
        template_folder=os.path.join(FRONTEND_DIR, "templates"),
        static_folder=os.path.join(FRONTEND_DIR, "static"),
        static_url_path="/static",
    )
    app.config.from_object(config_class)

    upload_path = os.path.join(BACKEND_DIR, app.config["UPLOAD_FOLDER"])
    app.config["UPLOAD_FOLDER_ABS"] = upload_path
    os.makedirs(upload_path, exist_ok=True)

    mail.init_app(app)
    csrf.init_app(app)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(manager_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(api_bp)
    csrf.exempt(api_bp)

    app.teardown_appcontext(close_db)

    @app.context_processor
    def inject_globals():
        from datetime import date

        return {"today": date.today()}

    from utils import format_date_display

    @app.template_filter("fmt_date")
    def fmt_date_filter(value):
        if not value:
            return "—"
        return format_date_display(value)

    @app.template_filter("fmt_date_input")
    def fmt_date_input_filter(value):
        return format_date_display(value) if value else ""

    @app.cli.command("init-db")
    def init_db_command():
        init_db(app)
        print("Database initialized.")

    if not app.config.get("TESTING"):
        _start_scheduler(app)

    return app


def _start_scheduler(app):
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        func=lambda: process_due_reminders(app),
        trigger="cron",
        hour=8,
        minute=0,
        id="due_reminders",
    )
    scheduler.start()


app = create_app()


if __name__ == "__main__":
    with app.app_context():
        try:
            init_db(app)
        except Exception as exc:
            app.logger.warning("DB init skipped: %s", exc)
    app.run(
        host=os.getenv("FLASK_HOST", "0.0.0.0"),
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=os.getenv("FLASK_ENV") == "development",
    )
