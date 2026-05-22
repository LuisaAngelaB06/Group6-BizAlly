from flask import Blueprint, request, jsonify
from Backend.extensions import db
from Backend.models import SystemFeedback

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
            user_id=data.get('user_id')
        )
        db.session.add(new_entry)
        db.session.commit()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"DB ERROR: {str(e)}")
        return jsonify({
            "error": "Feedback could not be saved because the database connection is unavailable.",
            "details": str(e)
        }), 503
