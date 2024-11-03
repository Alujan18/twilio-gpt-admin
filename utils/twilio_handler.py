import os
from datetime import datetime
from twilio.rest import Client
from models import Message, db
from utils.openai_handler import generate_response

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def send_message(to_number: str, message: str):
    try:
        message = client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=to_number
        )
        return message.sid
    except Exception as e:
        print(f"Twilio error: {str(e)}")
        return None

def process_twilio_webhook(form_data):
    from_number = form_data.get('From')
    message_body = form_data.get('Body')
    
    # Create message record
    message = Message(
        from_number=from_number,
        to_number=TWILIO_PHONE_NUMBER,
        content=message_body,
        status='processing'
    )
    db.session.add(message)
    db.session.commit()
    
    try:
        # Generate response using OpenAI
        response = generate_response(message_body)
        
        # Send response via Twilio
        send_message(from_number, response)
        
        # Update message record
        message.response = response
        message.status = 'completed'
        message.processed_at = datetime.utcnow()
        db.session.commit()
        
    except Exception as e:
        message.status = 'failed'
        message.response = str(e)
        db.session.commit()
