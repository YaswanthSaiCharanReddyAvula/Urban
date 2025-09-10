from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
import uuid
from datetime import datetime
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# App Config
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Database Config (SQLite for now, can switch to PostgreSQL later)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///urban_issues.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --------------------
# Database Models
# --------------------

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    issues = db.relationship("Issue", backref="reporter", lazy=True)
    comments = db.relationship("Comment", backref="author", lazy=True)


class Issue(db.Model):
    __tablename__ = "issues"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    priority = db.Column(db.String(20), default="medium")
    status = db.Column(db.String(20), default="pending")
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    address = db.Column(db.String(255), nullable=False)
    image_filename = db.Column(db.String(255))
    upvotes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reported_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    comments = db.relationship("Comment", backref="issue", lazy=True)


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey("issues.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_official = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# --------------------
# Utility Functions
# --------------------

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

# --------------------
# Replace sqlite3 queries with SQLAlchemy ORM
# --------------------

@app.route("/")
def index():
    category = request.args.get("category", "")
    status = request.args.get("status", "")
    search = request.args.get("search", "")

    query = Issue.query.join(User, isouter=True)

    if category and category != "all":
        query = query.filter(Issue.category == category)

    if status and status != "all":
        query = query.filter(Issue.status == status)

    if search:
        query = query.filter(
            (Issue.title.ilike(f"%{search}%")) |
            (Issue.description.ilike(f"%{search}%"))
        )

    issues = query.order_by(Issue.created_at.desc()).all()
    return render_template("index.html", issues=issues,
                           current_category=category,
                           current_status=status,
                           search_term=search)

# -----------------------
# ROUTES
# -----------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email, password = request.form['email'], request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session.update({
                'user_id': user.id,
                'user_name': user.name,
                'user_email': user.email,
                'is_admin': user.is_admin
            })
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        flash('Invalid email or password!', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name, email, password = request.form['name'], request.form['email'], request.form['password']
        if len(password) < 6:
            flash('Password must be at least 6 characters!', 'error')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already exists!', 'error')
            return render_template('register.html')

        hashed_password = generate_password_hash(password)
        user = User(name=name, email=email, password=hashed_password)
        db.session.add(user)
        db.session.commit()

        session.update({'user_id': user.id, 'user_name': name, 'user_email': email, 'is_admin': False})
        flash('Registration successful!', 'success')
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/report', methods=['GET', 'POST'])
def report_issue():
    if 'user_id' not in session:
        flash('Please login to report issues!', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        title, description = request.form['title'], request.form['description']
        category, priority = request.form['category'], request.form['priority']
        latitude, longitude = float(request.form['latitude']), float(request.form['longitude'])
        address = request.form['address']

        image_filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                filename = str(uuid.uuid4()) + '.' + file.filename.rsplit('.', 1)[1].lower()
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_filename = filename

        issue = Issue(title=title, description=description, category=category,
                      priority=priority, latitude=latitude, longitude=longitude,
                      address=address, image_filename=image_filename,
                      reported_by=session['user_id'])
        db.session.add(issue)
        db.session.commit()

        flash('Issue reported successfully!', 'success')
        return redirect(url_for('issue_detail', issue_id=issue.id))
    return render_template('report.html')

@app.route('/issue/<int:issue_id>')
def issue_detail(issue_id):
    issue = Issue.query.get_or_404(issue_id)
    comments = Comment.query.filter_by(issue_id=issue_id).order_by(Comment.created_at).all()
    return render_template('issue_detail.html', issue=issue, comments=comments)

@app.route('/add_comment/<int:issue_id>', methods=['POST'])
def add_comment(issue_id):
    if 'user_id' not in session:
        flash('Please login to comment!', 'error')
        return redirect(url_for('login'))

    content = request.form['content']
    comment = Comment(issue_id=issue_id, user_id=session['user_id'],
                      content=content, is_official=session.get('is_admin', False))
    db.session.add(comment)
    db.session.commit()
    flash('Comment added successfully!', 'success')
    return redirect(url_for('issue_detail', issue_id=issue_id))

@app.route('/admin')
def admin_panel():
    if not session.get('is_admin'):
        flash('Admin access required!', 'error')
        return redirect(url_for('index'))

    stats = {
        'total_issues': Issue.query.count(),
        'pending_issues': Issue.query.filter_by(status='pending').count(),
        'resolved_issues': Issue.query.filter_by(status='resolved').count(),
        'total_users': User.query.count()
    }
    recent_issues = Issue.query.order_by(Issue.created_at.desc()).limit(10).all()
    return render_template('admin.html', stats=stats, recent_issues=recent_issues)

@app.route('/update_status/<int:issue_id>', methods=['POST'])
def update_status(issue_id):
    if not session.get('is_admin'):
        return jsonify({'error': 'Admin access required'}), 403

    issue = Issue.query.get_or_404(issue_id)
    issue.status = request.form['status']
    db.session.commit()
    flash('Status updated successfully!', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/upvote/<int:issue_id>', methods=['POST'])
def upvote_issue(issue_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Login required'}), 401
    issue = Issue.query.get_or_404(issue_id)
    issue.upvotes += 1
    db.session.commit()
    return jsonify({'upvotes': issue.upvotes})

# -----------------------
# STARTUP
# -----------------------
if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
else:
    os.makedirs('uploads', exist_ok=True)
    db.create_all()