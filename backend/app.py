from flask import (
    Flask,
    request,
    jsonify,
    redirect,
    session,
    url_for,
    send_from_directory,
    send_file,
)

from flask_cors import CORS

from werkzeug.security import generate_password_hash, check_password_hash

from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv

from functools import wraps

from urllib.parse import urlparse

import sqlite3

import os

import secrets

import csv

import hashlib

import hmac

import psycopg2

import requests

from io import BytesIO, StringIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

import qrcode

from psycopg2.extras import RealDictCursor

load_dotenv()

# ========================================

# APP CONFIGURATION

# ========================================

app = Flask(__name__)

ALLOWED_ORIGINS = os.environ.get(
    "MANAS_ALLOWED_ORIGINS", "http://127.0.0.1:5000,http://localhost:5000"
).split(",")

CORS(
    app, resources={r"/api/*": {"origins": ALLOWED_ORIGINS}}, supports_credentials=True
)

# IMPORTANT:

# Change this to a long random secret before deployment.

app.secret_key = os.environ.get("MANAS_SECRET_KEY")

if not app.secret_key:

    raise RuntimeError("MANAS_SECRET_KEY environment variable is not set.")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("MANAS_PRODUCTION", "0") == "1",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PROJECT_DIR = os.path.dirname(BASE_DIR)

DATABASE = os.path.join(BASE_DIR, "analytics.db")

# ========================================

# ADMIN CONFIGURATION

# ========================================

ADMIN_USERNAME = os.environ.get("MANAS_ADMIN_USERNAME", "manas")

ADMIN_PASSWORD_HASH = os.environ.get("MANAS_ADMIN_PASSWORD_HASH")

ADMIN_EMAIL = os.environ.get("MANAS_EMAIL_ADDRESS")

# ========================================

# PASSWORD STORAGE HELPERS

# ========================================


def get_current_password_hash():

    connection = get_db()

    row = connection.execute(
        """

        SELECT password_hash

        FROM admin_credentials

        WHERE username = ?

        """,
        (ADMIN_USERNAME,),
    ).fetchone()

    connection.close()

    if row and row["password_hash"]:

        return row["password_hash"]

    return ADMIN_PASSWORD_HASH


def save_password_hash(new_password_hash):

    connection = get_db()

    connection.execute(
        """

        UPDATE admin_credentials

        SET password_hash = ?

        WHERE username = ?

        """,
        (new_password_hash, ADMIN_USERNAME),
    )

    connection.commit()

    connection.close()


# Email OTP configuration

OTP_EXPIRY_SECONDS = 10 * 60

OTP_MAX_ATTEMPTS = 5

# ========================================

# PASSWORD RESET OTP HELPERS

# ========================================


def generate_otp():

    return f"{secrets.randbelow(1_000_000):06d}"


def otp_digest(otp):

    return hmac.new(
        app.secret_key.encode("utf-8"),
        otp.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def send_otp_email(otp):

    if not ADMIN_EMAIL:

        raise RuntimeError("Email configuration is missing")

    resend_api_key = os.environ.get("RESEND_API_KEY")

    if not resend_api_key:

        raise RuntimeError("RESEND_API_KEY is missing")

    message = {
        "from": "onboarding@resend.dev",
        "to": [ADMIN_EMAIL],
        "subject": "Manas Link Hub - Password Reset OTP",
        "text": f"""Manas Link Hub Administrator,

Your password reset OTP is:

{otp}

This OTP expires in 10 minutes and can be used only once.

If you did not request a password reset, you can safely ignore this email.

Manas Link Hub

""",
    }

    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {resend_api_key}",
            "Content-Type": "application/json",
        },
        json=message,
        timeout=20,
    )

    response.raise_for_status()


# ========================================

# DATABASE CONNECTION

# ========================================

DATABASE_URL = os.environ.get("DATABASE_URL")


class DatabaseConnection:

    def __init__(self):

        if DATABASE_URL:

            self.is_postgres = True

            self.connection = psycopg2.connect(
                DATABASE_URL,
                cursor_factory=RealDictCursor,
            )

        else:

            self.is_postgres = False

            self.connection = sqlite3.connect(DATABASE)

            self.connection.row_factory = sqlite3.Row

    def execute(self, query, params=None):

        if self.is_postgres:

            query = query.replace("?", "%s")

            cursor = self.connection.cursor()

            if params is None:

                cursor.execute(query)

            else:

                cursor.execute(query, params)

            return cursor

        if params is None:

            return self.connection.execute(query)

        return self.connection.execute(query, params)

    def commit(self):

        self.connection.commit()

    def close(self):

        self.connection.close()


def get_db():

    return DatabaseConnection()


# ========================================
# DATABASE INITIALIZATION
# ========================================


