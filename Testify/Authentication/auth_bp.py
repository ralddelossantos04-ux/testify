from functools import wraps
from flask import flash
from flask import Blueprint, render_template, request, session, url_for, redirect, jsonify
from Testify.__init__ import db_config
import mysql.connector
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

# ── Email credentials ────────────────────────────────────────────────────────
SENDER_EMAIL = "kyutipakyu69@gmail.com"
APP_PASSWORD  = "eddg cmsb srmk oleg"

# ── OTP rules ────────────────────────────────────────────────────────────────
OTP_VALIDITY_MINUTES       = 5
OTP_RESEND_COOLDOWN_SECS   = 60
OTP_MAX_ATTEMPTS           = 5
OTP_MAX_REQUESTS_PER_10MIN = 3
RESET_SESSION_MINUTES      = 10

auth = Blueprint('auth', __name__, template_folder='templates',
                  static_folder='static', static_url_path='/auth/static')

# ─────────────────────────────────────────────────────────────────────────────
# Cache-control
# ─────────────────────────────────────────────────────────────────────────────
@auth.after_request
def add_no_cache_headers(response):
    """Prevent browser from caching auth pages so back-button won't show them."""
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def is_logged_in():
    return session.get('logged_in', False)


def _redirect_to_own_dashboard(role):
    """Redirect a user to the dashboard that matches their actual role."""
    if role == 'ADMIN':
        return redirect(url_for('admin.dashboard'))
    elif role == 'TEACHER':
        return redirect(url_for('teacher.dashboard'))
    else:
        return redirect(url_for('student.display_student'))


def role_required(required_role):
    """Decorator that ensures the user is logged in AND has the correct role.

    Usage:
        @student.route('/student_dashboard')
        @role_required('STUDENT')
        def display_student():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 1. Not logged in → send to login page
            if not is_logged_in():
                flash("Please log in first.", "error")
                return redirect(url_for('auth.login', role=required_role))

            # 2. Logged in but wrong role → send to their own dashboard
            user_role = session.get('role', '').upper()
            if user_role != required_role.upper():
                flash("Access denied. You do not have permission to view that page.", "error")
                return _redirect_to_own_dashboard(user_role)

            # 3. All good
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def _get_db():
    return mysql.connector.connect(**db_config)


def _send_otp_email(to_email: str, otp: str):
    """Send a 4-digit OTP via Gmail SMTP (TLS)."""
    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'Your Testify Password Reset Code'
    msg['From']    = SENDER_EMAIL
    msg['To']      = to_email

    html_body = f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:480px;margin:auto;
                border:1px solid #e2e6ed;border-radius:12px;overflow:hidden;">
      <div style="background:#12161c;padding:28px 32px;">
        <span style="font-size:20px;font-weight:700;color:#fff;">Testify</span>
      </div>
      <div style="padding:32px;">
        <h2 style="margin:0 0 12px;font-size:22px;color:#12161c;">Password Reset Code</h2>
        <p style="color:#5a6478;line-height:1.6;margin:0 0 24px;">
          Use the verification code below to reset your password.
          This code expires in <strong>{OTP_VALIDITY_MINUTES} minutes</strong>.
        </p>
        <div style="text-align:center;margin:0 0 24px;">
          <span style="display:inline-block;background:#e8f7ea;color:#1e7a2b;
                       font-size:40px;font-weight:800;letter-spacing:12px;
                       padding:18px 28px;border-radius:10px;">{otp}</span>
        </div>
        <p style="font-size:13px;color:#8e97a8;margin:0;">
          If you didn't request this, ignore this email — your account is safe.
        </p>
      </div>
    </div>
    """
    msg.attach(MIMEText(html_body, 'html'))

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.ehlo()
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())

