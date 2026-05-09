from flask import Blueprint, request, jsonify
from Backend.extensions import db
from models import SystemFeedback

routing_bp = Blueprint('routing_bp', __name__)

# Inside routes/routing.py
@routing_bp.route('/feedback/submit', methods=['POST'])
def submit_feedback():
    
    data = request.get_json()
    
    # 🌟 Pull 'source' (from your JS document.title) and 'rating'
    source_val = data.get('source')
    rating_val = data.get('rating')

    try:
        # Create the entry using the exact keywords from your model
        new_entry = SystemFeedback(source=source_val, rating=rating_val)
        db.session.add(new_entry)
        db.session.commit()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"❌ DB ERROR: {str(e)}") # Check your terminal for this message!
        return jsonify({"error": str(e)}), 500