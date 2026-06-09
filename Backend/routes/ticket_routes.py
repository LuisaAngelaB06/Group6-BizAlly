from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor
from Backend.extensions import db
from sqlalchemy import text
from Backend.database import get_connection
from Backend.routes.rbac import get_current_user, is_admin, is_technician, role_required
from Backend.socketio_instance import socketio
from Backend.routes.utils import log_system_event

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
@role_required("admin", "technician")
def get_tickets():
    current_user = get_current_user()
    conn, cursor = _get_cursor()
    if not conn:
        return _json_error("Database connection failed")

    try:
        if is_technician(current_user):
            if not current_user.get("technician_id"):
                return jsonify([]), 200
            cursor.execute(
                _ticket_select_clause("WHERE t.technician_id = %s"),
                (current_user["technician_id"],),
            )
        else:
            cursor.execute(_ticket_select_clause())
        return jsonify([_format_ticket(row) for row in cursor.fetchall()]), 200
    except Exception as e:
        print(f"Get Tickets Error: {e}")
        return _json_error("Failed to fetch tickets")
    finally:
        cursor.close()
        conn.close()


@ticket_bp.route("/tickets/<int:ticket_id>", methods=["GET"])
@role_required("admin", "technician")
def get_ticket(ticket_id):
    current_user = get_current_user()
    conn, cursor = _get_cursor()
    if not conn:
        return _json_error("Database connection failed")

    try:
        if is_technician(current_user):
            cursor.execute(
                _ticket_select_clause("WHERE t.ticket_id = %s AND t.technician_id = %s", ""),
                (ticket_id, current_user.get("technician_id")),
            )
        else:
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
        # 1. Insert the ticket first
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
        
        # 🌟 COMMIT 1: Save the ticket safely to the database immediately
        conn.commit()

        import re
        clean_sentence_title = re.sub(r'^\[.*?\]\s*', '', concern_title)

        # 🌟 TRIGGER 1: CLIENT ALERT
        try:
            from Backend.routes.utils import send_allitrack_alert
            client_msg = f"Your ticket #{ticket_id} regarding \"{clean_sentence_title}\" has been successfully logged. An IT administrator will review and assign a technician shortly."
            send_allitrack_alert(user_id, 'Ticket Successfully Submitted', client_msg, 'ticket-update', ticket_id, 'Open')
        except Exception as client_err:
            print(f"Submitting client notification generation failure: {client_err}")

        # 🌟 TRIGGER 2: ADMIN BROADCAST ALERTS (Guaranteed Delivery)
        try:
            from Backend.routes.utils import send_allitrack_alert
            
            cursor.execute("""SELECT * FROM "system_user" WHERE LOWER(user_type) LIKE '%admin%'""")
            admin_rows = cursor.fetchall()
            
            admin_msg = f"A new support ticket has been submitted: Ticket #{ticket_id} - \"{clean_sentence_title}\". Please review priority values and assign a technician."
            
            for admin_row in admin_rows:
                admin_user_id = admin_row.get("system_user_id") or admin_row.get("id") or admin_row.get("user_id")
                
                if admin_user_id:
                    # 🌟 UNCONDITIONAL DELIVERY: All Admins receive this alert!
                    send_allitrack_alert(admin_user_id, 'New Ticket Filed', admin_msg, 'ticket-update', ticket_id, 'Open')
                    
        except Exception as admin_alert_err:
            print(f"System admin broadcast routing error: {admin_alert_err}")

        # 🌟 SYNC CATEGORIES: FIXED THE VARCHAR vs INTEGER MISMATCH
        try:
            cursor.execute(
                """
                UPDATE notifications 
                SET product_category = %s, product_brand = %s, concern_type = %s
                WHERE ticket_id::varchar = %s
                """,
                (
                    product_category or None, 
                    product_brand or None, 
                    concern_type or None, 
                    str(ticket_id) # 🌟 explicitly converted to string
                )
            )
            conn.commit()
        except Exception as sync_err:
            conn.rollback()
            print(f"Category Sync Error: {sync_err}")

       # 🌟 TRIGGER 3: WEBSOCKETS
        try:
            socketio.emit("ticket_updated", {"ticket_id": ticket_id})
            socketio.emit("ticket_created", {"ticket_id": ticket_id})
        except Exception as ws_err:
            print(f"WebSocket live emission failure: {ws_err}")

        # 🌟 1. Grab the user's first name from the database
        user_name = f"User #{user_id}" # Fallback just in case
        try:
            # Note: Adjust 'user_id' if your system_user table calls it 'id' or 'system_user_id'
            cursor.execute('SELECT first_name FROM "system_user" WHERE user_id = %s', (user_id,))
            user_row = cursor.fetchone()
            if user_row and "first_name" in user_row:
                user_name = user_row["first_name"]
        except Exception as name_err:
            print(f"Could not fetch user name: {name_err}")

        # 🌟 2. Call the logger using the name we just found!
        log_system_event(
            user_identifier=str(user_id),  
            category="Ticket Management",  # 🌟 NEW
            action="Ticket Creation",
            log_level="INFO",
            description=f"Successfully created ticket #{ticket_id}"
        )

        return jsonify({
            "status": "success",
            "message": "Ticket created successfully",
            "Ticket_ID": ticket_id,
        }), 201

    # 🌟 MERGED ERROR HANDLING: Safely catches the error, rolls back, and logs it.
    except Exception as e:
        conn.rollback()
        print(f"Create Ticket Error: {e}")
        
        log_system_event(
            user_identifier=str(user_id) if 'user_id' in locals() else "System",
            action="Ticket Creation Failed",
            log_level="ERROR",
            description=str(e),
            status="Failed"
        )
        
        return _json_error("Failed to create ticket")
        
    finally:
        cursor.close()
        conn.close()

