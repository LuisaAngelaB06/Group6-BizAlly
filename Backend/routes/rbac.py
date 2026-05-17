from functools import wraps

from flask import g, jsonify, request
from psycopg2.extras import RealDictCursor

from Backend.database import get_connection


def _normalize_role(role):
    return str(role or "").strip().lower()


def _coerce_int(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def get_current_user():
    if hasattr(g, "current_user"):
        return g.current_user

    user_id = _coerce_int(request.headers.get("X-User-ID"))
    if not user_id:
        g.current_user = None
        return None

    conn = get_connection()
    if not conn:
        g.current_user = None
        return None

    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(
            """
            SELECT
                su.user_id,
                LOWER(su.user_type) AS user_type,
                t.technician_id
            FROM "system_user" su
            LEFT JOIN technician t ON t.user_id = su.user_id
            WHERE su.user_id = %s
            LIMIT 1
            """,
            (user_id,),
        )
        user = cursor.fetchone()
        if not user:
            g.current_user = None
            return None

        g.current_user = {
            "user_id": user["user_id"],
            "user_type": _normalize_role(user["user_type"]),
            "technician_id": user.get("technician_id"),
        }
        return g.current_user
    finally:
        cursor.close()
        conn.close()


def role_required(*roles):
    allowed_roles = {_normalize_role(role) for role in roles}

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"status": "error", "message": "Authentication required"}), 401

            if user["user_type"] not in allowed_roles:
                return jsonify({"status": "error", "message": "Forbidden"}), 403

            return view_func(*args, **kwargs)

        return wrapper

    return decorator


def is_admin(user=None):
    user = user or get_current_user()
    return bool(user and user.get("user_type") == "admin")


def is_technician(user=None):
    user = user or get_current_user()
    return bool(user and user.get("user_type") == "technician")
