from flask import Blueprint, request, jsonify
from database import get_connection
from werkzeug.security import generate_password_hash, check_password_hash
from psycopg2.extras import RealDictCursor 
import re # For password validation

auth_bp = Blueprint("auth", __name__)

# ==========================================
# 1. LOGIN
# ==========================================
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor) # Postgres dict mode[cite: 3]

    try:
        # Use double quotes for reserved word and LOWER for case-insensitivity[cite: 2, 4]
        query = 'SELECT * FROM "system_user" WHERE LOWER(Email) = LOWER(%s)'
        cursor.execute(query, (email,))
        user = cursor.fetchone()

        # Postgres returns keys in lowercase
        if user and check_password_hash(user["password_hash"], password):
            safe_user = {
                "user_id": user["user_id"],
                "Username": user["username"],
                "Name": user["name"],
                "Email": user["email"],
                "User_Type": user["user_type"],
                "Technician_ID": None 
            }

            if user["user_type"] in ["admin", "technician"]:
                tech_query = "SELECT Technician_ID FROM technician WHERE user_id = %s"
                cursor.execute(tech_query, (user["user_id"],))
                tech_record = cursor.fetchone()
                if tech_record:
                    safe_user["Technician_ID"] = tech_record["technician_id"]

            return jsonify({"status": "success", "user": safe_user}), 200
        else:
            return jsonify({"status": "error", "message": "Invalid email or password"}), 401
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"status": "error", "message": "Database error"}), 500
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 2. SIGNUP
# ==========================================
@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.json
    first_name = data.get("firstName")
    last_name = data.get("lastName")
    email = data.get("email")
    password = data.get("password") 

    name = f"{first_name} {last_name}".strip()
    username = email.split('@')[0]
    hashed_password = generate_password_hash(password)

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute('SELECT * FROM "system_user" WHERE LOWER(Email) = LOWER(%s)', (email,))
        if cursor.fetchone():
            return jsonify({"status": "error", "message": "Email already exists"}), 400

        query = """
            INSERT INTO "system_user" (Username, Name, Email, Password_Hash, User_Type, Created_At)
            VALUES (%s, %s, %s, %s, 'client', CURRENT_TIMESTAMP)
        """
        cursor.execute(query, (username, name, email, hashed_password))
        conn.commit()
        return jsonify({"status": "success", "message": "Account created successfully"}), 201
    except Exception as e:
        print(f"Signup error: {e}")
        return jsonify({"status": "error", "message": "Database error"}), 500
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 3. ADMIN: Reset User Password
# ==========================================
@auth_bp.route("/admin/reset-password", methods=["POST"])
def admin_reset_password():
    data = request.json
    target_user_id = data.get("target_user_id")
    
    if not target_user_id:
        return jsonify({"status": "error", "message": "Missing User ID"}), 400

    temp_password = "Password2026!"
    hashed_temp = generate_password_hash(temp_password)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('UPDATE "system_user" SET Password_Hash = %s WHERE user_id = %s', (hashed_temp, target_user_id))
        conn.commit()
        return jsonify({"status": "success", "message": f"Password successfully reset to: {temp_password}"}), 200
    except Exception as e:
        print(f"Admin Reset Error: {e}")
        return jsonify({"status": "error", "message": "Database error"}), 500
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 4. USER: Change Password (WITH REQUIREMENTS)
# ==========================================
@auth_bp.route("/user/change-password", methods=["POST"])
def change_password():
    data = request.json
    user_id = data.get("user_id")
    old_password = data.get("old_password")
    new_password = data.get("new_password")

    # RESTORED: Strict password validation[cite: 2]
    if (len(new_password) < 8 or 
        not re.search(r"[A-Z]", new_password) or 
        not re.search(r"[a-z]", new_password) or 
        not re.search(r"\d", new_password) or 
        not re.search(r"[!@#$%^&*(),.?\":{}|<>]", new_password)):
        return jsonify({"status": "error", "message": "New password does not meet security requirements."}), 400

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute('SELECT Password_Hash FROM "system_user" WHERE user_id = %s', (user_id,))
        user = cursor.fetchone()

        if not user or not check_password_hash(user["password_hash"], old_password):
            return jsonify({"status": "error", "message": "Incorrect current password"}), 401

        hashed_new = generate_password_hash(new_password)
        cursor.execute('UPDATE "system_user" SET Password_Hash = %s WHERE user_id = %s', (hashed_new, user_id))
        conn.commit()
        return jsonify({"status": "success", "message": "Password updated securely!"}), 200
    except Exception as e:
        print(f"Change Password Error: {e}")
        return jsonify({"status": "error", "message": "Database error"}), 500
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 5. ADMIN: Get All Users
# ==========================================
@auth_bp.route("/admin/users", methods=["GET"])
def get_all_staff():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Postgres requires double quotes for system_user[cite: 4]
        cursor.execute('SELECT user_id, Name, Email, User_Type, Account_Status FROM "system_user"')
        users = cursor.fetchall()
        
        # Mapping lowercase Postgres keys back to expected JS case[cite: 4]
        formatted_users = []
        for u in users:
            formatted_users.append({
                "user_id": u["user_id"],
                "Name": u["name"],
                "Email": u["email"],
                "User_Type": u["user_type"],
                "Account_Status": u["account_status"]
            })
        return jsonify(formatted_users), 200
    except Exception as e:
        print(f"Error fetching users: {e}")
        return jsonify([]), 500
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 6. ADMIN: Delete Users
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
        for user_id in user_ids:
            clean_id = str(user_id).replace("STF-", "")
            cursor.execute('DELETE FROM "system_user" WHERE user_id = %s', (clean_id,))
        conn.commit()
        return jsonify({"status": "success", "message": "Users permanently deleted"}), 200
    except Exception as e:
        print(f"Delete User Error: {e}")
        return jsonify({"status": "error", "message": "Database error"}), 500
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 7. ADMIN: Update User Status/Info
# ==========================================
@auth_bp.route("/admin/update-user", methods=["POST"])
def admin_update_user():
    data = request.json
    user_id = data.get("user_id")
    name = data.get("name")
    email = data.get("email")
    status = data.get("status")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = 'UPDATE "system_user" SET Name = %s, Email = %s, Account_Status = %s WHERE user_id = %s'
        cursor.execute(query, (name, email, status, user_id))
        conn.commit()
        return jsonify({"status": "success", "message": "User updated"}), 200
    except Exception as e:
        print(f"Update Error: {e}")
        return jsonify({"status": "error", "message": "Database update failed"}), 500
    finally:
        cursor.close()
        conn.close()

# ==========================================
# 8. USER: Update Own Profile
# ==========================================
@auth_bp.route("/user/update-profile", methods=["POST"])
def update_user_profile():
    data = request.json
    user_id = data.get("user_id")
    name = data.get("name")
    email = data.get("email")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = 'UPDATE "system_user" SET Name = %s, Email = %s WHERE user_id = %s'
        cursor.execute(query, (name, email, user_id))
        conn.commit()
        return jsonify({"status": "success", "message": "Profile updated successfully"}), 200
    except Exception as e:
        print(f"Profile Update Error: {e}")
        return jsonify({"status": "error", "message": "Failed to update profile"}), 500
    finally:
        cursor.close()
        conn.close()