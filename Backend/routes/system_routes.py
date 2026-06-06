from flask import Blueprint, request, jsonify
from Backend.database import get_connection
from Backend.routes.rbac import get_current_user, role_required
from Backend.routes.utils import log_system_event

system_bp = Blueprint("system", __name__)

# =========================
# GET SYSTEM SETTINGS
# =========================
@system_bp.route("/admin/settings", methods=["GET"])
@role_required("admin")
def get_settings():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT setting_key, setting_value FROM system_settings")
        settings = {row[0]: row[1] for row in cursor.fetchall()}
        return jsonify(settings), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# =========================
# UPDATE MAINTENANCE MODE
# =========================
@system_bp.route("/admin/settings/maintenance", methods=["POST"])
@role_required("admin")
def toggle_maintenance():
    data = request.get_json()
    # Expecting a boolean or string like "true"/"false"
    is_active = str(data.get("maintenance_mode", "false")).lower()
    
    current_user = get_current_user()
    user_id = current_user.get("user_id") if current_user else "System"

    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 🌟 FIXED: Upsert guarantees it works even on a fresh database!
        cursor.execute(
            """
            INSERT INTO system_settings (setting_key, setting_value, last_updated) 
            VALUES ('maintenance_mode', %s, CURRENT_TIMESTAMP)
            ON CONFLICT (setting_key) DO UPDATE 
            SET setting_value = EXCLUDED.setting_value, last_updated = CURRENT_TIMESTAMP
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
                log_level="CRITICAL", # 🚨 System is down!
                description="Administrator activated system-wide Maintenance Mode."
            )
        else:
            log_system_event(
                user_identifier=str(user_id),
                category="System Settings",
                action="Maintenance Mode Disabled",
                log_level="INFO", # ✅ System is back normal
                description="Administrator deactivated Maintenance Mode."
            )

        return jsonify({"status": "success", "message": f"Maintenance mode set to {is_active}"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()