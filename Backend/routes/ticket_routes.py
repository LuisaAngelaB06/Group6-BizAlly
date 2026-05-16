from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor

from Backend.database import get_connection

ticket_bp = Blueprint("tickets", __name__)

STATUS_LABELS = {
    1: "Open",
    2: "In Progress",
    3: "Resolved",
    4: "Closed",
}

DEFAULT_STATUS_ID = 1
DEFAULT_SERVICE_TYPE_ID = 1
DEFAULT_PRIORITY = "Medium"


def _json_error(message, status=500):
    return jsonify({"status": "error", "error": message, "message": message}), status


def _get_cursor():
    conn = get_connection()
    if not conn:
        return None, None
    return conn, conn.cursor(cursor_factory=RealDictCursor)


def _full_name(row, prefix):
    first_name = row.get(f"{prefix}_first_name") or ""
    last_name = row.get(f"{prefix}_last_name") or ""
    full_name = f"{first_name} {last_name}".strip()
    return full_name or None


def _format_ticket(row):
    ticket = dict(row)

    requestor_name = _full_name(ticket, "requestor")
    technician_name = _full_name(ticket, "technician")

    formatted = {
        "Ticket_ID": ticket.get("ticket_id"),
        "Service_Type_ID": ticket.get("service_type_id"),
        "user_id": ticket.get("user_id"),
        "Technician_ID": ticket.get("technician_id"),
        "Status_ID": ticket.get("status_id"),
        "Status": STATUS_LABELS.get(ticket.get("status_id"), "Unknown"),
        "Concern_Title": ticket.get("concern_title") or "",
        "Description": ticket.get("description") or "",
        "Priority": ticket.get("priority") or DEFAULT_PRIORITY,
        "Product_Category": ticket.get("product_category") or "",
        "Product_Brand": ticket.get("product_brand") or "",
        "Concern_Type": ticket.get("concern_type") or "",
        "Date_Created": ticket.get("date_created"),
        "Last_Updated": ticket.get("last_updated"),
        "Resolution_Details": ticket.get("resolution_details") or "",
        "Requestor_Name": requestor_name or "User",
        "Requester_Name": requestor_name or "User",
        "Technician_Name": technician_name or "Unassigned",
        "Email": ticket.get("requestor_email") or "",
        "Requestor_Email": ticket.get("requestor_email") or "",
        "Service_Type": ticket.get("service_type") or "Support",
        "Phone": ticket.get("requestor_phone") or "N/A",
        "Address": ticket.get("requestor_address") or "N/A",
    }

    return formatted


def _ticket_select_clause(where_clause="", order_clause="ORDER BY t.date_created DESC"):
    return f"""
        SELECT
            t.ticket_id,
            t.service_type_id,
            t.user_id,
            t.technician_id,
            t.status_id,
            t.concern_title,
            t.description,
            t.date_created,
            t.last_updated,
            t.priority,
            t.product_category,
            t.product_brand,
            t.concern_type,
            t.resolution_details,
            req_user.first_name AS requestor_first_name,
            req_user.last_name AS requestor_last_name,
            req_user.email AS requestor_email,
            c.phone_number AS requestor_phone, 
            c.address AS requestor_address,       
            tech_user.first_name AS technician_first_name,
            tech_user.last_name AS technician_last_name,
            st.name AS service_type
        FROM ticket t
        LEFT JOIN technician tech ON t.technician_id = tech.technician_id
        LEFT JOIN "system_user" tech_user ON tech.user_id = tech_user.user_id
        LEFT JOIN "system_user" req_user ON t.user_id = req_user.user_id
        LEFT JOIN "customer" c ON req_user.customer_id = c.customer_id 
        LEFT JOIN service_type st ON t.service_type_id = st.service_type_id
        {where_clause}
        {order_clause}
    """

def _coerce_int(value, default=None):
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clean_priority(value):
    priority = (value or DEFAULT_PRIORITY).strip()
    known = {
        "low": "Low",
        "medium": "Medium",
        "high": "High",
        "urgent": "Urgent",
        "critical": "Critical",
    }
    return known.get(priority.lower(), priority)


@ticket_bp.route("/tickets", methods=["GET"])
def get_tickets():
    conn, cursor = _get_cursor()
    if not conn:
        return _json_error("Database connection failed")

    try:
        cursor.execute(_ticket_select_clause())
        return jsonify([_format_ticket(row) for row in cursor.fetchall()]), 200
    except Exception as e:
        print(f"Get Tickets Error: {e}")
        return _json_error("Failed to fetch tickets")
    finally:
        cursor.close()
        conn.close()


@ticket_bp.route("/tickets/<int:ticket_id>", methods=["GET"])
def get_ticket(ticket_id):
    conn, cursor = _get_cursor()
    if not conn:
        return _json_error("Database connection failed")

    try:
        cursor.execute(_ticket_select_clause("WHERE t.ticket_id = %s", ""), (ticket_id,))
        ticket = cursor.fetchone()
        if not ticket:
            return _json_error("Ticket not found", 404)
        return jsonify(_format_ticket(ticket)), 200
    except Exception as e:
        print(f"Get Ticket Error: {e}")
        return _json_error("Failed to fetch ticket")
    finally:
        cursor.close()
        conn.close()


