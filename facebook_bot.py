from flask import Flask, request, jsonify, redirect, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import requests
import os
from dotenv import load_dotenv
import schedule
import time
import threading

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key')
db = SQLAlchemy(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

# Facebook Page Access Token
PAGE_ACCESS_TOKEN = os.getenv('PAGE_ACCESS_TOKEN')
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')

# Database Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin' or 'moderator'

class Reminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(80), nullable=False)
    time = db.Column(db.String(20), nullable=False)
    text = db.Column(db.String(200), nullable=False)

# Create the database
with app.app_context():
    db.create_all()
    # Create an admin user if it doesn't exist
    if not User.query.filter_by(username='admin').first():
        admin_user = User(username='admin', password='amijanina', role='admin')
        db.session.add(admin_user)
        db.session.commit()
# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Root route to avoid 404 errors
@app.route('/')
def home():
    return 'Welcome to the Facebook Bot Admin Tool!'

# Webhook verification
@app.route('/webhook', methods=['GET'])
def verify_webhook():
    hub_mode = request.args.get('hub.mode')
    hub_token = request.args.get('hub.verify_token')
    hub_challenge = request.args.get('hub.challenge')

    if hub_mode == 'subscribe' and hub_token == VERIFY_TOKEN:
        return hub_challenge, 200
    return 'Verification failed', 403

# Handle incoming messages
@app.route('/webhook', methods=['POST'])
def handle_webhook():
    data = request.json
    if data['object'] == 'page':
        for entry in data['entry']:
            for event in entry['messaging']:
                if 'message' in event:
                    handle_message(event)
    return jsonify({'status': 'ok'}), 200

# Function to handle messages
def handle_message(event):
    sender_id = event['sender']['id']
    message = event['message']

    if 'text' in message:
        text = message['text']
        if text.startswith('/remind'):
            set_reminder(sender_id, text)
        elif text.startswith('/add_moderator'):
            if is_admin(sender_id):
                add_moderator_via_bot(text)
            else:
                send_message(sender_id, 'Unauthorized')
        elif text.startswith('/reminders'):
            if is_moderator(sender_id):
                show_reminders(sender_id)
            else:
                send_message(sender_id, 'Unauthorized')
        else:
            send_message(sender_id, f'You said: {text}')
    elif 'attachments' in message:
        for attachment in message['attachments']:
            if attachment['type'] == 'file':
                file_url = attachment['payload']['url']
                send_message(sender_id, f'Download link: {file_url}')

# Function to send messages
def send_message(sender_id, message):
    url = f'https://graph.facebook.com/v12.0/me/messages?access_token={PAGE_ACCESS_TOKEN}'
    payload = {
        'recipient': {'id': sender_id},
        'message': {'text': message}
    }
    requests.post(url, json=payload)

# Function to set a reminder
def set_reminder(sender_id, text):
    try:
        _, time_str, reminder_text = text.split(' ', 2)
        new_reminder = Reminder(user_id=sender_id, time=time_str, text=reminder_text)
        db.session.add(new_reminder)
        db.session.commit()
        schedule.every().day.at(time_str).do(send_message, sender_id=sender_id, message=f'Reminder: {reminder_text}')
        send_message(sender_id, f'Reminder set for {time_str}: {reminder_text}')
    except Exception as e:
        send_message(sender_id, 'Invalid reminder format. Use: /remind HH:MM Your reminder text')

# Function to check if user is admin
def is_admin(sender_id):
    user = User.query.filter_by(username=sender_id).first()
    return user and user.role == 'admin'

# Function to check if user is moderator
def is_moderator(sender_id):
    user = User.query.filter_by(username=sender_id).first()
    return user and user.role in ['admin', 'moderator']

# Function to add moderator via bot
def add_moderator_via_bot(text):
    try:
        _, username, password = text.split(' ', 2)
        new_moderator = User(username=username, password=password, role='moderator')
        db.session.add(new_moderator)
        db.session.commit()
        send_message(username, 'You have been added as a moderator')
    except Exception as e:
        send_message(username, 'Failed to add moderator')

# Function to show reminders
def show_reminders(sender_id):
    reminders = Reminder.query.filter_by(user_id=sender_id).all()
    if reminders:
        reminder_list = '\n'.join([f'{r.time}: {r.text}' for r in reminders])
        send_message(sender_id, f'Your reminders:\n{reminder_list}')
    else:
        send_message(sender_id, 'You have no reminders')

# Admin routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            login_user(user)
            return redirect('/admin')
        return 'Invalid credentials'
    return '''
        <form method="post">
            Username: <input type="text" name="username"><br>
            Password: <input type="password" name="password"><br>
            <input type="submit" value="Login">
        </form>
    '''

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return 'Logged out'

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role == 'admin':
        return '''
            <h1>Admin Dashboard</h1>
            <a href="/add_moderator">Add Moderator</a><br>
            <a href="/reminders">View Reminders</a><br>
            <a href="/logout">Logout</a>
        '''
    elif current_user.role == 'moderator':
        return '''
            <h1>Moderator Dashboard</h1>
            <a href="/reminders">View Reminders</a><br>
            <a href="/logout">Logout</a>
        '''
    return 'Unauthorized'

@app.route('/add_moderator', methods=['GET', 'POST'])
@login_required
def add_moderator():
    if current_user.role != 'admin':
        return 'Unauthorized'
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        new_moderator = User(username=username, password=password, role='moderator')
        db.session.add(new_moderator)
        db.session.commit()
        return 'Moderator added'
    return '''
        <form method="post">
            Username: <input type="text" name="username"><br>
            Password: <input type="password" name="password"><br>
            <input type="submit" value="Add Moderator">
        </form>
    '''

@app.route('/reminders')
@login_required
def reminders():
    reminders = Reminder.query.all()
    return render_template_string('''
        <h1>Reminders</h1>
        <ul>
            {% for reminder in reminders %}
                <li>{{ reminder.time }}: {{ reminder.text }}</li>
            {% endfor %}
        </ul>
        <a href="/admin">Back to Dashboard</a>
    ''', reminders=reminders)

# Run the scheduler in a separate thread
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

# Start the scheduler thread only once
if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()

# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
