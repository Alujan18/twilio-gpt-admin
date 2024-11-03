import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_required, login_user, logout_user
from werkzeug.security import check_password_hash
from redis import Redis
from rq import Queue
from models import User, Message, db
from utils.twilio_handler import process_twilio_webhook
from utils.redis_handler import get_queue_stats

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "your-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Initialize Redis and RQ
redis_conn = Redis(host='0.0.0.0', port=6379)
message_queue = Queue('messages', connection=redis_conn)

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
    queue_stats = get_queue_stats(message_queue)
    return render_template('dashboard.html', messages=messages, stats=queue_stats)

@app.route('/webhook/twilio', methods=['POST'])
def twilio_webhook():
    try:
        # Process incoming Twilio message
        job = message_queue.enqueue(process_twilio_webhook, request.form)
        return jsonify({"status": "queued", "job_id": job.id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/queue-stats')
@login_required
def queue_stats():
    stats = get_queue_stats(message_queue)
    return jsonify(stats)

with app.app_context():
    db.create_all()