@ticket_bp.route("/tickets", methods=["POST"])
def create_ticket():
    data = request.get_json(silent=True) or {}
    concern_title = (data.get("Concern_Title") or data.get("title") or "").strip()
    description = (data.get("Description") or data.get("description") or "").strip()
    product_category = (data.get("Category") or data.get("Product_Category") or data.get("product_category") or "").strip()
    product_brand = (data.get("Product_Brand") or data.get("product_brand") or "").strip()
    concern_type = (data.get("Concern_Type") or data.get("concern_type") or "").strip()
    user_id = _coerce_int(data.get("user_id"))

    if not user_id:
        return _json_error("Missing user_id", 400)
    if not concern_title:
        return _json_error("Ticket subject is required", 400)
    if not description:
        return _json_error("Ticket description is required", 400)

    conn, cursor = _get_cursor()
    if not conn:
        return _json_error("Database connection failed")

    try:
        cursor.execute(
            """
            INSERT INTO ticket
                (service_type_id, user_id, technician_id, status_id,
                 concern_title, description, date_created, last_updated, priority,
                 product_category, product_brand, concern_type)
            VALUES (%s, %s, NULL, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, %s,
                    %s, %s, %s)
            RETURNING ticket_id
            """,
            (
                _coerce_int(data.get("Service_Type_ID"), DEFAULT_SERVICE_TYPE_ID),
                user_id,
                _coerce_int(data.get("Status_ID"), DEFAULT_STATUS_ID),
                concern_title,
                description,
                _clean_priority(data.get("Priority")),
                product_category or None,
                product_brand or None,
                concern_type or None,
            ),
        )
        ticket_id = cursor.fetchone()["ticket_id"]
        conn.commit()
        return jsonify({
            "status": "success",
            "message": "Ticket created successfully",
            "Ticket_ID": ticket_id,
        }), 201
    except Exception as e:
        conn.rollback()
        print(f"Create Ticket Error: {e}")
        return _json_error("Failed to create ticket")
    finally:
        cursor.close()
        conn.close()


@ticket_bp.route("/tickets/<int:ticket_id>", methods=["DELETE"])
def delete_ticket(ticket_id):
    conn, cursor = _get_cursor()
    if not conn:
        return _json_error("Database connection failed")

    try:
        cursor.execute("DELETE FROM ticket WHERE ticket_id = %s RETURNING ticket_id", (ticket_id,))
        deleted = cursor.fetchone()
        conn.commit()
        if not deleted:
            return _json_error("Ticket not found", 404)
        return jsonify({"status": "success", "message": "Ticket deleted successfully"}), 200
    except Exception as e:
        conn.rollback()
        print(f"Delete Ticket Error: {e}")
        return _json_error("Failed to delete ticket")
    finally:
        cursor.close()
        conn.close()


@ticket_bp.route("/tickets/user/<int:user_id>", methods=["GET"])
def get_user_tickets(user_id):
    conn, cursor = _get_cursor()
    if not conn:
        return _json_error("Database connection failed")

    try:
        cursor.execute(_ticket_select_clause("WHERE t.user_id = %s"), (user_id,))
        return jsonify([_format_ticket(row) for row in cursor.fetchall()]), 200
    except Exception as e:
        print(f"User Tickets Error: {e}")
        return _json_error("Failed to fetch user tickets")
    finally:
        cursor.close()
        conn.close()


@ticket_bp.route("/technicians", methods=["GET"])
def get_technicians():
    conn, cursor = _get_cursor()
    if not conn:
        return _json_error("Database connection failed")

    try:
        cursor.execute("""
            SELECT
                tech.technician_id,
                CONCAT_WS(' ', su.first_name, su.last_name) AS name,
                su.email
            FROM technician tech
            JOIN "system_user" su ON tech.user_id = su.user_id
            ORDER BY su.first_name, su.last_name
        """)
        technicians = [
            {
                "Technician_ID": row["technician_id"],
                "Name": row["name"] or row["email"] or "Technician",
                "Email": row["email"] or "",
            }
            for row in cursor.fetchall()
        ]
        return jsonify(technicians), 200
    except Exception as e:
        print(f"Technicians Error: {e}")
        return _json_error("Failed to fetch technicians")
    finally:
        cursor.close()
        conn.close()


