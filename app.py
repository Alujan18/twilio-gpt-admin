import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_required, login_user, logout_user
from werkzeug.security import check_password_hash
from rq import Queue
from models import User, Message, MessageTemplate, db
from utils.twilio_handler import process_twilio_webhook
from utils.redis_handler import (
    get_queue_stats, get_queue_history, record_queue_stats,
    get_processing_stats, update_processing_stats
)
from utils.redis_helper import RedisHelper
import logging
from urllib.parse import urlparse, parse_qs
from redis.exceptions import RedisError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "your-secret-key")

# Parse the database URL and add sslmode=require
db_url = os.environ.get("DATABASE_URL")
if db_url:
    try:
        url = urlparse(db_url)
        query_dict = parse_qs(url.query) if url.query else {}
        query_dict['sslmode'] = ['require']
        new_query = '&'.join(f"{k}={v[0]}" for k, v in query_dict.items())
        app.config["SQLALCHEMY_DATABASE_URI"] = f"{url.scheme}://{url.netloc}{url.path}?{new_query}"
        logger.info("Database URL configured with SSL enabled")
    except Exception as e:
        logger.error(f"Error parsing database URL: {str(e)}")
        app.config["SQLALCHEMY_DATABASE_URI"] = db_url + "?sslmode=require"
else:
    logger.error("DATABASE_URL environment variable not set")
    raise RuntimeError("DATABASE_URL environment variable is required")

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

def get_default_processing_stats():
    return {
        'avg_processing_time': 0,
        'total_processed': 0,
        'success_rate': 100,
        'hourly_volume': []
    }

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
    queue_stats = {'queued': 0, 'started': 0, 'finished': 0, 'failed': 0, 'deferred': 0, 'scheduled': 0}
    processing_stats = {
        'avg_processing_time': 0,
        'total_processed': 0,
        'success_rate': 100,
        'hourly_volume': []
    }
    
    if message_queue and redis_helper.health_check():
        try:
            queue_stats = get_queue_stats(message_queue)
            processing_stats = get_processing_stats(redis_conn)
            # Record current stats for historical tracking
            record_queue_stats(redis_conn, message_queue)
        except Exception as e:
            logger.error(f"Error fetching queue stats: {str(e)}")
            flash("Unable to fetch queue statistics", "error")
    else:
        flash("Queue system is currently unavailable", "warning")
    
    return render_template('dashboard.html', 
                         messages=messages, 
                         stats=queue_stats,
                         processing_stats=processing_stats)

@app.route('/templates')
@login_required
def templates():
    templates = MessageTemplate.query.order_by(MessageTemplate.created_at.desc()).all()
    return render_template('templates.html', templates=templates)

@app.route('/api/queue-stats')
@login_required
def queue_stats():
    if not message_queue or not redis_helper.health_check():
        return jsonify({
            "queue": {
                'queued': 0, 'started': 0, 'finished': 0, 
                'failed': 0, 'deferred': 0, 'scheduled': 0
            },
            "processing": get_default_processing_stats()
        })
        
    try:
        stats = get_queue_stats(message_queue)
        processing_stats = get_processing_stats(redis_conn)
        return jsonify({
            "queue": stats,
            "processing": processing_stats
        })
    except Exception as e:
        logger.error(f"Error fetching queue stats: {str(e)}")
        return jsonify({
            "queue": {
                'queued': 0, 'started': 0, 'finished': 0, 
                'failed': 0, 'deferred': 0, 'scheduled': 0
            },
            "processing": get_default_processing_stats()
        })

@app.route('/api/queue-history')
@login_required
def queue_history():
    try:
        if not redis_conn or not redis_helper.health_check():
            logger.warning("Redis connection unavailable - returning empty history")
            return jsonify([])
            
        period = request.args.get('period', '24')
        try:
            period = int(period)
        except ValueError:
            logger.warning(f"Invalid period value: {period}, using default 24")
            period = 24
            
        history = get_queue_history(redis_conn, period)
        return jsonify(history)
    except RedisError as e:
        logger.error(f"Redis error in queue history: {str(e)}")
        return jsonify([])
    except Exception as e:
        logger.error(f"Unexpected error in queue history: {str(e)}")
        return jsonify([])

@app.route('/templates/add', methods=['POST'])
@login_required
def add_template():
    try:
        template = MessageTemplate(
            name=request.form['name'],
            description=request.form['description'],
            trigger_keywords=request.form['keywords'],
            response_template=request.form['template']
        )
        db.session.add(template)
        db.session.commit()
        flash('Template added successfully')
    except Exception as e:
        flash(f'Error adding template: {str(e)}')
    return redirect(url_for('templates'))

@app.route('/templates/edit/<int:template_id>', methods=['POST'])
@login_required
def edit_template(template_id):
    template = MessageTemplate.query.get_or_404(template_id)
    try:
        template.name = request.form['name']
        template.description = request.form['description']
        template.trigger_keywords = request.form['keywords']
        template.response_template = request.form['template']
        db.session.commit()
        flash('Template updated successfully')
    except Exception as e:
        flash(f'Error updating template: {str(e)}')
    return redirect(url_for('templates'))

@app.route('/templates/toggle/<int:template_id>', methods=['POST'])
@login_required
def toggle_template(template_id):
    template = MessageTemplate.query.get_or_404(template_id)
    try:
        template.active = not template.active
        db.session.commit()
        flash(f'Template {"activated" if template.active else "deactivated"} successfully')
    except Exception as e:
        flash(f'Error toggling template: {str(e)}')
    return redirect(url_for('templates'))

@app.route('/webhook/twilio', methods=['POST'])
def twilio_webhook():
    if not message_queue or not redis_helper.health_check():
        logger.error("Queue system unavailable - cannot process webhook")
        return jsonify({"error": "Queue system unavailable"}), 503
        
    try:
        start_time = datetime.utcnow()
        job = message_queue.enqueue(process_twilio_webhook, request.form)
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        update_processing_stats(redis_conn, processing_time, True)
        return jsonify({"status": "queued", "job_id": job.id}), 200
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        if redis_conn:
            update_processing_stats(redis_conn, 0, False)
        return jsonify({"error": str(e)}), 500

with app.app_context():
    db.create_all()