def initialize_database():

    connection = get_db()

    connection.execute("""

        CREATE TABLE IF NOT EXISTS admin_credentials (

            username TEXT PRIMARY KEY,

            password_hash TEXT NOT NULL

        )

    """)

    existing_admin = connection.execute(
        """

        SELECT username

        FROM admin_credentials

        WHERE username = ?

        """,
        (ADMIN_USERNAME,),
    ).fetchone()

    if not existing_admin and ADMIN_PASSWORD_HASH:

        connection.execute(
            """

            INSERT INTO admin_credentials (

                username,

                password_hash

            )

            VALUES (?, ?)

            """,
            (ADMIN_USERNAME, ADMIN_PASSWORD_HASH),
        )
    # ========================================
    # PHASE 6 — LINK MANAGEMENT TABLE
    # ========================================

    if connection.is_postgres:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS links (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                url TEXT NOT NULL,
                icon TEXT NOT NULL DEFAULT '↗',
                description TEXT,
                enabled INTEGER NOT NULL DEFAULT 1,
                featured INTEGER NOT NULL DEFAULT 0,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

    else:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                url TEXT NOT NULL,
                icon TEXT NOT NULL DEFAULT '↗',
                description TEXT,
                enabled INTEGER NOT NULL DEFAULT 1,
                featured INTEGER NOT NULL DEFAULT 0,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

    # ========================================
    # SEED EXISTING PUBLIC LINKS
    # Only runs when the links table is empty.
    # ========================================

    link_count = connection.execute("""
        SELECT COUNT(*) AS count
        FROM links
    """).fetchone()["count"]

    if link_count == 0:

        seed_time = datetime.now(timezone.utc).isoformat()

        default_links = [
            (
                "VeyroDock",
                "https://github.com/manasomer0902/VeyroDock",
                "V",
                "A lightweight Spotify desktop widget for Windows.",
                1,
                1,
                0,
            ),
            (
                "GitHub",
                "https://github.com/manasomer0902",
                "GH",
                None,
                1,
                0,
                1,
            ),
            (
                "LinkedIn",
                "https://www.linkedin.com/in/manas-omer-6066b5287/",
                "in",
                None,
                1,
                0,
                2,
            ),
            (
                "My Portfolio",
                "https://manasomer0902.github.io/Portfolio/",
                "◎",
                None,
                1,
                0,
                3,
            ),
            (
                "Instagram",
                "https://www.instagram.com/manasomer09/",
                "IG",
                None,
                1,
                0,
                4,
            ),
        ]

        for (
            name,
            url,
            icon,
            description,
            enabled,
            featured,
            sort_order,
        ) in default_links:

            connection.execute(
                """
                INSERT INTO links (
                    name,
                    url,
                    icon,
                    description,
                    enabled,
                    featured,
                    sort_order,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    url,
                    icon,
                    description,
                    enabled,
                    featured,
                    sort_order,
                    seed_time,
                    seed_time,
                ),
            )

    if connection.is_postgres:

        connection.execute("""

            CREATE TABLE IF NOT EXISTS events (

                id SERIAL PRIMARY KEY,

                event_type TEXT NOT NULL,

                link_name TEXT,

                timestamp TEXT NOT NULL,

                user_agent TEXT,

                referrer TEXT,

                ip_address TEXT,

                timezone TEXT


            )

            """)

        connection.execute("""

            CREATE TABLE IF NOT EXISTS password_reset_otps (

                id SERIAL PRIMARY KEY,

                username TEXT NOT NULL,

                otp_digest TEXT NOT NULL,

                created_at TEXT NOT NULL,

                expires_at TEXT NOT NULL,

                attempts INTEGER NOT NULL DEFAULT 0,

                used INTEGER NOT NULL DEFAULT 0

            )

            """)

        connection.execute("""

            CREATE TABLE IF NOT EXISTS admin_credentials (

                username TEXT PRIMARY KEY,

                password_hash TEXT NOT NULL

            )

            """)

    else:

        connection.execute("""

            CREATE TABLE IF NOT EXISTS events (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                event_type TEXT NOT NULL,

                link_name TEXT,

                timestamp TEXT NOT NULL,

                user_agent TEXT,

                referrer TEXT,

                ip_address TEXT,

                timezone TEXT


            )

            """)

        # ----------------------------------------
        # TIMEZONE COLUMN
        # ----------------------------------------

        connection.execute("""

            CREATE TABLE IF NOT EXISTS password_reset_otps (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                username TEXT NOT NULL,

                otp_digest TEXT NOT NULL,

                created_at TEXT NOT NULL,

                expires_at TEXT NOT NULL,

                attempts INTEGER NOT NULL DEFAULT 0,

                used INTEGER NOT NULL DEFAULT 0

            )

            """)

        connection.execute("""

            CREATE TABLE IF NOT EXISTS admin_credentials (

                username TEXT PRIMARY KEY,

                password_hash TEXT NOT NULL

            )

            """)
    # ========================================
    # PHASE 7 — EVENT COLUMN MIGRATIONS
    # ========================================

    def ensure_event_column(column_name, column_definition):

        if connection.is_postgres:

            existing_column = connection.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                AND table_name = 'events'
                AND column_name = ?
                """,
                (column_name,),
            ).fetchone()

            if not existing_column:

                connection.execute(f"""
                    ALTER TABLE events
                    ADD COLUMN {column_name}
                    {column_definition}
                    """)

        else:

            existing_columns = connection.execute("""
                PRAGMA table_info(events)
                """).fetchall()

            column_names = {row["name"] for row in existing_columns}

            if column_name not in column_names:

                connection.execute(f"""
                    ALTER TABLE events
                    ADD COLUMN {column_name}
                    {column_definition}
                    """)

    ensure_event_column("timezone", "TEXT")

    ensure_event_column("campaign_id", "INTEGER")

    ensure_event_column("campaign_name", "TEXT")

    ensure_event_column("campaign_source", "TEXT")

    ensure_event_column("campaign_medium", "TEXT")

    ensure_event_column("qr_token", "TEXT")

    if ADMIN_PASSWORD_HASH:

        connection.execute(
            """

            INSERT INTO admin_credentials (username, password_hash)

            VALUES (?, ?)

            ON CONFLICT (username) DO NOTHING

            """,
            (ADMIN_USERNAME, ADMIN_PASSWORD_HASH),
        )

    # ========================================
    # PHASE 7 — CAMPAIGNS
    # ========================================

    if connection.is_postgres:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (

                id SERIAL PRIMARY KEY,

                name TEXT NOT NULL,

                source TEXT NOT NULL,

                medium TEXT NOT NULL,

                link_id INTEGER,

                token TEXT NOT NULL UNIQUE,

                enabled INTEGER NOT NULL DEFAULT 1,

                created_at TEXT NOT NULL,

                updated_at TEXT NOT NULL

            )
            """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS qr_codes (

                id SERIAL PRIMARY KEY,

                token TEXT NOT NULL UNIQUE,

                name TEXT NOT NULL,

                link_id INTEGER,

                campaign_id INTEGER,

                created_at TEXT NOT NULL,

                enabled INTEGER NOT NULL DEFAULT 1

            )
            """)

    else:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                name TEXT NOT NULL,

                source TEXT NOT NULL,

                medium TEXT NOT NULL,

                link_id INTEGER,

                token TEXT NOT NULL UNIQUE,

                enabled INTEGER NOT NULL DEFAULT 1,

                created_at TEXT NOT NULL,

                updated_at TEXT NOT NULL

            )
            """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS qr_codes (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                token TEXT NOT NULL UNIQUE,

                name TEXT NOT NULL,

                link_id INTEGER,

                campaign_id INTEGER,

                created_at TEXT NOT NULL,

                enabled INTEGER NOT NULL DEFAULT 1

            )
            """)

    # ========================================
    # MAIN LINK HUB QR
    # ========================================

    existing_main_qr = connection.execute(
        """
        SELECT id
        FROM qr_codes
        WHERE name = ?
        AND link_id IS NULL
        AND campaign_id IS NULL
        """,
        ("Main Link Hub",),
    ).fetchone()

    if not existing_main_qr:

        connection.execute(
            """
            INSERT INTO qr_codes (
                token,
                name,
                link_id,
                campaign_id,
                created_at,
                enabled
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                secrets.token_urlsafe(12),
                "Main Link Hub",
                None,
                None,
                datetime.now(timezone.utc).isoformat(),
                1,
            ),
        )

    connection.commit()

    connection.close()


initialize_database()

# AUTHENTICATION HELPER

# ========================================


def admin_required(function):

    @wraps(function)
    def decorated(*args, **kwargs):

        if not session.get("admin_logged_in"):

            return jsonify({"success": False, "error": "Authentication required"}), 401

        return function(*args, **kwargs)

    return decorated


# ========================================

# HEALTH CHECK

# PUBLIC

# ========================================


@app.route("/", methods=["GET"])
def home():

    return send_from_directory(PROJECT_DIR, "index.html")


@app.route("/profile.png", methods=["GET"])
def profile_image():

    return send_from_directory(PROJECT_DIR, "profile.png")

@app.route("/favicon.png", methods=["GET"])
def favicon_png():

    return send_from_directory(
        PROJECT_DIR,
        "favicon.png",
        mimetype="image/png"
    )


@app.route("/favicon.ico", methods=["GET"])
def favicon_ico():

    return send_from_directory(
        PROJECT_DIR,
        "favicon.png",
        mimetype="image/png"
    )

@app.route("/style.css")
def style_css():

    return send_from_directory(PROJECT_DIR, "style.css")


@app.route("/script.js")
def script_js():

    return send_from_directory(PROJECT_DIR, "script.js")


# ========================================

# LOGIN PAGE

# ========================================


@app.route("/admin/login", methods=["GET"])
def login_page():

    return """

    <!DOCTYPE html>

    <html lang="en">

    <head>

        <meta charset="UTF-8">

        <meta

            name="viewport"

            content="width=device-width, initial-scale=1.0"

        >

        <title>

            Manas Analytics Login

        </title>

        <style>

            * {

                box-sizing: border-box;

            }

            body {

                margin: 0;

                min-height: 100vh;

                display: grid;

                place-items: center;

                padding: 20px;

                background: #08090c;

                color: #f5f5f7;

                font-family:

                    -apple-system,

                    BlinkMacSystemFont,

                    "Segoe UI",

                    sans-serif;

            }

            .card {

                width:

                    min(

                        calc(100% - 32px),

                        380px

                    );

                padding: 30px;

                border:

                    1px solid

                    rgba(255,255,255,0.10);

                border-radius: 22px;

                background:

                    rgba(255,255,255,0.055);

                backdrop-filter:

                    blur(18px);

            }

            h1 {

                margin: 0;

                font-size: 27px;

                letter-spacing: -1px;

            }

            p {

                color: #9698a2;

                font-size: 13px;

                margin:

                    8px 0 25px;

            }

            label {

                display: block;

                margin-bottom: 7px;

                color: #9698a2;

                font-size: 11px;

            }

            input {

                width: 100%;

                padding: 13px;

                margin-bottom: 16px;

                border:

                    1px solid

                    rgba(255,255,255,0.10);

                border-radius: 12px;

                outline: none;

                background:

                    rgba(255,255,255,0.05);

                color: white;

                font-size: 14px;

            }

            input:focus {

                border-color:

                    rgba(139,124,255,0.6);

            }

            button {

                width: 100%;

                padding: 13px;

                border: none;

                border-radius: 12px;

                background: #8b7cff;

                color: white;

                font-size: 14px;

                font-weight: 600;

                cursor: pointer;

            }

            button:hover {

                opacity: 0.9;

            }

            .forgot {

                display: block;

                margin-top: 17px;

                color: #9698a2;

                font-size: 12px;

                text-align: center;

                text-decoration: none;

            }

            .forgot:hover {

                color: #b8afff;

            }

        </style>

    </head>

    <body>

        <form

            class="card"

            method="POST"

            action="/admin/login"

        >

            <h1>

                Manas Analytics

            </h1>

            <p>

                Private administrator dashboard

            </p>

            <label>

                Username

            </label>

            <input

                type="text"

                name="username"

                autocomplete="username"

                required

            >

            <label>

                Password

            </label><input

                type="password"

                name="password"

                autocomplete="current-password"

                required

            >

            <button type="submit">

                Sign In

            </button>

            <a

                class="forgot"

                href="/admin/forgot-password"

            >

                Forgot password?

            </a>

        </form>

    </body>

    </html>

    """


# ========================================

# LOGIN

# ========================================


@app.route("/admin/login", methods=["POST"])
def login():

    username = request.form.get("username", "").strip()

    password = request.form.get("password", "")

    current_password_hash = get_current_password_hash()

    if not current_password_hash:

        return (
            """

        <h2>

            Admin password is not configured.

        </h2>

        <p>

            Set MANAS_ADMIN_PASSWORD_HASH first.

        </p>

        """,
            500,
        )

    valid_username = username == ADMIN_USERNAME

    try:

        valid_password = check_password_hash(current_password_hash, password)

    except ValueError:

        valid_password = False

    if valid_username and valid_password:

        session.clear()

        session["admin_logged_in"] = True

        session["admin_username"] = username

        return redirect("/admin/dashboard")

    return (
        """

    <h2>

        Invalid username or password.

    </h2>

    <p>

        <a href="/admin/login">

            Try again

        </a>

    </p>

    """,
        401,
    )


# ========================================

# FORGOT PASSWORD - EMAIL OTP

# ========================================


def forgot_password_page(message="", otp_stage=False):

    message_html = ""

    if message:

        message_html = f'<div class="message">{message}</div>'

    if otp_stage:

        form_html = """

        <p>

            We sent a 6-digit OTP to your administrator email.

            The OTP expires in 10 minutes.

        </p>

        <form method="POST" action="/admin/forgot-password">

            <input type="hidden" name="action" value="verify_otp">

            <label>OTP</label>

            <input

                type="text"

                name="otp"

                inputmode="numeric"

                pattern="[0-9]{6}"

                maxlength="6"

                autocomplete="one-time-code"

                required

            >

            <label>New Password</label>

            <input

                type="password"

                name="new_password"

                autocomplete="new-password"

                minlength="8"

                required

            >

            <button type="submit">

                Verify OTP & Reset Password

            </button>

        </form>

        <form method="POST" action="/admin/forgot-password">

            <input type="hidden" name="action" value="resend">

            <button type="submit" class="secondary">

                Send New OTP

            </button>

        </form>

        """

    else:

        form_html = """

        <p>

            Enter your administrator username and email.

            We'll send you a 6-digit OTP.

        </p>

        <form method="POST" action="/admin/forgot-password">

            <input type="hidden" name="action" value="send_otp">

            <label>Admin Username</label>

            <input

                type="text"

                name="username"

                autocomplete="username"

                required

            >

            <label>Administrator Email</label>

            <input

                type="email"

                name="email"

                autocomplete="email"

                required

            >

            <button type="submit">

                Send OTP

            </button>

        </form>

        """

    return f"""

    <!DOCTYPE html>

    <html lang="en">

    <head>

        <meta charset="UTF-8">

        <meta name="viewport" content="width=device-width, initial-scale=1.0">

        <title>Reset Password</title>

        <style>

            * {{

                box-sizing: border-box;

            }}

            body {{

                margin: 0;

                min-height: 100vh;

                display: grid;

                place-items: center;

                padding: 20px;

                background: #08090c;

                color: #f5f5f7;

                font-family:

                    -apple-system,

                    BlinkMacSystemFont,

                    "Segoe UI",

                    sans-serif;

            }}

            .card {{

                width: min(calc(100% - 32px), 400px);

                padding: 30px;

                border: 1px solid rgba(255,255,255,0.10);

                border-radius: 22px;

                background: rgba(255,255,255,0.055);

                backdrop-filter: blur(18px);

            }}

            h1 {{

                margin: 0;

                font-size: 27px;

                letter-spacing: -1px;

            }}

            p {{

                color: #9698a2;

                font-size: 13px;

                line-height: 1.6;

                margin: 8px 0 25px;

            }}

            label {{

                display: block;

                margin-bottom: 7px;

                color: #9698a2;

                font-size: 11px;

            }}

            input {{

                width: 100%;

                padding: 13px;

                margin-bottom: 16px;

                border: 1px solid rgba(255,255,255,0.10);

                border-radius: 12px;

                outline: none;

                background: rgba(255,255,255,0.05);

                color: white;

                font-size: 14px;

            }}

            input:focus {{

                border-color: rgba(139,124,255,0.6);

            }}

            button {{

                width: 100%;

                padding: 13px;

                border: none;

                border-radius: 12px;

                background: #8b7cff;

                color: white;

                font-size: 14px;

                font-weight: 600;

                cursor: pointer;

                margin-bottom: 10px;

            }}

            button:hover {{

                opacity: 0.9;

            }}

            button.secondary {{

                background: rgba(255,255,255,0.08);

            }}

            .message {{

                margin-bottom: 18px;

                padding: 12px;

                border-radius: 12px;

                background: rgba(139,124,255,0.10);

                color: #c7c1ff;

                font-size: 12px;

                line-height: 1.5;

            }}

            .back {{

                display: block;

                margin-top: 8px;

                color: #9698a2;

                font-size: 12px;

                text-align: center;

                text-decoration: none;

            }}

            .back:hover {{

                color: white;

            }}

        </style>

    </head>

    <body>

        <div class="card">

            <h1>Reset Password</h1>

            {message_html}

            {form_html}

            <a class="back" href="/admin/login">

                ← Back to login

            </a>

        </div>

    </body>

    </html>

    """


def create_reset_otp(username):

    otp = generate_otp()

    now = datetime.now(timezone.utc)

    expires = datetime.fromtimestamp(now.timestamp() + OTP_EXPIRY_SECONDS, timezone.utc)

    connection = get_db()

    connection.execute(
        """

        UPDATE password_reset_otps

        SET used = 1

        WHERE username = ?

          AND used = 0

        """,
        (username,),
    )

    connection.execute(
        """

        INSERT INTO password_reset_otps (

            username,

            otp_digest,

            created_at,

            expires_at,

            attempts,

            used

        )

        VALUES (?, ?, ?, ?, 0, 0)

        """,
        (
            username,
            otp_digest(otp),
            now.isoformat(),
            expires.isoformat(),
        ),
    )

    connection.commit()

    connection.close()

    return otp


def get_active_reset_otp(username):

    connection = get_db()

    row = connection.execute(
        """

        SELECT *

        FROM password_reset_otps

        WHERE username = ?

          AND used = 0

        ORDER BY id DESC

        LIMIT 1

        """,
        (username,),
    ).fetchone()

    connection.close()

    return row


@app.route("/admin/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "GET":

        # Opening Forgot Password always starts a fresh reset flow.

        session.pop("password_reset_pending", None)

        session.pop("password_reset_username", None)

        return forgot_password_page(otp_stage=False)

    action = request.form.get("action", "send_otp")

    if action in ("send_otp", "resend"):

        username = request.form.get("username", "").strip()

        email = request.form.get("email", "").strip().lower()

        if action == "resend":

            username = session.get("password_reset_username", "")

            email = ADMIN_EMAIL.lower() if ADMIN_EMAIL else ""

        if (
            username != ADMIN_USERNAME
            or not ADMIN_EMAIL
            or email != ADMIN_EMAIL.lower()
        ):

            return (
                forgot_password_page(
                    "Invalid reset details.",
                    otp_stage=False,
                ),
                400,
            )

        existing = get_active_reset_otp(username)

        if existing:

            try:

                created = datetime.fromisoformat(existing["created_at"])

                elapsed = (datetime.now(timezone.utc) - created).total_seconds()

                if elapsed < 60:

                    session["password_reset_pending"] = True

                    session["password_reset_username"] = username

                    return (
                        forgot_password_page(
                            "Please wait about 60 seconds before requesting another OTP.",
                            otp_stage=True,
                        ),
                        429,
                    )

            except (ValueError, TypeError):

                pass

        try:

            otp = create_reset_otp(username)

            send_otp_email(otp)

        except Exception as exc:

            # Invalidate the OTP if email delivery failed so the user is not

            # incorrectly blocked by the 60-second OTP rate limit.

            try:

                connection = get_db()

                connection.execute(
                    """

                    UPDATE password_reset_otps

                    SET used = 1

                    WHERE username = ?

                      AND used = 0

                    """,
                    (username,),
                )

                connection.commit()

                connection.close()

            except Exception:

                pass

            print(f"OTP EMAIL ERROR: {exc!r}")

            return (
                forgot_password_page(
                    "We could not send the OTP email. Check your email configuration.",
                    otp_stage=False,
                ),
                500,
            )

        session["password_reset_pending"] = True

        session["password_reset_username"] = username

        return forgot_password_page(
            "OTP sent successfully. Check your administrator email.",
            otp_stage=True,
        )

    if action == "verify_otp":

        username = session.get("password_reset_username")

        if not session.get("password_reset_pending") or username != ADMIN_USERNAME:

            return (
                forgot_password_page(
                    "Your reset session has expired. Start again.",
                    otp_stage=False,
                ),
                400,
            )

        otp = request.form.get("otp", "").strip()

        new_password = request.form.get("new_password", "")

        if not otp.isdigit() or len(otp) != 6:

            return (
                forgot_password_page(
                    "Enter the 6-digit OTP from your email.",
                    otp_stage=True,
                ),
                400,
            )

        if len(new_password) < 8:

            return (
                forgot_password_page(
                    "Password must contain at least 8 characters.",
                    otp_stage=True,
                ),
                400,
            )

        row = get_active_reset_otp(username)

        if not row:

            session.pop("password_reset_pending", None)

            session.pop("password_reset_username", None)

            return (
                forgot_password_page(
                    "This OTP is no longer valid. Request a new OTP.",
                    otp_stage=False,
                ),
                400,
            )

        if row["attempts"] >= OTP_MAX_ATTEMPTS:

            return (
                forgot_password_page(
                    "Too many incorrect attempts. Request a new OTP.",
                    otp_stage=False,
                ),
                429,
            )

        try:

            expires_at = datetime.fromisoformat(row["expires_at"])

            if datetime.now(timezone.utc) >= expires_at:

                connection = get_db()

                connection.execute(
                    """

                    UPDATE password_reset_otps

                    SET used = 1

                    WHERE id = ?

                    """,
                    (row["id"],),
                )

                connection.commit()

                connection.close()

                session.pop("password_reset_pending", None)

                session.pop("password_reset_username", None)

                return (
                    forgot_password_page(
                        "This OTP has expired. Request a new OTP.",
                        otp_stage=False,
                    ),
                    400,
                )

        except (ValueError, TypeError):

            return (
                forgot_password_page(
                    "Invalid OTP session. Request a new OTP.",
                    otp_stage=False,
                ),
                400,
            )

        valid_otp = secrets.compare_digest(otp_digest(otp), row["otp_digest"])

        if not valid_otp:

            connection = get_db()

            connection.execute(
                """

                UPDATE password_reset_otps

                SET attempts = attempts + 1

                WHERE id = ?

                """,
                (row["id"],),
            )

            connection.commit()

            connection.close()

            return (
                forgot_password_page(
                    "Incorrect OTP. Check your email and try again.",
                    otp_stage=True,
                ),
                400,
            )

        try:

            save_password_hash(generate_password_hash(new_password))

            connection = get_db()

            connection.execute(
                """

                UPDATE password_reset_otps

                SET used = 1

                WHERE id = ?

                """,
                (row["id"],),
            )

            connection.commit()

            connection.close()

        except OSError:

            return (
                forgot_password_page(
                    "Password reset failed. The server could not save the new password.",
                    otp_stage=True,
                ),
                500,
            )

        session.clear()

        return """

        <!DOCTYPE html>

        <html lang="en">

        <head>

            <meta charset="UTF-8">

            <meta name="viewport" content="width=device-width, initial-scale=1.0">

            <title>Password Reset Successful</title>

            <style>

                body {

                    margin: 0;

                    min-height: 100vh;

                    display: grid;

                    place-items: center;

                    padding: 20px;

                    background: #08090c;

                    color: #f5f5f7;

                    font-family:

                        -apple-system,

                        BlinkMacSystemFont,

                        "Segoe UI",

                        sans-serif;

                }

                .card {

                    width: min(calc(100% - 32px), 420px);

                    padding: 30px;

                    border: 1px solid rgba(255,255,255,0.10);

                    border-radius: 22px;

                    background: rgba(255,255,255,0.055);

                    text-align: center;

                }

                h1 {

                    font-size: 25px;

                }

                p {

                    color: #9698a2;

                    font-size: 13px;

                    line-height: 1.6;

                }

                .success {

                    display: inline-block;

                    padding: 8px 12px;

                    border-radius: 20px;

                    background: rgba(105,211,156,0.10);

                    color: #69d39c;

                    font-size: 12px;

                }

                a {

                    display: inline-block;

                    margin-top: 15px;

                    padding: 12px 18px;

                    border-radius: 12px;

                    background: #8b7cff;

                    color: white;

                    font-size: 13px;

                    font-weight: 600;

                    text-decoration: none;

                }

            </style>

        </head>

        <body>

            <div class="card">

                <div class="success">✓ Password Updated</div>

                <h1>Password reset successfully</h1>

                <p>

                    Your administrator password has been changed.

                </p>

                <p>

                    The OTP has been invalidated and cannot be reused.

                </p>

                <a href="/admin/login">

                    Go to Login

                </a>

            </div>

        </body>

        </html>

        """

    return forgot_password_page(), 400


# ========================================

# LOGOUT

# ========================================


@app.route("/admin/logout", methods=["GET"])
def logout():

    session.clear()

    return redirect("/admin/login")


# ========================================

# DASHBOARD

# PROTECTED

# ========================================


@app.route("/admin/dashboard", methods=["GET"])
def admin_dashboard():

    if not session.get("admin_logged_in"):

        return redirect("/admin/login")

    dashboard_path = os.path.join(BASE_DIR, "dashboard.html")

    if not os.path.exists(dashboard_path):

        return (
            """

        <h2>

            Dashboard not found.

        </h2>

        """,
            404,
        )

    with open(dashboard_path, "r", encoding="utf-8") as file:

        return file.read()


# ========================================
# PHASE 6 — LINK MANAGEMENT
# ========================================


def validate_link_data(data):
    """
    Validate and normalize link-management input.
    """

    if not isinstance(data, dict):
        return None, "Invalid JSON data."

    name = str(data.get("name", "")).strip()
    url = str(data.get("url", "")).strip()
    icon = str(data.get("icon", "")).strip()
    description = data.get("description")

    if not name:
        return None, "Link name is required."

    if len(name) > 80:
        return None, "Link name must be 80 characters or less."

    if not url:
        return None, "URL is required."

    if len(url) > 1000:
        return None, "URL is too long."

    parsed_url = urlparse(url)

    if parsed_url.scheme not in ("http", "https"):
        return None, "URL must start with http:// or https://."

    if not parsed_url.netloc:
        return None, "Please enter a valid URL."

    if not icon:
        icon = "↗"

    if len(icon) > 10:
        return None, "Icon must be 10 characters or less."

    if description is not None:
        description = str(description).strip()

        if len(description) > 180:
            return None, "Description must be 180 characters or less."

        if not description:
            description = None

    enabled = bool(data.get("enabled", True))
    featured = bool(data.get("featured", False))

    return {
        "name": name,
        "url": url,
        "icon": icon,
        "description": description,
        "enabled": 1 if enabled else 0,
        "featured": 1 if featured else 0,
    }, None


# ========================================
# PUBLIC LINKS
# ========================================


@app.route("/api/public-links", methods=["GET"])
def public_links():

    connection = get_db()

    links = connection.execute("""
        SELECT
            id,
            name,
            url,
            icon,
            description,
            enabled,
            featured,
            sort_order
        FROM links
        WHERE enabled = 1
        ORDER BY featured DESC, sort_order ASC, id ASC
        """).fetchall()

    connection.close()

    return jsonify(
        {
            "success": True,
            "links": [dict(link) for link in links],
        }
    )


# ========================================
# ADMIN — GET LINKS
# ========================================


@app.route("/api/admin/links", methods=["GET"])
@admin_required
def admin_get_links():

    connection = get_db()

    links = connection.execute("""
        SELECT
            id,
            name,
            url,
            icon,
            description,
            enabled,
            featured,
            sort_order,
            created_at,
            updated_at
        FROM links
        ORDER BY sort_order ASC, id ASC
        """).fetchall()

    connection.close()

    return jsonify(
        {
            "success": True,
            "links": [dict(link) for link in links],
        }
    )


# ========================================
# ADMIN — ADD LINK
# ========================================


@app.route("/api/admin/links", methods=["POST"])
@admin_required
def admin_add_link():

    data = request.get_json(silent=True)

    cleaned, error = validate_link_data(data)

    if error:
        return (
            jsonify(
                {
                    "success": False,
                    "error": error,
                }
            ),
            400,
        )

    connection = get_db()

    existing = connection.execute(
        """
        SELECT id
        FROM links
        WHERE LOWER(name) = LOWER(?)
        """,
        (cleaned["name"],),
    ).fetchone()

    if existing:
        connection.close()

        return (
            jsonify(
                {
                    "success": False,
                    "error": "A link with this name already exists.",
                }
            ),
            409,
        )

    if cleaned["featured"]:
        connection.execute(
            """
            UPDATE links
            SET featured = 0,
                updated_at = ?
            """,
            (datetime.now(timezone.utc).isoformat(),),
        )

    max_order = connection.execute("""
        SELECT COALESCE(MAX(sort_order), -1) AS max_order
        FROM links
        """).fetchone()["max_order"]

    now = datetime.now(timezone.utc).isoformat()

    connection.execute(
        """
        INSERT INTO links (
            name,
            url,
            icon,
            description,
            enabled,
            featured,
            sort_order,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            cleaned["name"],
            cleaned["url"],
            cleaned["icon"],
            cleaned["description"],
            cleaned["enabled"],
            cleaned["featured"],
            max_order + 1,
            now,
            now,
        ),
    )

    connection.commit()
    connection.close()

    return jsonify(
        {
            "success": True,
            "message": "Link added successfully.",
        }
    )


