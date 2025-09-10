from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import uuid
from datetime import datetime
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = 'a93f6f1a2e3d47bc8bce14f5d3e7a02bbad6f9f8e812b2c1cf0ff7ac3a5fbc4a'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Email configuration with your credentials
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'yaswanthavula879@gmail.com'
app.config['MAIL_PASSWORD'] = 'kxke knka sbeb xfkd'

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Send email notification
def send_email_notification(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = app.config['MAIL_USERNAME']
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        text = msg.as_string()
        server.sendmail(app.config['MAIL_USERNAME'], to_email, text)
        server.quit()
        print(f"✅ Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Email sending failed: {str(e)}")
        print(f"📧 Email would have been sent to: {to_email}")
        print(f"📋 Subject: {subject}")
        return False

# Initialize database
def init_db():
    conn = sqlite3.connect('urban_issues.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        is_admin INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Issues table
    c.execute('''CREATE TABLE IF NOT EXISTS issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        priority TEXT DEFAULT 'medium',
        status TEXT DEFAULT 'pending',
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        address TEXT NOT NULL,
        image_filename TEXT,
        reported_by INTEGER,
        upvotes INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (reported_by) REFERENCES users (id)
    )''')
    
    # Comments table
    c.execute('''CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        issue_id INTEGER,
        user_id INTEGER,
        content TEXT NOT NULL,
        is_official INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (issue_id) REFERENCES issues (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # Create admin user if not exists
    c.execute("SELECT * FROM users WHERE email = 'admin@example.com'")
    if not c.fetchone():
        admin_password = generate_password_hash('admin123')
        c.execute("INSERT INTO users (name, email, password, is_admin) VALUES (?, ?, ?, ?)",
                 ('Admin User', 'admin@example.com', admin_password, 1))
    
    conn.commit()
    conn.close()

# Route to serve uploaded images
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Routes
@app.route('/')
def index():
    conn = sqlite3.connect('urban_issues.db')
    c = conn.cursor()
    
    # Get filters from query params
    category = request.args.get('category', '')
    status = request.args.get('status', '')
    search = request.args.get('search', '')
    
    # Build query
    query = '''SELECT i.*, u.name as reporter_name 
               FROM issues i 
               LEFT JOIN users u ON i.reported_by = u.id 
               WHERE 1=1'''
    params = []
    
    if category and category != 'all':
        query += ' AND i.category = ?'
        params.append(category)
    
    if status and status != 'all':
        query += ' AND i.status = ?'
        params.append(status)
    
    if search:
        query += ' AND (i.title LIKE ? OR i.description LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])
    
    query += ' ORDER BY i.created_at DESC'
    
    c.execute(query, params)
    issues = [dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]
    
    conn.close()
    
    return render_template('index.html', issues=issues, 
                         current_category=category, current_status=status, search_term=search)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = sqlite3.connect('urban_issues.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        conn.close()
        
        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            session['user_email'] = user[2]
            session['is_admin'] = user[4]
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password!', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        if len(password) < 6:
            flash('Password must be at least 6 characters!', 'error')
            return render_template('register.html')
        
        conn = sqlite3.connect('urban_issues.db')
        c = conn.cursor()
        
        # Check if user exists
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        if c.fetchone():
            flash('Email already exists!', 'error')
            conn.close()
            return render_template('register.html')
        
        # Create user
        hashed_password = generate_password_hash(password)
        c.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                 (name, email, hashed_password))
        user_id = c.lastrowid
        conn.commit()
        conn.close()
        
        # Auto-login after registration
        session['user_id'] = user_id
        session['user_name'] = name
        session['user_email'] = email
        session['is_admin'] = False
        
        # Send welcome email
        welcome_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px;">
            <h2 style="text-align: center; margin-bottom: 30px;">🏙 Welcome to Urban Issue Reporter!</h2>
            <div style="background: white; color: #333; padding: 30px; border-radius: 8px;">
                <p><strong>Hi {name},</strong></p>
                <p>Thank you for joining our community! You can now:</p>
                <ul style="line-height: 1.8;">
                    <li>🚨 Report urban issues in your area</li>
                    <li>📍 Use GPS to mark exact locations</li>
                    <li>📷 Upload photos of problems</li>
                    <li>💬 Engage with your community</li>
                    <li>👍 Support important issues with upvotes</li>
                </ul>
                <p style="margin-top: 30px;"><strong>Together, we can make our city better! 🌟</strong></p>
                <div style="text-align: center; margin-top: 30px;">
                    <a href="http://localhost:5000" style="background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">Start Reporting Issues</a>
                </div>
            </div>
            <p style="text-align: center; margin-top: 20px; font-size: 0.9rem;">Best regards,<br>Urban Issue Reporter Team</p>
        </div>
        """
        send_email_notification(email, "🏙 Welcome to Urban Issue Reporter!", welcome_body)
        
        flash('Registration successful! Welcome email sent!', 'success')
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
        title = request.form['title']
        description = request.form['description']
        category = request.form['category']
        priority = request.form['priority']
        latitude = float(request.form['latitude'])
        longitude = float(request.form['longitude'])
        address = request.form['address']
        
        # Handle file upload
        image_filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = str(uuid.uuid4()) + '.' + file.filename.rsplit('.', 1)[1].lower()
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_filename = filename
        
        # Save to database
        conn = sqlite3.connect('urban_issues.db')
        c = conn.cursor()
        c.execute("""INSERT INTO issues 
                    (title, description, category, priority, latitude, longitude, address, image_filename, reported_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                 (title, description, category, priority, latitude, longitude, address, image_filename, session['user_id']))
        issue_id = c.lastrowid
        conn.commit()
        conn.close()
        
        # Send notification email to user
        report_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px;">
            <h2 style="text-align: center; margin-bottom: 30px;">📋 Issue Reported Successfully!</h2>
            <div style="background: white; color: #333; padding: 30px; border-radius: 8px;">
                <p><strong>Hi {session['user_name']},</strong></p>
                <p>Your issue has been reported and assigned ID: <strong style="color: #667eea;">#{issue_id}</strong></p>
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #667eea; margin-top: 0;">Issue Details:</h3>
                    <p><strong>📌 Title:</strong> {title}</p>
                    <p><strong>📂 Category:</strong> {category.title()}</p>
                    <p><strong>⚡ Priority:</strong> {priority.title()}</p>
                    <p><strong>📍 Location:</strong> {address}</p>
                </div>
                <p><strong>Our team will review your report and update you on the progress. 🚀</strong></p>
                <div style="text-align: center; margin-top: 30px;">
                    <a href="http://localhost:5000/issue/{issue_id}" style="background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">View Your Issue</a>
                </div>
            </div>
            <p style="text-align: center; margin-top: 20px; font-size: 0.9rem;">Thank you for helping make our city better!<br>Urban Issue Reporter Team</p>
        </div>
        """
        send_email_notification(session['user_email'], f"📋 Issue Reported: {title}", report_body)
        
        flash('Issue reported successfully! Confirmation email sent!', 'success')
        return redirect(url_for('issue_detail', issue_id=issue_id))
    
    return render_template('report.html')

@app.route('/issue/<int:issue_id>')
def issue_detail(issue_id):
    conn = sqlite3.connect('urban_issues.db')
    c = conn.cursor()
    
    # Get issue details
    c.execute('''SELECT i.*, u.name as reporter_name, u.email as reporter_email 
                FROM issues i 
                LEFT JOIN users u ON i.reported_by = u.id 
                WHERE i.id = ?''', (issue_id,))
    issue = c.fetchone()
    
    if not issue:
        flash('Issue not found!', 'error')
        return redirect(url_for('index'))
    
    issue = dict(zip([col[0] for col in c.description], issue))
    
    # Get comments
    c.execute('''SELECT c.*, u.name as user_name 
                FROM comments c 
                LEFT JOIN users u ON c.user_id = u.id 
                WHERE c.issue_id = ? 
                ORDER BY c.created_at ASC''', (issue_id,))
    comments = [dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]
    
    conn.close()
    
    return render_template('issue_detail.html', issue=issue, comments=comments)

@app.route('/add_comment/<int:issue_id>', methods=['POST'])
def add_comment(issue_id):
    if 'user_id' not in session:
        flash('Please login to comment!', 'error')
        return redirect(url_for('login'))
    
    content = request.form['content']
    is_official = 1 if session.get('is_admin') else 0
    
    conn = sqlite3.connect('urban_issues.db')
    c = conn.cursor()
    
    # Add comment
    c.execute("INSERT INTO comments (issue_id, user_id, content, is_official) VALUES (?, ?, ?, ?)",
             (issue_id, session['user_id'], content, is_official))
    
    # Get issue and reporter details for email notification
    c.execute('''SELECT i.title, u.email, u.name 
                FROM issues i 
                LEFT JOIN users u ON i.reported_by = u.id 
                WHERE i.id = ?''', (issue_id,))
    issue_info = c.fetchone()
    
    conn.commit()
    conn.close()
    
    # Send email notification to issue reporter
    if issue_info and issue_info[1] and issue_info[1] != session.get('user_email'):
        comment_type = "Official Response" if is_official else "New Comment"
        comment_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px;">
            <h2 style="text-align: center; margin-bottom: 30px;">💬 {comment_type} on Your Issue!</h2>
            <div style="background: white; color: #333; padding: 30px; border-radius: 8px;">
                <p><strong>Hi {issue_info[2]},</strong></p>
                <p>There's a new {'official response' if is_official else 'comment'} on your issue: <strong style="color: #667eea;">{issue_info[0]}</strong></p>
                <div style="background: {'#f0f4ff' if is_official else '#f8f9fa'}; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid {'#667eea' if is_official else '#ddd'};">
                    <p><strong>{session['user_name']} {'(Official Response)' if is_official else ''} wrote:</strong></p>
                    <p style="font-style: italic; margin: 10px 0;">{content}</p>
                </div>
                <div style="text-align: center; margin-top: 30px;">
                    <a href="http://localhost:5000/issue/{issue_id}" style="background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">View Full Discussion</a>
                </div>
            </div>
            <p style="text-align: center; margin-top: 20px; font-size: 0.9rem;">Best regards,<br>Urban Issue Reporter Team</p>
        </div>
        """
        send_email_notification(issue_info[1], f"💬 {comment_type}: {issue_info[0]}", comment_body)
    
    flash('Comment added successfully!', 'success')
    return redirect(url_for('issue_detail', issue_id=issue_id))

@app.route('/admin')
def admin_panel():
    if not session.get('is_admin'):
        flash('Admin access required!', 'error')
        return redirect(url_for('index'))
    
    conn = sqlite3.connect('urban_issues.db')
    c = conn.cursor()
    
    # Get statistics
    c.execute("SELECT COUNT(*) FROM issues")
    total_issues = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM issues WHERE status = 'pending'")
    pending_issues = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM issues WHERE status = 'resolved'")
    resolved_issues = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    # Get recent issues
    c.execute('''SELECT i.*, u.name as reporter_name 
                FROM issues i 
                LEFT JOIN users u ON i.reported_by = u.id 
                ORDER BY i.created_at DESC 
                LIMIT 10''')
    recent_issues = [dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]
    
    conn.close()
    
    stats = {
        'total_issues': total_issues,
        'pending_issues': pending_issues,
        'resolved_issues': resolved_issues,
        'total_users': total_users
    }
    
    return render_template('admin.html', stats=stats, recent_issues=recent_issues)

@app.route('/update_status/<int:issue_id>', methods=['POST'])
def update_status(issue_id):
    if not session.get('is_admin'):
        return jsonify({'error': 'Admin access required'}), 403
    
    new_status = request.form['status']
    comment = request.form.get('comment', '')
    
    conn = sqlite3.connect('urban_issues.db')
    c = conn.cursor()
    
    # Update status
    c.execute("UPDATE issues SET status = ? WHERE id = ?", (new_status, issue_id))
    
    # Get issue and reporter details
    c.execute('''SELECT i.title, u.email, u.name 
                FROM issues i 
                LEFT JOIN users u ON i.reported_by = u.id 
                WHERE i.id = ?''', (issue_id,))
    issue_info = c.fetchone()
    
    # Add admin comment if provided
    if comment:
        c.execute("INSERT INTO comments (issue_id, user_id, content, is_official) VALUES (?, ?, ?, 1)",
                 (issue_id, session['user_id'], comment))
    
    conn.commit()
    conn.close()
    
    # Send status update email
    if issue_info and issue_info[1]:
        status_emojis = {
            'pending': '⏳',
            'in-progress': '🔄',
            'resolved': '✅',
            'rejected': '❌'
        }
        
        status_colors = {
            'pending': '#f39c12',
            'in-progress': '#3498db',
            'resolved': '#27ae60',
            'rejected': '#e74c3c'
        }
        
        status_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px;">
            <h2 style="text-align: center; margin-bottom: 30px;">{status_emojis.get(new_status, '📋')} Issue Status Updated!</h2>
            <div style="background: white; color: #333; padding: 30px; border-radius: 8px;">
                <p><strong>Hi {issue_info[2]},</strong></p>
                <p>Your issue <strong style="color: #667eea;">"{issue_info[0]}"</strong> has been updated by our team:</p>
                <div style="background: {status_colors.get(new_status, '#f8f9fa')}; color: white; padding: 25px; border-radius: 8px; margin: 25px 0; text-align: center;">
                    <h3 style="margin: 0; font-size: 1.5rem;">{status_emojis.get(new_status, '📋')} {new_status.replace('-', ' ').title()}</h3>
                </div>
                {f'<div style="background: #f0f4ff; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #667eea;"><p><strong>Official Comment:</strong></p><p style="font-style: italic;">{comment}</p></div>' if comment else ''}
                <div style="text-align: center; margin-top: 30px;">
                    <a href="http://localhost:5000/issue/{issue_id}" style="background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: bold;">View Issue Details</a>
                </div>
            </div>
            <p style="text-align: center; margin-top: 20px; font-size: 0.9rem;">Thank you for helping make our city better! 🌟<br>Urban Issue Reporter Team</p>
        </div>
        """
        send_email_notification(issue_info[1], f"{status_emojis.get(new_status, '📋')} Status Update: {issue_info[0]}", status_body)
    
    flash('Status updated successfully! Email notification sent!', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/upvote/<int:issue_id>', methods=['POST'])
def upvote_issue(issue_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Login required'}), 401
    
    conn = sqlite3.connect('urban_issues.db')
    c = conn.cursor()
    c.execute("UPDATE issues SET upvotes = upvotes + 1 WHERE id = ?", (issue_id,))
    c.execute("SELECT upvotes FROM issues WHERE id = ?", (issue_id,))
    upvotes = c.fetchone()[0]
    conn.commit()
    conn.close()
    
    return jsonify({'upvotes': upvotes})

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    init_db()
    print("🚀 Starting Urban Issue Reporter Flask App...")
    print("🌐 Open: http://localhost:5000")
    print("👤 Admin Login: admin@example.com / admin123")
    print("📧 Email notifications enabled with Gmail")
    print("📮 Sending emails from: sudheersugandham@gmail.com")
    app.run(debug=True, host='0.0.0.0', port=5000)