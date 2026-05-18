import mysql.connector
from flask import current_app, g
from werkzeug.security import generate_password_hash


def get_db():
    if "db" not in g:
        g.db = mysql.connector.connect(
            host=current_app.config["MYSQL_HOST"],
            port=current_app.config["MYSQL_PORT"],
            user=current_app.config["MYSQL_USER"],
            password=current_app.config["MYSQL_PASSWORD"],
            database=current_app.config["MYSQL_DATABASE"],
        )
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    """Create schema tables and seed default admin if empty."""
    import os

    schema_path = os.path.join(app.root_path, "sql", "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        raw = f.read()

    conn = mysql.connector.connect(
        host=app.config["MYSQL_HOST"],
        port=app.config["MYSQL_PORT"],
        user=app.config["MYSQL_USER"],
        password=app.config["MYSQL_PASSWORD"],
    )
    cursor = conn.cursor()
    for statement in _split_sql(raw):
        if statement.strip():
            try:
                cursor.execute(statement)
            except mysql.connector.Error:
                pass
    conn.commit()

    conn.close()
    conn = mysql.connector.connect(
        host=app.config["MYSQL_HOST"],
        port=app.config["MYSQL_PORT"],
        user=app.config["MYSQL_USER"],
        password=app.config["MYSQL_PASSWORD"],
        database=app.config["MYSQL_DATABASE"],
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) AS c FROM users")
    count = cursor.fetchone()["c"]
    if count == 0:
        pw = generate_password_hash(app.config["DEFAULT_ADMIN_PASSWORD"])
        cursor.execute(
            """
            INSERT INTO users (username, email, password_hash, role)
            VALUES (%s, %s, %s, 'admin')
            """,
            (
                app.config["DEFAULT_ADMIN_USERNAME"],
                app.config["DEFAULT_ADMIN_EMAIL"],
                pw,
            ),
        )
        conn.commit()

    for cat in ("General", "Development", "Operations", "Support"):
        try:
            cursor.execute(
                "INSERT IGNORE INTO categories (name) VALUES (%s)", (cat,)
            )
        except mysql.connector.Error:
            pass
    for team in ("Engineering", "Operations"):
        try:
            cursor.execute("INSERT IGNORE INTO teams (name) VALUES (%s)", (team,))
        except mysql.connector.Error:
            pass
    for tag in ("urgent", "backend", "frontend", "review"):
        try:
            cursor.execute("INSERT IGNORE INTO tags (name) VALUES (%s)", (tag,))
        except mysql.connector.Error:
            pass
    conn.commit()
    cursor.close()
    conn.close()


def _split_sql(sql):
    parts = []
    buf = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        buf.append(line)
        if stripped.endswith(";"):
            parts.append("\n".join(buf))
            buf = []
    if buf:
        parts.append("\n".join(buf))
    return parts