# ========================================
# ADMIN — EDIT LINK
# ========================================


@app.route("/api/admin/links/<int:link_id>", methods=["PUT"])
@admin_required
def admin_update_link(link_id):

    data = request.get_json(silent=True)

    cleaned, error = validate_link_data(data)

    if error:
        return (
            jsonify(
                {
                    "success": False,
                    "error": error,
                }
            ),
            400,
        )

    connection = get_db()

    existing = connection.execute(
        """
        SELECT *
        FROM links
        WHERE id = ?
        """,
        (link_id,),
    ).fetchone()

    if not existing:
        connection.close()

        return (
            jsonify(
                {
                    "success": False,
                    "error": "Link not found.",
                }
            ),
            404,
        )

    duplicate = connection.execute(
        """
        SELECT id
        FROM links
        WHERE LOWER(name) = LOWER(?)
        AND id != ?
        """,
        (
            cleaned["name"],
            link_id,
        ),
    ).fetchone()

    if duplicate:
        connection.close()

        return (
            jsonify(
                {
                    "success": False,
                    "error": "Another link already uses this name.",
                }
            ),
            409,
        )

    old_name = existing["name"]
    new_name = cleaned["name"]

    # ----------------------------------------
    # FEATURED LINK
    # Only one link can be featured.
    # ----------------------------------------

    if cleaned["featured"]:
        connection.execute(
            """
            UPDATE links
            SET featured = 0,
                updated_at = ?
            """,
            (datetime.now(timezone.utc).isoformat(),),
        )

    now = datetime.now(timezone.utc).isoformat()

    connection.execute(
        """
        UPDATE links
        SET
            name = ?,
            url = ?,
            icon = ?,
            description = ?,
            enabled = ?,
            featured = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            cleaned["name"],
            cleaned["url"],
            cleaned["icon"],
            cleaned["description"],
            cleaned["enabled"],
            cleaned["featured"],
            now,
            link_id,
        ),
    )

    # ----------------------------------------
    # KEEP ANALYTICS CONNECTED TO RENAMED LINK
    # ----------------------------------------

    if old_name != new_name:

        connection.execute(
            """
            UPDATE events
            SET link_name = ?
            WHERE LOWER(link_name) = LOWER(?)
            """,
            (
                new_name,
                old_name,
            ),
        )

    connection.commit()
    connection.close()

    return jsonify(
        {
            "success": True,
            "message": "Link updated successfully.",
        }
    )


# ========================================
# ADMIN — DELETE LINK
# ========================================


@app.route("/api/admin/links/<int:link_id>", methods=["DELETE"])
@admin_required
def admin_delete_link(link_id):

    connection = get_db()

    existing = connection.execute(
        """
        SELECT id
        FROM links
        WHERE id = ?
        """,
        (link_id,),
    ).fetchone()

    if not existing:
        connection.close()

        return (
            jsonify(
                {
                    "success": False,
                    "error": "Link not found.",
                }
            ),
            404,
        )

    connection.execute(
        """
        DELETE FROM links
        WHERE id = ?
        """,
        (link_id,),
    )

    connection.commit()
    connection.close()

    return jsonify(
        {
            "success": True,
            "message": "Link deleted successfully.",
        }
    )


# ========================================
# ADMIN — REORDER LINKS
# ========================================


@app.route("/api/admin/links/reorder", methods=["POST"])
@admin_required
def admin_reorder_links():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Invalid JSON data.",
                }
            ),
            400,
        )

    link_ids = data.get("link_ids")

    if not isinstance(link_ids, list):
        return (
            jsonify(
                {
                    "success": False,
                    "error": "link_ids must be a list.",
                }
            ),
            400,
        )

    connection = get_db()

    for position, link_id in enumerate(link_ids):

        try:
            link_id = int(link_id)
        except (TypeError, ValueError):
            continue

        connection.execute(
            """
            UPDATE links
            SET sort_order = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                position,
                datetime.now(timezone.utc).isoformat(),
                link_id,
            ),
        )

    connection.commit()
    connection.close()

    return jsonify(
        {
            "success": True,
            "message": "Link order updated.",
        }
    )


