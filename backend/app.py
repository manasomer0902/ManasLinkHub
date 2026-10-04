from flask import Flask, request, jsonify, redirect, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from functools import wraps
import sqlite3
import os
import secrets
import smtplib
import hashlib
import hmac
from email.message import EmailMessage

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


DATABASE = os.path.join(BASE_DIR, "analytics.db")


# ========================================
# ADMIN CONFIGURATION
# ========================================

ADMIN_USERNAME = os.environ.get("MANAS_ADMIN_USERNAME", "manas")


ADMIN_PASSWORD_HASH = os.environ.get("MANAS_ADMIN_PASSWORD_HASH")


ADMIN_EMAIL = os.environ.get("MANAS_EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = os.environ.get("MANAS_EMAIL_APP_PASSWORD")


# Local password storage.
#
# The environment variable is used as the initial password.
# After a successful password reset, the new hash is stored
# in this local file so it survives Flask restarts.

PASSWORD_FILE = os.path.join(BASE_DIR, "admin_password.hash")


# ========================================
# PASSWORD STORAGE HELPERS
# ========================================


def get_current_password_hash():
    """
    Return the password hash currently used for admin login.

    A locally saved reset password takes priority over the
    environment variable so password changes survive restarts.
    """

    if os.path.exists(PASSWORD_FILE):

        try:
            with open(PASSWORD_FILE, "r", encoding="utf-8") as file:

                saved_hash = file.read().strip()

            if saved_hash:
                return saved_hash

        except OSError:
            pass

    return ADMIN_PASSWORD_HASH


def save_password_hash(new_password_hash):
    """
    Save the new password hash atomically.
    """

    temporary_file = PASSWORD_FILE + ".tmp"

    with open(temporary_file, "w", encoding="utf-8") as file:

        file.write(new_password_hash)

    os.replace(temporary_file, PASSWORD_FILE)


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
    if not ADMIN_EMAIL or not EMAIL_APP_PASSWORD:
        raise RuntimeError("Email configuration is missing")

    message = EmailMessage()
    message["Subject"] = "Manas Link Hub - Password Reset OTP"
    message["From"] = ADMIN_EMAIL
    message["To"] = ADMIN_EMAIL

    message.set_content(f"""Manas Link Hub Administrator,

Your password reset OTP is:

{otp}

This OTP expires in 10 minutes and can be used only once.

If you did not request a password reset, you can safely ignore this email.

Manas Link Hub
""")

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as smtp:
        smtp.starttls()
        smtp.login(ADMIN_EMAIL, EMAIL_APP_PASSWORD)
        smtp.send_message(message)


# ========================================
# DATABASE CONNECTION
# ========================================


def get_db():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    return connection


# ========================================
# DATABASE INITIALIZATION
# ========================================


def initialize_database():

    connection = get_db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS events (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            event_type TEXT NOT NULL,

            link_name TEXT,

            timestamp TEXT NOT NULL,

            user_agent TEXT,

            referrer TEXT,

            ip_address TEXT

        )
    """)

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

    connection.commit()

    connection.close()


# ========================================
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

    return jsonify({"status": "online", "service": "Manas Link Hub Analytics"})


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
            </label>


            <input
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
        return forgot_password_page(
            otp_stage=bool(session.get("password_reset_pending"))
        )

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
            or not EMAIL_APP_PASSWORD
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

        except Exception:
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
# RECORD ANALYTICS EVENT
# PUBLIC
# ========================================


@app.route("/api/event", methods=["POST"])
def record_event():

    data = request.get_json(silent=True)

    if not data:

        return jsonify({"success": False, "error": "Invalid JSON"}), 400

    event_type = data.get("event_type", "unknown")

    link_name = data.get("link_name")

    timestamp = datetime.now(timezone.utc).isoformat()

    user_agent = request.headers.get("User-Agent")

    referrer = request.headers.get("Referer")

    ip_address = request.remote_addr

    connection = get_db()

    connection.execute(
        """
        INSERT INTO events (
            event_type,
            link_name,
            timestamp,
            user_agent,
            referrer,
            ip_address
        )

        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (event_type, link_name, timestamp, user_agent, referrer, ip_address),
    )

    connection.commit()

    connection.close()

    return jsonify({"success": True})


# ========================================
# ANALYTICS SUMMARY
# PROTECTED
# ========================================


@app.route("/api/analytics", methods=["GET"])
@admin_required
def analytics():

    connection = get_db()

    total_events = connection.execute("""
        SELECT COUNT(*) AS count
        FROM events
        """).fetchone()["count"]

    total_clicks = connection.execute("""
        SELECT COUNT(*) AS count
        FROM events
        WHERE event_type = 'click'
        """).fetchone()["count"]

    link_clicks = connection.execute("""
        SELECT
            link_name,
            COUNT(*) AS clicks

        FROM events

        WHERE event_type = 'click'

        GROUP BY link_name

        ORDER BY clicks DESC
        """).fetchall()

    connection.close()

    return jsonify(
        {
            "total_events": total_events,
            "total_clicks": total_clicks,
            "link_clicks": [dict(row) for row in link_clicks],
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

    events = connection.execute("""
        SELECT

            id,

            event_type,

            link_name,

            timestamp,

            user_agent,

            referrer

        FROM events

        ORDER BY id DESC

        LIMIT 20
        """).fetchall()

    connection.close()

    return jsonify({"events": [dict(event) for event in events]})


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

    return jsonify({"events": [dict(event) for event in events]})


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

    return jsonify({"database": DATABASE, "total_records": total_records})


# ========================================
# START SERVER
# ========================================

if __name__ == "__main__":

    initialize_database()

    print()

    print("========================================")

    print(" Manas Link Hub Analytics")

    print("========================================")

    print(f" Database: {DATABASE}")

    email_status = (
        "configured" if ADMIN_EMAIL and EMAIL_APP_PASSWORD else "NOT configured"
    )

    print(f" Email OTP: {email_status}")

    print(" Server: http://127.0.0.1:5000")

    print("========================================")

    print()

    app.run(host="127.0.0.1", port=5000, debug=True)
