from flask import Blueprint, request, jsonify, redirect, session
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

from sib_api_v3_sdk.rest import ApiException
from datetime import datetime, timedelta
from Backend.routes.rbac import role_required




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

    # Private/local network ranges cannot be geolocated.
    if (
        ip_address.startswith("10.") or
        ip_address.startswith("192.168.") or
        ip_address.startswith("172.16.") or
        ip_address.startswith("172.17.") or
        ip_address.startswith("172.18.") or
        ip_address.startswith("172.19.") or
        ip_address.startswith("172.20.") or
        ip_address.startswith("172.21.") or
        ip_address.startswith("172.22.") or
        ip_address.startswith("172.23.") or
        ip_address.startswith("172.24.") or
        ip_address.startswith("172.25.") or
        ip_address.startswith("172.26.") or
        ip_address.startswith("172.27.") or
        ip_address.startswith("172.28.") or
        ip_address.startswith("172.29.") or
        ip_address.startswith("172.30.") or
        ip_address.startswith("172.31.")
    ):
        return "Local Network"

    try:
        response = requests.get(
            f"http://ip-api.com/json/{ip_address}?fields=status,country,regionName,city",
            timeout=3,
        )
        data = response.json()

        if data.get("status") == "success":
            parts = [data.get("city"), data.get("regionName"), data.get("country")]
            location = ", ".join([part for part in parts if part])
            return location or "Unknown Location"

    except Exception as geo_error:
        print(f"IP geolocation failed: {geo_error}")

    return "Unknown Location"


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


load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

auth_bp = Blueprint("auth", __name__)
oauth = OAuth()

# ==========================================
# 1. LOGIN (FINAL MERGED)
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

        if user and check_password_hash(user["password_hash"], password):
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

            # Technician lookup
            if user["user_type"] in ["admin", "technician"]:
                tech_query = "SELECT Technician_ID FROM technician WHERE user_id = %s"
                cursor.execute(tech_query, (user["user_id"],))
                tech = cursor.fetchone()
                if tech:
                    safe_user["Technician_ID"] = tech["technician_id"]

            _record_login_attempt(cursor, user_id=user["user_id"], email=user["email"], status="success")
            cursor.execute(
                'UPDATE "system_user" SET last_login = CURRENT_TIMESTAMP WHERE user_id = %s',
                (user["user_id"],),
            )
            conn.commit()
            return jsonify({"status": "success", "user": safe_user}), 200

        _record_login_attempt(cursor, email=email, status="failed")
        conn.commit()
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
@auth_bp.route("/admin/reset-password", methods=["POST"])
@role_required("admin")
def admin_reset_password():
    data = request.json
    target_user_id = data.get("target_user_id")

    if not target_user_id:
        return jsonify({"status": "error", "message": "Missing User ID"}), 400

    temp_password = "Password2026!"
    hashed = generate_password_hash(temp_password)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            'UPDATE "system_user" SET password_Hash = %s WHERE user_id = %s',
            (hashed, target_user_id)
        )
        conn.commit()

        return jsonify({
            "status": "success",
            "message": f"Password reset to: {temp_password}"
        }), 200

    except Exception as e:
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
    data = request.json or {}

    target_user_id = data.get("user_id")
    user_type = (data.get("user_type") or data.get("User_Type") or "").strip().lower()

    if not target_user_id:
        return jsonify({"status": "error", "message": "Missing User ID"}), 400

    if user_type and user_type not in ["admin", "technician"]:
        return jsonify({"status": "error", "message": "Invalid role"}), 400

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
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
                    ? "/admin/all-tickets.html"
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
    data = request.json
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
        # 2. Check for existing link
        cursor.execute('SELECT customer_id FROM "system_user" WHERE user_id = %s', (user_id,))
        res = cursor.fetchone()
        customer_id = res[0] if res else None

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
    expiry = datetime.now() + timedelta(minutes=10)

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
        query = "INSERT INTO otp_verifications (email, otp_code, expires_at) VALUES (%s, %s, %s)"
        cursor.execute(query, (email, otp, expiry))
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
                    <p>This code expires in 10 minutes.</p>
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
# 12. RESEND OTP
# ==========================================
@auth_bp.route("/resend-otp", methods=["POST"])
def resend_otp():
    data = request.json
    email = data.get("email")

    if not email:
        return jsonify({"status": "error", "message": "Email is required"}), 400

    otp = str(random.randint(100000, 999999))
    expiry = datetime.now() + timedelta(minutes=10)

    conn = get_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500

    cursor = conn.cursor()
    try:
        # Delete any old OTPs for this email first
        cursor.execute("DELETE FROM otp_verifications WHERE email = %s", (email,))

        # Insert fresh OTP
        cursor.execute(
            "INSERT INTO otp_verifications (email, otp_code, expires_at) VALUES (%s, %s, %s)",
            (email, otp, expiry)
        )
        conn.commit()

        # Brevo — same config as send_otp
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
                    <p>This code expires in 10 minutes.</p>
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
    data = request.json or {}
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
    temp_password = generate_password_hash("Password2026!")

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute('SELECT user_id FROM "system_user" WHERE LOWER(Email) = LOWER(%s)', (email,))
        if cursor.fetchone():
            return jsonify({"status": "error", "message": "Email already exists"}), 400

        cursor.execute(
            """
            INSERT INTO "system_user"
            (Username, first_name, last_name, Email, password_Hash, User_Type, Account_Status, Created_At)
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
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

        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Staff created",
            "user_id": new_user["user_id"],
            "user_type": new_user["user_type"],
            "technician_id": technician_id,
            "temporary_password": "Password2026!"
        }), 201

    except Exception as e:
        conn.rollback()
        print(f"Create staff error: {e}")
        return jsonify({"status": "error", "message": "Database error"}), 500

    finally:
        cursor.close()
        conn.close()
