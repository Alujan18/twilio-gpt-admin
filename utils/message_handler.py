from twilio.rest import Client
from openai import OpenAI
from config import Config
from models import Message, db
from datetime import datetime

twilio_client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)

def process_message(message_id):
    message = Message.query.get(message_id)
    if not message:
        return
    
    try:
        # Get GPT response
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": message.content}]
        )
        gpt_response = response.choices[0].message.content

        # Send response via Twilio
        twilio_response = twilio_client.messages.create(
            body=gpt_response,
            from_=Config.TWILIO_PHONE_NUMBER,
            to=message.from_number
        )

        # Update message record
        message.response = gpt_response
        message.status = 'processed'
        message.processed_at = datetime.utcnow()
        db.session.commit()

    except Exception as e:
        message.status = 'failed'
        message.response = str(e)
        db.session.commit()
