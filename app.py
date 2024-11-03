import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_required, login_user, logout_user
from werkzeug.security import check_password_hash
from rq import Queue
from models import User, Message, db
from utils.twilio_handler import process_twilio_webhook
from utils.redis_handler import get_queue_stats
from utils.redis_helper import RedisHelper
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "your-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Initialize Redis and RQ with proper error handling
redis_helper = RedisHelper()
redis_conn = redis_helper.get_connection()
if redis_conn:
    message_queue = Queue('messages', connection=redis_conn)
else:
    message_queue = None
    logger.error("Failed to initialize Redis queue - some features may be unavailable")

db.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    messages = Message.query.order_by(Message.timestamp.desc()).limit(50).all()
    queue_stats = {'queued': 0, 'started': 0, 'finished': 0, 'failed': 0}
    
    if message_queue and redis_helper.health_check():
        try:
            queue_stats = get_queue_stats(message_queue)
        except Exception as e:
            logger.error(f"Error fetching queue stats: {str(e)}")
            flash("Unable to fetch queue statistics", "error")
    else:
        flash("Queue system is currently unavailable", "warning")
    
    return render_template('dashboard.html', messages=messages, stats=queue_stats)

@app.route('/webhook/twilio', methods=['POST'])
def twilio_webhook():
    if not message_queue or not redis_helper.health_check():
        logger.error("Queue system unavailable - cannot process webhook")
        return jsonify({"error": "Queue system unavailable"}), 503
        
    try:
        job = message_queue.enqueue(process_twilio_webhook, request.form)
        return jsonify({"status": "queued", "job_id": job.id}), 200
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/queue-stats')
@login_required
def queue_stats():
    if not message_queue or not redis_helper.health_check():
        return jsonify({"error": "Queue system unavailable"}), 503
        
    try:
        stats = get_queue_stats(message_queue)
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error fetching queue stats: {str(e)}")
        return jsonify({"error": str(e)}), 500

with app.app_context():
    db.create_all()
