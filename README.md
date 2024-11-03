# Twilio-GPT Admin Dashboard

A Flask-based backend administrator with Redis queue system for managing Twilio-GPT message communication.

## Features

- Admin Dashboard with Real-time Queue Monitoring
- Message Template Management
- Multiple Twilio Number Support with Priority Queue
- OpenAI GPT Integration
- Redis Queue System for Asynchronous Message Processing
- Advanced Queue Analytics and Statistics

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: PostgreSQL
- **Queue System**: Redis & RQ (Redis Queue)
- **APIs**: 
  - Twilio for SMS
  - OpenAI GPT for Message Generation
- **Frontend**: Bootstrap 5 with Dark Theme

## Prerequisites

- Python 3.11+
- PostgreSQL Database
- Redis Server
- Twilio Account
- OpenAI API Key

## Environment Variables

The following environment variables are required:

```env
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=your_twilio_number
OPENAI_API_KEY=your_openai_api_key
FLASK_SECRET_KEY=your_secret_key
```

## Installation

1. Clone the repository
```bash
git clone https://github.com/yourusername/twilio-gpt-admin.git
cd twilio-gpt-admin
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Initialize the database
```bash
python init_db.py
```

4. Start the Redis server
```bash
redis-server
```

5. Start the worker process
```bash
python worker.py
```

6. Run the Flask application
```bash
python main.py
```

## Default Login

- Username: admin
- Password: admin

*Note: Please change these credentials after first login.*

## Features Overview

### Message Templates
- Create and manage response templates
- Keyword-based template matching
- Template usage tracking

### Twilio Number Management
- Multiple number support
- Priority-based routing
- Daily message count tracking
- Active/Inactive status toggle

### Queue Monitoring
- Real-time queue status
- Message processing statistics
- Queue history visualization
- Message volume tracking

## License

MIT License