# ─────────────────────────────────────────────────────────────────────────────
# Standard auth routes
# ─────────────────────────────────────────────────────────────────────────────
@auth.route('/index')
def index():
    if is_logged_in():
        return _redirect_to_own_dashboard(session.get('role', '').upper())
    return render_template('index.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():

    role = request.args.get("role")
    if role:
        session['login_role'] = role.upper()
    role = session.get('login_role', 'STUDENT')

    if is_logged_in():
        return _redirect_to_own_dashboard(session.get('role', '').upper())

    if request.method == 'POST':

        username_input = request.form.get('username_input')
        password_input = request.form.get('password_input')

        connection = _get_db()
        cursor = connection.cursor(dictionary=True)

        query = """
        SELECT user_id, username, password, role
        FROM users
        WHERE username = %s
        """

        cursor.execute(query, (username_input,))
        user = cursor.fetchone()

        cursor.close()
        connection.close()

        # Support both plaintext (legacy) and werkzeug-hashed passwords
        stored_pw = user['password'] if user else ''
        pw_ok = (
            stored_pw == password_input or           # legacy plaintext
            (stored_pw.startswith('pbkdf2:') and check_password_hash(stored_pw, password_input))
        )
        if user and pw_ok and user['role'].upper() == role:

            session['logged_in'] = True
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['role'] = user['role']

            if user['role'].upper() == 'ADMIN':
                return redirect(url_for('admin.dashboard'))
            elif user['role'].upper() == 'TEACHER':
                return redirect(url_for('teacher.dashboard'))
            else:
                return redirect(url_for('student.display_student'))

        else:
            flash("Invalid username or password.", "error")
            return redirect(url_for('auth.login', role=role))

    return render_template('login.html', role=role)


@auth.route('/logingout', methods=['POST', 'GET'])
def logout():
    role = session.get('role', 'STUDENT').upper()
    session.clear()
    return redirect(url_for('auth.login', role=role))


@auth.route("/select-role")
def select_role():
    if is_logged_in():
        return _redirect_to_own_dashboard(session.get('role', '').upper())
    return render_template("index.html")


@auth.route('/recover-password')
def recover_password():
    return render_template('recover_password.html')

# ─────────────────────────────────────────────────────────────────────────────
# Password-recovery API endpoints
# ─────────────────────────────────────────────────────────────────────────────

@auth.route('/api/send-otp', methods=['POST'])
def api_send_otp():
    """
    Step 1 – validate email exists in DB, generate & email OTP.
    Body JSON: { "email": "..." }
    """
    data  = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()

    if not email:
        return jsonify(ok=False, error='Email is required.'), 400

    conn   = _get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT user_id, email FROM users WHERE LOWER(email) = %s AND status = 'active' AND role = 'student'",
        (email,)
    )
    user = cursor.fetchone()

    if not user:
        cursor.close(); conn.close()
        return jsonify(ok=False, error='No active student account found with that email address.'), 404

    user_id = user['user_id']
    now     = datetime.now()

    # ── Rate-limit: max 3 OTP requests per 10 minutes ───────────────────────
    cursor.execute(
        "SELECT reset_otp_requested_at FROM users WHERE user_id = %s",
        (user_id,)
    )
    row = cursor.fetchone()
    last_request = row['reset_otp_requested_at'] if row else None

    if last_request and isinstance(last_request, datetime):
        window_start = now - timedelta(minutes=10)
        if last_request > window_start:
            # Count how many times we've issued within the window
            cursor.execute(
                """SELECT reset_otp_attempts FROM users WHERE user_id = %s""",
                (user_id,)
            )
            att_row = cursor.fetchone()
            # We use reset_otp_attempts to track request count within window too
            # But to keep it simple, check cooldown first (60 s)
            elapsed = (now - last_request).total_seconds()
            if elapsed < OTP_RESEND_COOLDOWN_SECS:
                remaining = int(OTP_RESEND_COOLDOWN_SECS - elapsed)
                cursor.close(); conn.close()
                return jsonify(
                    ok=False,
                    error=f'Please wait {remaining} seconds before requesting another code.',
                    cooldown=remaining
                ), 429

    # ── Generate OTP ─────────────────────────────────────────────────────────
    otp    = ''.join(random.choices(string.digits, k=4))
    expiry = now + timedelta(minutes=OTP_VALIDITY_MINUTES)

    cursor.execute(
        """UPDATE users
           SET reset_otp = %s,
               reset_otp_expiry = %s,
               reset_otp_attempts = 0,
               reset_otp_requested_at = %s,
               reset_otp_used = 0
           WHERE user_id = %s""",
        (otp, expiry, now, user_id)
    )
    conn.commit()
    cursor.close(); conn.close()

    # ── Send email ───────────────────────────────────────────────────────────
    try:
        _send_otp_email(email, otp)
    except Exception as e:
        return jsonify(ok=False, error=f'Failed to send email: {str(e)}'), 500

    # Store email in session for subsequent steps
    session['recovery_email'] = email
    session['recovery_started_at'] = now.isoformat()

    return jsonify(ok=True, message='OTP sent successfully.')


