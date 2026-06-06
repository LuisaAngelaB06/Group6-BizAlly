from flask import Blueprint, request, jsonify
from Backend.extensions import db
from Backend.models import SystemFeedback
from Backend.routes.utils import log_system_event

routing_bp = Blueprint('routing_bp', __name__)

# Inside routes/routing.py
@routing_bp.route('/feedback/submit', methods=['POST'])
def submit_feedback():
    
    data = request.get_json()
    
    # Accept the diagnosis feedback payload; keep legacy source/rating names as fallbacks.
    source_val = data.get('service_module') or data.get('serviceModule') or data.get('source')
    rating_val = data.get('feedback') or data.get('diagnosis_feedback') or data.get('rating')
    nickname_val = data.get('nickname')
    session_id_val = data.get('session_id')
    user_id_val = data.get('user_id')  # Extract here to easily pass to the logger

    if not source_val:
        return jsonify({"error": "service_module is required"}), 400
    if not nickname_val:
        return jsonify({"error": "nickname is required"}), 400
    if not rating_val:
        return jsonify({"error": "feedback is required"}), 400
    if not session_id_val:
        return jsonify({"error": "session_id is required"}), 400

    try:
        new_entry = SystemFeedback(
            source=source_val,
            rating=rating_val,
            nickname=nickname_val,
            session_id=session_id_val,
            user_id=user_id_val
        )
        db.session.add(new_entry)
        db.session.commit()
        
        # 🌟 LOG IT: Record the feedback submission
        try:
            log_system_event(
                user_identifier=str(user_id_val or nickname_val), # Use ID if logged in, otherwise Nickname
                category="System Feedback",
                action="Feedback Submitted",
                log_level="INFO",
                description=f"Received '{rating_val}' feedback for module '{source_val}' from {nickname_val}."
            )
        except Exception as log_err:
            print(f"Failed to log feedback: {log_err}")

        return jsonify({"status": "success"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"DB ERROR: {str(e)}")
        return jsonify({
            "error": "Feedback could not be saved because the database connection is unavailable.",
            "details": str(e)
        }), 503