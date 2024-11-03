import os
from datetime import datetime
from twilio.rest import Client
from models import Message, TwilioNumber, db
from utils.openai_handler import generate_response

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def get_available_number():
    """Get the most suitable Twilio number based on priority and load balancing"""
    # Get active numbers ordered by priority (highest first) and message count (lowest first)
    available_number = TwilioNumber.query.filter_by(is_active=True)\
        .order_by(TwilioNumber.priority.desc(), TwilioNumber.daily_message_count)\
        .first()
    
    if available_number:
        # Update usage statistics
        available_number.daily_message_count += 1
        available_number.last_used = datetime.utcnow()
        db.session.commit()
        return available_number.phone_number
    
    # Fallback to default number if no numbers are available
    return os.environ.get("TWILIO_PHONE_NUMBER")

def send_message(to_number: str, message: str, priority: int = 0):
    """Send message with priority handling"""
    try:
        from_number = get_available_number()
        message = client.messages.create(
            body=message,
            from_=from_number,
            to=to_number
        )
        return message.sid
    except Exception as e:
        print(f"Twilio error: {str(e)}")
        return None

def process_twilio_webhook(form_data, priority: int = 0):
    """Process incoming webhook with priority support"""
    from_number = form_data.get('From')
    message_body = form_data.get('Body')
    to_number = form_data.get('To')
    
    # Get the TwilioNumber record for this number
    twilio_number = TwilioNumber.query.filter_by(phone_number=to_number).first()
    
    # Create message record
    message = Message(
        from_number=from_number,
        to_number=to_number,
        content=message_body,
        status='processing',
        priority=priority,
        twilio_number_id=twilio_number.id if twilio_number else None
    )
    db.session.add(message)
    db.session.commit()
    
    try:
        # Generate response using OpenAI
        response = generate_response(message_body)
        
        # Send response via Twilio
        send_message(from_number, response, priority)
        
        # Update message record
        message.response = response
        message.status = 'completed'
        message.processed_at = datetime.utcnow()
        db.session.commit()
        
    except Exception as e:
        message.status = 'failed'
        message.response = str(e)
        db.session.commit()

def reset_daily_counts():
    """Reset daily message counts for all numbers"""
    TwilioNumber.query.update({TwilioNumber.daily_message_count: 0})
    db.session.commit()
