from flask import Blueprint, jsonify, request
from database import get_connection

ticket_bp = Blueprint("tickets", __name__)

# GET all tickets
@ticket_bp.route("/tickets", methods=["GET"])
def get_tickets():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT 
        t.*,
        s.Name AS Technician_Name
    FROM ticket t
    LEFT JOIN technician tech ON t.Technician_ID = tech.Technician_ID
    LEFT JOIN system_user s ON tech.User_ID = s.User_ID
    """

    cursor.execute(query)
    tickets = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(tickets)


# POST create new ticket  ← ADD THIS SECTION
@ticket_bp.route("/tickets", methods=["POST"])
def create_ticket():
    data = request.json

    service_type_id = data.get("Service_Type_ID")
    user_id = data.get("User_ID")
    status_id = data.get("Status_ID")
    concern_title = data.get("Concern_Title")
    description = data.get("Description")
    priority = data.get("Priority")

    conn = get_connection()
    cursor = conn.cursor()

    query = """
        INSERT INTO ticket
        (Service_Type_ID, User_ID, Technician_ID, Status_ID,
         Concern_Title, Description, Date_Created, Last_Updated, Priority)
        VALUES (%s, %s, NULL, %s, %s, %s, NOW(), NOW(), %s)
    """

    cursor.execute(query, (
        service_type_id,
        user_id,
        status_id,
        concern_title,
        description,
        priority
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"message": "Ticket created successfully"})

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
    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT 
        t.*,
        s.Name AS Technician_Name
    FROM ticket t
    LEFT JOIN technician tech ON t.Technician_ID = tech.Technician_ID
    LEFT JOIN system_user s ON tech.User_ID = s.User_ID
    WHERE t.User_ID = %s
    """

    cursor.execute(query, (user_id,))
    tickets = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(tickets)

@ticket_bp.route("/technicians", methods=["GET"])
def get_technicians():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT t.Technician_ID, s.Name
    FROM technician t
    JOIN system_user s ON t.User_ID = s.User_ID
    """

    cursor.execute(query)
    technicians = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(technicians)

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
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. Total tickets in the system
        cursor.execute("SELECT COUNT(*) as total FROM ticket")
        total_tickets = cursor.fetchone()["total"]

        # 2. Resolved tickets (Status_ID = 3)
        cursor.execute("SELECT COUNT(*) as resolved FROM ticket WHERE Status_ID = 3")
        resolved_tickets = cursor.fetchone()["resolved"]

        # 3. Tickets by Category (Joining with service_type table)
        cursor.execute("""
            SELECT s.Name as category, COUNT(t.Ticket_ID) as count 
            FROM service_type s 
            LEFT JOIN ticket t ON s.Service_Type_ID = t.Service_Type_ID 
            GROUP BY s.Service_Type_ID, s.Name
        """)
        categories = cursor.fetchall()

        # 4. Tickets by Priority
        cursor.execute("SELECT Priority, COUNT(*) as count FROM ticket GROUP BY Priority")
        priorities = cursor.fetchall()

        cursor.close()
        conn.close()

        # Clean up the data for the frontend charts
        return jsonify({
            "total": total_tickets,
            "resolved": resolved_tickets,
            "categories": {c["category"]: c["count"] for c in categories},
            "priorities": {p["Priority"]: p["count"] for p in priorities}
        }), 200

    except Exception as e:
        print(f"Analytics Error: {e}")
        return jsonify({"error": "Failed to fetch analytics"}), 500
    

@ticket_bp.route("/api/feedback/submit", methods=["POST"])
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