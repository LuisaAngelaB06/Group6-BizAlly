from flask import Blueprint, request, jsonify, redirect, session, g
from Backend.database import get_connection
from werkzeug.security import generate_password_hash, check_password_hash
from psycopg2.extras import RealDictCursor
from authlib.integrations.flask_client import OAuth
from authlib.integrations.base_client.errors import MismatchingStateError
from dotenv import load_dotenv
import re
import os
import json
import base64
import sib_api_v3_sdk
import random
import requests
import secrets
import string
from html import escape
from Backend.routes.utils import log_system_event

from sib_api_v3_sdk.rest import ApiException
from datetime import datetime, timedelta
from Backend.routes.rbac import role_required
from Backend.routes.rbac import get_current_user, is_admin, is_technician, role_required





def _client_ip():
    """Get the real client IP locally and behind Render/proxies."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.headers.get("X-Real-IP") or request.remote_addr or "Unknown IP"


def _device_from_user_agent(user_agent):
    """Turn the long User-Agent string into a readable device label."""
    ua = (user_agent or "").lower()

    browser = "Browser"
    if "edg/" in ua:
        browser = "Microsoft Edge"
    elif "chrome/" in ua and "chromium" not in ua:
        browser = "Chrome"
    elif "firefox/" in ua:
        browser = "Firefox"
    elif "safari/" in ua and "chrome/" not in ua:
        browser = "Safari"

    os_name = "Unknown Device"
    if "windows" in ua:
        os_name = "Windows"
    elif "mac os" in ua or "macintosh" in ua:
        os_name = "macOS"
    elif "android" in ua:
        os_name = "Android"
    elif "iphone" in ua or "ipad" in ua:
        os_name = "iOS"
    elif "linux" in ua:
        os_name = "Linux"

    return f"{browser} on {os_name}"


def _location_from_ip(ip_address):
    """Return approximate city/region/country from a public IP address."""
    if not ip_address or ip_address in {"127.0.0.1", "localhost", "::1", "Unknown IP"}:
        return "Localhost"

    # Skip local networks
    if ip_address.startswith(("10.", "192.168.", "172.")):
        return "Local Network"

    # 🌟 FIXED: Use IPInfo as Primary for accurate City/Region tracking
    try:
        r = requests.get(f"https://ipinfo.io/{ip_address}/json", timeout=3)
        data = r.json()
        if "city" in data and "country" in data:
            parts = [p for p in [data.get("city"), data.get("region"), data.get("country")] if p]
            if parts:
                return ", ".join(parts)
    except Exception:
        pass

    # Fallback to old API if primary fails
    try:
        response = requests.get(f"http://ip-api.com/json/{ip_address}?fields=status,country,regionName,city", timeout=3)
        data = response.json()
        if data.get("status") == "success":
            parts = [data.get("city"), data.get("regionName"), data.get("country")]
            location = ", ".join([part for part in parts if part])
            return location or "Unknown Location"
    except Exception:
        pass

    return "Unknown Location"


def _send_lockout_email(email, name, location):
    """Silently alert the user that their account was locked due to brute force."""
    try:
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = os.getenv("BREVO_API_KEY")
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            sender={"name": "AlliTrack Security", "email": "noreply.allitrack@gmail.com"},
            to=[{"email": email, "name": name}],
            subject="Security Alert: Account Temporarily Locked",
            html_content=f"""
                <div style="font-family: sans-serif; padding: 20px; border: 1px solid #eee;">
                    <h2 style="color: #ef4444; margin-top: 0;">Security Alert</h2>
                    <p>Hello {name},</p>
                    <p>A failed login attempt just locked your AlliTrack account.</p>
                    <p><strong>Approximate Location:</strong> {location}</p>
                    <p>If this was you, please wait 15 minutes to try again.</p>
                    <p>If this was not you, someone is trying to guess your password. We recommend changing your password once you regain access.</p>
                </div>
            """
        )
        api_instance.send_transac_email(send_smtp_email)
    except Exception as e:
        print(f"Lockout Email Error: {e}")


def _record_login_attempt(cursor, user_id=None, email=None, status="success"):
    """Save a login attempt to login_history and prevent accidental duplicates."""
    try:
        ip_address = _client_ip()
        device = _device_from_user_agent(request.headers.get("User-Agent", ""))
        location = _location_from_ip(ip_address)
        normalized_email = (email or "").strip().lower()

        # Prevent duplicate rows when the frontend/browser sends the same login request twice.
        # Applies to BOTH successful and failed login attempts.
        if normalized_email:
            cursor.execute(
                """
                SELECT login_id
                FROM login_history
                WHERE LOWER(email) = LOWER(%s)
                  AND ip_address = %s
                  AND device = %s
                  AND status = %s
                  AND login_time >= timezone('Asia/Manila', now()) - INTERVAL '5 seconds'
                LIMIT 1
                """,
                (normalized_email, ip_address, device, status),
            )

            if cursor.fetchone():
                print("Duplicate login history skipped")
                return

        cursor.execute(
            """
            INSERT INTO login_history
                (user_id, email, ip_address, device, location, status, login_time)
            VALUES (%s, %s, %s, %s, %s, %s, timezone('Asia/Manila', now()))
            """,
            (
                user_id,
                normalized_email or email,
                ip_address,
                device,
                location,
                status,
            ),
        )

    except Exception as history_error:
        print(f"Login history insert failed: {history_error}")
        raise


def _generate_temporary_password(length=14):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(char.islower() for char in password)
            and any(char.isupper() for char in password)
            and any(char.isdigit() for char in password)
            and any(char in "!@#$%^&*" for char in password)
        ):
            return password


STAFF_ROLES = {"admin", "technician"}
IDENTITY_TYPE_KEYS = {"identity_type", "identityType", "profile_persona", "persona"}


def _strip_staff_identity_type(data):
    """Admin and Technician users intentionally do not store Identity Type."""
    return {key: value for key, value in (data or {}).items() if key not in IDENTITY_TYPE_KEYS}


def _send_staff_temporary_password_email(email, name, temporary_password, action="created"):
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = os.getenv("BREVO_API_KEY")
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    display_name = (name or email or "there").strip()
    safe_display_name = escape(display_name)
    safe_temporary_password = escape(temporary_password)
    action_text = "created" if action == "created" else "reset"
    subject = "AlliTrack temporary password"

    text_content = "\n".join([
        f"Hello {display_name},",
        "",
        f"Your AlliTrack admin/technician account password was {action_text}.",
        "",
        f"Temporary password: {temporary_password}",
        "",
        "Please sign in and change this password immediately.",
        "",
        "If you did not expect this email, contact your system administrator.",
    ])

    html_content = f"""
        <div style="font-family: Arial, Helvetica, sans-serif; padding: 24px; color: #172033;">
            <h2 style="margin: 0 0 12px; color: #1d4ed8;">AlliTrack temporary password</h2>
            <p>Hello {safe_display_name},</p>
            <p>Your AlliTrack admin/technician account password was {action_text}.</p>
            <div style="margin: 18px 0; padding: 16px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px;">
                <div style="font-size: 13px; color: #64748b; margin-bottom: 6px;">Temporary password</div>
                <div style="font-size: 20px; font-weight: 800; letter-spacing: 0.04em;">{safe_temporary_password}</div>
            </div>
            <p>Please sign in and change this password immediately.</p>
            <p style="font-size: 13px; color: #64748b;">If you did not expect this email, contact your system administrator.</p>
        </div>
    """

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        sender={"name": "AlliTrack", "email": "noreply.allitrack@gmail.com"},
        to=[{"email": email, "name": display_name}],
        subject=subject,
        text_content=text_content,
        html_content=html_content,
    )

    api_instance.send_transac_email(send_smtp_email)


load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

auth_bp = Blueprint("auth", __name__)
oauth = OAuth()

# ==========================================
# 1. LOGIN (FINAL MERGED + SOFT LOCK + SECONDS)
# ==========================================
# ==========================================
# 1. LOGIN (FINAL MERGED + SOFT LOCK + SECONDS)
# ==========================================
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    conn = get_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        query = 'SELECT * FROM "system_user" WHERE LOWER(Email) = LOWER(%s)'
        cursor.execute(query, (email,))
        user = cursor.fetchone()

        if user:
            # 🌟 1. CHECK LOCKOUT FIRST (Calculates Exact Seconds)
            cursor.execute('SELECT EXTRACT(EPOCH FROM (locked_until - NOW())) AS remaining_seconds FROM "system_user" WHERE user_id = %s AND locked_until > NOW()', (user["user_id"],))
            lock_data = cursor.fetchone()
            if lock_data and lock_data["remaining_seconds"] is not None and lock_data["remaining_seconds"] > 0:
                return jsonify({
                    "status": "error", 
                    "message": "Account locked.", 
                    "remaining_seconds": int(lock_data["remaining_seconds"])
                }), 403

            # 🌟 2. PASSWORD CHECK
            if check_password_hash(user["password_hash"], password):
                
                # --- MAINTENANCE BOUNCER ---
                user_role = (user["user_type"] or "client").lower()
                if "admin" not in user_role:
                    try:
                        cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'maintenance_mode'")
                        maintenance_setting = cursor.fetchone()
                        if maintenance_setting and maintenance_setting["setting_value"] == "true":
                            return jsonify({"status": "error", "message": "The system is currently undergoing scheduled maintenance. Please try again later."}), 503 
                    except Exception:
                        pass 

                # --- 2FA ENFORCEMENT ---
                if user_role == "admin":
                    try:
                        u_id = user["user_id"]
                        cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = %s", (f"2fa_user_{u_id}",))
                        tfa_setting = cursor.fetchone()
                        is_tfa_enabled = True if (tfa_setting and tfa_setting["setting_value"] == "true") else False
                    except Exception:
                        is_tfa_enabled = False 
                    
                    if is_tfa_enabled:
                        otp = str(random.randint(100000, 999999))
                        cursor.execute("DELETE FROM otp_verifications WHERE email = %s", (email,))
                        cursor.execute("INSERT INTO otp_verifications (email, otp_code, expires_at) VALUES (%s, %s, NOW() + INTERVAL '2 minutes')", (email, otp))
                        conn.commit()
                        
                        try:
                            configuration = sib_api_v3_sdk.Configuration()
                            configuration.api_key['api-key'] = os.getenv("BREVO_API_KEY")
                            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
                            
                            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                                sender={"name": "AlliTrack Security", "email": "noreply.allitrack@gmail.com"},
                                to=[{"email": email}],
                                subject="AlliTrack Admin 2FA Code",
                                html_content=f"""
                                    <div style="font-family: sans-serif; padding: 20px; border: 1px solid #eee;">
                                        <h2>Admin Authentication</h2>
                                        <p>Your 2FA login code for AlliTrack is:</p>
                                        <h1 style="color: #4f46e5;">{otp}</h1>
                                        <p>This code expires in 2 minutes.</p>
                                    </div>
                                """
                            )
                            api_instance.send_transac_email(send_smtp_email)
                        except Exception as e:
                            print(f"2FA Email Error: {e}")
                            
                        return jsonify({"status": "2fa_required", "email": email}), 200

                # 🌟 SUCCESSFUL LOGIN: CLEAR STRIKES
                cursor.execute('UPDATE "system_user" SET failed_attempts = 0, locked_until = NULL WHERE user_id = %s', (user["user_id"],))

                # --- SAFE USER CREATION ---
                full_name = f"{user['first_name']} {user['last_name'] or ''}".strip()
                safe_user = {
                    "user_id": user["user_id"],
                    "Username": user["username"],
                    "Name": full_name,
                    "Email": user["email"],
                    "User_Type": user["user_type"],
                    "is_profile_complete": user.get("is_profile_complete", False),
                    "profile_pic_url": user.get("profile_pic_url"),
                    "Technician_ID": None
                }

                if user["user_type"] in ["admin", "technician"]:
                    cursor.execute("SELECT Technician_ID FROM technician WHERE user_id = %s", (user["user_id"],))
                    tech = cursor.fetchone()
                    if tech:
                        safe_user["Technician_ID"] = tech["technician_id"]

                _record_login_attempt(cursor, user_id=user["user_id"], email=user["email"], status="success")
                cursor.execute('UPDATE "system_user" SET last_login = CURRENT_TIMESTAMP WHERE user_id = %s', (user["user_id"],))
                conn.commit()

                log_system_event(
                    user_identifier=str(user["user_id"]), 
                    category="Authentication", 
                    action="User Login", 
                    log_level="INFO", 
                    description="Successfully authenticated and logged into the system."
                )
                return jsonify({"status": "success", "user": safe_user}), 200
                
            else:
                # 🌟 3. WRONG PASSWORD (4TH STRIKE TRIGGER)
                cursor.execute('UPDATE "system_user" SET failed_attempts = COALESCE(failed_attempts, 0) + 1 WHERE user_id = %s RETURNING failed_attempts', (user["user_id"],))
                attempts = cursor.fetchone()["failed_attempts"]
                
                if attempts >= 4:
                    # SIMPLIFIED: Just do the lock, no complex RETURNING math needed
                    cursor.execute('UPDATE "system_user" SET failed_attempts = 0, locked_until = NOW() + INTERVAL \'15 minutes\' WHERE user_id = %s', (user["user_id"],))
                    conn.commit()
                    
                    ip_address = _client_ip()
                    location = _location_from_ip(ip_address)
                    _send_lockout_email(user["email"], user.get("first_name", "User"), location)
                    
                    log_system_event(
                        user_identifier=str(user["user_id"]), 
                        category="Security", 
                        action="Account Locked", 
                        log_level="CRITICAL", 
                        description=f"Account locked for 15 minutes due to 4 failed password attempts."
                    )
                    
                    # HARDCODED 900 SECONDS = 100% RELIABILITY
                    return jsonify({
                        "status": "error", 
                        "message": "Account locked.", 
                        "remaining_seconds": 900 
                    }), 403

        # (If user doesn't exist or under 4 strikes)
        _record_login_attempt(cursor, email=email, status="failed")
        conn.commit()

        log_system_event(
            user_identifier=email or "Unknown", 
            category="Authentication",
            action="Failed Login", 
            log_level="WARNING", 
            description="Attempted login with invalid credentials.", 
            status="Failed"
        )
        return jsonify({"status": "error", "message": "Invalid email or password"}), 401

    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"status": "error", "message": "Database error"}), 500
    finally:
        cursor.close()
        conn.close()

# ==========================================
# LOGIN HISTORY
# ==========================================
@auth_bp.route("/login-history", methods=["GET"])
def get_login_history():
    user_id = request.args.get("user_id")
    email = request.args.get("email")

    if not user_id and not email:
        return jsonify({"status": "success", "history": []}), 200

    conn = get_connection()
    if not conn:
        return jsonify({"status": "error", "history": []}), 500

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute(
            """
            SELECT
                login_id AS id,
                user_id,
                email,
                ip_address,
                device,
                location,
                status,
                TO_CHAR(login_time, 'YYYY-MM-DD HH24:MI:SS') AS login_time
            FROM login_history
            WHERE
                (%s IS NOT NULL AND user_id = %s)
                OR
                (%s IS NOT NULL AND LOWER(email) = LOWER(%s))
            ORDER BY login_time DESC
            LIMIT 20
            """,
            (user_id, user_id, email, email),
        )

        return jsonify({
            "status": "success",
            "history": cursor.fetchall()
        }), 200

    except Exception as e:
        print("Login history fetch error:", e)
        return jsonify({"status": "error", "history": []}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================
# 2. SIGNUP (FINAL)
# ==========================================
@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.json
    first_name = data.get("firstName")
    last_name = data.get("lastName")
    email = data.get("email")
    password = data.get("password")

    username = email.split('@')[0]
    hashed_password = generate_password_hash(password)

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute('SELECT * FROM "system_user" WHERE LOWER(Email) = LOWER(%s)', (email,))
        if cursor.fetchone():
            return jsonify({"status": "error", "message": "Email already exists"}), 400

        cursor.execute(
            """
            INSERT INTO "system_user"
            (Username, first_name, last_name, Email, password_Hash, User_Type, Created_At)
            VALUES (%s, %s, %s, %s, %s, 'client', CURRENT_TIMESTAMP)
            RETURNING user_id, username, first_name, last_name, email, user_type, is_profile_complete, profile_pic_url
            """,
            (username, first_name, last_name, email, hashed_password)
        )
        new_user = cursor.fetchone()
        conn.commit()

        # 🌟 NEW: Audit Log for Standard Registration
        log_system_event(
            user_identifier=str(new_user["user_id"]),
            category="User Management",
            action="User Registered",
            log_level="INFO",
            description=f"New client account registered for {email}."
        )

        full_name = f"{new_user['first_name']} {new_user['last_name'] or ''}".strip()

        safe_user = {
            "user_id": new_user["user_id"],
            "Username": new_user["username"],
            "Name": full_name,
            "Email": new_user["email"],
            "User_Type": new_user["user_type"],
            "is_profile_complete": new_user.get("is_profile_complete", False),
            "profile_pic_url": new_user.get("profile_pic_url"),
            "Technician_ID": None
        }

        return jsonify({"status": "success", "user": safe_user}), 201

    except Exception as e:
        print(f"Signup error: {e}")
        return jsonify({"status": "error", "message": "Database error"}), 500

    finally:
        cursor.close()
        conn.close()

# ==========================================
# 3. ADMIN RESET PASSWORD
# ==========================================
@auth_bp.route("/admin/verify-password", methods=["POST"])
@role_required("admin")
def admin_verify_password():
    data = request.json or {}
    password = data.get("password")
    current_user = getattr(g, "current_user", None)

    if not password:
        return jsonify({"status": "error", "message": "Password is required"}), 400

    if not current_user:
        return jsonify({"status": "error", "message": "Authentication required"}), 401

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute(
            'SELECT password_hash FROM "system_user" WHERE user_id = %s',
            (current_user["user_id"],)
        )
        user = cursor.fetchone()

        if not user or not check_password_hash(user.get("password_hash"), password):
            return jsonify({"status": "error", "message": "Invalid password", "valid": False}), 401

        return jsonify({"status": "success", "valid": True}), 200

    except Exception as e:
        print(f"Admin verify password error: {e}")
        return jsonify({"status": "error", "message": "Database error"}), 500

    finally:
        cursor.close()
        conn.close()


@auth_bp.route("/admin/reset-password", methods=["POST"])
@role_required("admin")
def admin_reset_password():
    data = request.json
    target_user_id = data.get("target_user_id")

    if not target_user_id:
        return jsonify({"status": "error", "message": "Missing User ID"}), 400

    temp_password = _generate_temporary_password()
    hashed = generate_password_hash(temp_password)

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute(
            """
            UPDATE "system_user"
            SET password_Hash = %s
            WHERE user_id = %s
            RETURNING email, first_name, last_name
            """,
            (hashed, target_user_id)
        )
        target_user = cursor.fetchone()

        if not target_user:
            conn.rollback()
            return jsonify({"status": "error", "message": "User not found"}), 404

        target_name = f"{target_user.get('first_name') or ''} {target_user.get('last_name') or ''}".strip()
        _send_staff_temporary_password_email(
            target_user["email"],
            target_name,
            temp_password,
            action="reset",
        )
        conn.commit()

        return jsonify({
            "status": "success",
            "message": f"Temporary password was sent to {target_user['email']}.",
            "email_sent": True
        }), 200

    except ApiException as e:
        conn.rollback()
        print(f"Reset password email error: {e}")
        return jsonify({"status": "error", "message": "Password was not reset because the email could not be sent."}), 500

    except Exception as e:
        conn.rollback()
        print(f"Reset error: {e}")
        return jsonify({"status": "error", "message": "Database error"}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================
# 4. CHANGE PASSWORD (STRICT)
# ==========================================
@auth_bp.route("/user/change-password", methods=["POST"])
def change_password():
    data = request.json
    user_id = data.get("user_id")
    old_password = data.get("old_password")
    new_password = data.get("new_password")

    # 1. Presence Validation
    if not all([user_id, old_password, new_password]):
        return jsonify({"status": "error", "message": "All fields are required"}), 400

    # 2. Strong Validation (Regex matching your frontend criteria)
    if (len(new_password) < 8 or
        not re.search(r"[A-Z]", new_password) or
        not re.search(r"[a-z]", new_password) or
        not re.search(r"\d", new_password) or
        not re.search(r"[!@#$%^&*(),.?\":{}|<>]", new_password)):
        return jsonify({"status": "error", "message": "Password does not meet strength requirements"}), 400

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 1. Fetch using lowercase column name
        cursor.execute('SELECT password_hash FROM "system_user" WHERE user_id = %s', (user_id,))
        user = cursor.fetchone()

        # 2. Check the dictionary safely
        stored_hash = user.get("password_hash") if user else None

        if not user or not stored_hash or not check_password_hash(stored_hash, old_password):
            return jsonify({"status": "error", "message": "Incorrect current password"}), 401

        # 3. Update using lowercase column name (No double quotes needed for the column)
        hashed = generate_password_hash(new_password)
        cursor.execute(
            'UPDATE "system_user" SET password_hash = %s WHERE user_id = %s',
            (hashed, user_id)
        )
        conn.commit()
        
        # 🌟 LOG IT
        from Backend.routes.utils import log_system_event
        log_system_event(
            user_identifier=str(user_id),
            category="User Management",
            action="Password Changed",
            log_level="INFO",
            description="User successfully changed their password."
        )
        
        return jsonify({"status": "success", "message": "Password updated successfully"}), 200

    except Exception as e:
        print(f"Change Password Error: {e}")
        return jsonify({"status": "error", "message": "A database error occurred"}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================
# 5. GET USERS (FORMATTED)
# ==========================================
@auth_bp.route("/admin/users", methods=["GET"])
@role_required("admin")
def get_all_staff():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute('''
        SELECT su.user_id, su.first_name, su.last_name, su.email, su.user_type,
               su.account_status, t.technician_id
        FROM "system_user" AS su
        LEFT JOIN "technician" AS t ON t.user_id = su.user_id
        WHERE LOWER(su.user_type) IN ('admin', 'technician')
        ORDER BY su.user_id ASC
        ''')
        users = cursor.fetchall()

        formatted = []
        for u in users:
            formatted.append({
                "user_id": u["user_id"],
                "technician_id": u["technician_id"],
                "first_name": u["first_name"] or "",
                "last_name": u["last_name"] or "",
                "Name": f"{u['first_name']} {u['last_name'] or ''}".strip(),
                "Email": u["email"],
                "User_Type": u["user_type"],
                "Account_Status": u["account_status"]
            })

        return jsonify(formatted), 200

    except Exception as e:
        print(f"Fetch error: {e}")
        return jsonify([]), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================
# 6. DELETE USERS
# ==========================================
@auth_bp.route("/admin/delete-users", methods=["POST"])
@role_required("admin")
def admin_delete_users():
    data = request.json
    user_ids = data.get("user_ids", [])

    if not user_ids:
        return jsonify({"status": "error", "message": "No users selected"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        for uid in user_ids:
            cursor.execute('DELETE FROM "system_user" WHERE user_id = %s', (uid,))
        conn.commit()

        # 🌟 LOG IT: Record the permanent deletion of accounts
        current_user = getattr(g, "current_user", None) or get_current_user()
        admin_id = current_user.get("user_id") if current_user else "System"
        from Backend.routes.utils import log_system_event

        for uid in user_ids:
            log_system_event(
                user_identifier=str(admin_id),
                category="User Management",
                action="Account Deleted",
                log_level="CRITICAL",
                description=f"Administrator permanently deleted user account ID: {uid}."
            )

        return jsonify({"status": "success", "message": "Users deleted"}), 200

    except Exception as e:
        print(f"Delete error: {e}")
        return jsonify({"status": "error", "message": "Database error"}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================
# 7. ADMIN UPDATE USER
# ==========================================
@auth_bp.route("/admin/update-user", methods=["POST"])
@role_required("admin")
def admin_update_user():
    data = _strip_staff_identity_type(request.json or {})

    target_user_id = data.get("user_id")
    user_type = (data.get("user_type") or data.get("User_Type") or "").strip().lower()

    if not target_user_id:
        return jsonify({"status": "error", "message": "Missing User ID"}), 400

    if user_type and user_type not in ["admin", "technician"]:
        return jsonify({"status": "error", "message": "Invalid role"}), 400

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Identity Type is intentionally omitted for Admin and Technician users.
        # If a legacy frontend submits it, clear it without touching other fields.
        cursor.execute(
            'UPDATE "system_user" SET profile_persona = NULL WHERE user_id = %s AND LOWER(user_type) = ANY(%s)',
            (target_user_id, list(STAFF_ROLES))
        )

        if user_type:
            query = """
            UPDATE "system_user"
            SET first_name = %s,
                last_name = %s,
                Email = %s,
                Account_Status = %s,
                User_Type = %s
            WHERE user_id = %s
            RETURNING user_id, user_type
            """
            cursor.execute(query, (
                data.get("first_name"),
                data.get("last_name"),
                data.get("email"),
                data.get("status"),
                user_type,
                target_user_id
            ))
        else:
            query = """
            UPDATE "system_user"
            SET first_name = %s,
                last_name = %s,
                Email = %s,
                Account_Status = %s
            WHERE user_id = %s
            RETURNING user_id, user_type
            """
            cursor.execute(query, (
                data.get("first_name"),
                data.get("last_name"),
                data.get("email"),
                data.get("status"),
                target_user_id
            ))

        updated_user = cursor.fetchone()

        if not updated_user:
            conn.rollback()
            return jsonify({"status": "error", "message": "User not found"}), 404

        final_role = (updated_user.get("user_type") or user_type or "").lower()
        technician_id = None

        if final_role == "technician":
            cursor.execute(
                'SELECT technician_id FROM "technician" WHERE user_id = %s',
                (target_user_id,)
            )
            existing_tech = cursor.fetchone()

            if existing_tech:
                technician_id = existing_tech["technician_id"]
            else:
                cursor.execute(
                    'INSERT INTO "technician" (user_id) VALUES (%s) RETURNING technician_id',
                    (target_user_id,)
                )
                technician_id = cursor.fetchone()["technician_id"]

        conn.commit()
        
        # 🌟 LOG IT
        current_user = getattr(g, "current_user", None) or get_current_user()
        admin_id = current_user.get("user_id") if current_user else "System"
        from Backend.routes.utils import log_system_event
        log_system_event(
            user_identifier=str(admin_id),
            category="User Management",
            action="Staff Updated",
            log_level="WARNING",
            description=f"Administrator updated profile/status for User ID {target_user_id}."
        )

        return jsonify({
            "status": "success",
            "message": "User updated",
            "user_id": target_user_id,
            "user_type": final_role,
            "technician_id": technician_id
        }), 200

    except Exception as e:
        conn.rollback()
        print(f"Update user error: {e}")
        return jsonify({"status": "error", "message": "Database error"}), 500

    finally:
        cursor.close()
        conn.close()

# ==========================================
# 9. GOOGLE OAUTH
# ==========================================
def init_oauth(app):
    oauth.init_app(app)

    oauth.register(
        name="google",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={
            "scope": "openid email profile"
        }
    )

@auth_bp.route("/google/login")
def google_login():
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI")

    if not redirect_uri:
        redirect_uri = "https://group6-bizally.onrender.com/api/auth/google/callback"

    print("REDIRECT URI USED:", redirect_uri)

    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.route("/google/callback")
def google_callback():
    try:
        oauth.google.authorize_access_token()
        user_info = oauth.google.userinfo()

        email = user_info.get("email")
        name = user_info.get("name") or email.split("@")[0]

        if not email:
            return jsonify({
                "status": "error",
                "message": "Google email not found"
            }), 400

        name_parts = name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        username = email.split("@")[0]

        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            cursor.execute(
                'SELECT * FROM "system_user" WHERE LOWER(Email) = LOWER(%s)',
                (email,)
            )
            user = cursor.fetchone()

            if not user:
                fake_password = generate_password_hash("GOOGLE_AUTH_USER_NO_PASSWORD")

                cursor.execute(
                    """
                    INSERT INTO "system_user"
                    (Username, first_name, last_name, Email, Password_Hash, User_Type, Created_At)
                    VALUES (%s, %s, %s, %s, %s, 'client', CURRENT_TIMESTAMP)
                    RETURNING *
                    """,
                    (username, first_name, last_name, email, fake_password)
                )
                user = cursor.fetchone()
                conn.commit()

                # 🌟 NEW: Audit Log for Google Registration
                log_system_event(
                    user_identifier=str(user["user_id"]),
                    category="User Management",
                    action="User Registered",
                    log_level="INFO",
                    description=f"New account created via Google OAuth for {email}."
                )

            full_name = f"{user['first_name']} {user['last_name'] or ''}".strip()

            safe_user = {
                "user_id": user["user_id"],
                "Username": user["username"],
                "Name": full_name,
                "Email": user["email"],
                "User_Type": user["user_type"],
                "is_profile_complete": user.get("is_profile_complete", False),
                "profile_pic_url": user.get("profile_pic_url"),
                "Technician_ID": None,
                "provider": "google"
            }

            session["user"] = safe_user

            safe_user_json = json.dumps(safe_user)
            safe_user_b64 = base64.b64encode(
                safe_user_json.encode("utf-8")
            ).decode("utf-8")

            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
            </head>
            <body style="display:none;">
                <script>
                    try {{
                        const user = JSON.parse(atob("{safe_user_b64}"));

                        localStorage.setItem("userData", JSON.stringify(user));
                        localStorage.setItem("authToken", "google_login");

                const role = (
                    user.User_Type ||
                    user.user_type ||
                    user.role ||
                    "client"
                ).toLowerCase();

                window.location.replace(
                    role === "technician"
                    ? "/technician/all-tickets.html"
                    : role === "admin"
                    ? "/admin/dashboard"
                    : "/user/dashboard"
            );
            }} catch (error) {{
               console.error(error);
            }}
        </script>
    </body>
    </html>
    """

        finally:
            cursor.close()
            conn.close()

    except MismatchingStateError:
        return redirect("/login")