# ========================================
# PHASE 7 — QR & CAMPAIGN ANALYTICS
# ========================================


def phase7_public_base_url():

    configured_url = os.environ.get("MANAS_PUBLIC_BASE_URL")

    if configured_url:

        return configured_url.rstrip("/")

    return request.url_root.rstrip("/")


def create_qr_record(connection, name, link_id=None, campaign_id=None):

    token = secrets.token_urlsafe(12)

    now = datetime.now(timezone.utc).isoformat()

    connection.execute(
        """
        INSERT INTO qr_codes (
            token,
            name,
            link_id,
            campaign_id,
            created_at,
            enabled
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            token,
            name,
            link_id,
            campaign_id,
            now,
            1,
        ),
    )

    return token


def generate_qr_png(data):

    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )

    qr.add_data(data)

    qr.make(fit=True)

    image = qr.make_image()

    buffer = BytesIO()

    image.save(buffer, format="PNG")

    buffer.seek(0)

    return buffer


# ========================================
# ADMIN — MAIN LINK HUB QR
# ========================================


@app.route("/api/admin/qr/main", methods=["GET"])
@admin_required
def admin_main_qr():

    connection = get_db()

    qr = connection.execute(
        """
        SELECT
            id,
            token,
            name,
            created_at,
            enabled
        FROM qr_codes
        WHERE name = ?
        AND link_id IS NULL
        AND campaign_id IS NULL
        LIMIT 1
        """,
        ("Main Link Hub",),
    ).fetchone()

    if not qr:

        token = create_qr_record(connection, "Main Link Hub")

        connection.commit()

        qr = connection.execute(
            """
            SELECT
                id,
                token,
                name,
                created_at,
                enabled
            FROM qr_codes
            WHERE token = ?
            """,
            (token,),
        ).fetchone()

    connection.close()

    scan_url = phase7_public_base_url() + "/qr/" + qr["token"]

    return jsonify(
        {
            "success": True,
            "qr": {
                **dict(qr),
                "scan_url": scan_url,
                "image_url": "/api/admin/qr/" + qr["token"] + "/image",
            },
        }
    )


# ========================================
# ADMIN — INDIVIDUAL LINK QR
# ========================================


@app.route("/api/admin/qr/link/<int:link_id>", methods=["GET"])
@admin_required
def admin_link_qr(link_id):

    connection = get_db()

    link = connection.execute(
        """
        SELECT
            id,
            name,
            url,
            enabled
        FROM links
        WHERE id = ?
        """,
        (link_id,),
    ).fetchone()

    if not link:

        connection.close()

        return (
            jsonify(
                {
                    "success": False,
                    "error": "Link not found.",
                }
            ),
            404,
        )

    qr = connection.execute(
        """
        SELECT
            id,
            token,
            name,
            created_at,
            enabled
        FROM qr_codes
        WHERE link_id = ?
        AND campaign_id IS NULL
        LIMIT 1
        """,
        (link_id,),
    ).fetchone()

    if not qr:

        token = create_qr_record(
            connection,
            "QR - " + link["name"],
            link_id=link_id,
        )

        connection.commit()

        qr = connection.execute(
            """
            SELECT
                id,
                token,
                name,
                created_at,
                enabled
            FROM qr_codes
            WHERE token = ?
            """,
            (token,),
        ).fetchone()

    connection.close()

    scan_url = phase7_public_base_url() + "/qr/" + qr["token"]

    return jsonify(
        {
            "success": True,
            "qr": {
                **dict(qr),
                "link_id": link_id,
                "link_name": link["name"],
                "scan_url": scan_url,
                "image_url": "/api/admin/qr/" + qr["token"] + "/image",
            },
        }
    )


# ========================================
# ADMIN — ALL QR CODES
# ========================================


@app.route("/api/admin/qr-codes", methods=["GET"])
@admin_required
def admin_qr_codes():

    connection = get_db()

    rows = connection.execute("""
        SELECT
            q.id,
            q.token,
            q.name,
            q.link_id,
            q.campaign_id,
            q.created_at,
            q.enabled,
            l.name AS link_name,
            c.name AS campaign_name
        FROM qr_codes q
        LEFT JOIN links l
            ON l.id = q.link_id
        LEFT JOIN campaigns c
            ON c.id = q.campaign_id
        ORDER BY q.created_at DESC
        """).fetchall()

    connection.close()

    qr_codes = []

    for row in rows:

        item = dict(row)

        item["scan_url"] = phase7_public_base_url() + "/qr/" + item["token"]

        item["image_url"] = "/api/admin/qr/" + item["token"] + "/image"

        qr_codes.append(item)

    return jsonify(
        {
            "success": True,
            "qr_codes": qr_codes,
        }
    )


# ========================================
# ADMIN — QR IMAGE
# ========================================


@app.route("/api/admin/qr/<token>/image", methods=["GET"])
@admin_required
def admin_qr_image(token):

    connection = get_db()

    qr = connection.execute(
        """
        SELECT token
        FROM qr_codes
        WHERE token = ?
        AND enabled = 1
        """,
        (token,),
    ).fetchone()

    connection.close()

    if not qr:

        return (
            jsonify(
                {
                    "success": False,
                    "error": "QR code not found.",
                }
            ),
            404,
        )

    scan_url = phase7_public_base_url() + "/qr/" + token

    image_buffer = generate_qr_png(scan_url)

    return send_file(
        image_buffer,
        mimetype="image/png",
        as_attachment=(request.args.get("download") == "1"),
        download_name=("manas-link-hub-qr.png"),
    )


# ========================================
# ADMIN — CREATE CAMPAIGN
# ========================================


@app.route("/api/admin/campaigns", methods=["POST"])
@admin_required
def admin_create_campaign():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):

        return (
            jsonify(
                {
                    "success": False,
                    "error": "Invalid JSON data.",
                }
            ),
            400,
        )

    name = str(data.get("name", "")).strip()

    source = str(data.get("source", "")).strip().lower()

    medium = str(data.get("medium", "")).strip().lower()

    link_id = data.get("link_id")

    if not name:

        return (
            jsonify(
                {
                    "success": False,
                    "error": "Campaign name is required.",
                }
            ),
            400,
        )

    if len(name) > 100:

        return (
            jsonify(
                {
                    "success": False,
                    "error": "Campaign name must be 100 characters or less.",
                }
            ),
            400,
        )

    if not source:

        return (
            jsonify(
                {
                    "success": False,
                    "error": "Campaign source is required.",
                }
            ),
            400,
        )

    if not medium:

        return (
            jsonify(
                {
                    "success": False,
                    "error": "Campaign medium is required.",
                }
            ),
            400,
        )

    if len(source) > 80:

        return (
            jsonify(
                {
                    "success": False,
                    "error": "Campaign source is too long.",
                }
            ),
            400,
        )

    if len(medium) > 80:

        return (
            jsonify(
                {
                    "success": False,
                    "error": "Campaign medium is too long.",
                }
            ),
            400,
        )

    if link_id in (
        "",
        None,
    ):

        link_id = None

    else:

        try:

            link_id = int(link_id)

        except (TypeError, ValueError):

            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Invalid link.",
                    }
                ),
                400,
            )

    connection = get_db()

    if link_id is not None:

        link = connection.execute(
            """
            SELECT
                id,
                name
            FROM links
            WHERE id = ?
            """,
            (link_id,),
        ).fetchone()

        if not link:

            connection.close()

            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Selected link does not exist.",
                    }
                ),
                404,
            )

    existing = connection.execute(
        """
        SELECT id
        FROM campaigns
        WHERE LOWER(name) = LOWER(?)
        """,
        (name,),
    ).fetchone()

    if existing:

        connection.close()

        return (
            jsonify(
                {
                    "success": False,
                    "error": "A campaign with this name already exists.",
                }
            ),
            409,
        )

    now = datetime.now(timezone.utc).isoformat()

    token = secrets.token_urlsafe(12)

    connection.execute(
        """
        INSERT INTO campaigns (
            name,
            source,
            medium,
            link_id,
            token,
            enabled,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            source,
            medium,
            link_id,
            token,
            1,
            now,
            now,
        ),
    )

    campaign = connection.execute(
        """
        SELECT id
        FROM campaigns
        WHERE token = ?
        """,
        (token,),
    ).fetchone()

    campaign_id = campaign["id"]

    qr_token = create_qr_record(
        connection,
        "Campaign - " + name,
        link_id=link_id,
        campaign_id=campaign_id,
    )

    connection.commit()
    connection.close()

    return jsonify(
        {
            "success": True,
            "message": "Campaign created successfully.",
            "campaign": {
                "id": campaign_id,
                "name": name,
                "source": source,
                "medium": medium,
                "link_id": link_id,
                "token": token,
                "qr_token": qr_token,
                "scan_url": phase7_public_base_url() + "/qr/" + qr_token,
                "image_url": "/api/admin/qr/" + qr_token + "/image",
            },
        }
    )


# ========================================
# ADMIN — CAMPAIGN PERFORMANCE
# ========================================


@app.route("/api/admin/campaigns", methods=["GET"])
@admin_required
def admin_campaigns():

    connection = get_db()

    campaigns = connection.execute("""
        SELECT
            c.id,
            c.name,
            c.source,
            c.medium,
            c.link_id,
            c.token,
            c.enabled,
            c.created_at,
            c.updated_at,
            l.name AS link_name,

            (
                SELECT COUNT(*)
                FROM events e
                WHERE e.campaign_id = c.id
                AND e.event_type = 'click'
            ) AS clicks

        FROM campaigns c

        LEFT JOIN links l
            ON l.id = c.link_id

        ORDER BY c.created_at DESC
        """).fetchall()

    qr_rows = connection.execute("""
        SELECT
            campaign_id,
            token
        FROM qr_codes
        WHERE campaign_id IS NOT NULL
        """).fetchall()

    qr_map = {row["campaign_id"]: row["token"] for row in qr_rows}

    connection.close()

    result = []

    for campaign in campaigns:

        item = dict(campaign)

        qr_token = qr_map.get(item["id"])

        if qr_token:

            item["qr_token"] = qr_token

            item["scan_url"] = phase7_public_base_url() + "/qr/" + qr_token

            item["image_url"] = "/api/admin/qr/" + qr_token + "/image"

        else:

            item["qr_token"] = None
            item["scan_url"] = None
            item["image_url"] = None

        result.append(item)

    return jsonify(
        {
            "success": True,
            "campaigns": result,
        }
    )


