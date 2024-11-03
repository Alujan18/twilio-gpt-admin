import os

class Config:
    # Flask
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "your-secret-key")
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Redis
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
    
    # Twilio
    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")
    
    # OpenAI
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
