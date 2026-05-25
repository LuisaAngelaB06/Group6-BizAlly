import re

from flask import Blueprint, jsonify, request

from Backend.database import get_connection
from Backend.mailer import send_contact_notification

contact_bp = Blueprint("contact", __name__)

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _json_error(message, status=400):
    return jsonify({"status": "error", "message": message, "error": message}), status


@contact_bp.route("/contact-messages", methods=["POST"])
def create_contact_message():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    subject = (data.get("subject") or "").strip()
    message = (data.get("message") or "").strip()

    if not name or not email or not subject or not message:
        return _json_error("Name, email, subject, and message are required", 400)

    if not EMAIL_RE.match(email):
        return _json_error("Please enter a valid email address", 400)

    conn = get_connection()
    if not conn:
        return _json_error("Database connection failed", 500)

    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO contact_messages
                (name, email, subject, message, status, source, created_at)
            VALUES
                (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING id
            """,
            (name, email, subject, message, "new", "contact-us"),
        )
        contact_message_id = cursor.fetchone()[0]
        conn.commit()
        try:
            send_contact_notification({
                "name": name,
                "email": email,
                "subject": subject,
                "message": message,
            })
        except Exception as e:
            print(f"Contact Email Notification Error: {e}")
            return _json_error("Message saved, but email notification failed", 500)
        return jsonify({
            "status": "success",
            "message": "Message sent successfully",
            "id": str(contact_message_id),
        }), 201
    except Exception as e:
        conn.rollback()
        print(f"Create Contact Message Error: {e}")
        return _json_error("Failed to send message", 500)
    finally:
        cursor.close()
        conn.close()