# ========================================
# ADMIN — DELETE CAMPAIGN
# ========================================


@app.route("/api/admin/campaigns/<int:campaign_id>", methods=["DELETE"])
@admin_required
def admin_delete_campaign(campaign_id):

    connection = get_db()

    existing = connection.execute(
        """
        SELECT id
        FROM campaigns
        WHERE id = ?
        """,
        (campaign_id,),
    ).fetchone()

    if not existing:

        connection.close()

        return (
            jsonify(
                {
                    "success": False,
                    "error": "Campaign not found.",
                }
            ),
            404,
        )

    connection.execute(
        """
        DELETE FROM qr_codes
        WHERE campaign_id = ?
        """,
        (campaign_id,),
    )

    connection.execute(
        """
        DELETE FROM campaigns
        WHERE id = ?
        """,
        (campaign_id,),
    )

    connection.commit()
    connection.close()

    return jsonify(
        {
            "success": True,
            "message": "Campaign deleted successfully.",
        }
    )


# ========================================
# PUBLIC — QR REDIRECT / TRACKING
# ========================================


@app.route("/qr/<token>", methods=["GET"])
def public_qr_redirect(token):

    connection = get_db()

    qr = connection.execute(
        """
        SELECT
            q.id,
            q.token,
            q.link_id,
            q.campaign_id,
            q.enabled,

            l.name AS link_name,
            l.url AS link_url,
            l.enabled AS link_enabled,

            c.name AS campaign_name,
            c.source AS campaign_source,
            c.medium AS campaign_medium,
            c.enabled AS campaign_enabled

        FROM qr_codes q

        LEFT JOIN links l
            ON l.id = q.link_id

        LEFT JOIN campaigns c
            ON c.id = q.campaign_id

        WHERE q.token = ?

        LIMIT 1
        """,
        (token,),
    ).fetchone()

    if not qr:

        connection.close()

        return (
            "QR code not found.",
            404,
        )

    if not qr["enabled"]:

        connection.close()

        return (
            "This QR code is disabled.",
            410,
        )

    if qr["campaign_id"] is not None and not qr["campaign_enabled"]:

        connection.close()

        return (
            "This campaign is disabled.",
            410,
        )

    if qr["link_id"] is not None and (not qr["link_url"] or not qr["link_enabled"]):

        connection.close()

        return (
            "The destination link is unavailable.",
            410,
        )

    if qr["link_id"] is not None:

        destination = qr["link_url"]

        link_name = qr["link_name"]

    else:

        destination = request.url_root

        link_name = "Main Link Hub"

    timestamp = datetime.now(timezone.utc).isoformat()

    user_agent = request.headers.get("User-Agent")

    referrer = request.headers.get("Referer")

    ip_address = request.remote_addr

    connection.execute(
        """
        INSERT INTO events (
            event_type,
            link_name,
            timestamp,
            user_agent,
            referrer,
            ip_address,
            timezone,
            campaign_id,
            campaign_name,
            campaign_source,
            campaign_medium,
            qr_token
        )
        VALUES (
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?
        )
        """,
        (
            "click",
            link_name,
            timestamp,
            user_agent,
            referrer,
            ip_address,
            None,
            qr["campaign_id"],
            qr["campaign_name"],
            qr["campaign_source"],
            qr["campaign_medium"],
            token,
        ),
    )

    connection.commit()
    connection.close()

    return redirect(destination)


# ========================================
# RECORD ANALYTICS EVENT
# PUBLIC
# ========================================


@app.route("/api/event", methods=["POST"])
def record_event():

    data = request.get_json(silent=True)

    if not data:

        return jsonify({"success": False, "error": "Invalid JSON"}), 400

    # ----------------------------------------
    # BASIC EVENT DATA
    # ----------------------------------------

    event_type = data.get("event_type", "unknown")

    link_name = data.get("link_name")

    # ----------------------------------------
    # SERVER DATA
    # ----------------------------------------

    timestamp = datetime.now(timezone.utc).isoformat()

    user_agent = request.headers.get("User-Agent")

    referrer = request.headers.get("Referer")

    ip_address = request.remote_addr

    # ----------------------------------------
    # CLIENT TIMEZONE
    # Privacy-conscious:
    # timezone only, no GPS/location.
    # ----------------------------------------

    timezone_name = data.get("timezone")

    if not isinstance(timezone_name, str):
        timezone_name = None

    else:

        timezone_name = timezone_name.strip()

        if not timezone_name:

            timezone_name = None

        elif len(timezone_name) > 100:

            timezone_name = None

    # ----------------------------------------
    # SAVE EVENT
    # ----------------------------------------

    connection = get_db()

    connection.execute(
        """
        INSERT INTO events (
            event_type,
            link_name,
            timestamp,
            user_agent,
            referrer,
            ip_address,
            timezone
        )

        VALUES (
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?
        )
        """,
        (
            event_type,
            link_name,
            timestamp,
            user_agent,
            referrer,
            ip_address,
            timezone_name,
        ),
    )

    connection.commit()

    connection.close()

    return jsonify({"success": True})


# ========================================

# ANALYTICS HELPERS

# ========================================


def detect_browser(user_agent):

    if not user_agent:

        return "Unknown"

    ua = user_agent.lower()

    if "edg/" in ua:

        return "Edge"

    if "opr/" in ua or "opera" in ua:

        return "Opera"

    if "firefox/" in ua:

        return "Firefox"

    if "chrome/" in ua and "edg/" not in ua:

        return "Chrome"

    if "safari/" in ua and "chrome/" not in ua:

        return "Safari"

    return "Other"


def detect_device(user_agent):

    if not user_agent:

        return "Unknown"

    ua = user_agent.lower()

    if "ipad" in ua or "tablet" in ua:

        return "Tablet"

    if "mobile" in ua or "iphone" in ua or "android" in ua:

        return "Mobile"

    return "Desktop"


def detect_operating_system(user_agent):

    if not user_agent:
        return "Unknown"

    ua = user_agent.lower()

    if "iphone" in ua or "ipad" in ua or "ipod" in ua:
        return "iOS"

    if "android" in ua:
        return "Android"

    if "windows phone" in ua:
        return "Windows Phone"

    if "windows" in ua:
        return "Windows"

    if "macintosh" in ua or "mac os x" in ua:
        return "macOS"

    if "cros" in ua:
        return "ChromeOS"

    if "linux" in ua:
        return "Linux"

    return "Other"


