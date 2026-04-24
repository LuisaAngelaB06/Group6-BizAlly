from flask import Blueprint, request, jsonify
from database import get_connection
# NEW: Import the security tools!
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        query = "SELECT * FROM system_user WHERE Email = %s"
        cursor.execute(query, (email,))
        user = cursor.fetchone()

        # NEW: Securely check the typed password against the hashed database password
        if user and check_password_hash(user["Password_Hash"], password):
            safe_user = {
                "User_ID": user["User_ID"],
                "Username": user["Username"],
                "Name": user["Name"],
                "Email": user["Email"],
                "User_Type": user["User_Type"],
                "Technician_ID": None 
            }

            # If they are an admin, check if they are in the technician table
            if user["User_Type"] in ["admin", "technician"]:
                tech_query = "SELECT Technician_ID FROM technician WHERE User_ID = %s"
                cursor.execute(tech_query, (user["User_ID"],))
                tech_record = cursor.fetchone()
                if tech_record:
                    safe_user["Technician_ID"] = tech_record["Technician_ID"]

            cursor.close()
            conn.close()
            print("User logged in:", safe_user["Email"], "- Role:", safe_user["User_Type"])
            return jsonify({"status": "success", "user": safe_user}), 200
            
        else:
            cursor.close()
            conn.close()
            return jsonify({"status": "error", "message": "Invalid email or password"}), 401

    except Exception as e:
        print(f"Login error: {e}")
        if conn.is_connected():
            cursor.close()
            conn.close()
        return jsonify({"status": "error", "message": "Database connection failed"}), 500


@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.json
    first_name = data.get("firstName")
    last_name = data.get("lastName")
    email = data.get("email")
    password = data.get("password") 

    name = f"{first_name} {last_name}".strip()
    username = email.split('@')[0]

    # NEW: Encrypt the password before saving it to the database!
    # This turns "mypassword" into a giant scrambled string of characters
    hashed_password = generate_password_hash(password)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM system_user WHERE Email = %s", (email,))
    existing_user = cursor.fetchone()

    if existing_user:
        cursor.close()
        conn.close()
        return jsonify({"status": "error", "message": "Email already exists"}), 400

    # Insert using the new hashed_password
    query = """
        INSERT INTO system_user (Username, Name, Email, Password_Hash, User_Type, Created_At)
        VALUES (%s, %s, %s, %s, 'client', NOW())
    """
    try:
        cursor.execute(query, (username, name, email, hashed_password))
        conn.commit()
        
        cursor.close()
        conn.close()
        return jsonify({"status": "success", "message": "Account created successfully"}), 201
        
    except Exception as e:
        print(f"Signup error: {e}")
        return jsonify({"status": "error", "message": "Database error"}), 500
    
    # ==========================================
# 1. ADMIN OVERRIDE: Force Reset a User's Password
# ==========================================
@auth_bp.route("/admin/reset-password", methods=["POST"])
def admin_reset_password():
    data = request.json
    target_user_id = data.get("target_user_id")
    
    if not target_user_id:
        return jsonify({"status": "error", "message": "Missing User ID"}), 400

    # The temporary password the Admin will give to the user
    temp_password = "Password2026!"
    
    # Encrypt the temporary password
    hashed_temp = generate_password_hash(temp_password)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Overwrite their old forgotten password with the new temporary hash
        cursor.execute("UPDATE system_user SET Password_Hash = %s WHERE User_ID = %s", (hashed_temp, target_user_id))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "status": "success", 
            "message": f"Password successfully reset to: {temp_password}"
        }), 200
        
    except Exception as e:
        print(f"Admin Reset Error: {e}")
        return jsonify({"status": "error", "message": "Database error"}), 500


# ==========================================
# 2. USER UPDATE: Customer/Staff changes their own password
# ==========================================
@auth_bp.route("/user/change-password", methods=["POST"])
def change_password():
    data = request.json
    user_id = data.get("user_id")
    old_password = data.get("old_password")
    new_password = data.get("new_password")

    # Strict password validation for the new password
    import re
    if len(new_password) < 8 or not re.search(r"[A-Z]", new_password) or not re.search(r"[a-z]", new_password) or not re.search(r"\d", new_password) or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", new_password):
        return jsonify({"status": "error", "message": "New password does not meet security requirements."}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. Verify their old password first
        cursor.execute("SELECT Password_Hash FROM system_user WHERE User_ID = %s", (user_id,))
        user = cursor.fetchone()

        if not user or not check_password_hash(user["Password_Hash"], old_password):
            cursor.close()
            conn.close()
            return jsonify({"status": "error", "message": "Incorrect current password"}), 401

        # 2. Hash the new password and update the database
        hashed_new = generate_password_hash(new_password)
        cursor.execute("UPDATE system_user SET Password_Hash = %s WHERE User_ID = %s", (hashed_new, user_id))
        conn.commit()

        cursor.close()
        conn.close()
        return jsonify({"status": "success", "message": "Password updated securely!"}), 200

    except Exception as e:
        print(f"Change Password Error: {e}")
        return jsonify({"status": "error", "message": "Database error"}), 500

# ==========================================
# 3. ADMIN TOOL: Get all staff members
# ==========================================
@auth_bp.route("/admin/users", methods=["GET"])
def get_all_staff():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # THE FIX: Added Account_Status to the SELECT statement
        cursor.execute("SELECT User_ID, Name, Email, User_Type, Account_Status FROM system_user")
        users = cursor.fetchall()
        
        cursor.close()
        conn.close()
        return jsonify(users), 200
    except Exception as e:
        print(f"Error fetching users: {e}")
        return jsonify([]), 500
        
# ==========================================
# ADMIN TOOL: Hard Delete Users
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
        # Loop through the IDs and delete them from the database
        for user_id in user_ids:
            # Clean the ID just in case it came through as "STF-1001"
            clean_id = str(user_id).replace("STF-", "")
            cursor.execute("DELETE FROM system_user WHERE User_ID = %s", (clean_id,))
            
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"status": "success", "message": "Users permanently deleted"}), 200
    except Exception as e:
        print(f"Delete User Error: {e}")
        return jsonify({"status": "error", "message": "Database error"}), 500
    
@auth_bp.route("/admin/update-user", methods=["POST"])
def admin_update_user():
    data = request.json
    user_id = data.get("user_id")
    name = data.get("name")
    email = data.get("email")
    status = data.get("status") # This receives 'active', 'inactive', or 'suspended'

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # We update the Name, Email, and the Account_Status column
        query = "UPDATE system_user SET Name = %s, Email = %s, Account_Status = %s WHERE User_ID = %s"
        cursor.execute(query, (name, email, status, user_id))
        conn.commit()
        
        return jsonify({"status": "success", "message": "User updated"}), 200
    except Exception as e:
        print(f"Update Error: {e}")
        return jsonify({"status": "error", "message": "Database update failed"}), 500
    finally:
        cursor.close()
        conn.close()