@auth_bp.route("/user/update-profile", methods=["POST"])
def update_profile():
    data = request.json or {}
    user_id = data.get("user_id")
    
    # 1. Validation (Letters and dots only)
    name_regex = r"^[a-zA-Z.\s]*$"
    f_name = data.get("first_name", "").strip()
    l_name = data.get("last_name", "").strip()
    if not re.match(name_regex, f_name) or not re.match(name_regex, l_name):
        return jsonify({"status": "error", "message": "Invalid characters in name"}), 400

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT user_type, customer_id FROM "system_user" WHERE user_id = %s', (user_id,))
        user_row = cursor.fetchone()

        if not user_row:
            return jsonify({"status": "error", "message": "User not found"}), 404

        user_role = str(user_row[0] or "").strip().lower()

        if user_role in STAFF_ROLES:
            # Identity Type is intentionally omitted for Admin and Technician users.
            # Their profile updates ignore persona/customer identity data and keep other fields intact.
            cursor.execute("""
                UPDATE "system_user"
                SET first_name = %s,
                    last_name = %s,
                    email = %s,
                    profile_persona = NULL,
                    profile_pic_url = COALESCE(%s, profile_pic_url),
                    is_profile_complete = %s
                WHERE user_id = %s
            """, (f_name, l_name, data.get("email"), data.get("photo"), True, user_id))
            conn.commit()
            return jsonify({"status": "success"}), 200

        # 2. Check for existing link
        customer_id = user_row[1]

        # 3. Handle Missing Customer Record (Satisfying NOT NULL constraints)
        if customer_id is None:
            cursor.execute("""
                INSERT INTO customer (company_name, contact_person, phone_number, address, company_email) 
                VALUES (%s, %s, %s, %s, %s) RETURNING customer_id
            """, (
                data.get("company_name") or "New Company",
                data.get("contact_person") or f_name,
                data.get("phone") or "0900-000-0000",
                data.get("address") or "Pending",
                data.get("company_email") or data.get("email")
            ))
            customer_id = cursor.fetchone()[0]
            # LINK the user to this new ID
            cursor.execute('UPDATE "system_user" SET customer_id = %s WHERE user_id = %s', (customer_id, user_id))

        # 4. Update system_user (Persona, Photo, and Status)
        cursor.execute("""
            UPDATE "system_user" 
            SET first_name = %s, last_name = %s, email = %s, 
                profile_persona = %s, profile_pic_url = %s, is_profile_complete = %s
            WHERE user_id = %s
        """, (f_name, l_name, data.get("email"), data.get("persona"), data.get("photo"), True, user_id))

        # 5. Update Customer table
        cursor.execute("""
            UPDATE customer SET 
                phone_number = %s, address = %s, company_name = %s, 
                contact_person = %s, company_email = %s
            WHERE customer_id = %s
        """, (data.get("phone"), data.get("address"), data.get("company_name"), 
              data.get("contact_person"), data.get("company_email"), customer_id))

        conn.commit()
        return jsonify({"status": "success"}), 200
    # Update your update_profile route in auth_routes_7.py
    except Exception as e:
        conn.rollback()
        error_str = str(e)
        
        # Check if the error is specifically about the duplicate email
        if "system_user_email_key" in error_str:
            return jsonify({
                "status": "error", 
                "message": "This email is already registered. Try logging in with this account instead!"
            }), 400
        
        # For any other error, keep it as it was
        print(f"DATABASE ERROR: {error_str}")
        return jsonify({"status": "error", "message": "An unexpected error occurred."}), 500
    finally:
        cursor.close()
        conn.close()


