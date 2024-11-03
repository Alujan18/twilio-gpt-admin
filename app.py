from flask import Flask, request, render_template, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, Admin, Message
from utils.redis_helper import enqueue_message, get_queue_metrics
from config import Config
import logging

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

# Routes
@app.route('/webhook/twilio', methods=['POST'])
def twilio_webhook():
    from_number = request.form.get('From')
    content = request.form.get('Body')
    
    message = Message(
        from_number=from_number,
        to_number=Config.TWILIO_PHONE_NUMBER,
        content=content,
        status='pending'
    )
    db.session.add(message)
    db.session.commit()
    
    enqueue_message(message.id)
    return '', 200

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        admin = Admin.query.filter_by(username=request.form.get('username')).first()
        if admin and admin.check_password(request.form.get('password')):
            login_user(admin)
            return redirect(url_for('dashboard'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    messages = Message.query.order_by(Message.created_at.desc()).limit(50).all()
    metrics = get_queue_metrics()
    return render_template('dashboard.html', messages=messages, metrics=metrics)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

with app.app_context():
    db.create_all()
