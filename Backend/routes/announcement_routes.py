from flask import Blueprint, request, jsonify
from Backend.database import get_connection
from psycopg2.extras import RealDictCursor
from Backend.socketio_instance import socketio
from Backend.routes.rbac import get_current_user, role_required

announcement_bp = Blueprint("announcements", __name__)

VALID_TARGET_AUDIENCES = {"user", "technician", "all"}


def _normalize_target_audience(value):
    audience = str(value or "all").strip().lower()
    return audience if audience in VALID_TARGET_AUDIENCES else "all"


def _ensure_target_audience_column(cursor):
    cursor.execute("""
        ALTER TABLE announcements
        ADD COLUMN IF NOT EXISTS target_audience VARCHAR(20) NOT NULL DEFAULT 'all'
    """)

# =========================
# CREATE ANNOUNCEMENT
# =========================
@announcement_bp.route("/admin/announcements", methods=["POST"])
@role_required("admin")
def create_announcement():
    data = request.json
    target_audience = _normalize_target_audience(data.get("target_audience"))

    conn = get_connection()
    cursor = conn.cursor()

    try:
        _ensure_target_audience_column(cursor)
        query = """
            INSERT INTO announcements
            (title, message, priority, expiry_date, created_by, target_audience, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, timezone('Asia/Manila', now()))
        """

        cursor.execute(query, (
            data.get("title"),
            data.get("message"),
            data.get("priority", "normal"),
            data.get("expiry_date"),
            data.get("admin_id"),
            target_audience
        ))

        conn.commit()
        socketio.emit("new_announcement", {
            "status": "created",
            "target_audience": target_audience
        })
        return jsonify({"status": "success"}), 201
    

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# =========================
# UPDATE ANNOUNCEMENT
# =========================
@announcement_bp.route("/admin/announcements/update", methods=["POST"])
@role_required("admin")
def update_announcement():
    data = request.json
    ann_id = data.get("announcement_id")
    target_audience = _normalize_target_audience(data.get("target_audience"))

    conn = get_connection()
    cursor = conn.cursor()

    try:
        _ensure_target_audience_column(cursor)
        # Reset read status
        cursor.execute(
            "DELETE FROM announcement_reads WHERE announcement_id = %s",
            (ann_id,)
        )

        query = """
            UPDATE announcements
            SET title = %s,
                message = %s,
                priority = %s,
                expiry_date = %s,
                target_audience = %s
            WHERE announcement_id = %s
        """

        cursor.execute(query, (
            data.get("title"),
            data.get("message"),
            data.get("priority", "normal"),
            data.get("expiry_date"),
            target_audience,
            ann_id
        ))

        conn.commit()
        socketio.emit("announcement_updated", {
            "status": "updated",
            "target_audience": target_audience
        })
        return jsonify({"status": "success"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# =========================
# GET ALL (ADMIN)
# =========================
@announcement_bp.route("/admin/announcements/all", methods=["GET"])
@role_required("admin", "technician")
def get_all_announcements_admin():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        _ensure_target_audience_column(cursor)
        conn.commit()
        current_user = get_current_user()
        where_clause = ""
        params = ()
        if current_user and current_user.get("user_type") == "technician":
            where_clause = "WHERE COALESCE(target_audience, 'all') IN ('technician', 'all')"

        cursor.execute("""
            SELECT
                announcement_id,
                title,
                message,
                priority,
                expiry_date,
                created_by,
                COALESCE(target_audience, 'all') AS target_audience,
                TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') AS created_at
            FROM announcements
            {where_clause}
            ORDER BY created_at DESC
        """.format(where_clause=where_clause), params)

        return jsonify(cursor.fetchall()), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# =========================
# GET UNREAD (RED DOT)
# =========================
@announcement_bp.route("/user/announcements/unread/<int:user_id>", methods=["GET"])
def get_unread_announcements(user_id):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        _ensure_target_audience_column(cursor)
        conn.commit()
        cursor.execute("""
            SELECT a.announcement_id
            FROM announcements a
            LEFT JOIN announcement_reads r
                ON a.announcement_id = r.announcement_id
                AND r.user_id = %s
            WHERE r.user_id IS NULL
            AND (a.expiry_date IS NULL OR a.expiry_date >= CURRENT_DATE)
            AND COALESCE(a.target_audience, 'all') IN ('user', 'all')
        """, (user_id,))

        return jsonify(cursor.fetchall()), 200

    except Exception:
        return jsonify([]), 500

    finally:
        cursor.close()
        conn.close()


# =========================
# GET ALL (USER)
# =========================
@announcement_bp.route("/user/announcements/all/<int:user_id>", methods=["GET"])
def get_all_announcements_user(user_id):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        _ensure_target_audience_column(cursor)
        conn.commit()
        cursor.execute("""
            SELECT
                a.announcement_id,
                a.title,
                a.message,
                a.created_by,
                TO_CHAR(a.created_at, 'YYYY-MM-DD HH24:MI:SS') AS created_at,
                a.priority,
                COALESCE(a.target_audience, 'all') AS target_audience,
                TO_CHAR(a.expiry_date, 'YYYY-MM-DD') AS expiry_date,
                CASE WHEN r.user_id IS NOT NULL THEN 1 ELSE 0 END AS is_read
            FROM announcements a
            LEFT JOIN announcement_reads r
                ON a.announcement_id = r.announcement_id
                AND r.user_id = %s
            WHERE (a.expiry_date IS NULL OR a.expiry_date >= CURRENT_DATE)
            AND COALESCE(a.target_audience, 'all') IN ('user', 'all')
            ORDER BY a.created_at DESC
        """, (user_id,))

        return jsonify(cursor.fetchall()), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# =========================
# MARK AS READ
# =========================
@announcement_bp.route("/user/announcements/read", methods=["POST"])
def mark_as_read():
    data = request.get_json()

    user_id = data.get('user_id')
    announcement_id = data.get('announcement_id')


    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO announcement_reads (user_id, announcement_id)
            VALUES (%s, %s)
            ON CONFLICT (user_id, announcement_id) DO NOTHING
        """, (data.get("user_id"), data.get("announcement_id")))

        conn.commit()
        return jsonify({"status": "success"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()

# =========================
# DELETE ANNOUNCEMENT
# =========================
@announcement_bp.route("/admin/announcements/delete", methods=["POST"])
@role_required("admin")
def delete_announcement():
    data = request.json
    ann_id = data.get("announcement_id")

    if not ann_id:
        return jsonify({"status": "error", "message": "Missing announcement_id"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM announcements WHERE announcement_id = %s", (ann_id,))
        conn.commit()

        socketio.emit("announcement_deleted", {
            "status": "deleted",
            "announcement_id": ann_id
        })

        return jsonify({"status": "success"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()