def build_breakdown(items):

    counts = {}

    for item in items:

        if not item:

            item = "Unknown"

        counts[item] = counts.get(item, 0) + 1

    return [
        {
            "name": name,
            "count": count,
        }
        for name, count in sorted(
            counts.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]


# ========================================
# TRAFFIC SOURCE
# ========================================


def detect_traffic_source(referrer):

    if not referrer:
        return "Direct"

    try:

        hostname = urlparse(referrer).hostname

        if not hostname:
            return "Other"

        hostname = hostname.lower()

    except Exception:

        return "Other"

    # ----------------------------------------
    # SOCIAL
    # ----------------------------------------

    if "instagram.com" in hostname or "instagram" in hostname:
        return "Instagram"

    if "facebook.com" in hostname or "fb.com" in hostname:
        return "Facebook"

    if "linkedin.com" in hostname or "linkedin" in hostname:
        return "LinkedIn"

    if "twitter.com" in hostname or "x.com" in hostname:
        return "X / Twitter"

    if "youtube.com" in hostname:
        return "YouTube"

    # ----------------------------------------
    # DEVELOPMENT
    # ----------------------------------------

    if "github.com" in hostname:
        return "GitHub"

    if "gitlab.com" in hostname:
        return "GitLab"

    # ----------------------------------------
    # SEARCH
    # ----------------------------------------

    if "google." in hostname:
        return "Google"

    if "bing.com" in hostname:
        return "Bing"

    if "duckduckgo.com" in hostname:
        return "DuckDuckGo"

    # ----------------------------------------
    # FALLBACK
    # ----------------------------------------

    return hostname


def safe_referrer(referrer):

    if not referrer:
        return "Direct"

    try:

        hostname = urlparse(referrer).hostname

        if hostname:
            return hostname.lower()

    except Exception:

        pass

    return "Other"


# ========================================
# APPROXIMATE LOCATION
# ========================================


def detect_approximate_region(timezone_name):

    if not timezone_name:
        return "Unknown"

    timezone_name = timezone_name.strip()

    # Privacy-conscious:
    # expose only country/region, not raw timezone.

    timezone_map = {
        "Asia/Kolkata": "India",
        "Asia/Calcutta": "India",
        "Asia/Dubai": "UAE",
        "Asia/Singapore": "Singapore",
        "Asia/Tokyo": "Japan",
        "Asia/Seoul": "South Korea",
        "Asia/Shanghai": "China",
        "Europe/London": "United Kingdom",
        "Europe/Paris": "France / Central Europe",
        "Europe/Berlin": "Germany / Central Europe",
        "America/New_York": "United States · East",
        "America/Chicago": "United States · Central",
        "America/Denver": "United States · Mountain",
        "America/Los_Angeles": "United States · West",
        "Australia/Sydney": "Australia",
    }

    if timezone_name in timezone_map:
        return timezone_map[timezone_name]

    if timezone_name.startswith("Asia/"):
        return "Asia"

    if timezone_name.startswith("Europe/"):
        return "Europe"

    if timezone_name.startswith("America/"):
        return "Americas"

    if timezone_name.startswith("Australia/"):
        return "Australia"

    if timezone_name.startswith("Africa/"):
        return "Africa"

    if timezone_name.startswith("Pacific/"):
        return "Pacific"

    return "Other"


# ========================================
# PRIVACY - MASK IP
# ========================================


def mask_ip(ip_address):

    if not ip_address:
        return "Unknown"

    # IPv4
    if "." in ip_address:

        parts = ip_address.split(".")

        if len(parts) == 4:

            return f"{parts[0]}." f"{parts[1]}." f"xxx.xxx"

    # IPv6
    if ":" in ip_address:

        parts = ip_address.split(":")

        return ":".join(parts[:3]) + ":••••"

    return "Hidden"


# ========================================
# ANALYTICS SUMMARY
# PROTECTED
# ========================================


@app.route("/api/analytics", methods=["GET"])
@admin_required
def analytics():

    connection = get_db()

    start = request.args.get("start")

    end = request.args.get("end")

    # ----------------------------------------

    # BUILD DATE FILTER

    # ----------------------------------------

    date_filter = ""

    date_params = []

    if start and end:

        date_filter = """

            WHERE timestamp >= ?

            AND timestamp < ?

        """

        date_params = [
            start,
            end,
        ]

    # ----------------------------------------

    # TOTAL EVENTS

    # ----------------------------------------

    total_events = connection.execute(
        f"""

        SELECT COUNT(*) AS count

        FROM events

        {date_filter}

        """,
        date_params,
    ).fetchone()["count"]

    # ----------------------------------------

    # TOTAL CLICKS

    # ----------------------------------------

    click_filter = """

        event_type = 'click'

    """

    click_params = []

    if start and end:

        click_filter += """

            AND timestamp >= ?

            AND timestamp < ?

        """

        click_params = [
            start,
            end,
        ]

    total_clicks = connection.execute(
        f"""

        SELECT COUNT(*) AS count

        FROM events

        WHERE {click_filter}

        """,
        click_params,
    ).fetchone()["count"]

    # ----------------------------------------

    # LINK CLICK BREAKDOWN

    # ----------------------------------------

    link_clicks = connection.execute(
        f"""

        SELECT

            link_name,

            COUNT(*) AS clicks

        FROM events

        WHERE event_type = 'click'

        {

            "AND timestamp >= ? AND timestamp < ?"

            if start and end

            else ""

        }

        GROUP BY link_name

        ORDER BY clicks DESC

        """,
        date_params,
    ).fetchall()

    # ----------------------------------------

    # TOP LINK

    # ----------------------------------------

    top_link = None

    if link_clicks:

        top_link = {
            "link_name": link_clicks[0]["link_name"],
            "clicks": link_clicks[0]["clicks"],
        }

    # ----------------------------------------

    # GET FILTERED EVENTS

    # FOR VISITOR INSIGHTS

    # ----------------------------------------

    visitor_events = connection.execute(
        f"""

        SELECT

            ip_address,

            user_agent,

            referrer,

            timezone

        FROM events

        WHERE event_type = 'visit'

        {

            "AND timestamp >= ? AND timestamp < ?"

            if start and end

            else ""

        }

        """,
        date_params,
    ).fetchall()

    # ----------------------------------------

    # UNIQUE + REPEAT VISITORS

    # ----------------------------------------

    visitor_counts = {}

    for event in visitor_events:

        ip = event["ip_address"]

        if not ip:

            continue

        visitor_counts[ip] = visitor_counts.get(ip, 0) + 1

    unique_visitors = len(visitor_counts)

    repeat_visitors = sum(1 for count in visitor_counts.values() if count > 1)

    one_time_visitors = sum(1 for count in visitor_counts.values() if count == 1)
    # ----------------------------------------

    # BROWSER BREAKDOWN

    # ----------------------------------------

    browser_breakdown = build_breakdown(
        [detect_browser(event["user_agent"]) for event in visitor_events]
    )

    # ----------------------------------------

    # DEVICE BREAKDOWN

    # ----------------------------------------

    device_breakdown = build_breakdown(
        [detect_device(event["user_agent"]) for event in visitor_events]
    )

    # ----------------------------------------
    # OPERATING SYSTEM BREAKDOWN
    # ----------------------------------------

    os_breakdown = build_breakdown(
        [detect_operating_system(event["user_agent"]) for event in visitor_events]
    )

    # ----------------------------------------

    # REFERRER BREAKDOWN

    # ----------------------------------------

    referrer_breakdown = build_breakdown(
        [safe_referrer(event["referrer"]) for event in visitor_events]
    )

    # ----------------------------------------
    # TRAFFIC SOURCE BREAKDOWN
    # ----------------------------------------

    traffic_source_breakdown = build_breakdown(
        [detect_traffic_source(event["referrer"]) for event in visitor_events]
    )

    # ----------------------------------------
    # APPROXIMATE LOCATION
    # ----------------------------------------

    location_breakdown = build_breakdown(
        [detect_approximate_region(event["timezone"]) for event in visitor_events]
    )

    # ----------------------------------------

    # LAST ACTIVITY

    # ----------------------------------------

    last_activity = connection.execute(
        f"""

        SELECT

            id,

            event_type,

            link_name,

            timestamp

        FROM events

        {

            "WHERE timestamp >= ? AND timestamp < ?"

            if start and end

            else ""

        }

        ORDER BY id DESC

        LIMIT 1

        """,
        date_params,
    ).fetchone()

    connection.close()

    # ----------------------------------------

    # RESPONSE

    # ----------------------------------------

    return jsonify(
        {
            "success": True,
            "range": {
                "start": start,
                "end": end,
            },
            "summary": {
                "total_events": total_events,
                "total_clicks": total_clicks,
                "top_link": top_link,
                "last_activity": (dict(last_activity) if last_activity else None),
            },
            "visitor_insights": {
                "unique_visitors": unique_visitors,
                "repeat_visitors": repeat_visitors,
                "browser_breakdown": browser_breakdown,
                "device_breakdown": device_breakdown,
                "os_breakdown": os_breakdown,
                "referrer_breakdown": referrer_breakdown,
                "visitor_type_breakdown": [
                    {
                        "name": "One-time Visitors",
                        "count": one_time_visitors,
                    },
                    {
                        "name": "Repeat Visitors",
                        "count": repeat_visitors,
                    },
                ],
                "traffic_source_breakdown": traffic_source_breakdown,
                "location_breakdown": location_breakdown,
            },
            "link_clicks": [dict(row) for row in link_clicks],
            # Compatibility
            "total_events": total_events,
            "total_clicks": total_clicks,
        }
    )


# ========================================
# INDIVIDUAL LINK ANALYTICS
# PHASE 5
# PROTECTED
# ========================================


@app.route("/api/link-analytics", methods=["GET"])
@admin_required
def link_analytics():

    connection = get_db()

    link_name = request.args.get("link_name", "").strip()

    if not link_name:

        connection.close()

        return jsonify({"success": False, "message": "Link name is required."}), 400

    # ========================================
    # DATE RANGES
    # ========================================

    today_start = request.args.get("today_start")

    today_end = request.args.get("today_end")

    week_start = request.args.get("week_start")

    week_end = request.args.get("week_end")

    month_start = request.args.get("month_start")

    month_end = request.args.get("month_end")

    history_start = request.args.get("history_start")

    history_end = request.args.get("history_end")

    # ========================================
    # TIMEZONE OFFSET
    #
    # JavaScript getTimezoneOffset():
    # India = -330
    #
    # UTC → local:
    # UTC - offset
    # ========================================

    try:

        timezone_offset = int(request.args.get("timezone_offset", "0"))

    except (TypeError, ValueError):

        timezone_offset = 0

    def count_clicks(start=None, end=None):

        query = """
            SELECT COUNT(*) AS count
            FROM events
            WHERE event_type = 'click'
            AND link_name = ?
        """

        params = [link_name]

        if start and end:

            query += """
                AND timestamp >= ?
                AND timestamp < ?
            """

            params.extend([start, end])

        row = connection.execute(query, params).fetchone()

        return row["count"]

    # ========================================
    # PERIOD COUNTS
    # ========================================

    today_clicks = count_clicks(today_start, today_end)

    week_clicks = count_clicks(week_start, week_end)

    month_clicks = count_clicks(month_start, month_end)

    all_time_clicks = count_clicks()

    # ========================================
    # ALL-TIME CLICK EVENTS
    #
    # Used for:
    # - Peak hour
    # - Peak day
    # ========================================

    click_events = connection.execute(
        """
            SELECT timestamp
            FROM events
            WHERE event_type = 'click'
            AND link_name = ?
            ORDER BY timestamp ASC
            """,
        (link_name,),
    ).fetchall()

    hour_counts = {}

    day_counts = {}

    for event in click_events:

        timestamp = event["timestamp"]

        if not timestamp:
            continue

        try:

            event_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        except ValueError:

            continue

        local_time = event_time + timedelta(minutes=-timezone_offset)

        hour = local_time.hour

        day = local_time.strftime("%A")

        hour_counts[hour] = hour_counts.get(hour, 0) + 1

        day_counts[day] = day_counts.get(day, 0) + 1

    peak_hour = None

    peak_day = None

    if hour_counts:

        peak_hour_number = max(hour_counts, key=hour_counts.get)

        peak_hour = {
            "label": f"{peak_hour_number:02d}:00",
            "clicks": hour_counts[peak_hour_number],
        }

    if day_counts:

        peak_day_name = max(day_counts, key=day_counts.get)

        peak_day = {"label": peak_day_name, "clicks": day_counts[peak_day_name]}

    # ========================================
    # TRAFFIC SOURCES PER LINK
    # ========================================

    source_events = connection.execute(
        """
            SELECT referrer
            FROM events
            WHERE event_type = 'click'
            AND link_name = ?
            """,
        (link_name,),
    ).fetchall()

    source_counts = {}

    for event in source_events:

        source = detect_traffic_source(event["referrer"])

        source_counts[source] = source_counts.get(source, 0) + 1

    traffic_sources = [
        {"name": name, "count": count}
        for name, count in sorted(
            source_counts.items(), key=lambda item: item[1], reverse=True
        )
    ]

    # ========================================
    # RECENT CLICK DETAILS
    # ========================================

    recent_clicks = connection.execute(
        """
            SELECT
                timestamp,
                user_agent,
                referrer
            FROM events
            WHERE event_type = 'click'
            AND link_name = ?
            ORDER BY id DESC
            LIMIT 10
            """,
        (link_name,),
    ).fetchall()

    click_details = []

    for event in recent_clicks:

        click_details.append(
            {
                "timestamp": event["timestamp"],
                "browser": detect_browser(event["user_agent"]),
                "device": detect_device(event["user_agent"]),
                "referrer": safe_referrer(event["referrer"]),
                "traffic_source": detect_traffic_source(event["referrer"]),
            }
        )

    # ========================================
    # 30-DAY PERFORMANCE HISTORY
    # ========================================

    history_events = []

    if history_start and history_end:

        history_events = connection.execute(
            """
                SELECT timestamp
                FROM events
                WHERE event_type = 'click'
                AND link_name = ?
                AND timestamp >= ?
                AND timestamp < ?
                ORDER BY timestamp ASC
                """,
            (link_name, history_start, history_end),
        ).fetchall()

    else:

        history_events = connection.execute(
            """
                SELECT timestamp
                FROM events
                WHERE event_type = 'click'
                AND link_name = ?
                ORDER BY timestamp ASC
                """,
            (link_name,),
        ).fetchall()

    history_counts = {}

    for event in history_events:

        timestamp = event["timestamp"]

        if not timestamp:

            continue

        try:

            event_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        except ValueError:

            continue

        local_time = event_time + timedelta(minutes=-timezone_offset)

        date_key = local_time.strftime("%Y-%m-%d")

        history_counts[date_key] = history_counts.get(date_key, 0) + 1

    history = [
        {"date": date, "clicks": count}
        for date, count in sorted(history_counts.items())
    ]

    connection.close()

    # ========================================
    # RESPONSE
    # ========================================

    return jsonify(
        {
            "success": True,
            "link_name": link_name,
            "periods": {
                "today": today_clicks,
                "week": week_clicks,
                "month": month_clicks,
                "all_time": all_time_clicks,
            },
            "peak_activity": {"hour": peak_hour, "day": peak_day},
            "traffic_sources": traffic_sources,
            "recent_clicks": click_details,
            "history": history,
        }
    )


# ========================================

# ANALYTICS CHART DATA

# PROTECTED

# ========================================


@app.route("/api/chart-data", methods=["GET"])
@admin_required
def chart_data():

    connection = get_db()

    start = request.args.get("start")
    end = request.args.get("end")

    # ----------------------------------------
    # DATE FILTER
    # ----------------------------------------

    date_filter = ""
    date_params = []

    if start and end:

        date_filter = """
            WHERE timestamp >= ?
            AND timestamp < ?
        """

        date_params = [start, end]

    # ----------------------------------------
    # CHART EVENTS
    #
    # IMPORTANT:
    # No IP address is returned here.
    # ----------------------------------------

    events = connection.execute(
        f"""
        SELECT
            event_type,
            link_name,
            timestamp,
            referrer,
            user_agent,
            timezone
        FROM events
        {date_filter}
        ORDER BY timestamp ASC
        """,
        date_params,
    ).fetchall()

    connection.close()

    return jsonify(
        {
            "success": True,
            "range": {
                "start": start,
                "end": end,
            },
            "events": [dict(event) for event in events],
        }
    )


# ========================================

# RECENT ACTIVITY

# PROTECTED

# ========================================


@app.route("/api/recent", methods=["GET"])
@admin_required
def recent_activity():

    connection = get_db()

    start = request.args.get("start")

    end = request.args.get("end")

    # ----------------------------------------

    # DATE FILTER

    # ----------------------------------------

    date_filter = ""

    date_params = []

    if start and end:

        date_filter = """

            WHERE timestamp >= ?

            AND timestamp < ?

        """

        date_params = [
            start,
            end,
        ]

    # ----------------------------------------

    # GET RECENT EVENTS

    # ----------------------------------------

    events = connection.execute(
        f"""

        SELECT

            id,

            event_type,

            link_name,

            timestamp,

            user_agent,

            referrer,

            ip_address

        FROM events

        {date_filter}

        ORDER BY id DESC

        LIMIT 20

        """,
        date_params,
    ).fetchall()

    connection.close()

    # ========================================
    # PRIVACY - MASK IP BEFORE RESPONSE
    # ========================================

    safe_events = []

    for event in events:

        item = dict(event)

        item["referrer"] = safe_referrer(item.get("referrer"))

        item["ip_address"] = mask_ip(item.get("ip_address"))

        safe_events.append(item)

    return jsonify({"events": safe_events})


# ========================================

# CLEAR ANALYTICS

# PROTECTED

# ========================================


@app.route("/api/analytics/clear", methods=["POST"])
@admin_required
def clear_analytics():

    connection = get_db()

    connection.execute("DELETE FROM events")

    connection.commit()

    connection.close()

    return jsonify(
        {
            "success": True,
            "message": "Analytics cleared successfully.",
        }
    )


# ========================================
# ALL EVENTS
# PROTECTED
# ========================================


@app.route("/api/events", methods=["GET"])
@admin_required
def all_events():

    connection = get_db()

    events = connection.execute("""

        SELECT

            id,

            event_type,

            link_name,

            timestamp,

            user_agent,

            referrer,

            ip_address

        FROM events

        ORDER BY id DESC

        """).fetchall()

    connection.close()

    safe_events = []

    for event in events:

        item = dict(event)

        item["referrer"] = safe_referrer(item.get("referrer"))

        item["ip_address"] = mask_ip(item.get("ip_address"))

        safe_events.append(item)

    return jsonify({"events": safe_events})


# ========================================
# PHASE 8 — EXPORT CSV
# PROTECTED
# ========================================


@app.route("/api/export/csv", methods=["GET"])
@admin_required
def export_csv():

    connection = get_db()

    events = connection.execute("""
        SELECT
            id,
            event_type,
            link_name,
            timestamp,
            user_agent,
            referrer,
            ip_address,
            timezone,
            campaign_id,
            campaign_name,
            campaign_source,
            campaign_medium,
            qr_token
        FROM events
        ORDER BY id DESC
        """).fetchall()

    connection.close()

    output = StringIO()

    writer = csv.writer(output)

    # ----------------------------------------
    # CSV HEADER
    # ----------------------------------------

    writer.writerow(
        [
            "ID",
            "Event Type",
            "Link",
            "Timestamp",
            "Browser",
            "Device",
            "Referrer",
            "IP Address",
            "Timezone",
            "Campaign ID",
            "Campaign Name",
            "Campaign Source",
            "Campaign Medium",
            "QR Token",
        ]
    )

    # ----------------------------------------
    # CSV DATA
    # ----------------------------------------

    for event in events:

        row = dict(event)

        writer.writerow(
            [
                row.get("id"),
                row.get("event_type"),
                row.get("link_name"),
                row.get("timestamp"),
                detect_browser(row.get("user_agent")),
                detect_device(row.get("user_agent")),
                safe_referrer(row.get("referrer")),
                mask_ip(row.get("ip_address")),
                row.get("timezone"),
                row.get("campaign_id"),
                row.get("campaign_name"),
                row.get("campaign_source"),
                row.get("campaign_medium"),
                row.get("qr_token"),
            ]
        )

    output.seek(0)

    return app.response_class(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=manas-link-hub-analytics.csv"
        },
    )


