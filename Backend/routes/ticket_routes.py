from flask import Blueprint, jsonify, request
from database import get_connection
from psycopg2.extras import RealDictCursor #

ticket_bp = Blueprint("tickets", __name__)

@ticket_bp.route("/tickets", methods=["GET"])
def get_tickets():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor) 
    try:
        # UPDATED: Concatenating first_name and last_name for both Tech and Requestor
        query = """
        SELECT 
            t.*, 
            (tech_u.first_name || ' ' || COALESCE(tech_u.last_name, '')) AS technician_name,
            (req_u.first_name || ' ' || COALESCE(req_u.last_name, '')) AS requestor_name
        FROM ticket t
        LEFT JOIN technician tech ON t.Technician_ID = tech.Technician_ID
        LEFT JOIN "system_user" tech_u ON tech.user_id = tech_u.user_id
        LEFT JOIN "system_user" req_u ON t.user_id = req_u.user_id
        ORDER BY t.Date_Created DESC
        """
        cursor.execute(query)
        tickets = cursor.fetchall()
        
        # Mapping lowercase Postgres keys back to the JS-expected CamelCase
        for t in tickets:
            t["Ticket_ID"] = t.pop("ticket_id")
            t["Concern_Title"] = t.pop("concern_title")
            t["Priority"] = t.pop("priority")
            t["Technician_Name"] = t.pop("technician_name")
            t["Requestor_Name"] = t.pop("requestor_name")
            
        return jsonify(tickets), 200
    except Exception as e:
        print(f"Database Error: {e}")
        return jsonify({"error": "Failed to fetch tickets"}), 500
    finally:
        cursor.close()
        conn.close()

@ticket_bp.route("/tickets", methods=["POST"])
def create_ticket():
    data = request.json
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Replaced NOW() with CURRENT_TIMESTAMP for Postgres compatibility[cite: 4]
        query = """
            INSERT INTO ticket
            (Service_Type_ID, user_id, Technician_ID, Status_ID,
             Concern_Title, Description, Date_Created, Last_Updated, Priority)
            VALUES (%s, %s, NULL, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, %s)
        """
        cursor.execute(query, (
            data.get("Service_Type_ID"),
            data.get("user_id"),
            data.get("Status_ID"),
            data.get("Concern_Title"),
            data.get("Description"),
            data.get("Priority")
        ))
        conn.commit()
        return jsonify({"message": "Ticket created successfully"}), 201
    except Exception as e:
        print(f"Create Ticket Error: {e}")
        return jsonify({"error": "Failed to create ticket"}), 500
    finally:
        cursor.close()
        conn.close()


# DELETE ticket
@ticket_bp.route("/tickets/<int:ticket_id>", methods=["DELETE"])
def delete_ticket(ticket_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM ticket WHERE Ticket_ID = %s", (ticket_id,))
    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"message": "Ticket deleted successfully"})

@ticket_bp.route("/tickets/user/<int:user_id>", methods=["GET"])
def get_user_tickets(user_id):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor) # Fixed cursor type

    try:
        # UPDATED: Concatenating tech name
        query = """
        SELECT 
            t.*,
            (s.first_name || ' ' || COALESCE(s.last_name, '')) AS technician_name
        FROM ticket t
        LEFT JOIN technician tech ON t.Technician_ID = tech.Technician_ID
        LEFT JOIN "system_user" s ON tech.user_id = s.user_id
        WHERE t.user_id = %s
        """
        cursor.execute(query, (user_id,))
        tickets = cursor.fetchall()

        # Format for JS
        for t in tickets:
            t["Ticket_ID"] = t.pop("ticket_id")
            t["Technician_Name"] = t.pop("technician_name")

        return jsonify(tickets), 200
    except Exception as e:
        print(f"User Tickets Error: {e}")
        return jsonify([]), 500
    finally:
        cursor.close()
        conn.close()

@ticket_bp.route("/technicians", methods=["GET"])
def get_technicians():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor) # Fixed cursor type

    try:
        # UPDATED: Concatenating tech name
        query = """
        SELECT 
            t.Technician_ID, 
            (s.first_name || ' ' || COALESCE(s.last_name, '')) AS name
        FROM technician t
        JOIN "system_user" s ON t.user_id = s.user_id
        """
        cursor.execute(query)
        technicians = cursor.fetchall()
        
        # Format for JS
        for tech in technicians:
            tech["Name"] = tech.pop("name")
            tech["Technician_ID"] = tech.pop("technician_id")

        return jsonify(technicians), 200
    except Exception as e:
        print(f"Tech Fetch Error: {e}")
        return jsonify([]), 500
    finally:
        cursor.close()
        conn.close()

@ticket_bp.route('/tickets/<int:ticket_id>', methods=["PUT"])
def update_ticket(ticket_id):
    try:
        data = request.json
        status_id = data.get('Status_ID')
        priority = data.get('Priority')
        technician_id = data.get('Technician_ID')
        # Get Resolution_Details, default to empty string if not provided
        resolution_details = data.get('Resolution_Details', '') 

        # NOTE: Make sure your database connection variable here (e.g., mysql.connection) 
        # matches what you use in your other routes!
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
            UPDATE ticket 
            SET Status_ID = %s, Priority = %s, Technician_ID = %s, Resolution_Details = %s, Last_Updated = CURRENT_TIMESTAMP
            WHERE Ticket_ID = %s
        """
        cursor.execute(query, (status_id, priority, technician_id, resolution_details, ticket_id))
        conn.commit()
        cursor.close()

        return jsonify({"message": "Ticket updated successfully"}), 200

    except Exception as e:
        print(f"Error updating ticket: {e}")
        return jsonify({"error": "Failed to update ticket"}), 500

@ticket_bp.route("/tickets/analytics", methods=["GET"])
def get_analytics():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute('SELECT COUNT(*) as total FROM ticket')
        total_tickets = cursor.fetchone()["total"]

        cursor.execute('SELECT COUNT(*) as resolved FROM ticket WHERE Status_ID = 3')
        resolved_tickets = cursor.fetchone()["resolved"]

        # UPDATED: Service type table often uses 'name' which is fine, 
        # but the JOIN must handle lowercase keys
        cursor.execute("""
            SELECT s.Name as category, COUNT(t.Ticket_ID) as count 
            FROM service_type s 
            LEFT JOIN ticket t ON s.Service_Type_ID = t.Service_Type_ID 
            GROUP BY s.Service_Type_ID, s.Name
        """)
        categories = cursor.fetchall()

        cursor.execute('SELECT priority, COUNT(*) as count FROM ticket GROUP BY priority')
        priorities = cursor.fetchall()

        return jsonify({
            "total": total_tickets,
            "resolved": resolved_tickets,
            "categories": {c["category"]: c["count"] for c in categories},
            "priorities": {p["priority"]: p["count"] for p in priorities}
        }), 200

    except Exception as e:
        print(f"Analytics Error: {e}")
        return jsonify({"error": "Failed to fetch analytics"}), 500
    finally:
        cursor.close()
        conn.close()
    

@ticket_bp.route("/feedback/submit", methods=["POST"])
def submit_feedback():
    data = request.json
    source = data.get("source")
    rating = data.get("rating")
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Insert the rating into our brand new table
        query = "INSERT INTO system_feedback (Source, Rating) VALUES (%s, %s)"
        cursor.execute(query, (source, rating))
        conn.commit()
        
        print(f"✅ New Feedback Saved: {source} - {rating}") # Helpful for debugging!
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        print(f"Feedback Error: {e}")
        return jsonify({"status": "error", "message": "Database error"}), 500
    finally:
        cursor.close()
        conn.close()