@auth.route('/api/verify-otp', methods=['POST'])
def api_verify_otp():
    """
    Step 2 – verify the OTP the user typed.
    Body JSON: { "email": "...", "otp": "1234" }
    """
    data  = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    otp   = (data.get('otp') or '').strip()

    if not email or not otp:
        return jsonify(ok=False, error='Email and OTP are required.'), 400

    # Guard: recovery must have been initiated in this session
    if session.get('recovery_email') != email:
        return jsonify(ok=False, error='Session mismatch. Please start over.'), 403

    conn   = _get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """SELECT user_id, reset_otp, reset_otp_expiry,
                  reset_otp_attempts, reset_otp_used
           FROM users
           WHERE LOWER(email) = %s AND status = 'active'""",
        (email,)
    )
    user = cursor.fetchone()

    if not user:
        cursor.close(); conn.close()
        return jsonify(ok=False, error='Account not found.'), 404

    user_id  = user['user_id']
    attempts = user['reset_otp_attempts'] or 0

    # ── Already used ─────────────────────────────────────────────────────────
    if user['reset_otp_used']:
        cursor.close(); conn.close()
        return jsonify(ok=False, error='This code has already been used. Request a new one.'), 400

    # ── Too many attempts ─────────────────────────────────────────────────────
    if attempts >= OTP_MAX_ATTEMPTS:
        cursor.close(); conn.close()
        return jsonify(ok=False, error='Too many failed attempts. Please request a new code.'), 429

    # ── Expired ───────────────────────────────────────────────────────────────
    expiry = user['reset_otp_expiry']
    if not expiry or datetime.now() > expiry:
        cursor.close(); conn.close()
        return jsonify(ok=False, error='Your code has expired. Please request a new one.'), 400

    # ── Wrong OTP ─────────────────────────────────────────────────────────────
    if otp != user['reset_otp']:
        new_attempts = attempts + 1
        cursor.execute(
            "UPDATE users SET reset_otp_attempts = %s WHERE user_id = %s",
            (new_attempts, user_id)
        )
        conn.commit()
        remaining = OTP_MAX_ATTEMPTS - new_attempts
        cursor.close(); conn.close()
        msg = f'Incorrect code. {remaining} attempt(s) remaining.' if remaining > 0 \
              else 'No attempts remaining. Please request a new code.'
        return jsonify(ok=False, error=msg, attempts_left=remaining), 400

    # ── Correct OTP ───────────────────────────────────────────────────────────
    cursor.execute(
        "UPDATE users SET reset_otp_used = 1 WHERE user_id = %s",
        (user_id,)
    )
    conn.commit()
    cursor.close(); conn.close()

    # Mark OTP verified in session so reset-password step is unlocked
    session['otp_verified'] = True
    session['recovery_verified_at'] = datetime.now().isoformat()

    return jsonify(ok=True, message='OTP verified.')


@auth.route('/api/resend-otp', methods=['POST'])
def api_resend_otp():
    """
    Resend (regenerate) the OTP for the current recovery email.
    Body JSON: { "email": "..." }
    Delegates to the same logic as send-otp after cooldown check.
    """
    return api_send_otp()


@auth.route('/api/reset-password', methods=['POST'])
def api_reset_password():
    """
    Step 3 – set the new password (bcrypt-hashed via werkzeug).
    Body JSON: { "email": "...", "password": "..." }
    """
    data     = request.get_json(silent=True) or {}
    email    = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or not password:
        return jsonify(ok=False, error='Email and password are required.'), 400

    # Must have completed OTP step in this session
    if session.get('recovery_email') != email or not session.get('otp_verified'):
        return jsonify(ok=False, error='Unauthorized. Please complete verification first.'), 403

    # 10-minute session window for password reset
    verified_at_str = session.get('recovery_verified_at')
    if verified_at_str:
        verified_at = datetime.fromisoformat(verified_at_str)
        if datetime.now() > verified_at + timedelta(minutes=RESET_SESSION_MINUTES):
            session.pop('otp_verified', None)
            return jsonify(ok=False, error='Reset session expired. Please start over.'), 403

    if len(password) < 8:
        return jsonify(ok=False, error='Password must be at least 8 characters.'), 400

    hashed = generate_password_hash(password)

    conn   = _get_db()
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE users
           SET password = %s,
               reset_otp = NULL,
               reset_otp_expiry = NULL,
               reset_otp_attempts = 0,
               reset_otp_used = 1
           WHERE LOWER(email) = %s AND status = 'active'""",
        (hashed, email)
    )
    conn.commit()
    affected = cursor.rowcount
    cursor.close(); conn.close()

    if affected == 0:
        return jsonify(ok=False, error='Account not found or already inactive.'), 404

    # Clear recovery session keys
    for key in ('recovery_email', 'recovery_started_at', 'otp_verified', 'recovery_verified_at'):
        session.pop(key, None)

    return jsonify(ok=True, message='Password updated successfully.')