@ticket_bp.route("/tickets/<int:ticket_id>", methods=["DELETE"])
@role_required("admin")
def delete_ticket(ticket_id):
    conn, cursor = _get_cursor()
    if not conn:
        return _json_error("Database connection failed")

    try:
        cursor.execute("DELETE FROM ticket WHERE ticket_id = %s RETURNING ticket_id", (ticket_id,))
        deleted = cursor.fetchone()
        
        if not deleted:
            return _json_error("Ticket not found", 404)
            
        conn.commit()

        # 🌟 LOG IT: Record the permanent deletion of a ticket
        from flask import g
        current_user = getattr(g, "current_user", None) or get_current_user()
        admin_id = current_user.get("user_id") if current_user else "System"

        log_system_event(
            user_identifier=str(admin_id),
            category="Ticket Management",
            action="Ticket Deleted",
            log_level="CRITICAL",
            description=f"Administrator permanently deleted Ticket #{ticket_id} from the database."
        )

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
@role_required("admin")
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
@role_required("admin", "technician")
def update_ticket(ticket_id):
    data = request.get_json(silent=True) or {}
    current_user = get_current_user()
    status_id = _coerce_int(data.get("Status_ID"))
    technician_id = _coerce_int(data.get("Technician_ID"))
    priority = _clean_priority(data.get("Priority"))
    resolution_details = data.get("Resolution_Details") or ""

    if status_id not in STATUS_LABELS:
        return _json_error("Invalid ticket status", 400)

    if is_technician(current_user) and not current_user.get("technician_id"):
        return _json_error("Technician profile not found", 403)

    conn, cursor = _get_cursor()
    if not conn:
        return _json_error("Database connection failed")

    try:
        cursor.execute("SELECT user_id, concern_title, status_id, technician_id, priority, resolution_details FROM ticket WHERE ticket_id = %s", (ticket_id,))
        ticket_meta = cursor.fetchone()
        
        old_status_id = ticket_meta.get("status_id") if ticket_meta else None
        old_technician_id = ticket_meta.get("technician_id") if ticket_meta else None
        old_priority = ticket_meta.get("priority") if ticket_meta else None
        old_resolution = ticket_meta.get("resolution_details") if ticket_meta else None

        # 🌟 NEW: The Admin Lockout!
        if old_status_id == 4:
            return _json_error("This ticket has been cancelled by the client and can no longer be modified.", 403)

        # 2. CORE UPDATE: Apply modifications based on user role
        if is_technician(current_user):
            cursor.execute(
                """
                UPDATE ticket
                SET status_id = %s,
                    resolution_details = %s,
                    last_updated = CURRENT_TIMESTAMP
                WHERE ticket_id = %s
                  AND technician_id = %s
                RETURNING ticket_id, technician_id
                """,
                (
                    status_id,
                    resolution_details,
                    ticket_id,
                    current_user["technician_id"],
                ),
            )
        else:
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
                RETURNING ticket_id, technician_id
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
        
        if not updated:
            return _json_error("Ticket not found", 404)

        # 3. CATEGORY SYNC: Ensure frontend badges get updated metadata
        cursor.execute(
            """
            UPDATE notifications n
            SET product_category = t.product_category,
                product_brand = t.product_brand,
                concern_type = t.concern_type
            FROM ticket t
            WHERE n.ticket_id::varchar = t.ticket_id::varchar
              AND n.ticket_id::varchar = %s
            """,
            (str(ticket_id),)
        )

        # 🌟 ARCHITECTURE FIX: Commit the ticket FIRST before handling notifications!
        conn.commit()

        # ==========================================
        # 🌟 NEW: SMART AUDIT LOGGING ENGINE
        # Compares old vs new data to log exact actions
        # ==========================================
        try:
            from Backend.routes.utils import log_system_event
            current_user_id = current_user.get("user_id") or "System"

            # 1. Check for Status Changes
            if status_id and str(status_id) != str(old_status_id):
                status_text = STATUS_LABELS.get(status_id, str(status_id))
                
                action_name = "Ticket Status Changed"
                if "resolved" in status_text.lower():
                    action_name = "Ticket Resolved"
                elif "closed" in status_text.lower():
                    action_name = "Ticket Closed"
                # 🌟 NEW: Added the Cancel trigger!
                elif "cancel" in status_text.lower(): 
                    action_name = "Cancel Ticket"
                    
                log_system_event(
                    user_identifier=str(current_user_id), 
                    category="Ticket Management",
                    action=action_name,
                    log_level="INFO",
                    description=f"Ticket #{ticket_id} status updated to {status_text}."
                )

            # 2. Check for Priority Changes (Admins Only usually)
            if priority and str(priority) != str(old_priority):
                log_system_event(
                    user_identifier=str(current_user_id),
                    category="Ticket Management",
                    action="Ticket Priority Updated",
                    log_level="WARNING",
                    description=f"Ticket #{ticket_id} priority changed to {priority}."
                )

            # 3. Check for Technician Assignments
            if technician_id and str(technician_id) != str(old_technician_id):
                action_name = "Ticket Reassigned" if old_technician_id else "Ticket Assigned"
                log_system_event(
                    user_identifier=str(current_user_id),
                    category="Ticket Management",
                    action=action_name,
                    log_level="INFO",
                    description=f"Ticket #{ticket_id} {action_name.lower()} to Technician ID {technician_id}."
                )

            # 4. Check for Resolution Details Updates
            if resolution_details and str(resolution_details) != str(old_resolution):
                log_system_event(
                    user_identifier=str(current_user_id),
                    category="Ticket Management",
                    action="Ticket Resolution",
                    log_level="INFO",
                    description=f"Resolution details added/updated for Ticket #{ticket_id}."
                )
                
        except Exception as log_err:
            print(f"⚠️ Failed to process smart ticket logs: {log_err}")

        # ==========================================

        # 4. NOTIFICATION ENGINE
        if ticket_meta:
            import re
            clean_sentence_title = re.sub(r'^\[.*?\]\s*', '', ticket_meta.get('concern_title', ''))
            status_text = STATUS_LABELS.get(status_id, "Updated")
            new_tech_id = updated.get("technician_id")

            # CHANNEL A: Client Notification (Only if status changed)
            if status_id != old_status_id:
                try:
                    from Backend.routes.utils import send_allitrack_alert
                    update_msg = f"The processing status for your ticket regarding \"{clean_sentence_title}\" has been changed to {status_text}."
                    send_allitrack_alert(ticket_meta["user_id"], 'Ticket Status Updated', update_msg, 'ticket-update', ticket_id, status_text)
                except Exception as client_err:
                    print(f"Client notification error: {client_err}")

            # CHANNEL B: Staff & Admin Routing
            try:
                from Backend.routes.utils import send_allitrack_alert
                
                # Case 1: Admin assigns to a new Technician
                if new_tech_id and new_tech_id != old_technician_id:
                    cursor.execute('SELECT user_id FROM technician WHERE technician_id = %s', (new_tech_id,))
                    tech_row = cursor.fetchone()
                    if tech_row and tech_row.get("user_id"):
                        assign_msg = f"You have been assigned to Ticket #{ticket_id}: \"{clean_sentence_title}\". Please review the technical details and manage its resolution state."
                        send_allitrack_alert(tech_row["user_id"], 'New Ticket Assigned to You', assign_msg, 'ticket-update', ticket_id, status_text)

                # Case 2: Admin overwrites an already-assigned ticket -> Alert the Tech
                elif old_technician_id and status_id != old_status_id:
                    if not is_technician(current_user) or current_user.get("technician_id") != old_technician_id:
                        cursor.execute('SELECT user_id FROM technician WHERE technician_id = %s', (old_technician_id,))
                        tech_row = cursor.fetchone()
                        if tech_row and tech_row.get("user_id"):
                            tech_update_msg = f"Ticket #{ticket_id} (\"{clean_sentence_title}\") assigned to you has been updated by an Administrator. Status changed to: {status_text}."
                            send_allitrack_alert(tech_row["user_id"], 'Assigned Ticket Status Updated', tech_update_msg, 'ticket-update', ticket_id, status_text)

                # Case 3: Technician updates ticket -> Broadcast to Admins
                if is_technician(current_user) and status_id != old_status_id:
                    cursor.execute("""SELECT * FROM "system_user" WHERE LOWER(user_type) LIKE '%admin%'""")
                    admin_rows = cursor.fetchall()
                    
                    tech_name = current_user.get("name") or current_user.get("Name") or "A Technician"
                    admin_update_msg = f"Ticket #{ticket_id} (\"{clean_sentence_title}\") has been updated by Technician {tech_name}. Status changed to: {status_text}."
                    
                    for admin_row in admin_rows:
                        admin_user_id = admin_row.get("system_user_id") or admin_row.get("id") or admin_row.get("user_id")
                        if admin_user_id:
                            send_allitrack_alert(admin_user_id, 'Technician Ticket Status Updated', admin_update_msg, 'ticket-update', ticket_id, status_text)

            except Exception as staff_err:
                print(f"Staff routing error: {staff_err}")

        # 5. WEBSOCKET REAL-TIME EMISSIONS
        socketio.emit("ticket_updated", {"ticket_id": updated["ticket_id"]})
        if is_admin(current_user) and "Technician_ID" in data:
            socketio.emit("ticket_assigned", {
                "ticket_id": updated["ticket_id"],
                "technician_id": updated.get("technician_id"),
            })

        return jsonify({"status": "success", "message": "Ticket updated successfully"}), 200

    except Exception as e:
        conn.rollback()
        print(f"Update Ticket Error: {e}")
        return _json_error("Failed to update ticket")
    finally:
        cursor.close()
        conn.close()


