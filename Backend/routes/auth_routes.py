from flask import Blueprint, request, jsonify
from database import get_connection
from werkzeug.security import generate_password_hash, check_password_hash
from psycopg2.extras import RealDictCursor
import re

auth_bp = Blueprint("auth", __name__)

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
                "Technician_ID": None
            }

            # Technician lookup
            if user["user_type"] in ["admin", "technician"]:
                tech_query = "SELECT Technician_ID FROM technician WHERE user_id = %s"
                cursor.execute(tech_query, (user["user_id"],))
                tech = cursor.fetchone()
                if tech:
                    safe_user["Technician_ID"] = tech["technician_id"]

            return jsonify({"status": "success", "user": safe_user}), 200

        return jsonify({"status": "error", "message": "Invalid email or password"}), 401

    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"status": "error", "message": "Database error"}), 500

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

        # Updated to insert into first_name and last_name
        query = """
            INSERT INTO "system_user"
            (Username, first_name, last_name, Email, Password_Hash, User_Type, Created_At)
            VALUES (%s, %s, %s, %s, %s, 'client', CURRENT_TIMESTAMP)
        """
        cursor.execute(query, (username, first_name, last_name, email, hashed_password))
        conn.commit()

        return jsonify({"status": "success", "message": "Account created successfully"}), 201

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
            'UPDATE "system_user" SET Password_Hash = %s WHERE user_id = %s',
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

    # Strong validation
    if (len(new_password) < 8 or
        not re.search(r"[A-Z]", new_password) or
        not re.search(r"[a-z]", new_password) or
        not re.search(r"\d", new_password) or
        not re.search(r"[!@#$%^&*(),.?\":{}|<>]", new_password)):
        return jsonify({"status": "error", "message": "Weak password"}), 400

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute('SELECT Password_Hash FROM "system_user" WHERE user_id = %s', (user_id,))
        user = cursor.fetchone()

        if not user or not check_password_hash(user["password_hash"], old_password):
            return jsonify({"status": "error", "message": "Incorrect password"}), 401

        hashed = generate_password_hash(new_password)
        cursor.execute(
            'UPDATE "system_user" SET Password_Hash = %s WHERE user_id = %s',
            (hashed, user_id)
        )
        conn.commit()

        return jsonify({"status": "success", "message": "Password updated"}), 200

    except Exception as e:
        print(f"Change error: {e}")
        return jsonify({"status": "error", "message": "Database error"}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================
# 5. GET USERS (FORMATTED)
# ==========================================
@auth_bp.route("/admin/users", methods=["GET"])
def get_all_staff():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute('SELECT user_id, first_name, last_name, Email, User_Type, Account_Status FROM "system_user"')
        users = cursor.fetchall()

        formatted = []
        for u in users:
            formatted.append({
                "user_id": u["user_id"],
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
def admin_update_user():
    data = request.json

    conn = get_connection()
    cursor = conn.cursor()

    try:
        query = '''
        UPDATE "system_user"
        SET first_name = %s, last_name = %s, Email = %s, Account_Status = %s
        WHERE user_id = %s
        '''
        cursor.execute(query, (
            data.get("first_name"),
            data.get("last_name"),
            data.get("email"),
            data.get("status"),
            data.get("user_id")
        ))
        conn.commit()

        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(e)
        return jsonify({"status": "error"}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================
# 8. USER UPDATE PROFILE
# ==========================================
@auth_bp.route("/user/update-profile", methods=["POST"])
def update_user_profile():
    data = request.json

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            'UPDATE "system_user" SET first_name=%s, last_name=%s, Email=%s WHERE user_id=%s',
            (data.get("first_name"), data.get("last_name"), data.get("email"), data.get("user_id"))
        )
        conn.commit()

        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(e)
        return jsonify({"status": "error"}), 500

    finally:
        cursor.close()
        conn.close()