# ========================================
# PHASE 8 — EXPORT FILTERED CSV
# PROTECTED
# ========================================


@app.route("/api/export/csv/filtered", methods=["GET"])
@admin_required
def export_filtered_csv():

    connection = get_db()

    start = request.args.get("start")
    end = request.args.get("end")

    # ----------------------------------------
    # DATE FILTER
    # ----------------------------------------

    date_filter = ""
    date_params = []

    if start and end:

        date_filter = """
            WHERE timestamp >= ?
            AND timestamp < ?
        """

        date_params = [
            start,
            end,
        ]

    # ----------------------------------------
    # GET FILTERED EVENTS
    # ----------------------------------------

    events = connection.execute(
        f"""
        SELECT
            id,
            event_type,
            link_name,
            timestamp,
            user_agent,
            referrer,
            ip_address,
            timezone,
            campaign_id,
            campaign_name,
            campaign_source,
            campaign_medium,
            qr_token
        FROM events
        {date_filter}
        ORDER BY id DESC
        """,
        date_params,
    ).fetchall()

    connection.close()

    # ----------------------------------------
    # CREATE CSV
    # ----------------------------------------

    output = StringIO()

    writer = csv.writer(output)

    writer.writerow(
        [
            "ID",
            "Event Type",
            "Link",
            "Timestamp",
            "Browser",
            "Device",
            "Referrer",
            "IP Address",
            "Timezone",
            "Campaign ID",
            "Campaign Name",
            "Campaign Source",
            "Campaign Medium",
            "QR Token",
        ]
    )

    # ----------------------------------------
    # CSV DATA
    # ----------------------------------------

    for event in events:

        row = dict(event)

        writer.writerow(
            [
                row.get("id"),
                row.get("event_type"),
                row.get("link_name"),
                row.get("timestamp"),
                detect_browser(row.get("user_agent")),
                detect_device(row.get("user_agent")),
                safe_referrer(row.get("referrer")),
                mask_ip(row.get("ip_address")),
                row.get("timezone"),
                row.get("campaign_id"),
                row.get("campaign_name"),
                row.get("campaign_source"),
                row.get("campaign_medium"),
                row.get("qr_token"),
            ]
        )

    output.seek(0)

    return app.response_class(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=manas-link-hub-filtered-analytics.csv"
        },
    )


# ========================================
# PHASE 8 — ANALYTICS SUMMARY
# PROTECTED
# ========================================


@app.route("/api/reports/summary", methods=["GET"])
@admin_required
def analytics_summary():

    connection = get_db()

    start = request.args.get("start")
    end = request.args.get("end")

    # ----------------------------------------
    # DATE FILTER
    # ----------------------------------------

    date_filter = ""

    date_params = []

    if start and end:

        date_filter = """
            WHERE timestamp >= ?
            AND timestamp < ?
        """

        date_params = [
            start,
            end,
        ]

    # ----------------------------------------
    # TOTAL EVENTS
    # ----------------------------------------

    total_events = connection.execute(
        f"""
        SELECT COUNT(*) AS count
        FROM events
        {date_filter}
        """,
        date_params,
    ).fetchone()["count"]

    # ----------------------------------------
    # TOTAL VISITS
    # ----------------------------------------

    visit_params = []

    visit_filter = """
        event_type = 'visit'
    """

    if start and end:

        visit_filter += """
            AND timestamp >= ?
            AND timestamp < ?
        """

        visit_params = [
            start,
            end,
        ]

    total_visits = connection.execute(
        f"""
        SELECT COUNT(*) AS count
        FROM events
        WHERE {visit_filter}
        """,
        visit_params,
    ).fetchone()["count"]

    # ----------------------------------------
    # TOTAL CLICKS
    # ----------------------------------------

    click_params = []

    click_filter = """
        event_type = 'click'
    """

    if start and end:

        click_filter += """
            AND timestamp >= ?
            AND timestamp < ?
        """

        click_params = [
            start,
            end,
        ]

    total_clicks = connection.execute(
        f"""
        SELECT COUNT(*) AS count
        FROM events
        WHERE {click_filter}
        """,
        click_params,
    ).fetchone()["count"]

    # ----------------------------------------
    # VISITOR EVENTS
    # ----------------------------------------

    visitor_events = connection.execute(
        f"""
        SELECT
            ip_address,
            user_agent,
            referrer
        FROM events
        WHERE event_type = 'visit'

        {
            "AND timestamp >= ? AND timestamp < ?"
            if start and end
            else ""
        }

        """,
        date_params,
    ).fetchall()

    # ----------------------------------------
    # UNIQUE + REPEAT VISITORS
    # ----------------------------------------

    visitor_counts = {}

    for event in visitor_events:

        ip = event["ip_address"]

        if not ip:

            continue

        visitor_counts[ip] = visitor_counts.get(ip, 0) + 1

    unique_visitors = len(visitor_counts)

    repeat_visitors = sum(1 for count in visitor_counts.values() if count > 1)

    # ----------------------------------------
    # BROWSER
    # ----------------------------------------

    browser_breakdown = build_breakdown(
        [detect_browser(event["user_agent"]) for event in visitor_events]
    )

    # ----------------------------------------
    # DEVICE
    # ----------------------------------------

    device_breakdown = build_breakdown(
        [detect_device(event["user_agent"]) for event in visitor_events]
    )

    # ----------------------------------------
    # REFERRER
    # ----------------------------------------

    referrer_breakdown = build_breakdown(
        [safe_referrer(event["referrer"]) for event in visitor_events]
    )

    # ----------------------------------------
    # TRAFFIC SOURCE
    # ----------------------------------------

    traffic_source_breakdown = build_breakdown(
        [detect_traffic_source(event["referrer"]) for event in visitor_events]
    )

    # ----------------------------------------
    # TOP LINK
    # ----------------------------------------

    link_clicks = connection.execute(
        f"""
        SELECT
            link_name,
            COUNT(*) AS clicks
        FROM events
        WHERE event_type = 'click'

        {
            "AND timestamp >= ? AND timestamp < ?"
            if start and end
            else ""
        }

        GROUP BY link_name
        ORDER BY clicks DESC
        LIMIT 1
        """,
        date_params,
    ).fetchone()

    top_link = None

    if link_clicks:

        top_link = {
            "name": link_clicks["link_name"],
            "clicks": link_clicks["clicks"],
        }

    # ----------------------------------------
    # CLICK RATE
    # ----------------------------------------

    click_rate = (total_clicks / total_visits) * 100 if total_visits > 0 else 0

    # ----------------------------------------
    # LAST ACTIVITY
    # ----------------------------------------

    last_activity = connection.execute(
        f"""
        SELECT
            id,
            event_type,
            link_name,
            timestamp
        FROM events

        {
            "WHERE timestamp >= ? AND timestamp < ?"
            if start and end
            else ""
        }

        ORDER BY id DESC
        LIMIT 1
        """,
        date_params,
    ).fetchone()

    connection.close()

    # ----------------------------------------
    # RESPONSE
    # ----------------------------------------

    return jsonify(
        {
            "success": True,
            "range": {
                "start": start,
                "end": end,
            },
            "summary": {
                "total_events": total_events,
                "total_visits": total_visits,
                "total_clicks": total_clicks,
                "unique_visitors": unique_visitors,
                "repeat_visitors": repeat_visitors,
                "click_rate": round(click_rate, 2),
                "top_link": top_link,
                "top_browser": (
                    browser_breakdown[0]["name"] if browser_breakdown else None
                ),
                "top_device": (
                    device_breakdown[0]["name"] if device_breakdown else None
                ),
                "top_referrer": (
                    referrer_breakdown[0]["name"] if referrer_breakdown else None
                ),
                "top_traffic_source": (
                    traffic_source_breakdown[0]["name"]
                    if traffic_source_breakdown
                    else None
                ),
                "last_activity": (dict(last_activity) if last_activity else None),
            },
        }
    )


# ========================================
# PHASE 8 — MONTHLY REPORT
# PROTECTED
# ========================================


