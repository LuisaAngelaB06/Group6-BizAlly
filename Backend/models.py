from datetime import datetime
# Import db from where it is initialized (extensions or app)
from Backend.extensions import db 

class SystemFeedback(db.Model):
    __tablename__ = 'system_feedback'
    
    # Matches: feedback_id serial not null
    feedback_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Matches: source character varying(255) not null
    source = db.Column(db.String(255), nullable=False)
    
    # Matches: rating character varying(50) not null
    rating = db.Column(db.String(50), nullable=False)

    # Anonymous diagnosis feedback fields
    nickname = db.Column(db.String(100), nullable=False)
    session_id = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, nullable=True)
    
    # Matches: created_at timestamp default CURRENT_TIMESTAMP
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, source, rating, nickname, session_id, user_id=None):
        self.source = source
        self.rating = rating
        self.nickname = nickname
        self.session_id = session_id
        self.user_id = user_id
