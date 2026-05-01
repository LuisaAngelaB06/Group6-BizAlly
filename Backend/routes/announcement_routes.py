from flask import Blueprint, request, jsonify
from database import get_connection


announcement_bp = Blueprint("announcements", __name__)


# 1. ADMIN: Create a new announcement (UPDATED to include Priority)
@announcement_bp.route("/admin/announcements", methods=["POST"])
def create_announcement():
    data = request.json
    # ... other fields ...
    expiry = data.get("expiry_date") # Get expiry from JSON


    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = """INSERT INTO announcements (Title, Message, Priority, Target_Role, Expiry_Date, Created_By)
                   VALUES (%s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (data['title'], data['message'], data['priority'], data['target'], expiry, data['admin_id']))
        conn.commit()
        return jsonify({"status": "success"}), 201
    except Exception as e:
        print(f"Error creating announcement: {e}")
        return jsonify({"status": "error", "message": "Database error"}), 500
    finally:
        cursor.close()
        conn.close()


# 2. NEW: Update Announcement Route
@announcement_bp.route("/admin/announcements/update", methods=["POST"])
def update_announcement():
    data = request.json
    ann_id = data.get("announcement_id")
   
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM announcement_reads WHERE Announcement_ID = %s", (ann_id,))
        query = "UPDATE announcements SET Title=%s, Message=%s... WHERE Announcement_ID=%s"
        query = """UPDATE announcements
                   SET Title = %s, Message = %s, Priority = %s, Target_Role = %s, Expiry_Date = %s
                   WHERE Announcement_ID = %s"""
        cursor.execute(query, (data['title'], data['message'], data['priority'], data['target'], data['expiry_date'], ann_id))
        conn.commit()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# 2. ADMIN: Get ALL announcements for the management list (THE MISSING 404 ROUTE)
@announcement_bp.route("/admin/announcements/all", methods=["GET"])
def get_all_announcements_admin():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Fetch everything so the Admin can see and manage all history
        cursor.execute("SELECT * FROM announcements ORDER BY Created_At DESC")
        announcements = cursor.fetchall()
        return jsonify(announcements), 200
    except Exception as e:
        print(f"Error fetching all: {e}")
        return jsonify([]), 500
    finally:
        cursor.close()
        conn.close()


# 1. FOR THE RED DOT (Global check) - FIXED Read_ID error
@announcement_bp.route("/user/announcements/unread/<int:user_id>", methods=["GET"])
def get_unread_announcements(user_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # THE FIX: Check for r.user_id IS NULL instead of Read_ID
        query = """
            SELECT a.Announcement_ID FROM announcements a
            LEFT JOIN announcement_reads r
                ON a.Announcement_ID = r.Announcement_ID AND r.user_id = %s
            WHERE r.user_id IS NULL
            AND (a.Expiry_Date IS NULL OR a.Expiry_Date >= CURDATE())
        """
        cursor.execute(query, (user_id,))
        unread = cursor.fetchall()
        return jsonify(unread), 200
    except Exception as e:
        print(f"Unread Route Error: {e}")
        return jsonify([]), 500
    finally:
        cursor.close()
        conn.close()


# 2. FOR THE ANNOUNCEMENTS PAGE - FIXED Read_ID error
@announcement_bp.route("/user/announcements/all/<int:user_id>", methods=["GET"])
def get_all_announcements_user(user_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT
                a.Announcement_ID,
                a.Title,
                a.Message,
                a.Target_Role,
                a.Created_By,
                CAST(a.Created_At AS CHAR) AS Created_At,
                a.Priority,
                CAST(a.Expiry_Date AS CHAR) AS Expiry_Date,
                CASE
                    WHEN r.user_id IS NOT NULL THEN 1
                    ELSE 0
                END AS is_read
            FROM announcements a
            LEFT JOIN announcement_reads r
                ON a.Announcement_ID = r.Announcement_ID
                AND r.user_id = %s
            WHERE (a.Expiry_Date IS NULL OR a.Expiry_Date >= CURDATE())
            ORDER BY a.Created_At DESC
        """


        cursor.execute(query, (user_id,))
        results = cursor.fetchall()
        return jsonify(results), 200


    except Exception as e:
        print(f"All Route Error: {e}")
        return jsonify([]), 500


    finally:
        cursor.close()
        conn.close()


# 3. ALL USERS: Mark an announcement as read
@announcement_bp.route("/user/announcements/read", methods=["POST"])
def mark_as_read():
    data = request.json
    user_id = data.get("user_id")
    announcement_id = data.get("announcement_id")


    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = "INSERT IGNORE INTO announcement_reads (user_id, Announcement_ID) VALUES (%s, %s)"
        cursor.execute(query, (user_id, announcement_id))
        conn.commit()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# 3. ADMIN: Delete an announcement
@announcement_bp.route("/admin/announcements/delete", methods=["POST"])
def delete_announcement():
    data = request.json
    announcement_id = data.get("announcement_id")


    conn = get_connection()
    cursor = conn.cursor()
    try:
        # This will remove it from the database permanently
        cursor.execute("DELETE FROM announcements WHERE Announcement_ID = %s", (announcement_id,))
        conn.commit()
        return jsonify({"status": "success", "message": "Announcement deleted"}), 200
    except Exception as e:
        print(f"Delete Error: {e}")
        return jsonify({"status": "error", "message": "Database error"}), 500
    finally:
        cursor.close()
        conn.close()