@app.route("/api/reports/monthly", methods=["GET"])
@admin_required
def monthly_report():

    connection = get_db()

    month = request.args.get("month")

    # ----------------------------------------
    # VALIDATE MONTH
    # ----------------------------------------

    if not month:

        connection.close()

        return (
            jsonify({"success": False, "message": "Month is required. Use YYYY-MM."}),
            400,
        )

    try:

        month_start = datetime.strptime(month, "%Y-%m").replace(tzinfo=timezone.utc)

    except ValueError:

        connection.close()

        return (
            jsonify({"success": False, "message": "Invalid month. Use YYYY-MM."}),
            400,
        )

    # ----------------------------------------
    # NEXT MONTH
    # ----------------------------------------

    if month_start.month == 12:

        next_month = month_start.replace(year=month_start.year + 1, month=1, day=1)

    else:

        next_month = month_start.replace(month=month_start.month + 1, day=1)

    start = month_start.isoformat()
    end = next_month.isoformat()

    # ----------------------------------------
    # TOTAL EVENTS
    # ----------------------------------------

    total_events = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM events
        WHERE timestamp >= ?
        AND timestamp < ?
        """,
        [
            start,
            end,
        ],
    ).fetchone()["count"]

    # ----------------------------------------
    # TOTAL VISITS
    # ----------------------------------------

    total_visits = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM events
        WHERE event_type = 'visit'
        AND timestamp >= ?
        AND timestamp < ?
        """,
        [
            start,
            end,
        ],
    ).fetchone()["count"]

    # ----------------------------------------
    # TOTAL CLICKS
    # ----------------------------------------

    total_clicks = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM events
        WHERE event_type = 'click'
        AND timestamp >= ?
        AND timestamp < ?
        """,
        [
            start,
            end,
        ],
    ).fetchone()["count"]

    # ----------------------------------------
    # VISITOR EVENTS
    # ----------------------------------------

    visitor_events = connection.execute(
        """
        SELECT
            ip_address,
            user_agent,
            referrer
        FROM events
        WHERE event_type = 'visit'
        AND timestamp >= ?
        AND timestamp < ?
        """,
        [
            start,
            end,
        ],
    ).fetchall()

    # ----------------------------------------
    # UNIQUE + REPEAT VISITORS
    # ----------------------------------------

    visitor_counts = {}

    for event in visitor_events:

        ip = event["ip_address"]

        if not ip:

            continue

        visitor_counts[ip] = visitor_counts.get(ip, 0) + 1

    unique_visitors = len(visitor_counts)

    repeat_visitors = sum(1 for count in visitor_counts.values() if count > 1)

    # ----------------------------------------
    # BROWSER BREAKDOWN
    # ----------------------------------------

    browser_breakdown = build_breakdown(
        [detect_browser(event["user_agent"]) for event in visitor_events]
    )

    # ----------------------------------------
    # DEVICE BREAKDOWN
    # ----------------------------------------

    device_breakdown = build_breakdown(
        [detect_device(event["user_agent"]) for event in visitor_events]
    )

    # ----------------------------------------
    # TRAFFIC SOURCE BREAKDOWN
    # ----------------------------------------

    traffic_source_breakdown = build_breakdown(
        [detect_traffic_source(event["referrer"]) for event in visitor_events]
    )

    # ----------------------------------------
    # TOP LINK
    # ----------------------------------------

    top_link = connection.execute(
        """
        SELECT
            link_name,
            COUNT(*) AS clicks
        FROM events
        WHERE event_type = 'click'
        AND timestamp >= ?
        AND timestamp < ?
        GROUP BY link_name
        ORDER BY clicks DESC
        LIMIT 1
        """,
        [
            start,
            end,
        ],
    ).fetchone()

    top_link_data = None

    if top_link:

        top_link_data = {
            "name": top_link["link_name"],
            "clicks": top_link["clicks"],
        }

    # ----------------------------------------
    # CLICK RATE
    # ----------------------------------------

    click_rate = (total_clicks / total_visits) * 100 if total_visits > 0 else 0

    # ----------------------------------------
    # DAILY ACTIVITY
    # ----------------------------------------

    daily_rows = connection.execute(
        """
        SELECT
            substr(timestamp, 1, 10) AS date,
            COUNT(*) AS events,
            SUM(
                CASE
                    WHEN event_type = 'visit'
                    THEN 1
                    ELSE 0
                END
            ) AS visits,
            SUM(
                CASE
                    WHEN event_type = 'click'
                    THEN 1
                    ELSE 0
                END
            ) AS clicks
        FROM events
        WHERE timestamp >= ?
        AND timestamp < ?
        GROUP BY substr(timestamp, 1, 10)
        ORDER BY date ASC
        """,
        [
            start,
            end,
        ],
    ).fetchall()

    daily_activity = [
        {
            "date": row["date"],
            "events": row["events"],
            "visits": row["visits"],
            "clicks": row["clicks"],
        }
        for row in daily_rows
    ]

    connection.close()

    # ----------------------------------------
    # RESPONSE
    # ----------------------------------------

    return jsonify(
        {
            "success": True,
            "month": month,
            "range": {
                "start": start,
                "end": end,
            },
            "summary": {
                "total_events": total_events,
                "total_visits": total_visits,
                "total_clicks": total_clicks,
                "unique_visitors": unique_visitors,
                "repeat_visitors": repeat_visitors,
                "click_rate": round(click_rate, 2),
                "top_link": top_link_data,
                "top_browser": (
                    browser_breakdown[0]["name"] if browser_breakdown else None
                ),
                "top_device": (
                    device_breakdown[0]["name"] if device_breakdown else None
                ),
                "top_traffic_source": (
                    traffic_source_breakdown[0]["name"]
                    if traffic_source_breakdown
                    else None
                ),
            },
            "daily_activity": daily_activity,
        }
    )


# ========================================
# PHASE 8 — PDF MONTHLY REPORT
# PROTECTED
# ========================================


@app.route("/api/reports/monthly/pdf", methods=["GET"])
@admin_required
def monthly_report_pdf():

    connection = get_db()

    month = request.args.get("month")

    # ----------------------------------------
    # VALIDATE MONTH
    # ----------------------------------------

    if not month:

        connection.close()

        return (
            jsonify({"success": False, "message": "Month is required. Use YYYY-MM."}),
            400,
        )

    try:

        month_start = datetime.strptime(month, "%Y-%m").replace(tzinfo=timezone.utc)

    except ValueError:

        connection.close()

        return (
            jsonify({"success": False, "message": "Invalid month. Use YYYY-MM."}),
            400,
        )

    # ----------------------------------------
    # NEXT MONTH
    # ----------------------------------------

    if month_start.month == 12:

        next_month = month_start.replace(year=month_start.year + 1, month=1, day=1)

    else:

        next_month = month_start.replace(month=month_start.month + 1, day=1)

    start = month_start.isoformat()
    end = next_month.isoformat()

    # ----------------------------------------
    # SUMMARY
    # ----------------------------------------

    total_events = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM events
        WHERE timestamp >= ?
        AND timestamp < ?
        """,
        [start, end],
    ).fetchone()["count"]

    total_visits = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM events
        WHERE event_type = 'visit'
        AND timestamp >= ?
        AND timestamp < ?
        """,
        [start, end],
    ).fetchone()["count"]

    total_clicks = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM events
        WHERE event_type = 'click'
        AND timestamp >= ?
        AND timestamp < ?
        """,
        [start, end],
    ).fetchone()["count"]

    visitor_events = connection.execute(
        """
        SELECT
            ip_address,
            user_agent,
            referrer
        FROM events
        WHERE event_type = 'visit'
        AND timestamp >= ?
        AND timestamp < ?
        """,
        [start, end],
    ).fetchall()

    # ----------------------------------------
    # VISITORS
    # ----------------------------------------

    visitor_counts = {}

    for event in visitor_events:

        ip = event["ip_address"]

        if not ip:

            continue

        visitor_counts[ip] = visitor_counts.get(ip, 0) + 1

    unique_visitors = len(visitor_counts)

    repeat_visitors = sum(1 for count in visitor_counts.values() if count > 1)

    # ----------------------------------------
    # BROWSER / DEVICE / SOURCE
    # ----------------------------------------

    browser_breakdown = build_breakdown(
        [detect_browser(event["user_agent"]) for event in visitor_events]
    )

    device_breakdown = build_breakdown(
        [detect_device(event["user_agent"]) for event in visitor_events]
    )

    traffic_source_breakdown = build_breakdown(
        [detect_traffic_source(event["referrer"]) for event in visitor_events]
    )

    # ----------------------------------------
    # TOP LINK
    # ----------------------------------------

    top_link = connection.execute(
        """
        SELECT
            link_name,
            COUNT(*) AS clicks
        FROM events
        WHERE event_type = 'click'
        AND timestamp >= ?
        AND timestamp < ?
        GROUP BY link_name
        ORDER BY clicks DESC
        LIMIT 1
        """,
        [start, end],
    ).fetchone()

    top_link_name = top_link["link_name"] if top_link else "No clicks"

    top_link_clicks = top_link["clicks"] if top_link else 0

    # ----------------------------------------
    # CLICK RATE
    # ----------------------------------------

    click_rate = (total_clicks / total_visits) * 100 if total_visits > 0 else 0

    # ----------------------------------------
    # DAILY ACTIVITY
    # ----------------------------------------

    daily_rows = connection.execute(
        """
        SELECT
            substr(timestamp, 1, 10) AS date,
            COUNT(*) AS events,
            SUM(
                CASE
                    WHEN event_type = 'visit'
                    THEN 1
                    ELSE 0
                END
            ) AS visits,
            SUM(
                CASE
                    WHEN event_type = 'click'
                    THEN 1
                    ELSE 0
                END
            ) AS clicks
        FROM events
        WHERE timestamp >= ?
        AND timestamp < ?
        GROUP BY substr(timestamp, 1, 10)
        ORDER BY date ASC
        """,
        [start, end],
    ).fetchall()

    connection.close()

    # ----------------------------------------
    # CREATE PDF
    # ----------------------------------------

    pdf_buffer = BytesIO()

    document = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = styles["Title"]

    heading_style = styles["Heading2"]

    normal_style = styles["BodyText"]

    story = []

    # ----------------------------------------
    # TITLE
    # ----------------------------------------

    story.append(Paragraph("Manas Link Hub", title_style))

    story.append(Paragraph(f"Monthly Analytics Report — {month}", heading_style))

    story.append(Spacer(1, 8))

    story.append(
        Paragraph(
            f"Report period: "
            f"{month_start.strftime('%d %B %Y')} "
            f"to "
            f"{(next_month - timedelta(days=1)).strftime('%d %B %Y')}",
            normal_style,
        )
    )

    story.append(Spacer(1, 14))

    # ----------------------------------------
    # SUMMARY TABLE
    # ----------------------------------------

    summary_data = [
        ["Metric", "Value"],
        ["Total Events", str(total_events)],
        ["Total Visits", str(total_visits)],
        ["Total Clicks", str(total_clicks)],
        ["Click Rate", f"{click_rate:.2f}%"],
        ["Unique Visitors", str(unique_visitors)],
        ["Repeat Visitors", str(repeat_visitors)],
        ["Top Link", f"{top_link_name} " f"({top_link_clicks} clicks)"],
        [
            "Top Browser",
            (browser_breakdown[0]["name"] if browser_breakdown else "No data"),
        ],
        [
            "Top Device",
            (device_breakdown[0]["name"] if device_breakdown else "No data"),
        ],
        [
            "Top Traffic Source",
            (
                traffic_source_breakdown[0]["name"]
                if traffic_source_breakdown
                else "No data"
            ),
        ],
    ]

    summary_table = Table(
        summary_data,
        colWidths=[
            70 * mm,
            95 * mm,
        ],
    )

    summary_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#eeeeee"),
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    story.append(summary_table)

    story.append(Spacer(1, 18))

    # ----------------------------------------
    # DAILY ACTIVITY
    # ----------------------------------------

    story.append(Paragraph("Daily Activity", heading_style))

    story.append(Spacer(1, 8))

    daily_data = [
        [
            "Date",
            "Events",
            "Visits",
            "Clicks",
        ]
    ]

    for row in daily_rows:

        daily_data.append(
            [
                row["date"],
                str(row["events"]),
                str(row["visits"]),
                str(row["clicks"]),
            ]
        )

    if len(daily_data) == 1:

        daily_data.append(
            [
                "No activity",
                "0",
                "0",
                "0",
            ]
        )

    daily_table = Table(
        daily_data,
        colWidths=[
            60 * mm,
            35 * mm,
            35 * mm,
            35 * mm,
        ],
        repeatRows=1,
    )

    daily_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#eeeeee"),
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey,
                ),
                (
                    "ALIGN",
                    (1, 1),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    story.append(daily_table)

    story.append(Spacer(1, 18))

    story.append(Paragraph("Generated by Manas Link Hub Analytics", normal_style))

    # ----------------------------------------
    # BUILD PDF
    # ----------------------------------------

    document.build(story)

    pdf_buffer.seek(0)

    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=(f"manas-link-hub-report-{month}.pdf"),
    )


# ========================================

# DATABASE INFORMATION

# PROTECTED

# ========================================


@app.route("/api/database", methods=["GET"])
@admin_required
def database_info():

    connection = get_db()

    total_records = connection.execute("""

        SELECT COUNT(*) AS count

        FROM events

        """).fetchone()["count"]

    connection.close()

    return jsonify(
        {
            "database": "PostgreSQL" if DATABASE_URL else DATABASE,
            "total_records": total_records,
        }
    )


# ========================================

# START SERVER

# ========================================

if __name__ == "__main__":

    print()

    print("========================================")

    print(" Manas Link Hub Analytics")

    print("========================================")

    print(f" Database: {'PostgreSQL' if DATABASE_URL else DATABASE}")

    email_status = (
        "configured"
        if ADMIN_EMAIL and os.environ.get("RESEND_API_KEY")
        else "NOT configured"
    )

    print(f" Email OTP: {email_status}")

    print(" Server: http://127.0.0.1:5000")

    print("========================================")

    print()

    app.run(host="127.0.0.1", port=5000, debug=True)