@ticket_bp.route("/tickets/<int:ticket_id>", methods=["PUT", "PATCH"])
def update_ticket(ticket_id):
    data = request.get_json(silent=True) or {}
    status_id = _coerce_int(data.get("Status_ID"))
    technician_id = _coerce_int(data.get("Technician_ID"))
    priority = _clean_priority(data.get("Priority"))
    resolution_details = data.get("Resolution_Details") or ""

    if status_id not in STATUS_LABELS:
        return _json_error("Invalid ticket status", 400)

    conn, cursor = _get_cursor()
    if not conn:
        return _json_error("Database connection failed")

    try:
        cursor.execute(
            """
            UPDATE ticket
            SET status_id = %s,
                priority = %s,
                technician_id = %s,
                resolution_details = %s,
                product_category = COALESCE(%s, product_category),
                product_brand = COALESCE(%s, product_brand),
                concern_type = COALESCE(%s, concern_type),
                last_updated = CURRENT_TIMESTAMP
            WHERE ticket_id = %s
            RETURNING ticket_id
            """,
            (
                status_id,
                priority,
                technician_id,
                resolution_details,
                (data.get("Category") or data.get("Product_Category") or data.get("product_category") or None),
                (data.get("Product_Brand") or data.get("product_brand") or None),
                (data.get("Concern_Type") or data.get("concern_type") or None),
                ticket_id,
            ),
        )
        updated = cursor.fetchone()
        conn.commit()
        if not updated:
            return _json_error("Ticket not found", 404)
        return jsonify({"status": "success", "message": "Ticket updated successfully"}), 200
    except Exception as e:
        conn.rollback()
        print(f"Update Ticket Error: {e}")
        return _json_error("Failed to update ticket")
    finally:
        cursor.close()
        conn.close()


@ticket_bp.route("/tickets/analytics", methods=["GET"])
def get_analytics():
    conn, cursor = _get_cursor()
    if not conn:
        return _json_error("Database connection failed")

    try:
        cursor.execute("SELECT COUNT(*) AS total FROM ticket")
        total_tickets = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS resolved FROM ticket WHERE status_id IN (3, 4)")
        resolved_tickets = cursor.fetchone()["resolved"]

        cursor.execute("""
            SELECT COALESCE(st.name, 'Support') AS category, COUNT(t.ticket_id) AS count
            FROM ticket t
            LEFT JOIN service_type st ON t.service_type_id = st.service_type_id
            GROUP BY COALESCE(st.name, 'Support')
            ORDER BY category
        """)
        categories = cursor.fetchall()

        cursor.execute("""
            SELECT COALESCE(priority, %s) AS priority, COUNT(*) AS count
            FROM ticket
            GROUP BY COALESCE(priority, %s)
            ORDER BY priority
        """, (DEFAULT_PRIORITY, DEFAULT_PRIORITY))
        priorities = cursor.fetchall()

        cursor.execute("""
            SELECT status_id, COUNT(*) AS count
            FROM ticket
            GROUP BY status_id
            ORDER BY status_id
        """)
        statuses = cursor.fetchall()

        cursor.execute("""
            SELECT COALESCE(NULLIF(product_category, ''), 'Uncategorized') AS category,
                   COUNT(*) AS count
            FROM ticket
            GROUP BY COALESCE(NULLIF(product_category, ''), 'Uncategorized')
            ORDER BY count DESC, category
        """)
        product_categories = cursor.fetchall()

        cursor.execute("""
            SELECT COALESCE(NULLIF(product_brand, ''), 'Unknown') AS brand,
                   COUNT(*) AS count
            FROM ticket
            GROUP BY COALESCE(NULLIF(product_brand, ''), 'Unknown')
            ORDER BY count DESC, brand
        """)
        product_brands = cursor.fetchall()

        cursor.execute("""
            SELECT COALESCE(NULLIF(concern_type, ''), 'Other') AS concern,
                   COUNT(*) AS count
            FROM ticket
            GROUP BY COALESCE(NULLIF(concern_type, ''), 'Other')
            ORDER BY count DESC, concern
        """)
        concern_types = cursor.fetchall()

        return jsonify({
            "total": total_tickets,
            "resolved": resolved_tickets,
            "open": sum(row["count"] for row in statuses if row["status_id"] == 1),
            "in_progress": sum(row["count"] for row in statuses if row["status_id"] == 2),
            "closed": sum(row["count"] for row in statuses if row["status_id"] == 4),
            "categories": {row["category"]: row["count"] for row in categories},
            "priorities": {row["priority"]: row["count"] for row in priorities},
            "product_categories": {
                row["category"]: row["count"] for row in product_categories
            },
            "product_brands": {
                row["brand"]: row["count"] for row in product_brands
            },
            "concern_types": {
                row["concern"]: row["count"] for row in concern_types
            },
            "statuses": {
                STATUS_LABELS.get(row["status_id"], "Unknown"): row["count"]
                for row in statuses
            },
        }), 200
    except Exception as e:
        print(f"Analytics Error: {e}")
        return _json_error("Failed to fetch analytics")
    finally:
        cursor.close()
        conn.close()


@ticket_bp.route('/api/feedback/submit', methods=['POST'])
def submit_anonymous_feedback():
    data = request.get_json()
    
    # 🌟 The Fix: Only require the rating. 
    # Don't use data['key'] because it throws a 400 if missing.
    rating = data.get('rating') 
    context = data.get('context', 'quickfix-two') # To know which fix they used

    if not rating:
        return jsonify({"error": "Rating is required"}), 400

    # Save to your PostgreSQL table (ensure columns allow NULL for user_id/ticket_id)
    try:
        # Example SQL logic:
        # "INSERT INTO feedback (rating, context, created_at) VALUES (%s, %s, NOW())"
        return jsonify({"status": "success", "message": "Feedback received anonymously"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500