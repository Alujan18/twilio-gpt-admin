from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

class TwilioNumber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    friendly_name = db.Column(db.String(100))
    priority = db.Column(db.Integer, default=0)  # Higher number = higher priority
    is_active = db.Column(db.Boolean, default=True)
    daily_message_count = db.Column(db.Integer, default=0)
    last_used = db.Column(db.DateTime)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    from_number = db.Column(db.String(20), nullable=False)
    to_number = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    priority = db.Column(db.Integer, default=0)  # Message priority
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)
    template_used = db.Column(db.Integer, db.ForeignKey('message_template.id'), nullable=True)
    twilio_number_id = db.Column(db.Integer, db.ForeignKey('twilio_number.id'))

class MessageTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    trigger_keywords = db.Column(db.Text, nullable=False)  # Comma-separated keywords
    response_template = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    active = db.Column(db.Boolean, default=True)
    usage_count = db.Column(db.Integer, default=0)
