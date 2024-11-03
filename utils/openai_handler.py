import os
from openai import OpenAI
from models import MessageTemplate, db

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def find_matching_template(message: str) -> MessageTemplate:
    """Find a matching template based on keywords in the message."""
    templates = MessageTemplate.query.filter_by(active=True).all()
    
    for template in templates:
        keywords = [k.strip().lower() for k in template.trigger_keywords.split(',')]
        message_lower = message.lower()
        
        if any(keyword in message_lower for keyword in keywords):
            template.usage_count += 1
            db.session.commit()
            return template
    
    return None

def generate_response(message: str) -> str:
    try:
        # First check for matching template
        template = find_matching_template(message)
        
        if template:
            return template.response_template
            
        # If no template matches, use OpenAI
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": message}]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"OpenAI API error: {str(e)}")
        return "I apologize, but I'm unable to process your request at the moment."