@ticket_bp.route("/tickets/analytics", methods=["GET"])
@role_required("admin")
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

@ticket_bp.route("/api/notifications/user/<int:user_id>", methods=["GET"])
@ticket_bp.route("/notifications/user/<int:user_id>", methods=["GET"])
def get_user_notifications(user_id):
    conn, cursor = _get_cursor()
    if not conn:
        return _json_error("Database connection failed")
    try:
        # 🌟 UPDATED QUERY: Left joins the ticket table to fetch sub-category classification metadata strings safely
        cursor.execute(
            """
            SELECT n.id, n.title, n.message, n.type, n.ticket_id, n.unread, n.created_at,
                   t.product_category, t.product_brand, t.concern_type
            FROM notifications n
            LEFT JOIN ticket t ON n.ticket_id = t.ticket_id::text
            WHERE n.user_id = %s 
            ORDER BY n.created_at DESC
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        notifications_list = []
        for row in rows:
            notifications_list.append({
                "id": row["id"],
                "title": row["title"],
                "message": row["message"],
                "type": row["type"],
                "ticketId": row["ticket_id"],
                "unread": row["unread"],
                "is_read": not row["unread"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                # 🌟 ADDED FIELDS: Handed off directly to the frontend response dictionary
                "product_category": row["product_category"] or "",
                "product_brand": row["product_brand"] or "",
                "concern_type": row["concern_type"] or ""
            })
        return jsonify(notifications_list), 200
    except Exception as e:
        print(f"Fetch Error: {e}")
        return _json_error("Failed to retrieve notification records")
    finally:
        cursor.close()
        conn.close()


@ticket_bp.route("/api/notifications/<int:notif_id>/read", methods=["PATCH"])
@ticket_bp.route("/notifications/<int:notif_id>/read", methods=["PATCH"])
def mark_single_notification_read(notif_id):
    conn, cursor = _get_cursor()
    if not conn:
        return _json_error("Database connection failed")
    try:
        cursor.execute("UPDATE notifications SET unread = FALSE WHERE id = %s RETURNING id", (notif_id,))
        updated = cursor.fetchone()
        conn.commit()
        if not updated:
            return _json_error("Notification not found", 404)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        conn.rollback()
        return _json_error(str(e))
    finally:
        cursor.close()
        conn.close()


@ticket_bp.route("/api/notifications/read-all", methods=["POST"])
@ticket_bp.route("/notifications/read-all", methods=["POST"])
def mark_all_notifications_read():
    user_id = request.args.get('user_id')
    if not user_id:
        return _json_error("Missing user_id parameter", 400)
    conn, cursor = _get_cursor()
    if not conn:
        return _json_error("Database connection failed")
    try:
        cursor.execute("UPDATE notifications SET unread = FALSE WHERE user_id = %s", (user_id,))
        conn.commit()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        conn.rollback()
        return _json_error(str(e))
    finally:
        cursor.close()
        conn.close()

# 🌟 FIXED DECORATOR: Uses your Blueprint and removes the manual '/api' prefix
@ticket_bp.route("/notifications/delete", methods=["POST"])
def delete_notifications():
    data = request.get_json() or {}
    notification_ids = data.get("ids", [])
    
    if not notification_ids:
        return jsonify({"status": "error", "message": "No IDs provided"}), 400
        
    conn, cursor = _get_cursor()
    if not conn:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500
        
    try:
        placeholders = ', '.join(['%s'] * len(notification_ids))
        query = f"DELETE FROM notifications WHERE id IN ({placeholders})"
        
        cursor.execute(query, tuple(notification_ids))
        conn.commit()
        
        return jsonify({
            "status": "success", 
            "message": f"Successfully deleted {len(notification_ids)} notifications"
        }), 200
        
    except Exception as e:
        conn.rollback()
        print(f"Delete Notifications Error: {e}")
        return jsonify({"status": "error", "message": "Failed to delete notifications"}), 500
    finally:
        cursor.close()
        conn.close()

@ticket_bp.route('/system-logs', methods=['GET'], strict_slashes=False)
def get_system_logs():

    try:
        # JOIN matches both regular users (by user_id) and Google users (by email)
        query = text("""
            SELECT 
                sl.*, 
                su.user_id,
                su.first_name, 
                su.last_name, 
                su.user_type
            FROM system_logs sl
            LEFT JOIN "system_user" su 
                ON sl.user_identifier = su.user_id::varchar
                OR sl.user_identifier = su.email
            ORDER BY sl.created_at DESC
        """)

        result = db.session.execute(query)
        logs = []

        for row in result:
            log_data = dict(row._mapping)
            
            # Extract joined user data safely
            db_first_name = log_data.get('first_name')
            user_type = str(log_data.get('user_type') or '').lower()

            # 🌟 LOGIC 1: The Table Display Name
            if db_first_name:
                if 'admin' in user_type:
                    table_name = 'Admin'
                elif 'technician' in user_type:
                    table_name = 'Technician'
                else:
                    table_name = db_first_name
            else:
                # Fallback if they have no account (or if it's a raw system event)
                table_name = log_data.get('user_identifier') or 'System'

            # 🌟 LOGIC 2: The Modal Full Name
            if db_first_name:
                full_name = f"{db_first_name} {log_data.get('last_name') or ''}".strip()
            else:
                full_name = log_data.get('user_identifier') or 'System'

            log_data['table_name'] = table_name
            log_data['full_name'] = full_name
            
            logs.append(log_data)

        return jsonify(logs), 200

    except Exception as e:
        print(f"Error fetching logs: {e}")
        return jsonify({"error": "Failed to fetch system logs"}), 500

# ==========================================
# CLIENT: CANCEL TICKET
# ==========================================
@ticket_bp.route("/tickets/<int:ticket_id>/cancel", methods=["PATCH", "PUT"])
def cancel_ticket(ticket_id):
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")

    if not user_id:
        return _json_error("Unauthorized: Missing user ID", 401)

    conn, cursor = _get_cursor()
    if not conn:
        return _json_error("Database connection failed")

    try:
        # 🌟 UPGRADED PRE-QUERY: Grab title and technician for the notifications!
        cursor.execute("SELECT user_id, status_id, concern_title, technician_id FROM ticket WHERE ticket_id = %s", (ticket_id,))
        ticket_meta = cursor.fetchone()

        if not ticket_meta:
            return _json_error("Ticket not found", 404)
            
        if str(ticket_meta["user_id"]) != str(user_id):
            return _json_error("You do not have permission to cancel this ticket.", 403)
            
        current_status = ticket_meta["status_id"]
        
        if current_status == 4:
            return _json_error("Ticket is already cancelled.", 400)
            
        if current_status != 1: 
            return _json_error("This ticket is already being processed or resolved. It can no longer be cancelled.", 400)

        # Execute Cancel
        cursor.execute(
            """
            UPDATE ticket
            SET status_id = 4,
                last_updated = CURRENT_TIMESTAMP
            WHERE ticket_id = %s
            """,
            (ticket_id,)
        )
        conn.commit()

        # Audit Log
        from Backend.routes.utils import log_system_event, send_allitrack_alert
        log_system_event(
            user_identifier=str(user_id), 
            category="Ticket Management",
            action="Cancel Ticket",
            log_level="INFO",
            description=f"Client cancelled their own ticket #{ticket_id}."
        )

        # ==========================================
        # 🌟 NEW: NOTIFICATION ENGINE & WEBSOCKETS
        # ==========================================
        try:
            import re
            clean_title = re.sub(r'^\[.*?\]\s*', '', ticket_meta.get('concern_title', ''))

            # 1. Alert all Admins
            cursor.execute("""SELECT * FROM "system_user" WHERE LOWER(user_type) LIKE '%admin%'""")
            admin_rows = cursor.fetchall()
            admin_msg = f"Ticket #{ticket_id} (\"{clean_title}\") has been cancelled by the client."
            for admin_row in admin_rows:
                admin_id = admin_row.get("system_user_id") or admin_row.get("id") or admin_row.get("user_id")
                if admin_id:
                    send_allitrack_alert(admin_id, 'Ticket Cancelled by Client', admin_msg, 'ticket-update', ticket_id, 'Closed')

            # 2. Alert Technician (if one was somehow assigned while it was still 'Open')
            tech_id = ticket_meta.get("technician_id")
            if tech_id:
                cursor.execute('SELECT user_id FROM technician WHERE technician_id = %s', (tech_id,))
                tech_row = cursor.fetchone()
                if tech_row and tech_row.get("user_id"):
                    tech_msg = f"Ticket #{ticket_id} (\"{clean_title}\") assigned to you was cancelled by the client."
                    send_allitrack_alert(tech_row["user_id"], 'Assigned Ticket Cancelled', tech_msg, 'ticket-update', ticket_id, 'Closed')

            # 3. Trigger Real-Time Frontend Update
            from Backend.socketio_instance import socketio
            socketio.emit("ticket_updated", {"ticket_id": ticket_id})

        except Exception as notif_err:
            print(f"Cancel notifications error: {notif_err}")
        # ==========================================

        return jsonify({"status": "success", "message": "Ticket successfully cancelled."}), 200

    except Exception as e:
        conn.rollback()
        print(f"Cancel Ticket Error: {e}")
        return _json_error("Failed to cancel ticket")
    finally:
        cursor.close()
        conn.close()