@auth_bp.route("/user/profile/<int:user_id>", methods=["GET"])
def get_profile(user_id):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # LEFT JOIN ensures we get user data even if customer data is still being built
        cursor.execute("""
            SELECT 
                u.first_name, u.last_name, u.email, 
                u.profile_persona, u.profile_pic_url, u.is_profile_complete,
                c.phone_number, c.address, c.company_name, 
                c.contact_person, c.company_email
            FROM "system_user" u
            LEFT JOIN customer c ON u.customer_id = c.customer_id
            WHERE u.user_id = %s
        """, (user_id,))
        row = cursor.fetchone()
        return jsonify({"status": "success", "data": row}) if row else (jsonify({"status": "error"}), 404)
    finally:
        cursor.close()
        conn.close()

# auth_routes_7.py - Add this new route

@auth_bp.route("/user/update-photo", methods=["POST"])
def update_user_photo():
    data = request.json
    user_id = data.get("user_id")
    # 'photo_data' will be the compressed string or null (for removal)
    photo_text = data.get("photo_data") 

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Use the exact column from image_b65fa0.png: profile_pic_url
        cursor.execute(
            'UPDATE "system_user" SET profile_pic_url = %s WHERE user_id = %s',
            (photo_text, user_id)
        )
        conn.commit()
        return jsonify({"status": "success", "message": "Photo updated instantly"}), 200
    except Exception as e:
        conn.rollback()
        print(f"Instant Photo Update Failure: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@auth_bp.route('/user/profile/complete/<int:user_id>', methods=['GET'])
def get_profile_completion_status(user_id):
    conn = get_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Pull live boolean status along with your base64 string column
        cursor.execute('SELECT is_profile_complete, profile_pic_url FROM "system_user" WHERE user_id = %s', (user_id,))
        user = cursor.fetchone()
        
        is_complete = user.get("is_profile_complete", False) if user else False
        photo_url = user.get("profile_pic_url") if user else None

        return jsonify({
            "status": "success",
            "is_profile_complete": is_complete,
            "profile_pic_url": photo_url
        }), 200

    except Exception as e:
        print(f"Error checking status for user {user_id}: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 10. SEND OTP
# ==========================================
@auth_bp.route("/send-otp", methods=["POST"])
def send_otp():
    data = request.json
    email = data.get("email")

    if not email:
        return jsonify({"status": "error", "message": "Email is required"}), 400

    otp = str(random.randint(100000, 999999))
    expiry = datetime.now() + timedelta(minutes=2)

    conn = get_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500
    
    cursor = conn.cursor()
    try:
        # 1. Check for existing user
        cursor.execute('SELECT * FROM "system_user" WHERE LOWER(Email) = LOWER(%s)', (email,))
        if cursor.fetchone():
             return jsonify({"status": "error", "message": "Email already exists"}), 400

        # 2. Save OTP to PostgreSQL
        # 🌟 FIXED: Let PostgreSQL do the time math!
        query = "INSERT INTO otp_verifications (email, otp_code, expires_at) VALUES (%s, %s, NOW() + INTERVAL '2 minutes')"
        cursor.execute(query, (email, otp))
        conn.commit()

        # 3. BREVO CONFIGURATION
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = os.getenv("BREVO_API_KEY")
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

        # 4. SEND EMAIL
        # Important: The sender email MUST be verified in your Brevo dashboard
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            sender={"name": "AlliTrack", "email": "noreply.allitrack@gmail.com"},
            to=[{"email": email}],
            subject="AlliTrack Verification Code",
            html_content=f"""
                <div style="font-family: sans-serif; padding: 20px; border: 1px solid #eee;">
                    <h2>Verify your account</h2>
                    <p>Use the following code to complete your signup for AlliTrack:</p>
                    <h1 style="color: #4f46e5;">{otp}</h1>
                    <p>This code expires in 2 minutes.</p> 
                </div>
            """
        )

        api_instance.send_transac_email(send_smtp_email)
        return jsonify({"status": "success", "message": "OTP sent"}), 200

    except ApiException as e:
        print(f"Brevo API Error: {e}")
        return jsonify({"status": "error", "message": "Email service failed"}), 500
    except Exception as e:
        print(f"OTP Error: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 11. VERIFY OTP
# ==========================================
@auth_bp.route("/verify-otp", methods=["POST"])
def verify_otp():
    data = request.json
    email = data.get("email")
    otp_code = data.get("otp")

    if not email or not otp_code:
        return jsonify({"status": "error", "message": "Email and OTP are required"}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500

    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(
            """
            SELECT * FROM otp_verifications
            WHERE email = %s AND otp_code = %s AND expires_at > NOW()
            ORDER BY created_at DESC LIMIT 1
            """,
            (email, otp_code)
        )
        record = cursor.fetchone()

        if not record:
            return jsonify({"status": "error", "message": "Invalid or expired code"}), 400

        # Clean up used OTP
        cursor.execute("DELETE FROM otp_verifications WHERE email = %s", (email,))
        conn.commit()

        return jsonify({"status": "success", "message": "OTP verified"}), 200

    except Exception as e:
        print(f"Verify OTP error: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500
    finally:
        cursor.close()
        conn.close()


# ==========================================
# 12. RESEND OTP (WITH SECONDS & LOCKOUT)
# ==========================================
@auth_bp.route("/resend-otp", methods=["POST"])
def resend_otp():
    data = request.json
    email = data.get("email")

    if not email:
        return jsonify({"status": "error", "message": "Email is required"}), 400

    otp = str(random.randint(100000, 999999))
    
    conn = get_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500

    cursor = conn.cursor(cursor_factory=RealDictCursor) 
    try:
        # 🌟 1. CHECK LOCKOUT FIRST 
        cursor.execute('SELECT EXTRACT(EPOCH FROM (locked_until - NOW())) AS remaining_seconds FROM "system_user" WHERE LOWER(email) = LOWER(%s) AND locked_until > NOW()', (email,))
        lock_data = cursor.fetchone()
        if lock_data and lock_data["remaining_seconds"] > 0:
            return jsonify({
                "status": "error", 
                "message": "Account locked.", 
                "remaining_seconds": int(lock_data["remaining_seconds"])
            }), 403

        # Delete any old OTPs for this email first
        cursor.execute("DELETE FROM otp_verifications WHERE email = %s", (email,))

        # Insert fresh OTP
        cursor.execute("INSERT INTO otp_verifications (email, otp_code, expires_at) VALUES (%s, %s, NOW() + INTERVAL '2 minutes')", (email, otp))
        conn.commit()

        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = os.getenv("BREVO_API_KEY")
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            sender={"name": "AlliTrack", "email": "noreply.allitrack@gmail.com"},
            to=[{"email": email}],
            subject="AlliTrack — New Verification Code",
            html_content=f"""
                <div style="font-family: sans-serif; padding: 20px; border: 1px solid #eee;">
                    <h2>New verification code</h2>
                    <p>Here's your new code for AlliTrack:</p>
                    <h1 style="color: #4f46e5;">{otp}</h1>
                    <p>This code expires in 2 minutes.</p>
                </div>
            """
        )

        api_instance.send_transac_email(send_smtp_email)
        return jsonify({"status": "success", "message": "OTP resent"}), 200

    except ApiException as e:
        print(f"Brevo Resend Error: {e}")
        return jsonify({"status": "error", "message": "Email service failed"}), 500
    except Exception as e:
        print(f"Resend OTP error: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 13. CREATE STAFF (Admin)
# ==========================================
@auth_bp.route("/admin/create-user", methods=["POST"])
@role_required("admin")
def admin_create_user():
    data = _strip_staff_identity_type(request.json or {})
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    status = data.get("status", "active")
    user_type = (data.get("user_type") or data.get("User_Type") or "technician").strip().lower()

    if not name or not email:
        return jsonify({"status": "error", "message": "Name and email are required"}), 400

    if user_type not in ["admin", "technician"]:
        return jsonify({"status": "error", "message": "Invalid role"}), 400

    name_parts = name.split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""
    username = email.split("@")[0]
    temporary_password = _generate_temporary_password()
    temp_password = generate_password_hash(temporary_password)

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute('SELECT user_id FROM "system_user" WHERE LOWER(Email) = LOWER(%s)', (email,))
        if cursor.fetchone():
            return jsonify({"status": "error", "message": "Email already exists"}), 400

        cursor.execute(
            """
            INSERT INTO "system_user"
            (Username, first_name, last_name, Email, password_Hash, User_Type, Account_Status, profile_persona, Created_At)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NULL, CURRENT_TIMESTAMP)
            RETURNING user_id, user_type
            """,
            (username, first_name, last_name, email, temp_password, user_type, status)
        )
        new_user = cursor.fetchone()

        technician_id = None
        if user_type == "technician":
            cursor.execute(
                'INSERT INTO "technician" (user_id) VALUES (%s) RETURNING technician_id',
                (new_user["user_id"],)
            )
            tech = cursor.fetchone()
            technician_id = tech["technician_id"]

        _send_staff_temporary_password_email(
            email,
            f"{first_name} {last_name}".strip(),
            temporary_password,
            action="created",
        )
        conn.commit()

        # 🌟 NEW: Audit Log for Admin Adding Staff
        log_system_event(
            user_identifier=str(new_user["user_id"]), 
            category="User Management",
            action="Add Staff",
            log_level="INFO",
            description=f"Created a new {user_type} account for {email}."
        )

        return jsonify({
            "status": "success",
            "message": f"Staff created. Temporary password was sent to {email}.",
            "user_id": new_user["user_id"],
            "user_type": new_user["user_type"],
            "technician_id": technician_id,
            "email_sent": True
        }), 201

    except ApiException as e:
        conn.rollback()
        print(f"Create staff email error: {e}")
        return jsonify({"status": "error", "message": "Staff was not created because the email could not be sent."}), 500

    except Exception as e:
        conn.rollback()
        print(f"Create staff error: {e}")
        return jsonify({"status": "error", "message": "Database error"}), 500

    finally:
        cursor.close()
        conn.close()

# ==========================================
# 14. SYSTEM SETTINGS (MAINTENANCE)
# ==========================================
@auth_bp.route("/admin/settings", methods=["GET"])
@role_required("admin")
def get_settings():

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Auto-create the table and insert default value if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                setting_key VARCHAR(50) PRIMARY KEY,
                setting_value VARCHAR(255) NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cursor.execute("""
            INSERT INTO system_settings (setting_key, setting_value) 
            VALUES ('maintenance_mode', 'false') 
            ON CONFLICT (setting_key) DO NOTHING;
        """)

        cursor.execute("""
            INSERT INTO system_settings (setting_key, setting_value)
            VALUES ('two_factor_auth', 'true')
            ON CONFLICT (setting_key) DO NOTHING;
        """)
        
        cursor.execute("SELECT setting_key, setting_value FROM system_settings")
        settings = {row[0]: row[1] for row in cursor.fetchall()}

        user_id = request.args.get("user_id")

        if user_id:
            user_key = f"2fa_user_{user_id}"

            if user_key in settings:
                settings["two_factor_auth"] = settings[user_key]
            else:
                settings["two_factor_auth"] = "false"

        return jsonify({
            "status": "success",
            "settings": settings
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@auth_bp.route("/admin/settings/maintenance", methods=["POST"])
@role_required("admin")
def toggle_maintenance():
    data = request.get_json() or {}
    is_active = str(data.get("maintenance_mode", "false")).lower()
    
    current_user = getattr(g, "current_user", None) or get_current_user()
    user_id = current_user.get("user_id") if current_user else "System"

    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """
            UPDATE system_settings 
            SET setting_value = %s, last_updated = CURRENT_TIMESTAMP 
            WHERE setting_key = 'maintenance_mode'
            """,
            (is_active,)
        )
        conn.commit()

        # 🌟 THE LOGS: Dynamic leveling based on the action
        if is_active == "true":
            log_system_event(
                user_identifier=str(user_id),
                category="System Settings",
                action="Maintenance Mode Enabled",
                log_level="CRITICAL",
                description="Administrator activated system-wide Maintenance Mode."
            )
        else:
            log_system_event(
                user_identifier=str(user_id),
                category="System Settings",
                action="Maintenance Mode Disabled",
                log_level="INFO",
                description="Administrator deactivated Maintenance Mode."
            )

        return jsonify({"status": "success", "message": f"Maintenance mode set to {is_active}"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 🌟 VERIFY 2FA LOGIN (WITH SECONDS & LOCKOUT)
# ==========================================
@auth_bp.route("/verify-2fa-login", methods=["POST"])
def verify_2fa_login():
    data = request.json
    email = data.get("email")
    otp_code = data.get("otp")

    if not email or not otp_code:
        return jsonify({"status": "error", "message": "Email and OTP are required"}), 400

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute('SELECT * FROM "system_user" WHERE LOWER(Email) = LOWER(%s)', (email,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        # 🌟 1. CHECK LOCKOUT FIRST 
        cursor.execute('SELECT EXTRACT(EPOCH FROM (locked_until - NOW())) AS remaining_seconds FROM "system_user" WHERE user_id = %s AND locked_until > NOW()', (user["user_id"],))
        lock_data = cursor.fetchone()
        if lock_data and lock_data["remaining_seconds"] > 0:
            return jsonify({
                "status": "error", 
                "message": "Account locked.",
                "remaining_seconds": int(lock_data["remaining_seconds"])
            }), 403

        # 2. VERIFY THE OTP
        cursor.execute("SELECT * FROM otp_verifications WHERE email = %s AND otp_code = %s AND expires_at > NOW()", (email, otp_code))
        
        if not cursor.fetchone():
            # 🌟 3. WRONG OTP (4TH STRIKE TRIGGER)
            cursor.execute('UPDATE "system_user" SET failed_attempts = COALESCE(failed_attempts, 0) + 1 WHERE user_id = %s RETURNING failed_attempts', (user["user_id"],))
            attempts = cursor.fetchone()["failed_attempts"]
            
            if attempts >= 4:
                cursor.execute('UPDATE "system_user" SET failed_attempts = 0, locked_until = NOW() + INTERVAL \'15 minutes\' WHERE user_id = %s RETURNING EXTRACT(EPOCH FROM (locked_until - NOW())) AS remaining_seconds', (user["user_id"],))
                new_lock = cursor.fetchone()
                conn.commit()
                
                ip_address = _client_ip()
                location = _location_from_ip(ip_address)
                _send_lockout_email(user["email"], user.get("first_name", "User"), location)
                
                log_system_event(
                    user_identifier=str(user["user_id"]), 
                    category="Security", 
                    action="Account Locked", 
                    log_level="CRITICAL", 
                    description=f"Account locked for 15 minutes due to 4 failed 2FA attempts."
                )
                
                return jsonify({
                    "status": "error", 
                    "message": "Account locked.", 
                    "remaining_seconds": int(new_lock["remaining_seconds"])
                }), 403

            log_system_event(
                user_identifier=str(user["user_id"]), 
                category="Security", 
                action="2FA Login Failed", 
                log_level="WARNING", 
                description="Failed 2FA verification attempt. Invalid or expired code entered."
            )
            conn.commit()
            return jsonify({"status": "error", "message": "Invalid or expired code"}), 400

        # 🌟 CORRECT OTP: CLEAR STRIKES AND LOG IN
        cursor.execute("DELETE FROM otp_verifications WHERE email = %s", (email,))
        cursor.execute('UPDATE "system_user" SET failed_attempts = 0, locked_until = NULL WHERE user_id = %s', (user["user_id"],))
        
        full_name = f"{user['first_name']} {user['last_name'] or ''}".strip()
        safe_user = {
            "user_id": user["user_id"],
            "Username": user["username"],
            "Name": full_name,
            "Email": user["email"],
            "User_Type": user["user_type"],
            "is_profile_complete": user.get("is_profile_complete", False),
            "profile_pic_url": user.get("profile_pic_url"),
            "Technician_ID": None
        }

        if user["user_type"] in ["admin", "technician"]:
            cursor.execute("SELECT Technician_ID FROM technician WHERE user_id = %s", (user["user_id"],))
            tech = cursor.fetchone()
            if tech:
                safe_user["Technician_ID"] = tech["technician_id"]

        _record_login_attempt(cursor, user_id=user["user_id"], email=user["email"], status="success")
        cursor.execute('UPDATE "system_user" SET last_login = CURRENT_TIMESTAMP WHERE user_id = %s', (user["user_id"],))
        conn.commit()

        log_system_event(
            user_identifier=str(user["user_id"]), 
            category="Authentication", 
            action="2FA Login Success", 
            log_level="INFO", 
            description="Successfully authenticated via 2FA."
        )
        return jsonify({"status": "success", "user": safe_user}), 200

    except Exception as e:
        print(f"2FA verify error: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 🌟 GET ALL SYSTEM SETTINGS (Unified & Clean)
# ==========================================
@auth_bp.route("/admin/settings", methods=["GET"])
def get_system_settings():
    user_id = str(request.args.get("user_id"))
    
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("SELECT setting_key, setting_value FROM system_settings")
        settings = cursor.fetchall()
        settings_dict = {row["setting_key"]: row["setting_value"] for row in settings}
        
        # 🌟 FIXED: Strictly default 2FA to FALSE and Timeout to 60 for all new accounts!
        settings_dict["two_factor_auth"] = "false" 
        settings_dict["session_timeout"] = "60" # Default fallback
        
        # Override with the user's personal setting if they have interacted with it before
        if user_id and user_id not in ["undefined", "null", "None", ""]:
            # 1. Check Personal 2FA
            user_2fa_key = f"2fa_user_{user_id}"
            if user_2fa_key in settings_dict:
                settings_dict["two_factor_auth"] = str(settings_dict[user_2fa_key]).lower()
            
            # 2. 🌟 NEW: Check Personal Session Timeout
            user_timeout_key = f"session_timeout_{user_id}"
            if user_timeout_key in settings_dict:
                settings_dict["session_timeout"] = str(settings_dict[user_timeout_key])
                
        return jsonify({"status": "success", "settings": settings_dict}), 200
    except Exception as e:
        print(f"Error fetching settings: {e}")
        return jsonify({"status": "error", "message": "Failed to fetch settings"}), 500
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 🌟 SAVE 2FA SETTING
# ==========================================
@auth_bp.route("/admin/settings/2fa", methods=["POST"])
@role_required("admin")
def toggle_2fa():
    data = request.get_json() or {}

    is_active = str(data.get("two_factor_auth", "false")).lower()
    user_id = str(data.get("user_id"))
    
    # 🌟 FIXED: Strictly block "undefined" ghost IDs from cluttering the database!
    if not user_id or user_id in ["undefined", "null", "None", ""]:
        return jsonify({"status": "error", "message": "Valid User ID is required"}), 400
        
    setting_key = f"2fa_user_{user_id}"
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO system_settings (setting_key, setting_value) 
            VALUES (%s, %s)
            ON CONFLICT (setting_key) DO UPDATE 
            SET setting_value = EXCLUDED.setting_value, last_updated = CURRENT_TIMESTAMP
            """,
            (setting_key, is_active)
        )
        conn.commit()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 🌟 GET ALL SYSTEM LOGS
# ==========================================
@auth_bp.route("/admin/system-logs", methods=["GET"])
def get_system_logs():
    conn = get_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500

    # RealDictCursor ensures we get JSON-friendly dictionaries back
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Fetch the 200 most recent logs
        cursor.execute("SELECT * FROM system_logs ORDER BY timestamp DESC LIMIT 200")
        logs = cursor.fetchall()
        
        # Format the timestamps nicely for the frontend
        for log in logs:
            if log.get("timestamp"):
                log["formatted_time"] = log["timestamp"].strftime("%b %d, %Y - %I:%M %p")
                
        return jsonify({"status": "success", "logs": logs}), 200
        
    except Exception as e:
        print(f"Log fetch error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 🌟 SAVE SESSION TIMEOUT (PER-USER)
# ==========================================
@auth_bp.route("/admin/settings/timeout", methods=["POST"])
@role_required("admin")
def update_session_timeout():
    data = request.get_json() or {}
    timeout_value = str(data.get("session_timeout", "60")).strip()  # Default to 60 if not provided

    # Security check: Ensure they only send valid minute options
    allowed_values = ["1", "15", "30", "60", "120", "240"]
    if timeout_value not in allowed_values:
        timeout_value = "15"

    current_user = getattr(g, "current_user", None) or get_current_user()
    user_id = current_user.get("user_id") if current_user else None

    if not user_id:
        return jsonify({"status": "error", "message": "User ID required"}), 400

    # 🌟 SAVES ONLY FOR THIS SPECIFIC USER
    setting_key = f"session_timeout_{user_id}"

    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """
            INSERT INTO system_settings (setting_key, setting_value) 
            VALUES (%s, %s)
            ON CONFLICT (setting_key) DO UPDATE 
            SET setting_value = EXCLUDED.setting_value, last_updated = CURRENT_TIMESTAMP
            """,
            (setting_key, timeout_value)
        )
        conn.commit()

        log_system_event(
            user_identifier=str(user_id),
            category="System Settings",
            action="Session Timeout Updated",
            log_level="WARNING",
            description=f"User updated their personal session timeout to {timeout_value} minutes."
        )

        return jsonify({"status": "success", "message": f"Timeout set to {timeout_value} minutes"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# ==========================================
# ⚠️ DANGER ZONE: CLEAR LOGS
# ==========================================
@auth_bp.route("/admin/settings/clear-logs", methods=["POST"])
@role_required("admin")
def clear_all_logs():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Instantly wipe all rows from the system_logs table and reset the ID counter
        cursor.execute("TRUNCATE TABLE system_logs RESTART IDENTITY;")
        conn.commit()

        # Log the fact that the logs were cleared (starts the new log table cleanly!)
        current_user = getattr(g, "current_user", None) or get_current_user()
        admin_id = current_user.get("user_id") if current_user else "System"
        
        log_system_event(
            user_identifier=str(admin_id),
            category="System Settings",
            action="Logs Cleared",
            log_level="CRITICAL",
            description="Administrator permanently deleted all system logs and audit trails."
        )

        return jsonify({"status": "success", "message": "All system logs have been permanently deleted."}), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# ==========================================
# ⚠️ DANGER ZONE: RESET DATABASE
# ==========================================
@auth_bp.route("/admin/settings/reset-database", methods=["POST"])
@role_required("admin")
def reset_database():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 1. Wipe standard utility tables
        cursor.execute("TRUNCATE TABLE system_logs RESTART IDENTITY CASCADE;")
        cursor.execute("TRUNCATE TABLE login_history RESTART IDENTITY CASCADE;")
        cursor.execute("TRUNCATE TABLE otp_verifications RESTART IDENTITY CASCADE;")
        
        # 2. Reset System Settings to absolute defaults
        cursor.execute("TRUNCATE TABLE system_settings RESTART IDENTITY CASCADE;")
        cursor.execute(
            """
            INSERT INTO system_settings (setting_key, setting_value) 
            VALUES ('maintenance_mode', 'false'), ('two_factor_auth', 'false')
            """
        )

        # 3. Wipe all users EXCEPT the admin performing the reset so you aren't locked out!
        current_user = getattr(g, "current_user", None) or get_current_user()
        admin_id = current_user.get("user_id") if current_user else None
        
        if admin_id:
            cursor.execute('DELETE FROM "system_user" WHERE user_id != %s', (admin_id,))

        conn.commit()

        # 4. Leave a single footprint
        log_system_event(
            user_identifier=str(admin_id),
            category="System Settings",
            action="Factory Reset",
            log_level="CRITICAL",
            description="Administrator performed a factory reset. All non-admin data wiped."
        )

        return jsonify({"status": "success", "message": "Database reset to factory defaults."}), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()
