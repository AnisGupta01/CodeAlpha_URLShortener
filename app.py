"""CodeAlpha Backend Internship - Task 1: Simple URL Shortener (Flask + SQLite)."""
import os
import re
import secrets
import sqlite3
import string
from datetime import datetime, timezone
from urllib.parse import urlparse

from flask import Flask, g, jsonify, redirect, render_template, request

ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 6
MAX_URL_LENGTH = 2048
RESERVED_CODES = {"api", "static", "health", "favicon.ico"}
CUSTOM_CODE_RE = re.compile(r"^[A-Za-z0-9_-]{3,32}$")

SCHEMA = """
CREATE TABLE IF NOT EXISTS urls (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    short_code   TEXT    NOT NULL UNIQUE,
    original_url TEXT    NOT NULL,
    created_at   TEXT    NOT NULL,
    clicks       INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_urls_original ON urls(original_url);
"""


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DATABASE"] = db_path or os.environ.get(
        "DATABASE_PATH", os.path.join(os.path.dirname(__file__), "urls.db")
    )

    # ---------- database helpers ----------
    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    init_conn = sqlite3.connect(app.config["DATABASE"])
    try:
        init_conn.executescript(SCHEMA)
        init_conn.commit()
    finally:
        init_conn.close()

    # ---------- helpers ----------
    def validate_url(raw):
        """Return (clean_url, error). Only absolute http/https URLs are allowed."""
        if not isinstance(raw, str) or not raw.strip():
            return None, "A 'url' field is required."
        url = raw.strip()
        if len(url) > MAX_URL_LENGTH:
            return None, f"URL is too long (max {MAX_URL_LENGTH} characters)."
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return None, "URL must be a valid http:// or https:// address."
        return url, None

    def generate_code(db):
        for _ in range(10):
            code = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
            if code not in RESERVED_CODES and not db.execute(
                "SELECT 1 FROM urls WHERE short_code = ?", (code,)
            ).fetchone():
                return code
        raise RuntimeError("Could not generate a unique short code.")

    def short_url_for(code):
        return request.host_url.rstrip("/") + "/" + code

    def row_to_dict(row):
        return {
            "short_code": row["short_code"],
            "short_url": short_url_for(row["short_code"]),
            "original_url": row["original_url"],
            "created_at": row["created_at"],
            "clicks": row["clicks"],
        }

    # ---------- routes ----------
    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.post("/api/shorten")
    def shorten():
        data = request.get_json(silent=True) or {}
        url, error = validate_url(data.get("url"))
        if error:
            return jsonify(error=error), 400

        db = get_db()
        custom = data.get("custom_code")
        if custom:
            if not isinstance(custom, str) or not CUSTOM_CODE_RE.match(custom):
                return jsonify(
                    error="custom_code must be 3-32 characters: letters, digits, '-' or '_'."
                ), 400
            if custom.lower() in RESERVED_CODES:
                return jsonify(error="That custom code is reserved."), 400
            if db.execute(
                "SELECT 1 FROM urls WHERE short_code = ?", (custom,)
            ).fetchone():
                return jsonify(error="That custom code is already taken."), 409
            code = custom
        else:
            existing = db.execute(
                "SELECT * FROM urls WHERE original_url = ? ORDER BY id LIMIT 1", (url,)
            ).fetchone()
            if existing:  # same long URL -> reuse its short code
                return jsonify(row_to_dict(existing)), 200
            code = generate_code(db)

        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        db.execute(
            "INSERT INTO urls (short_code, original_url, created_at) VALUES (?, ?, ?)",
            (code, url, created_at),
        )
        db.commit()
        row = db.execute("SELECT * FROM urls WHERE short_code = ?", (code,)).fetchone()
        return jsonify(row_to_dict(row)), 201

    @app.get("/api/urls")
    def list_urls():
        rows = get_db().execute(
            "SELECT * FROM urls ORDER BY id DESC LIMIT 20"
        ).fetchall()
        return jsonify([row_to_dict(r) for r in rows])

    @app.get("/api/urls/<code>")
    def url_stats(code):
        row = get_db().execute(
            "SELECT * FROM urls WHERE short_code = ?", (code,)
        ).fetchone()
        if not row:
            return jsonify(error="Short code not found."), 404
        return jsonify(row_to_dict(row))

    @app.get("/<code>")
    def follow(code):
        db = get_db()
        row = db.execute(
            "SELECT original_url FROM urls WHERE short_code = ?", (code,)
        ).fetchone()
        if not row:
            return render_template("404.html", code=code), 404
        db.execute("UPDATE urls SET clicks = clicks + 1 WHERE short_code = ?", (code,))
        db.commit()
        return redirect(row["original_url"], code=302)

    return app


if __name__ == "__main__":
    create_app().run(
        host="127.0.0.1",
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
