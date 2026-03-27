from flask import Flask, render_template, request, redirect, url_for, session, flash
import pymysql
from datetime import datetime, date, timedelta
import os
from werkzeug.utils import secure_filename
from fpdf import FPDF
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import uuid
from flask import render_template_string
from xhtml2pdf import pisa
from flask_moment import Moment
import time
from flask import make_response
import smtplib
from email.mime.text import MIMEText
import random
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from io import BytesIO
from flask import render_template, request, redirect, url_for, session, flash, send_file
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from flask import send_from_directory
from reportlab.lib.styles import ParagraphStyle
from config import get_connection
from dotenv import load_dotenv
from decimal import Decimal
from PIL import Image as PILImage
from reportlab.platypus import Image as RLImage
import requests
from reportlab.lib.pagesizes import A4 ,landscape
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from flask import send_file

load_dotenv()

UPLOAD_FOLDER_INVOICES = 'static/invoices'
os.makedirs(UPLOAD_FOLDER_INVOICES, exist_ok=True)

app = Flask(__name__)
app.secret_key = 'your_secret_key'

moment = Moment(app)

ZEPTOMAIL_API_URL = "https://api.zeptomail.in/v1.1/email"
ZEPTOMAIL_API_TOKEN = os.environ.get("ZEPTO_TOKEN")
ZEPTOMAIL_FROM_EMAIL = "contact@rudhisoft.com"
ZEPTOMAIL_FROM_NAME = "Rudhiarch"

from werkzeug.security import generate_password_hash, check_password_hash

UPLOAD_FOLDER = 'static/uploads'
UPLOAD_FOLDER_INVOICES = 'static/invoices'
UPLOAD_FOLDER_VENDOR = 'static/vendor_quotes'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_INVOICES, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_VENDOR, exist_ok=True)
UPLOAD_FOLDER_PROGRESS = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_otp():
    """Generate a random 6-digit OTP"""
    return str(random.randint(100000, 999999))


def send_otp_email(email, otp):
    """
    Send OTP email using ZeptoMail
    Returns: (success: bool, error_message: str or None)
    """
    try:
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Zoho-enczapikey {ZEPTOMAIL_API_TOKEN}"
        }
        
        payload = {
            "from": {
                "address": ZEPTOMAIL_FROM_EMAIL,
                "name": ZEPTOMAIL_FROM_NAME
            },
            "to": [
                {
                    "email_address": {
                        "address": email
                    }
                }
            ],
            "subject": "Your OTP Code for Verification",
            "htmlbody": f"""
                <html>
                    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                            <h2 style="color: #1e3a8a; text-align: center;">OTP Verification</h2>
                            <p>Hello,</p>
                            <p>Your One-Time Password (OTP) for verification is:</p>
                            <div style="text-align: center; margin: 30px 0;">
                                <span style="font-size: 32px; font-weight: bold; color: #1e3a8a; letter-spacing: 5px; padding: 15px 30px; border: 2px dashed #1e3a8a; border-radius: 8px; display: inline-block;">
                                    {otp}
                                </span>
                            </div>
                            <p style="color: #e74c3c; font-weight: bold;">⚠️ This code will expire in 5 minutes.</p>
                            <p>If you didn't request this code, please ignore this email.</p>
                            <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                            <p style="font-size: 12px; color: #666;">
                                Best regards,<br>
                                <strong>Rudhiarch Team</strong>
                            </p>
                        </div>
                    </body>
                </html>
            """
        }
        
        response = requests.post(ZEPTOMAIL_API_URL, headers=headers, json=payload, timeout=10)
        
        # Log response for debugging
        print(f"ZeptoMail Status Code: {response.status_code}")
        print(f"ZeptoMail Response: {response.text}")
        
        response.raise_for_status()
        return True, None
        
    except requests.exceptions.Timeout:
        return False, "Email service timeout. Please try again."
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to send email: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            error_msg += f" - {e.response.text}"
        return False, error_msg
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"
    



    ################################### NOTIFICATION HELPER FUNCTIONS ###################################

"""
FIXED NOTIFICATION HELPER FUNCTIONS
Replace lines 206-285 in your app.py with these functions
"""

def create_notification(user_id, org_id, notification_type, reference_id, message):
    """
    Create a new notification for a user
    
    Args:
        user_id: ID of the user to notify
        org_id: Organization ID
        notification_type: Type of notification (e.g., 'project_assigned', 'invoice_generated')
        reference_id: ID of the related record
        message: Notification message text
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO notifications (user_id, org_id, notification_type, reference_id, message, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (user_id, org_id, notification_type, reference_id, message))
        conn.commit()
    except Exception as e:
        print(f"Error creating notification: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()


def get_unread_notifications_count(user_id, org_id, notification_type=None):
    """Get count of unread notifications for a user"""
    conn = get_connection(dict_cursor=False)  # ✅ Use regular cursor
    cur = conn.cursor()
    try:
        if notification_type:
            query = """
                SELECT COUNT(*) 
                FROM notifications 
                WHERE user_id = %s AND org_id = %s 
                AND notification_type = %s AND is_read = 0
            """
            params = (user_id, org_id, notification_type)
        else:
            query = """
                SELECT COUNT(*) 
                FROM notifications 
                WHERE user_id = %s AND org_id = %s AND is_read = 0
            """
            params = (user_id, org_id)
        
        # print(f"🔍 QUERY: user_id={user_id}, org_id={org_id}, type={notification_type}")
        
        cur.execute(query, params)
        result = cur.fetchone()
        count = result[0] if result else 0  # ✅ Now this will work
        
        # print(f"📊 RESULT: Found {count} notifications")
        
        return count
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0
    finally:
        cur.close()
        conn.close()

def mark_notifications_as_read(user_id, org_id, notification_type):
    """
    Mark notifications as read when user visits a page
    
    Args:
        user_id: User ID
        org_id: Organization ID
        notification_type: Type of notification to mark as read
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE notifications 
            SET is_read = 1 
            WHERE user_id = %s AND org_id = %s 
            AND notification_type = %s AND is_read = 0
        """, (user_id, org_id, notification_type))
        conn.commit()
    except Exception as e:
        print(f"Error marking notifications as read: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()


def get_recent_notifications(user_id, org_id, limit=10):
    """
    Get recent notifications for a user (both read and unread)
    
    Args:
        user_id: User ID
        org_id: Organization ID
        limit: Maximum number of notifications to return
    
    Returns:
        list: List of notification dictionaries
    """
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cur.execute("""
            SELECT id, notification_type, reference_id, message, is_read, created_at
            FROM notifications 
            WHERE user_id = %s AND org_id = %s 
            ORDER BY created_at DESC
            LIMIT %s
        """, (user_id, org_id, limit))
        
        notifications = cur.fetchall()
        
        # Convert datetime to string for JSON serialization
        for notif in notifications:
            if notif['created_at']:
                notif['created_at'] = notif['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        return notifications
    except Exception as e:
        print(f"Error getting recent notifications: {e}")
        return []
    finally:
        cur.close()
        conn.close()


def delete_old_notifications(days=30):
    """
    Delete read notifications older than specified days
    Can be called from a scheduled task
    
    Args:
        days: Number of days to keep notifications
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            DELETE FROM notifications 
            WHERE is_read = 1 
            AND created_at < DATE_SUB(NOW(), INTERVAL %s DAY)
        """, (days,))
        deleted_count = cur.rowcount
        conn.commit()
        print(f"Deleted {deleted_count} old notifications")
        return deleted_count
    except Exception as e:
        print(f"Error deleting old notifications: {e}")
        conn.rollback()
        return 0
    finally:
        cur.close()
        conn.close()
 ######################forgot password routes######################################   
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        cursor.execute("SELECT * FROM register WHERE email = %s", (email,))
        user = cursor.fetchone()
        conn.close()

        if user:
            otp = generate_otp()  # Generate random 6-digit OTP
            success, error = send_otp_email(email, otp)

            if success:
                session['reset_email'] = email
                session['reset_otp'] = otp
                session['reset_otp_expiry'] = (datetime.now() + timedelta(minutes=5)).timestamp()

                flash('OTP sent to your email. Please check your inbox.')
                return redirect(url_for('verify_reset_otp'))
            else:
                flash(f"Error sending OTP: {error}")
        else:
            flash("Email not registered.")
    
    return render_template('forgot_password.html')

##############################verify reset OTP######################################

@app.route('/verify_reset_otp', methods=['GET', 'POST'])
def verify_reset_otp():
    if request.method == 'POST':
        otp_input = request.form.get('otp', '').strip()
        
        if 'reset_otp' not in session or 'reset_email' not in session:
            flash("Session expired. Please try again.")
            return redirect(url_for('forgot_password'))

        # Check if OTP has expired
        if time.time() > session.get('reset_otp_expiry', 0):
            flash("OTP expired. Please request a new one.")
            session.pop('reset_email', None)
            session.pop('reset_otp', None)
            session.pop('reset_otp_expiry', None)
            return redirect(url_for('forgot_password'))

        # Verify OTP
        if otp_input == session['reset_otp']:
            flash("OTP verified successfully. Please set a new password.")
            return redirect(url_for('reset_password'))
        else:
            flash("Invalid OTP. Please try again.")
    
    return render_template("verify_reset_otp.html")
##################################### reset password ######################################

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    # Ensure user has verified OTP first
    if 'reset_email' not in session:
        flash("Unauthorized access. Please start the password reset process again.")
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for('reset_password'))

        hashed_pw = generate_password_hash(new_password)
        email = session.get('reset_email')
        
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("UPDATE register SET password_hash = %s WHERE email = %s", (hashed_pw, email))
        conn.commit()
        conn.close()

        # Clear all reset session values
        session.pop('reset_email', None)
        session.pop('reset_otp', None)
        session.pop('reset_otp_expiry', None)

        flash("Password reset successful. You can now login with your new password.")
        return redirect(url_for('login'))

    return render_template('reset_password.html')



######################################registration routes######################################
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'role' not in session or session['role'] != 'admin':
        flash("Only admin can register new users.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role'].strip().lower()

        # Only collect license/contact if architect
        license_number = request.form.get('license_number') if role == 'architect' else None
        contact_no = request.form.get('contact_no', '').strip()

        # Check if email already exists
        try:
            conn = get_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            cursor.execute("SELECT email FROM register WHERE email = %s", (email,))
            existing_user = cursor.fetchone()
            
            if existing_user:
                flash('Email already exists.', 'error')
                conn.close()
                return redirect(url_for('register'))

            # Generate OTP
            otp = generate_otp()
            
            # Send OTP email
            success, error = send_otp_email(email, otp)
            
            if success:
                # Store registration data in session temporarily
                session['pending_registration'] = {
                    'name': name,
                    'email': email,
                    'password': password,
                    'role': role,
                    'license_number': license_number,
                    'contact_no': contact_no,
                    'otp': otp,
                    'otp_expiry': (datetime.now() + timedelta(minutes=5)).timestamp()
                }
                
                flash('OTP sent to the user\'s email. Please verify to complete registration.', 'success')
                return redirect(url_for('verify_registration_otp'))
            else:
                flash(f"Error sending OTP: {error}", 'error')
                conn.close()
                return redirect(url_for('register'))

        except Exception as e:
            flash(f'Registration failed: {e}', 'error')
            if conn:
                conn.close()
            return redirect(url_for('register'))

    return render_template('register.html')
#######################################login routes######################################
@app.route('/login', methods=['GET', 'POST'])

def login():

    if request.method == 'GET':
        session.pop('_flashes', None) 
  
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM register WHERE email=%s", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['name'] = user['name']
            session['org_id'] = user['org_id']
            
            flash('Login successful!')
            
            role = session['role']
            if role == 'admin':
                response = redirect(url_for('admin_dashboard'))
            elif role == 'site_engineer':
                response =redirect(url_for('site_engineer_dashboard'))
            elif role == 'architect':
                response = redirect(url_for('architect_dashboard'))
            elif role == 'accountant':
                response = redirect(url_for('accountant_dashboard'))
            else:
                flash('Invalid user role.')
                return redirect(url_for('login'))
            
        
            session.pop('_flashes', None)
            return response
        else:
            flash('Invalid email or password.')

    return render_template('login.html')

##########################################verify OTP######################################
# @app.route('/verify_otp', methods=['GET', 'POST'])
# def verify_otp():
#     if request.method == 'POST':
#         user_otp = request.form.get('otp', '').strip()
#         pending_user = session.get('pending_user')

#         if not pending_user:
#             flash("Session expired or invalid. Please login again.")
#             return redirect(url_for('login'))

#         # Check if OTP has expired
#         if time.time() > pending_user['otp_expiry']:
#             flash("OTP expired. Please login again.")
#             session.pop('pending_user', None)
#             return redirect(url_for('login'))

#         # Verify OTP
#         if user_otp == pending_user['otp']:
#             # OTP correct: promote to logged-in user
#             session['user_id'] = pending_user['id']
#             session['role'] = pending_user['role']
#             session['name'] = pending_user['name']
#             session['org_id'] = pending_user['org_id']
#             session.pop('pending_user', None)

#             flash('Login successful!')
            
#             # Redirect based on role
#             role = session['role']
#             if role == 'admin':
#                 response = redirect(url_for('admin_dashboard'))
#             elif role == 'site_engineer':
#                 response = redirect(url_for('site_engineer_dashboard'))
#             elif role == 'architect':
#                 response = redirect(url_for('architect_dashboard'))
#             elif role == 'accountant':
#                 response = redirect(url_for('accountant_dashboard'))
#             else:
#                 flash('Invalid user role.')
#                 return redirect(url_for('login'))
            
#             # Clear flash messages before redirecting
#             session.pop('_flashes', None)
#             return response
#         else:
#             flash("Invalid OTP. Please try again.")
            
#     return render_template("verify.html")
@app.route('/verify_registration_otp', methods=['GET', 'POST'])
def verify_registration_otp():
    if 'role' not in session or session['role'] != 'admin':
        flash("Only admin can register new users.")
        return redirect(url_for('login'))
    
    if 'pending_registration' not in session:
        flash("No pending registration found. Please start registration again.")
        return redirect(url_for('register'))
    
    if request.method == 'POST':
        otp_input = request.form.get('otp', '').strip()
        pending_data = session.get('pending_registration')
        
        if not pending_data:
            flash("Session expired. Please try again.")
            return redirect(url_for('register'))

        # Check if OTP has expired
        if time.time() > pending_data.get('otp_expiry', 0):
            flash("OTP expired. Please register again.")
            session.pop('pending_registration', None)
            return redirect(url_for('register'))

        # Verify OTP
        if otp_input == pending_data['otp']:
            # OTP is correct, proceed with registration
            try:
                conn = get_connection()
                cursor = conn.cursor(pymysql.cursors.DictCursor)

                # Get admin's org_id
                admin_id = session['user_id']
                cursor.execute("SELECT org_id FROM register WHERE id = %s", (admin_id,))
                admin_data = cursor.fetchone()
                
                if not admin_data:
                    flash("Unable to retrieve admin's organization.")
                    return redirect(url_for('register'))
                
                org_id = admin_data['org_id']

                # Hash password
                password_hash = generate_password_hash(pending_data['password'])

                # Insert user with org_id
                cursor.execute("""
                    INSERT INTO register (name, email, password_hash, role, contact_no, org_id)
                    VALUES (%s, %s, %s, %s, %s,%s)
                """, (
                    pending_data['name'], 
                    pending_data['email'], 
                    password_hash, 
                    pending_data['role'], 
                    pending_data['contact_no'],
                    org_id
                ))
                register_id = cursor.lastrowid
                conn.commit()

                # If architect, insert into architects table
                if pending_data['role'] == 'architect':
                    cursor.execute("""
                        INSERT INTO architects (name, email, license_number, contact_no, register_id, org_id)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        pending_data['name'], 
                        pending_data['email'], 
                        pending_data['license_number'], 
                        pending_data['contact_no'], 
                        register_id, 
                        org_id
                    ))
                    conn.commit()

                conn.close()
                
                # Clear pending registration data
                session.pop('pending_registration', None)
                
                flash('User registered successfully!', 'success')
                return redirect(url_for('register'))

            except pymysql.err.IntegrityError:
                conn.rollback()
                conn.close()
                session.pop('pending_registration', None)
                flash('Email already exists.', 'error')
                return redirect(url_for('register'))

            except Exception as e:
                conn.rollback()
                conn.close()
                session.pop('pending_registration', None)
                flash(f'Registration failed: {e}', 'error')
                return redirect(url_for('register'))
        else:
            flash("Invalid OTP. Please try again.", 'error')
    
    # Show OTP verification form
    return render_template("verify_registration_otp.html", email=session.get('pending_registration', {}).get('email'))
########################################admin routes######################################
@app.route('/admin1')

def admin_dashboard():
    if 'role' in session and session['role'] == 'admin':
        # Clear any lingering flash messages
        session.pop('_flashes', None)
        admin_name = session.get('name')
        return render_template('admin_dashboard.html', admin_name=admin_name)
    return redirect('/')


#########################################site engineer routes######################################

@app.route('/siteengineer/dashboard')

def site_engineer_dashboard():
    if session.get('role') != 'site_engineer':
        return redirect(url_for('login'))

    site_engineer_id = session['user_id']

    # Fetch site engineer's name
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("SELECT name FROM register WHERE id = %s", (site_engineer_id,))
    engineer = cur.fetchone()

    # Fetch sites assigned to this engineer
    cur.execute("SELECT * FROM sites WHERE site_engineer_id = %s", (site_engineer_id,))
    assigned_sites = cur.fetchall()

    # You can also fetch other dashboard data here if needed

    cur.close()
    conn.close()

    return render_template(
        'site_engineer_dashboard.html',
        engineer=engineer,
        assigned_sites=assigned_sites
    )

##########################################architect routes######################################

@app.route('/architect_dashboard', methods=['GET', 'POST'])
def architect_dashboard():
    if 'role' in session and session['role'] == 'architect':
        user_id = session['user_id']

        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)

        selected_project = None
        project_details = {}

        try:
            cur.execute("SELECT * FROM architects WHERE register_id = %s", (user_id,))
            architect = cur.fetchone()

            if not architect:
                return "Architect profile not found.", 404

            cur.execute("SELECT id, project_name FROM projects WHERE architect_id = %s", (user_id,))
            project_list = cur.fetchall()

            selected_project_id = request.form.get('selected_project_id') or request.args.get('project_id')
            
            if selected_project_id:
                cur.execute("SELECT * FROM projects WHERE id = %s AND architect_id = %s", (selected_project_id, user_id))
                selected_project = cur.fetchone()

                if selected_project:
                    details_tables = [
                        "design_details", "structural_details", "material_specifications",
                        "site_conditions", "utilities_services", "cost_estimation"
                    ]
                    for table in details_tables:
                        cur.execute(f"SELECT * FROM {table} WHERE project_id = %s", (selected_project_id,))
                        project_details[table] = cur.fetchone()

                    cur.execute("SELECT * FROM drawing_documents WHERE project_id = %s", (selected_project_id,))
                    project_details['drawing_documents'] = cur.fetchall()

        finally:
            conn.close()

        return render_template(
            "architect_dashboard.html",
            architect=architect,
            project_list=project_list,
            selected_project=selected_project,
            details=project_details
        )

    return redirect(url_for('login'))


# ✅ Additional helper function to clean up duplicate architects
@app.route('/cleanup_architects', methods=['POST'])
def cleanup_architects():
    """
    Helper function to clean up duplicate architect entries
    Call this once to fix your database
    """
    if 'role' in session and session['role'] == 'architect':
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        try:
            # Find duplicate architects by email
            cur.execute("""
                SELECT email, MIN(id) as keep_id, GROUP_CONCAT(id) as all_ids
                FROM architects 
                WHERE email IS NOT NULL 
                GROUP BY email 
                HAVING COUNT(*) > 1
            """)
            duplicates = cur.fetchall()
            
            for dup in duplicates:
                email = dup['email']
                keep_id = dup['keep_id']
                all_ids = dup['all_ids'].split(',')
                
                # Update all projects to use the kept architect ID
                for old_id in all_ids:
                    if int(old_id) != keep_id:
                        cur.execute("""
                            UPDATE projects 
                            SET architect_id = %s 
                            WHERE architect_id = %s
                        """, (keep_id, old_id))
                
                # Delete duplicate architect entries
                cur.execute("""
                    DELETE FROM architects 
                    WHERE email = %s AND id != %s
                """, (email, keep_id))
            
            conn.commit()
            return "Cleanup completed successfully!"
            
        except Exception as e:
            conn.rollback()
            return f"Error during cleanup: {e}"
        finally:
            conn.close()
    
    return "Unauthorized"

############################################## accountant routes ######################################
@app.route('/accountant_dashboard')
def accountant_dashboard():
    if 'role' not in session or session['role'] != 'accountant':
        return redirect(url_for('login'))

    accountant_id = session['user_id']
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    cur.execute("""
        SELECT DISTINCT
            p.id AS project_id,
            p.project_name,
            i.id AS invoice_id,
            i.invoice_number,
            i.vendor_name,
            i.total_amount,
            i.gst_amount,
            i.generated_on,
            i.status,
            i.pdf_filename,
            i.bill_to_name,
            i.bill_to_address,
            i.subtotal,
            se.name AS site_engineer_name
        FROM accountant_projects ap
        JOIN projects p ON ap.project_id = p.id
        LEFT JOIN invoices i ON i.project_id = p.id AND i.status = 'Approved'
        LEFT JOIN register se ON i.site_engineer_id = se.id
        WHERE ap.accountant_id = %s AND ap.org_id = %s
        ORDER BY p.project_name, i.generated_on DESC
    """, (accountant_id, session['org_id']))
    results = cur.fetchall()

    # Organize the data by project
    projects_with_invoices = {}
    for row in results:
        project_id = row['project_id']
        if project_id not in projects_with_invoices:
            projects_with_invoices[project_id] = {
                'project_name': row['project_name'],
                'invoices': [],
                'seen_invoice_ids': set()
            }
        if row['invoice_id'] and row['invoice_id'] not in projects_with_invoices[project_id]['seen_invoice_ids']:
            projects_with_invoices[project_id]['invoices'].append(row)
            projects_with_invoices[project_id]['seen_invoice_ids'].add(row['invoice_id'])

    # Clean up helper set before passing to template
    for project in projects_with_invoices.values():
        project.pop('seen_invoice_ids', None)

    cur.close()
    conn.close()

    return render_template(
        'accountant_dashboard.html',
        projects_with_invoices=projects_with_invoices
    )
@app.route('/accountant/invoices')
def accountant_view_invoices():
    if 'role' not in session or session['role'] != 'accountant':
        return redirect(url_for('login'))
    
    accountant_id = session['user_id']
    org_id = session['org_id']
    
    mark_notifications_as_read(accountant_id, org_id, 'invoice_approved')
    
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # ✅ FIXED: Only fetch invoices strictly linked to assigned projects
    cur.execute("""
        SELECT DISTINCT
            p.id AS project_id,
            p.project_name,
            i.id AS invoice_id,
            i.invoice_number,
            i.vendor_name,
            i.total_amount,
            i.gst_amount,
            i.generated_on,
            i.status,
            i.pdf_filename,
            i.bill_to_name,
            i.bill_to_address,
            i.subtotal,
            se.name AS site_engineer_name
        FROM accountant_projects ap
        JOIN projects p ON ap.project_id = p.id
        LEFT JOIN invoices i ON i.project_id = p.id AND i.status = 'Approved'
        LEFT JOIN register se ON i.site_engineer_id = se.id
        WHERE ap.accountant_id = %s AND ap.org_id = %s
        ORDER BY p.project_name, i.generated_on DESC
    """, (accountant_id, org_id))
    results = cur.fetchall()

    projects_with_invoices = {}
    for row in results:
        project_id = row['project_id']
        if project_id not in projects_with_invoices:
            projects_with_invoices[project_id] = {
                'project_name': row['project_name'],
                'invoices': [],
                'seen_invoice_ids': set()
            }
        if row['invoice_id'] and row['invoice_id'] not in projects_with_invoices[project_id]['seen_invoice_ids']:
            projects_with_invoices[project_id]['invoices'].append(row)
            projects_with_invoices[project_id]['seen_invoice_ids'].add(row['invoice_id'])

    for project in projects_with_invoices.values():
        project.pop('seen_invoice_ids', None)

    cur.close()
    conn.close()

    return render_template(
        'accountant_view_invoices.html',
        projects_with_invoices=projects_with_invoices
    )
############################### Architect Project Management Routes ######################################
@app.route('/add_design_details', methods=['POST'])
def add_design_details():
    if 'role' in session and session['role'] == 'architect':
        project_id = request.form['project_id']
        building_usage = request.form['building_usage']
        num_floors = request.form['num_floors']
        area_sqft = request.form['area_sqft']
        plot_area = request.form['plot_area']
        fsi = request.form['fsi']

        conn = get_connection()
        cur = conn.cursor()

        # Check if design details already exist for this project
        cur.execute("SELECT id FROM design_details WHERE project_id = %s AND org_id = %s",
                    (project_id, session['org_id']))
        existing = cur.fetchone()
        print("existing  : ",existing)

        if existing:
            # Update existing record
            cur.execute("""
                UPDATE design_details
                SET building_usage = %s,
                    num_floors = %s,
                    area_sqft = %s,
                    plot_area = %s,
                    fsi = %s
                WHERE project_id = %s AND org_id = %s
            """, (building_usage, num_floors, area_sqft, plot_area, fsi, project_id, session['org_id']))
            flash("Design details updated successfully.")
        else:
            # Insert new record if not present
            cur.execute("""
                INSERT INTO design_details (project_id, building_usage, num_floors, area_sqft, plot_area, fsi, org_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (project_id, building_usage, num_floors, area_sqft, plot_area, fsi, session['org_id']))
            flash("Design details added successfully.")

        conn.commit()
        conn.close()
        return redirect(url_for('architect_dashboard', project_id=project_id))

    return redirect(url_for('login'))

########################################### Add Structural Details ######################################

@app.route('/add_structural_details', methods=['POST'])
def add_structural_details():
    if 'role' in session and session['role'] == 'architect':
        project_id = request.form['project_id']
        foundation_type = request.form['foundation_type']
        framing_system = request.form['framing_system']
        slab_type = request.form['slab_type']
        beam_details = request.form['beam_details']
        load_calculation = request.form['load_calculation']

        conn = get_connection()
        cur = conn.cursor()

        # Check if structural details already exist for this project and org
        cur.execute("SELECT id FROM structural_details WHERE project_id = %s AND org_id = %s",
                    (project_id, session['org_id']))
        existing = cur.fetchone()

        if existing:
            # --- Update existing record ---
            cur.execute("""
                UPDATE structural_details
                SET foundation_type = %s,
                    framing_system = %s,
                    slab_type = %s,
                    beam_details = %s,
                    load_calculation = %s
                WHERE project_id = %s AND org_id = %s
            """, (foundation_type, framing_system, slab_type, beam_details, load_calculation, project_id, session['org_id']))
            flash("Structural details updated successfully.")
        else:
            # --- Insert new record ---
            cur.execute("""
                INSERT INTO structural_details (project_id, foundation_type, framing_system, slab_type, beam_details, load_calculation, org_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (project_id, foundation_type, framing_system, slab_type, beam_details, load_calculation, session['org_id']))
            flash("Structural details added successfully.")

        conn.commit()
        conn.close()

        return redirect(url_for('architect_dashboard', project_id=project_id))

    return redirect(url_for('login'))


########################################## Add Material Specifications ######################################

@app.route('/add_material_specification', methods=['POST'])
def add_material_specification():
    if 'role' in session and session['role'] == 'architect':
        project_id = request.form['project_id']
        primary_material = request.form['primary_material']
        wall_material = request.form['wall_material']
        roofing_material = request.form['roofing_material']
        flooring_material = request.form['flooring_material']
        fire_safety_materials = request.form['fire_safety_materials']

        conn = get_connection()
        cur = conn.cursor()

        # Check if material specification already exists for this project and org
        cur.execute("SELECT id FROM material_specifications WHERE project_id = %s AND org_id = %s",
                    (project_id, session['org_id']))
        existing = cur.fetchone()

        if existing:
            # --- Update existing record ---
            cur.execute("""
                UPDATE material_specifications
                SET primary_material = %s,
                    wall_material = %s,
                    roofing_material = %s,
                    flooring_material = %s,
                    fire_safety_materials = %s
                WHERE project_id = %s AND org_id = %s
            """, (primary_material, wall_material, roofing_material, flooring_material, fire_safety_materials, project_id, session['org_id']))
            flash("Material specifications updated successfully.")
        else:
            # --- Insert new record ---
            cur.execute("""
                INSERT INTO material_specifications (project_id, primary_material, wall_material, roofing_material, flooring_material, fire_safety_materials, org_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (project_id, primary_material, wall_material, roofing_material, flooring_material, fire_safety_materials, session['org_id']))
            flash("Material specifications added successfully.")

        conn.commit()
        conn.close()
        return redirect(url_for('architect_dashboard', project_id=project_id))

    return redirect(url_for('login'))

    
import os
from werkzeug.utils import secure_filename
from flask import request, redirect, flash, url_for, session

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

############################### Upload Drawing Documents ######################################

@app.route('/upload_layout', methods=['POST'])
def upload_layout():
    if 'role' in session and session['role'] == 'architect':
        file = request.files.get('layout_file')
        layout_type = request.form.get('layout_type')
        document_title = request.form.get('document_title')
        project_id = request.form.get('project_id')
        uploaded_by = session.get('user_id')

        required_types = ['Architectural Layout', 'Elevation Drawing', 'Section/Structural', 'Electrical', 'Plumbing/Sanitation']

        if layout_type in required_types and (not file or not allowed_file(file.filename)):
            flash("PDF file is required for selected layout type.")
            return redirect(url_for('architect_dashboard', project_id=project_id))

        file_path = ""
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            file_path = os.path.join('uploads', filename).replace("\\", "/")
        elif layout_type in required_types:
            flash("File upload failed or missing.")
            return redirect(url_for('architect_dashboard', project_id=project_id))

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id FROM drawing_documents
            WHERE project_id = %s AND layout_type = %s
        """, (project_id, layout_type))
        existing = cur.fetchone()

        if existing:
            # Update existing document
            cur.execute("""
                UPDATE drawing_documents
                SET document_title = %s,
                    file_path = %s,
                    uploaded_by = %s,
                    uploaded_on = NOW()
                WHERE project_id = %s AND layout_type = %s
            """, (document_title, file_path, uploaded_by, project_id, layout_type))
        else:
            # Insert new document
            cur.execute("""
                INSERT INTO drawing_documents (
                    project_id, layout_type, document_title, file_path, uploaded_by, org_id
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (project_id, layout_type, document_title, file_path, uploaded_by, session['org_id']))

        conn.commit()
        conn.close()

        flash("Drawing document uploaded successfully.")
        return redirect(url_for('architect_dashboard', project_id=project_id))

    flash("Unauthorized access.")
    return redirect(url_for('login'))


################################# site conditions #######################################
@app.route('/upload_site_conditions', methods=['POST'])
def upload_site_conditions():
    if 'role' in session and session['role'] == 'architect':
        soil_file = request.files.get('soil_report')
        topo_file = request.files.get('topo_map')
        water_table_level = request.form.get('water_table_level')
        project_id = request.form.get('project_id')

        soil_path = ""
        topo_path = ""

        if soil_file and allowed_file(soil_file.filename):
            soil_filename = secure_filename("soil_" + soil_file.filename)
            soil_save_path = os.path.join(app.config['UPLOAD_FOLDER'], soil_filename)
            soil_file.save(soil_save_path)
            soil_path = os.path.join('uploads', soil_filename).replace("\\", "/")

        if topo_file and allowed_file(topo_file.filename):
            topo_filename = secure_filename("topo_" + topo_file.filename)
            topo_save_path = os.path.join(app.config['UPLOAD_FOLDER'], topo_filename)
            topo_file.save(topo_save_path)
            topo_path = os.path.join('uploads', topo_filename).replace("\\", "/")

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO site_conditions (project_id, soil_report_path, water_table_level, topo_counter_map_path, org_id)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                soil_report_path = VALUES(soil_report_path),
                water_table_level = VALUES(water_table_level),
                topo_counter_map_path = VALUES(topo_counter_map_path)
        """, (project_id, soil_path, water_table_level, topo_path, session['org_id']))
        conn.commit()
        conn.close()

        flash("Site condition documents uploaded successfully.")
        return redirect(url_for('architect_dashboard', project_id=project_id))

    flash("Unauthorized access.")
    return redirect(url_for('login'))


#############################################logout route######################################

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
# ############--- SITE ENGINEER DASHBOARD: Add Worker ---##############
#@app.route('/addworker', methods=['GET', 'POST'])
#def add_worker():
#    if session.get('role') != 'site_engineer':
 #       return redirect(url_for('login'))

  #  if request.method == 'POST':
  #      name = request.form['name']
  #      contact_no = request.form['contact_no']
  #      aadhar_no = request.form['aadhar']
  #      try:
 #           cursor.execute("INSERT INTO workers (name, contact_no, aadhar_no) VALUES (%s, %s, %s)",
 #                          (name, contact_no, aadhar_no))
 #           db.commit()
 #           flash('Worker added successfully!')
 #           return redirect(url_for('site_engineer_workers'))  # Redirect to workers list
  #      except pymysql.err.IntegrityError:
 ##   return render_template('add_worker.html')

# --- ADMIN DASHBOARD: View Workers ---
#@app.route('/admin/dashboard')
#def admin():
#    if session.get('role') != 'admin':
#        return redirect(url_for('login'))
#cursor.execute("SELECT * FROM workers")
  #  workers = cursor.fetchall()
 #   return render_template('view_workers.html', workers=workers)

############################# Submit Worker Report ######################################
@app.route('/submit_worker_report', methods=['GET', 'POST'])
def submit_worker_report():
    if 'role' not in session or session['role'] != 'site_engineer':
        return redirect(url_for('login'))

    site_engineer_id = session['user_id']
    org_id = session['org_id']
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # Handle POST submission
    if request.method == 'POST':
        project_id = request.form['project_id']
        worker_count = request.form['worker_count']
        report_date = request.form['report_date']

        try:
            cur.execute("""
                INSERT INTO daily_worker_report (site_engineer_id, project_id, worker_count, report_date, org_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (site_engineer_id, project_id, worker_count, report_date, org_id))
            
            report_id = cur.lastrowid
            conn.commit()
            
            # ========== NOTIFICATION CODE ==========
            # Get project name for notification message
            cur.execute("SELECT project_name FROM projects WHERE id = %s", (project_id,))
            project = cur.fetchone()
            project_name = project['project_name'] if project else 'Unknown Project'
            
            # Get all admins in the organization
            cur.execute("""
                SELECT id FROM register 
                WHERE role = 'admin' AND org_id = %s
            """, (org_id,))
            admins = cur.fetchall()
            
            # Create notification for each admin
            for admin in admins:
                create_notification(
                    user_id=admin['id'],
                    org_id=org_id,
                    notification_type='worker_report_new',
                    reference_id=report_id,
                    message=f'Worker report submitted: {worker_count} workers at {project_name} on {report_date} by {session.get("name")}'
                )
            # ========================================
            
            flash('Worker report submitted successfully.')
            
        except Exception as e:
            conn.rollback()
            flash(f'Error submitting report: {str(e)}')
        finally:
            cur.close()
            conn.close()
            
        return redirect(url_for('submit_worker_report'))

    # Fetch only projects assigned to this site engineer (by admin)
    cur.execute("""
        SELECT p.*
        FROM projects p
        JOIN sites s ON p.project_name = s.site_name
        WHERE s.site_engineer_id = %s AND s.org_id = %s
    """, (site_engineer_id, org_id))
    projects = cur.fetchall()
    
    cur.close()
    conn.close()

    return render_template('submit_worker_report.html', projects=projects)

########################################## View Worker Reports ######################################
@app.route('/view_worker_reports')
def view_worker_reports():
    if 'role' not in session or session['role'] not in ['admin', 'site_engineer']:
        return redirect(url_for('login'))

    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    user_id = session.get('user_id')
    org_id = session.get('org_id')
    
    # ✅ ADD THIS - Mark worker report notifications as read when admin visits this page
    if session['role'] == 'admin':
        mark_notifications_as_read(user_id, org_id, 'worker_report_new')

    # Get the logged-in user's org_id
    cur.execute("SELECT org_id FROM register WHERE id = %s", (user_id,))
    user_data = cur.fetchone()

    if not user_data:
        flash("User organization not found.", "danger")
        return redirect(url_for('login'))

    org_id = user_data['org_id']

    # Step 2: Role-based view
    if session['role'] == 'admin':
        # Admin: Show reports for their org_id
        cur.execute("""
            SELECT 
                dr.id, 
                r.name AS site_engineer, 
                p.project_name, 
                dr.worker_count, 
                dr.report_date,
                dr.org_id
            FROM daily_worker_report dr
            JOIN projects p ON dr.project_id = p.id
            JOIN register r ON dr.site_engineer_id = r.id
            WHERE dr.org_id = %s
            ORDER BY dr.report_date DESC
        """, (org_id,))
        reports = cur.fetchall()

    else:
        # Site Engineer: Show only their own reports for their org_id
        # First get the site engineer's name
        cur.execute("SELECT name FROM register WHERE id = %s", (user_id,))
        engineer = cur.fetchone()
        engineer_name = engineer['name'] if engineer else 'Unknown'

        # Fetch their worker reports
        cur.execute("""
            SELECT 
                dr.id, 
                p.project_name, 
                dr.worker_count, 
                dr.report_date
            FROM daily_worker_report dr
            JOIN projects p ON dr.project_id = p.id
            WHERE dr.site_engineer_id = %s AND dr.org_id = %s
            ORDER BY dr.report_date DESC
        """, (user_id, org_id))
        reports = cur.fetchall()

        # Inject site engineer name into each report
        for report in reports:
            report['site_engineer'] = engineer_name

    return render_template('view_worker_reports.html', reports=reports)




########################################## Add Inventory ######################################
@app.route('/add_inventory', methods=['GET', 'POST'])
def add_inventory():
    if 'role' not in session or session['role'] != 'site_engineer':
        return redirect(url_for('login'))

    if 'org_id' not in session or 'user_id' not in session:
        flash("Unauthorized access", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Get form data - now handling arrays
            material_descriptions = request.form.getlist('material_description[]')
            quantities = request.form.getlist('quantity[]')
            status = request.form['status']
            inv_date = request.form['date']
            org_id = session['org_id']
            site_engineer_id = session['user_id']
            engineer_name = session.get('name', 'Engineer')  # ✅ Get engineer name
            
            # Validate that we have matching arrays
            if len(material_descriptions) != len(quantities):
                flash('Error: Mismatched material descriptions and quantities', 'danger')
                return redirect(url_for('add_inventory'))
            
            # Validate that we have at least one item
            if not material_descriptions or not material_descriptions[0].strip():
                flash('Error: At least one material description is required', 'danger')
                return redirect(url_for('add_inventory'))
            
            # Insert multiple items in a transaction
            query = """
                INSERT INTO inventory (material_description, quantity, date, status, org_id, site_engineer_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            items_added = 0
            inventory_items = []  # ✅ Store items for notification message
            
            for i in range(len(material_descriptions)):
                desc = material_descriptions[i].strip()
                qty_str = quantities[i].strip()
                
                # Skip empty entries
                if not desc or not qty_str:
                    continue
                
                try:
                    qty = int(qty_str)
                    if qty < 0:
                        flash(f'Error: Quantity cannot be negative for item {i+1}', 'danger')
                        conn.rollback()
                        return redirect(url_for('add_inventory'))
                        
                except ValueError:
                    flash(f'Error: Invalid quantity for item {i+1}', 'danger')
                    conn.rollback()
                    return redirect(url_for('add_inventory'))
                
                # Insert the item
                cursor.execute(query, (desc, qty, inv_date, status, org_id, site_engineer_id))
                items_added += 1
                inventory_items.append(f"{desc} (Qty: {qty})")  # ✅ Track items
            
            if items_added == 0:
                flash('Error: No valid items to add', 'danger')
                conn.rollback()
                return redirect(url_for('add_inventory'))
            
            conn.commit()
            
            # ========== NOTIFICATION CODE ==========
            # Get all admins in the organization
            cursor.execute("""
                SELECT id FROM register 
                WHERE role = 'admin' AND org_id = %s
            """, (org_id,))
            admins = cursor.fetchall()
            
            # Create notification message
            if items_added == 1:
                notification_message = f'{engineer_name} added inventory: {inventory_items[0]}'
            else:
                # Show first 2 items, then "and X more"
                if items_added <= 3:
                    items_preview = ', '.join(inventory_items)
                else:
                    items_preview = ', '.join(inventory_items[:2]) + f' and {items_added - 2} more items'
                notification_message = f'{engineer_name} added {items_added} inventory items: {items_preview}'
            
            # Create notification for each admin
            for admin in admins:
                create_notification(
                    user_id=admin['id'],
                    org_id=org_id,
                    notification_type='inventory_added',
                    reference_id=None,  # Multiple items, no single reference
                    message=notification_message
                )
            # ========================================
            
            # Success message based on number of items added
            if items_added == 1:
                flash('1 inventory item added successfully!', 'success')
            else:
                flash(f'{items_added} inventory items added successfully!', 'success')
                
            return redirect(url_for('add_inventory'))

        except Exception as e:
            conn.rollback()
            flash(f'Error adding inventory: {str(e)}', 'danger')
            return redirect(url_for('add_inventory'))

        finally:
            cursor.close()
            conn.close()

    return render_template('add_inventory.html')


######################################## View Inventory ######################################

@app.route('/view_inventory')
def view_inventory():
    if 'org_id' not in session:
        flash("Unauthorized access", "danger")
        return redirect(url_for('login'))

    org_id = session['org_id']
    user_id = session.get('user_id')
    role = session.get('role')
    
    # ✅ Mark inventory notifications as read for admins
    if role == 'admin':
        mark_notifications_as_read(user_id, org_id, 'inventory_added')
    
    db = get_connection()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    cursor.execute("""
        SELECT 
            inventory.*,
            register.name AS site_engineer_name
        FROM inventory
        JOIN register ON inventory.site_engineer_id = register.id
        WHERE inventory.org_id = %s
        ORDER BY inventory.date DESC
    """, (org_id,))
    
    inventory = cursor.fetchall()

    response = make_response(render_template('view_inventory.html', inventory=inventory))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    cursor.close()
    db.close()
    
    return response
########################---assign sites---#######################################
@app.route('/assign_site', methods=['GET', 'POST'])
def assign_site():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    db = get_connection()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    cursor.execute(
        "SELECT id, name FROM register WHERE role = 'site_engineer' AND org_id = %s",
        (session['org_id'],)
    )
    engineers = cursor.fetchall()

    if request.method == 'POST':
        site_name = request.form['site_name'].strip()
        location = request.form['location'].strip()
        engineer_id = request.form['site_engineer_id']

        # ✅ Check: same site_name + same site_engineer_id already exists?
        cursor.execute(
            "SELECT site_id FROM sites WHERE LOWER(site_name) = LOWER(%s) AND site_engineer_id = %s AND org_id = %s",
            (site_name, engineer_id, session['org_id'])
        )
        existing = cursor.fetchone()

        if existing:
            flash('This site name is already assigned to this Project Manager.', 'error')
            cursor.close()
            db.close()
            return render_template('assign_site.html', engineers=engineers)

        try:
            # ✅ Insert the site
            cursor.execute(
                "INSERT INTO sites (site_name, location, site_engineer_id, org_id) VALUES (%s, %s, %s, %s)",
                (site_name, location, engineer_id, session['org_id'])
            )
            site_id = cursor.lastrowid
            db.commit()
            
            # ========== NOTIFICATION CODE ==========
            # Create notification for site engineer
            create_notification(
                user_id=engineer_id,
                org_id=session['org_id'],
                notification_type='project_assigned',
                reference_id=site_id,
                message=f'New site assigned: {site_name} at {location}'
            )
            # ========================================
            
            flash('Site assigned successfully.', 'success')
            
        except Exception as e:
            db.rollback()
            flash(f'Error assigning site: {str(e)}', 'error')
        finally:
            cursor.close()
            db.close()
            
        return redirect(url_for('assign_site'))

    cursor.close()
    db.close()
    return render_template('assign_site.html', engineers=engineers)


# ✅ AJAX endpoint — checks duplicate based on site_name + site_engineer_id
@app.route('/check_duplicate_site', methods=['POST'])
def check_duplicate_site():
    data = request.get_json()
    site_name   = data.get('site_name', '').strip()
    engineer_id = data.get('site_engineer_id', '')

    if not site_name or not engineer_id:
        return jsonify({ "duplicate": False })

    db = get_connection()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    cursor.execute(
        "SELECT site_id FROM sites WHERE LOWER(site_name) = LOWER(%s) AND site_engineer_id = %s AND org_id = %s",
        (site_name, engineer_id, session['org_id'])
    )
    exists = cursor.fetchone()
    db.close()

    return jsonify({ "duplicate": exists is not None })

################################--- View Assigned Sites ---###################

@app.route('/view_assigned_sites')
def view_assigned_sites():
    if session.get('role') != 'site_engineer':
        return redirect(url_for('login'))

    engineer_id = session['user_id']  # Make sure user_id is set on login
    mark_notifications_as_read(
        user_id=session['user_id'],
        org_id=session['org_id'],
        notification_type='project_assigned'
    )

    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM sites WHERE site_engineer_id = %s", (engineer_id,))
    sites = cursor.fetchall()
    conn.close()

    return render_template('view_assigned_sites.html', sites=sites)


######################## 🌟 Upload Progress Report (SITE ENGINEER)###################
@app.route('/upload_progress', methods=['GET', 'POST'])
def upload_progress():
    if session.get('role') != 'site_engineer':
        return redirect(url_for('login'))

    site_engineer_id = session['user_id']

    if request.method == 'POST':
        site_id = request.form['site_id']
        progress = request.form['progress']
        remark = request.form['remark']
        today = date.today()

        # Image upload
        img = request.files.get('image')
        img_filename = None
        if img and img.filename:
            ext = img.filename.rsplit('.', 1)[1].lower()
            if ext in ['jpg', 'jpeg', 'png', 'gif']:
                img_filename = f"{int(time.time())}_{secure_filename(img.filename)}"
                img.save(os.path.join(UPLOAD_FOLDER_PROGRESS, img_filename))
                print("DEBUG: Image saved as", img_filename)
            else:
                print("DEBUG: Invalid image format")
        else:
            print("DEBUG: No image uploaded")

        # PDF upload
        pdf = request.files.get('pdf')
        pdf_filename = None
        if pdf and pdf.filename:
            ext = pdf.filename.rsplit('.', 1)[1].lower()
            if ext == 'pdf':
                pdf_filename = f"{int(time.time())}_{secure_filename(pdf.filename)}"
                pdf.save(os.path.join(UPLOAD_FOLDER_PROGRESS, pdf_filename))
                print("DEBUG: PDF saved as", pdf_filename)
            else:
                print("DEBUG: Invalid PDF format")
        else:
            print("DEBUG: No PDF uploaded")

        # Insert into DB
        db = get_connection()  # ✅ Correctly get connection
        cursor = db.cursor(pymysql.cursors.DictCursor)  # ✅ Get cursor from connection
        cursor.execute("""
            INSERT INTO progress_reports 
            (site_id, progress_percent, image_path, pdf_path, report_date, remark,org_id) 
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (site_id, progress, img_filename, pdf_filename, today, remark, session['org_id']))
        db.commit()
        # ========== ADD THIS NOTIFICATION CODE ==========
        # Get site details
        cursor.execute("""
            SELECT site_name FROM sites WHERE site_id = %s
        """, (site_id,))
        site_data = cursor.fetchone()
        site_name = site_data['site_name'] if site_data else 'Unknown Site'
        
        # Get all admins
        cursor.execute("""
            SELECT id FROM register 
            WHERE role = 'admin' AND org_id = %s
        """, (session['org_id'],))
        admins = cursor.fetchall()
        
        for admin in admins:
            create_notification(
                user_id=admin['id'],
                org_id=session['org_id'],
                notification_type='progress_report',
                reference_id=site_id,
                message=f'Progress report uploaded for {site_name}: {progress}% complete by {session.get("name")}'
            )
        db.close()
        flash('Progress report uploaded successfully!', 'success')
        return redirect(url_for('upload_progress'))

    # GET method: fetch assigned sites
    db = get_connection()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM sites WHERE site_engineer_id = %s and org_id = %s", (site_engineer_id,session['org_id']))
    sites = cursor.fetchall()
    db.close()

    return render_template('upload_progress.html', sites=sites)


################################### View Progress Reports (ADMIN)###############################################
@app.route('/view_progress')
def view_progress():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    

    admin_id = session['user_id']
    org_id = session['org_id']

    mark_notifications_as_read(admin_id, org_id, 'progress_report')

    db = get_connection()
    cursor = db.cursor(pymysql.cursors.DictCursor)


    # Use the correct SQL order: WHERE before ORDER BY
    # Assuming org_id is in the sites table
    query = """
        SELECT pr.*, s.site_name, pr.report_date AS upload_date
        FROM progress_reports pr
        JOIN sites s ON pr.site_id = s.site_id
        WHERE s.org_id = %s
        ORDER BY pr.report_date DESC
    """

    cursor.execute(query, (session['org_id'],))
    reports = cursor.fetchall()

    return render_template('view_progress.html', reports=reports)


# ✅ Vendor Inventory with PDF quotes by site engineer & admin approval

import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER_VENDOR = 'static/vendor_quotes'
os.makedirs(UPLOAD_FOLDER_VENDOR, exist_ok=True)
ALLOWED_EXT = {'pdf'}

def allowed(filename: str) -> bool:
  return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

####################################add_vendor_inventory######################################## 
@app.route('/add_vendor_inventory', methods=['GET', 'POST'])
def add_vendor_inventory():
    if session.get('role') != 'site_engineer':
        return redirect(url_for('login'))

    if request.method == 'POST':
        materials  = request.form.getlist('material_description[]')
        quantities = request.form.getlist('quantity[]')
        statuses   = request.form.getlist('status[]')
        vendors    = request.form.getlist('vendor_name[]')
        v_types    = request.form.getlist('vendor_type[]')
        files      = request.files.getlist('quotation[]')

        if not materials:
            flash('No items submitted.', 'danger')
            return redirect(url_for('add_vendor_inventory'))

        # ✅ Get submitter info
        site_engineer_id = session['user_id']
        org_id = session['org_id']

        db = get_connection()
        cursor = db.cursor(pymysql.cursors.DictCursor)

        try:
            added = 0
            
            for i in range(len(materials)):
                if not materials[i].strip():
                    continue

                file = files[i]
                filename = None
                
                if file and allowed(file.filename):
                    filename = f"{int(time.time())}_{secure_filename(file.filename)}"
                    file.save(os.path.join(UPLOAD_FOLDER_VENDOR, filename))
                else:
                    db.rollback()
                    cursor.close()
                    db.close()
                    flash('Please upload a valid PDF for every item.', 'danger')
                    return redirect(url_for('add_vendor_inventory'))

                # ✅ Insert with site_engineer_id
                cursor.execute("""
                    INSERT INTO vendor_inventory
                    (material_description, quantity, date, status,
                     vendor_name, vendor_type, vendor_quotation_pdf, org_id, site_engineer_id)
                    VALUES (%s, %s, CURDATE(), %s, %s, %s, %s, %s, %s)
                """, (
                    materials[i],
                    int(quantities[i]),
                    statuses[i],
                    vendors[i],
                    v_types[i],
                    filename,
                    org_id,
                    site_engineer_id
                ))
                
                added += 1

            db.commit()

            # Notify admins about pending items
            if added > 0:
                cursor.execute("""
                    SELECT id FROM register 
                    WHERE role = 'admin' AND org_id = %s
                """, (org_id,))
                admins = cursor.fetchall()
                
                summary = f'{added} vendor inventory item(s) submitted for approval by {session.get("name")}'
                
                for admin in admins:
                    create_notification(
                        user_id=admin['id'],
                        org_id=org_id,
                        notification_type='vendor_pending',
                        reference_id=None,
                        message=summary
                    )

            flash(f'{added} item(s) added successfully!', 'success')

        except Exception as e:
            db.rollback()
            print(f"Error in add_vendor_inventory: {e}")
            import traceback
            traceback.print_exc()
            flash(f'Error adding vendor inventory: {str(e)}', 'danger')
            
        finally:
            cursor.close()
            db.close()

        return redirect(url_for('add_vendor_inventory'))

    return render_template('add_vendor_inventory.html')

###################### --- Admin View Vendor Inventory --- ####################################################

@app.route('/admin/vendor_inventory', methods=['GET', 'POST'])
def admin_vendor_inventory():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    admin_id = session['user_id']
    org_id = session.get('org_id')
    mark_notifications_as_read(admin_id, org_id, 'vendor_pending')

    db = get_connection()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    if request.method == 'POST':
        rec_id = request.form['id']
        remark = request.form['remark']
        approval = request.form['approval']

        try:
            # ✅ This will now work because site_engineer_id exists
            cursor.execute("""
                SELECT 
                    material_description, 
                    vendor_name, 
                    quantity,
                    site_engineer_id
                FROM vendor_inventory
                WHERE id = %s AND org_id = %s
            """, (rec_id, org_id))
            vendor_data = cursor.fetchone()

            # Update record
            cursor.execute("""
                UPDATE vendor_inventory 
                SET admin_remark=%s, admin_approval=%s 
                WHERE id=%s AND org_id=%s
            """, (remark, approval, rec_id, org_id))
            db.commit()
            
            # ========== NOTIFICATION - ONLY SUBMITTER ==========
            if vendor_data and vendor_data.get('site_engineer_id'):
                material_desc = vendor_data['material_description']
                vendor_name = vendor_data['vendor_name']
                quantity = vendor_data['quantity']
                submitter_id = vendor_data['site_engineer_id']
                
                if approval.lower() == 'approved':
                    notification_message = f'Vendor item "{material_desc}" (Qty: {quantity}) from {vendor_name} has been approved'
                    notification_type = 'vendor_approved'
                elif approval.lower() == 'rejected':
                    notification_message = f'Vendor item "{material_desc}" (Qty: {quantity}) from {vendor_name} has been rejected'
                    notification_type = 'vendor_rejected'
                else:
                    notification_message = f'Vendor item "{material_desc}" (Qty: {quantity}) from {vendor_name} status updated to {approval}'
                    notification_type = 'vendor_status_updated'
                
                if remark and remark.strip():
                    notification_message += f'. Remark: {remark}'
                
                # ✅ NOTIFY ONLY THE SUBMITTER
                create_notification(
                    user_id=submitter_id,
                    org_id=org_id,
                    notification_type=notification_type,
                    reference_id=rec_id,
                    message=notification_message
                )
            # ===================================================
            
            flash(f'Vendor inventory {approval.lower()} successfully.', 'success')
            
        except Exception as e:
            db.rollback()
            flash(f'Error updating vendor inventory: {str(e)}', 'danger')
        finally:
            cursor.close()
            db.close()
        
        active_tab = request.args.get('tab', 'all')
        return redirect(url_for('admin_vendor_inventory', tab=active_tab))

    # GET request
    active_tab = request.args.get('tab', 'all')

    cursor.execute("""
        SELECT * FROM vendor_inventory 
        WHERE org_id = %s
        ORDER BY 
            CASE admin_approval
                WHEN 'pending' THEN 1
                WHEN 'approved' THEN 2
                WHEN 'rejected' THEN 3
            END,
            id DESC
    """, (org_id,))
    
    all_inventory = cursor.fetchall()
    
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN admin_approval = 'pending' THEN 1 ELSE 0 END) as pending_count,
            SUM(CASE WHEN admin_approval = 'approved' THEN 1 ELSE 0 END) as approved_count,
            SUM(CASE WHEN admin_approval = 'rejected' THEN 1 ELSE 0 END) as rejected_count,
            COUNT(*) as total_count
        FROM vendor_inventory 
        WHERE org_id = %s
    """, (org_id,))
    
    counts = cursor.fetchone()
    cursor.close()
    db.close()
    
    return render_template('admin_vendor_inventory.html', 
                         inventory=all_inventory,
                         active_tab=active_tab,
                         counts=counts)



########################################### Site Engineer View Inventory ######################################
@app.route('/site_engineer/view_inventory')
def site_engineer_view_inventory():
    if 'role' not in session or session['role'] != 'site_engineer':
        return redirect(url_for('login'))

    if 'org_id' not in session:
        flash("Unauthorized access", "danger")
        return redirect(url_for('login'))

    org_id = session['org_id']
    db = get_connection()

    with db.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("""
            SELECT * FROM inventory
            WHERE org_id = %s
            ORDER BY date DESC
        """, (org_id,))
        data = cursor.fetchall()

    return render_template('view_inventory.html', inventory=data)



############################################ Site Engineer Approved Vendor Inventory ######################################
@app.route('/site_engineer/approved_vendor_inventory')
def site_engineer_approved_vendor_quotations():
    if session.get('role') != 'site_engineer':
        return redirect(url_for('login'))

    if 'org_id' not in session:
        flash("Unauthorized access", "danger")
        return redirect(url_for('login'))

    org_id = session['org_id']
    site_engineer_id = session['user_id']
    mark_notifications_as_read(site_engineer_id, org_id, 'vendor_approved')
    mark_notifications_as_read(site_engineer_id, org_id, 'vendor_rejected')
    db = get_connection()

    with db.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("""
            SELECT * FROM vendor_inventory
            WHERE admin_approval = 'approved' AND org_id = %s
            ORDER BY date DESC
        """, (org_id,))
        approved_inventory = cursor.fetchall()

    return render_template('site_engineer_approved_vendor_quotations.html', inventory=approved_inventory)



############################################### Add Enquiry ######################################
@app.route('/add_enquiry', methods=['GET', 'POST'])
def add_enquiry():
    if 'role' in session and session['role'] == 'site_engineer':
        if request.method == 'POST':
            name = request.form['name']
            address = request.form['address']
            contact_no = request.form['contact_no']
            requirement = request.form['requirement']
            engineer_id = session['user_id']
            org_id = session.get('org_id')  # Fetch org_id from session

            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO enquiries (site_engineer_id, name, address, contact_no, requirement, org_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (engineer_id, name, address, contact_no, requirement, org_id)
            )
            enquiry_id = cur.lastrowid  # Get the ID of the newly inserted enquiry
            conn.commit()
            ########## NOTIFICATION CODE ##########
            cur.execute("""
                SELECT id FROM register 
                WHERE role = 'admin' AND org_id = %s
            """, (org_id,))
            admins = cur.fetchall()
            for admin in admins:
                create_notification(
                    user_id=admin['id'],
                    org_id=org_id,
                    notification_type='enquiry_new',
                    reference_id=enquiry_id,
                    message=f'New visitor enquiry from {name} submitted by {session.get("name")}'
                )

            conn.close()    


            flash('Enquiry submitted successfully.', 'success')
            return redirect(url_for('add_enquiry'))

        return render_template('add_enquiry.html')

    else:
        return redirect(url_for('login'))

    
################################################ View Enquiries ######################################
@app.route('/admin/enquiries')
def view_enquiries():
    if 'role' in session and session['role'] in ['admin', 'site_engineer']:
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        org_id = session.get('org_id')
        user_id = session.get('user_id')

        # ========== MARK NOTIFICATIONS AS READ ==========
        # When admin views enquiries, mark enquiry notifications as read
        if session['role'] == 'admin':
            mark_notifications_as_read(
                user_id=user_id,
                org_id=org_id,
                notification_type='enquiry_new'
            )
        # =================================================

        if session['role'] == 'admin':
            cur.execute("""
                SELECT e.*, r.name AS engineer_name 
                FROM enquiries e
                JOIN register r ON e.site_engineer_id = r.id
                WHERE e.org_id = %s
                ORDER BY e.enquiry_date DESC
            """, (org_id,))
        else:  # site_engineer
            site_engineer_id = session['user_id']
            cur.execute("""
                SELECT e.*, r.name AS engineer_name 
                FROM enquiries e
                JOIN register r ON e.site_engineer_id = r.id
                WHERE e.site_engineer_id = %s AND e.org_id = %s
                ORDER BY e.enquiry_date DESC
            """, (site_engineer_id, org_id))

        enquiries = cur.fetchall()
        cur.close()
        conn.close()
        
        return render_template('view_enquiry.html', enquiries=enquiries)
    else:
        return redirect(url_for('login'))

    

 ################################################# Add Architect ######################################   
@app.route('/add_architect', methods=['GET', 'POST'])
def add_architect():
    conn = get_connection()
    cursor = conn.cursor()

    # Get site engineers
    cursor.execute("SELECT id, name FROM register WHERE role = 'site_engineer'")
    engineers = cursor.fetchall()

    # ✅ Get all site names
    cursor.execute("SELECT site_id, site_name FROM sites")
    sites = cursor.fetchall()

    if request.method == 'POST':
        name = request.form['name']
        license_number = request.form.get('license_number', '')
        contact_no = request.form.get('contact_no', '')
        email = request.form['email']
        site_id = request.form['project_name']  # renamed to project_name in form, but stores site_id
        site_engineer_id = request.form['site_engineer_id']

        insert_query = """
            INSERT INTO architects (name, license_number, contact_no, email, project_name, site_engineer_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        # store site name directly in project_name
        selected_site_name = next((s['site_name'] for s in sites if str(s['site_id']) == site_id), '')
        cursor.execute(insert_query, (name, license_number, contact_no, email, selected_site_name, site_engineer_id))
        conn.commit()
        conn.close()
        flash('Architect added successfully.')
        return redirect(url_for('view_architects'))

    conn.close()
    return render_template('add_architect.html', engineers=engineers, sites=sites)


################################################# View Architects ######################################
@app.route('/view_architects')
def view_architects():
    if 'role' in session and session['role'] in ['admin', 'site_engineer']:
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)

        if session['role'] == 'site_engineer':
            site_engineer_id = session['user_id']
            cur.execute("SELECT * FROM architects WHERE site_engineer_id = %s", (site_engineer_id,))
        else:
            cur.execute("SELECT * FROM architects")

        architects = cur.fetchall()
        conn.close()
        return render_template('view_architects.html', architects=architects)
    return redirect(url_for('login'))



########################################### View Architect Details ######################################
@app.route('/view_architect_details/<int:architect_id>')
def view_architect_details(architect_id):
    if 'role' in session and session['role'] in ['admin', 'site_engineer']:
        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor(pymysql.cursors.DictCursor)
            cur.execute("SELECT * FROM architects WHERE id = %s", (architect_id,))
            architect = cur.fetchone()
            
            if not architect:
                flash('Architect not found.', 'error')
                return redirect(url_for('view_architects'))
                
            return render_template('architect_detail.html', architect=architect)
            
        except Exception as e:
            flash(f'Error fetching architect details: {str(e)}', 'error')
            return redirect(url_for('view_architects'))
        finally:
            if conn:
                conn.close()
    return redirect(url_for('login'))

########################################### Upload Utilities Services ######################################

@app.route('/upload_utilities_services', methods=['POST'])
def upload_utilities_services():
    if 'role' in session and session['role'] == 'architect':
        project_id = request.form.get('project_id')
        water_supply = request.form.get('water_supply_source')
        drainage_system = request.form.get('drainage_system_type')
        power_supply = request.form.get('power_supply_source')

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO utilities_services (
                project_id, water_supply_source, drainage_system_type, power_supply_source, org_id
            ) VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                water_supply_source = VALUES(water_supply_source),
                drainage_system_type = VALUES(drainage_system_type),
                power_supply_source = VALUES(power_supply_source)
        """, (project_id, water_supply, drainage_system, power_supply, session['org_id']))
        conn.commit()
        conn.close()

        flash("Utilities Services uploaded successfully.")
        return redirect(url_for('architect_dashboard', project_id=project_id))

    flash("Unauthorized access.")
    return redirect(url_for('login'))



############################################ Upload Cost Estimation ######################################
# @app.route('/upload_cost_estimation', methods=['POST'])
# def upload_cost_estimation():
#     if 'role' in session and session['role'] == 'architect':
#         project_id = request.form.get('project_id')
#         arch_cost = request.form.get('architectural_design_cost')
#         struct_cost = request.form.get('structural_design_cost')
#         summary = request.form.get('estimation_summary')
#         boq = request.form.get('boq_reference')
#         cost_per_sqft = request.form.get('cost_per_sqft')
#         org_id = session['org_id']

#         # Ensure the upload directory exists
#         os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

#         # Generate unique PDF filename
#         filename = f"estimation_{uuid.uuid4().hex[:8]}.pdf"
#         save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#         #relative_path = os.path.join('uploads', os.path.basename(app.config['UPLOAD_FOLDER']), filename).replace("\\", "/")
#         relative_path = os.path.join('uploads', filename).replace("\\", "/")


#         # Create PDF from submitted data
#         pdf_data = {
#             "Project ID": project_id,
#             "Architectural Design Cost": arch_cost,
#             "Structural Design Cost": struct_cost,
#             "Estimation Summary": summary,
#             "BOQ Reference": boq,
#             "Cost per Sqft": cost_per_sqft
#         }
#         generate_estimation_pdf(pdf_data, save_path)

#         # Save to DB
#         conn = get_connection()
#         cur = conn.cursor()

#         # Update if project already has entry
#         cur.execute("SELECT id FROM cost_estimation WHERE project_id = %s and org_id = %s", (project_id,org_id))
#         if cur.fetchone():
#             cur.execute("""
#                 UPDATE cost_estimation
#                 SET architectural_design_cost = %s,
#                     structural_design_cost = %s,
#                     estimation_summary = %s,
#                     boq_reference = %s,
#                     cost_per_sqft = %s,
#                     report_pdf_path = %s,
#                     generated_on = NOW()
#                 WHERE project_id = %s and org_id = %s
#             """, (arch_cost, struct_cost, summary, boq, cost_per_sqft, relative_path, project_id,org_id))
#         else:
#             cur.execute("""
#                 INSERT INTO cost_estimation
#                     (project_id, architectural_design_cost, structural_design_cost,
#                      estimation_summary, boq_reference, cost_per_sqft, report_pdf_path,org_id)
#                 VALUES (%s, %s, %s, %s, %s, %s, %s,%s)
#             """, (project_id, arch_cost, struct_cost, summary, boq, cost_per_sqft, relative_path,org_id))

#         conn.commit()
#         conn.close()

#         flash("Cost estimation saved and PDF generated.")
#         return redirect(url_for('architect_dashboard'))

#     flash("Unauthorized access.")
#     return redirect(url_for('login'))




########################################## Generate PDF for Cost Estimation ######################################
def generate_estimation_pdf(data, save_path):
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(save_path, pagesize=letter)
    width, height = letter
    y = height - 50

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Cost Estimation Report")
    y -= 30

    c.setFont("Helvetica", 12)
    for label, value in data.items():
        c.drawString(50, y, f"{label}: {value}")
        y -= 20

    c.save()
########################################### Generate Cost Estimation PDF ######################################
@app.route('/generate_cost_estimation_pdf', methods=['POST'])
def generate_cost_estimation_pdf():
    if 'role' in session and session['role'] == 'architect':
        try:
            project_id = request.form['project_id']
            # Fetch project name
            conn_temp = get_connection()
            cur_temp = conn_temp.cursor(pymysql.cursors.DictCursor)
            cur_temp.execute("SELECT project_name FROM projects WHERE id = %s", (project_id,))
            project_data = cur_temp.fetchone()
            project_name = project_data['project_name'] if project_data else 'N/A'
            cur_temp.close()
            conn_temp.close()
            architectural_cost = request.form['architectural_design_cost']
            structural_cost = request.form['structural_design_cost']
            estimation_summary = request.form['estimation_summary']
            boq_reference = request.form['boq_reference']
            cost_per_sqft = request.form['cost_per_sqft']
            org_id = session['org_id']

            # Create uploads folder if not exists
            upload_folder = os.path.join('static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)

            # Generate PDF
            filename = f"estimation_{uuid.uuid4().hex[:8]}.pdf"
            filepath = os.path.join(upload_folder, filename)
            relative_path = f"uploads/{filename}"

            # Create Professional PDF
            pdf = FPDF()
            pdf.add_page()
            
            # Header with colored background
            pdf.set_fill_color(41, 128, 185)  # Professional blue
            pdf.rect(0, 0, 210, 40, 'F')
            
            # Company/Report Title
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", 'B', 24)
            pdf.ln(10)
            pdf.cell(0, 10, txt="COST ESTIMATION REPORT", ln=True, align="C")
            
            pdf.set_font("Arial", size=10)
            pdf.cell(0, 8, txt="A to Z Construction Cost Analysis", ln=True, align="C")
            
            # Reset text color
            pdf.set_text_color(0, 0, 0)
            pdf.ln(15)
            
            # Project Information Section
            pdf.set_font("Arial", 'B', 14)
            pdf.set_fill_color(236, 240, 241)
            pdf.cell(0, 10, txt="Project Information", ln=True, fill=True)
            pdf.ln(5)
            
            pdf.set_font("Arial", size=11)
            
            # Two-column layout for project info
            col_width = 90
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(50, 8, txt="Project ID:", border=0)
            pdf.set_font("Arial", size=11)
            pdf.cell(col_width, 8, txt=str(project_id), border=0, ln=True)

            pdf.set_font("Arial", 'B', 11)
            pdf.cell(50, 8, txt="Project Name:", border=0)
            pdf.set_font("Arial", size=11)
            pdf.cell(col_width, 8, txt=str(project_name), border=0, ln=True)
            
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(50, 8, txt="Generated On:", border=0)
            pdf.set_font("Arial", size=11)
            from datetime import datetime
            pdf.cell(col_width, 8, txt=datetime.now().strftime("%B %d, %Y"), border=0, ln=True)
            
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(50, 8, txt="BOQ Reference:", border=0)
            pdf.set_font("Arial", size=11)
            pdf.cell(col_width, 8, txt=str(boq_reference), border=0, ln=True)
            
            pdf.ln(10)
            
            # Cost Breakdown Section
            pdf.set_font("Arial", 'B', 14)
            pdf.set_fill_color(236, 240, 241)
            pdf.cell(0, 10, txt="Cost Breakdown", ln=True, fill=True)
            pdf.ln(5)
            
            # Table header
            pdf.set_fill_color(52, 152, 219)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(120, 10, txt="Description", border=1, fill=True)
            pdf.cell(70, 10, txt="Amount (Rs.)", border=1, fill=True, align='R', ln=True)
            
            # Table content
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", size=11)
            
            # Row 1
            pdf.set_fill_color(245, 245, 245)
            pdf.cell(120, 10, txt="Architectural Design Cost", border=1, fill=True)
            pdf.cell(70, 10, txt=f"{float(architectural_cost):,.2f}", border=1, fill=True, align='R', ln=True)
            
            # Row 2
            pdf.cell(120, 10, txt="Structural Design Cost", border=1)
            pdf.cell(70, 10, txt=f"{float(structural_cost):,.2f}", border=1, align='R', ln=True)
            
            # Row 3
            pdf.set_fill_color(245, 245, 245)
            pdf.cell(120, 10, txt="Cost per Sq.ft", border=1, fill=True)
            pdf.cell(70, 10, txt=f"{float(cost_per_sqft):,.2f}", border=1, fill=True, align='R', ln=True)
            
            # Total row
            total_cost = float(architectural_cost) + float(structural_cost)
            pdf.set_fill_color(52, 152, 219)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(120, 12, txt="TOTAL ESTIMATED COST", border=1, fill=True)
            pdf.cell(70, 12, txt=f"{total_cost:,.2f}", border=1, fill=True, align='R', ln=True)
            
            pdf.set_text_color(0, 0, 0)
            pdf.ln(10)
            
            # Estimation Summary Section
            pdf.set_font("Arial", 'B', 14)
            pdf.set_fill_color(236, 240, 241)
            pdf.cell(0, 10, txt="Estimation Summary", ln=True, fill=True)
            pdf.ln(5)
            
            pdf.set_font("Arial", size=10)
            pdf.multi_cell(0, 7, txt=estimation_summary, border=1, fill=False)
            
            pdf.ln(10)
            
            # Footer Section
            pdf.set_y(-30)
            pdf.set_font("Arial", 'I', 9)
            pdf.set_text_color(128, 128, 128)
            pdf.cell(0, 5, txt="This is a computer-generated document and does not require a signature.", ln=True, align="C")
            # pdf.cell(0, 5, txt=f"Document ID: {filename.replace('.pdf', '')}", ln=True, align="C")
            
            # Page number
            pdf.set_y(-15)
            pdf.set_font("Arial", 'I', 8)
            # pdf.cell(0, 10, txt=f"Page {pdf.page_no()}", align="C")
            
            pdf.output(filepath)

            # Save PDF path to database
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT id FROM cost_estimation WHERE project_id = %s and org_id = %s", (project_id, org_id))
            if cur.fetchone():
                cur.execute("""
                    UPDATE cost_estimation 
                    SET architectural_design_cost = %s,
                        structural_design_cost = %s,
                        estimation_summary = %s,
                        boq_reference = %s,
                        cost_per_sqft = %s,
                        report_pdf_path = %s,
                        generated_on = NOW()
                    WHERE project_id = %s and org_id = %s
                """, (architectural_cost, structural_cost, estimation_summary, boq_reference, cost_per_sqft, relative_path, project_id, org_id))
            else:
                cur.execute("""
                    INSERT INTO cost_estimation 
                    (project_id, architectural_design_cost, structural_design_cost, 
                     estimation_summary, boq_reference, cost_per_sqft, report_pdf_path, generated_on, org_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s)
                """, (project_id, architectural_cost, structural_cost, estimation_summary,
                      boq_reference, cost_per_sqft, relative_path, org_id))
            conn.commit()
            conn.close()

            flash('Cost Estimation PDF generated successfully.', 'success')
            return redirect(url_for('architect_dashboard'))

        except Exception as e:
            print("Error generating PDF:", e)
            flash('Failed to generate PDF.', 'danger')
            return redirect(url_for('architect_dashboard'))
    else:
        flash("Unauthorized access.")
        return redirect(url_for('login'))
    

############################################ Assign Architect to Project ######################################@app.route('/select_project_by_org')@app.route('/select_project_by_org', methods=['GET'])
@app.route('/select_project_by_org', methods=['GET'])
def select_project_by_org():
    if 'user_id' not in session or 'org_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 401

    org_id = session['org_id']
    print("Org ID from session:", org_id)

    try:
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        query = "SELECT site_id, site_name FROM sites WHERE org_id = %s"
        print("Running query...")
        cursor.execute(query, (org_id,))
        projects = cursor.fetchall()
        print("Fetched projects:", projects)

        return jsonify({'status': 'success', 'projects': projects})

    except Exception as e:
        import traceback
        print("DB error in /select_project_by_org:", e)
        traceback.print_exc()
    return jsonify({'status': 'error', 'message': 'Error loading projects'}), 500



@app.route('/assign_architect', methods=['GET', 'POST'])
def assign_architect():
    if 'role' in session and session['role'] in ['admin', 'site_engineer']:
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            # Get sites assigned to site engineers
            if session['role'] == 'admin':
                cursor.execute("""
                    SELECT s.site_id, s.site_name
                    FROM sites s
                    WHERE s.site_engineer_id IS NOT NULL
                """)
            else:
                site_engineer_id = session['user_id']
                cursor.execute("""
                    SELECT s.site_id, s.site_name
                    FROM sites s
                    WHERE s.site_engineer_id = %s
                """, (site_engineer_id,))
            projects = cursor.fetchall()

            cursor.execute("SELECT id, name FROM register WHERE role = 'architect' AND org_id = %s", (session['org_id'],))
            architects = cursor.fetchall()

            if request.method == 'POST':
                site_id = request.form['project_id']
                architect_id = request.form['architect_id']

                conn.begin()
                try:
                    cursor.execute("SELECT site_name FROM sites WHERE site_id = %s AND org_id = %s", (site_id, session['org_id']))
                    site = cursor.fetchone()

                    if site:
                        project_name = site['site_name']

                        # ✅ Check if project already exists for this site
                        cursor.execute("""
                            SELECT id FROM projects 
                            WHERE site_id = %s AND org_id = %s 
                            LIMIT 1
                        """, (site_id, session['org_id']))
                        existing_project = cursor.fetchone()

                        if existing_project:
                            # ✅ Update existing project with new architect
                            project_id = existing_project['id']
                            cursor.execute("""
                                UPDATE projects 
                                SET architect_id = %s 
                                WHERE id = %s
                            """, (architect_id, project_id))
                        else:
                            # ✅ Insert new project only if it doesn't exist
                            cursor.execute("""
                                INSERT INTO projects (project_name, architect_id, site_id, org_id)
                                VALUES (%s, %s, %s, %s)
                            """, (project_name, architect_id, site_id, session['org_id']))
                            project_id = cursor.lastrowid

                        create_notification(
                            user_id=architect_id,
                            org_id=session['org_id'],
                            notification_type='project_assigned',
                            reference_id=project_id,
                            message=f'New project assigned: {project_name}'
                        )

                        conn.commit()
                        flash('Project and Architect assigned successfully.')
                    else:
                        conn.rollback()
                        flash('Site not found.', 'error')

                except Exception as e:
                    conn.rollback()
                    flash(f'Error assigning project: {str(e)}', 'error')

            return render_template('assign_architect.html',
                                   projects=projects,
                                   architects=architects,
                                   session=session)

        except Exception as e:
            if conn:
                conn.rollback()
            flash(f'Database error: {str(e)}', 'error')
            return render_template('assign_architect.html',
                                   projects=[],
                                   architects=[],
                                   session=session)
        finally:
            if conn:
                conn.close()
    else:
        return redirect(url_for('login'))

@app.route('/get_assigned_sites_by_architect')
def get_assigned_sites_by_architect():
    if 'role' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'})
    
    architect_id = request.args.get('architect_id')
    org_id = session['org_id']
    
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    cursor.execute("""
        SELECT site_id FROM projects 
        WHERE architect_id = %s AND org_id = %s
    """, (architect_id, org_id))
    
    assigned = cursor.fetchall()
    conn.close()
    
    assigned_site_ids = [row['site_id'] for row in assigned]
    return jsonify({'status': 'success', 'assigned_site_ids': assigned_site_ids})        
    
########################################### Admin Assigned Sites ######################################    
@app.route('/admin/assigned_sites')
def admin_assigned_sites():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    cursor = get_connection()
    cursor.execute("SELECT * FROM sites WHERE site_engineer_id IS NOT NULL")
    sites = cursor.fetchall()
    return render_template('admin_assigned_sites.html', sites=sites)

########################################### View Assigned Architects ######################################

@app.route('/view_assigned_architects')
def view_assigned_architects():
    if 'role' not in session or session['role'] not in ['admin', 'site_engineer']:
        return redirect(url_for('login'))

    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    if session['role'] == 'admin':
        cur.execute("""
            SELECT s.site_id, s.site_name, p.id AS project_id, r.name AS architect_name, r.email AS architect_email
            FROM sites s
            LEFT JOIN projects p ON s.site_id = p.site_id
            LEFT JOIN register r ON p.architect_id = r.id
            WHERE s.org_id = %s
        """ , (session['org_id'],))
    else:
        site_engineer_id = session['user_id']
        cur.execute("""
            SELECT s.site_id, s.site_name, p.id AS project_id, r.name AS architect_name, r.email AS architect_email
            FROM sites s
            LEFT JOIN projects p ON s.site_id = p.site_id
            LEFT JOIN register r ON p.architect_id = r.id
            WHERE s.site_engineer_id = %s
        """, (site_engineer_id,))
    
    sites = cur.fetchall()
    cur.close()
    conn.close()
    sites = sorted(sites, key=lambda x: x.get('project_assigned_date') or '', reverse=True)
    
    # Create current_user object to pass to template
    current_user = {
        'role': session['role'],
        'user_id': session['user_id'],
        'name': session.get('name', ''),
        'email': session.get('email', '')
    }
    
    return render_template('view_assigned_architects.html', sites=sites, current_user=current_user)


################################################# View Project Details ######################################
@app.route('/view_project_details', methods=['GET', 'POST'])
def view_project_details():
    if 'role' not in session or session['role'] not in ['admin', 'site_engineer']:
        return redirect(url_for('login'))

    user_id = session['user_id']
    role = session['role']
    org_id = session.get('org_id')

    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Get all project options for dropdown
    if role == 'admin':
        cursor.execute("SELECT id, project_name FROM projects WHERE org_id = %s", (org_id,))
        project_list = cursor.fetchall()
    elif role == 'site_engineer':
        cursor.execute("""
            SELECT p.id, p.project_name
            FROM projects p
            JOIN sites s ON p.site_id = s.site_id
            WHERE s.site_engineer_id = %s AND s.org_id = %s
        """, (user_id, org_id))
        project_list = cursor.fetchall()
        print("DEBUG: Fetched project_list for site_engineer:", project_list)
    else:
        project_list = []

    selected_project = None
    project_id = request.form.get('project_id')
    print("DEBUG: Selected project_id from form:", project_id)

    if request.method == 'POST' and project_id:
        # Validate if selected project belongs to org
        cursor.execute("SELECT * FROM projects WHERE id = %s AND org_id = %s", (project_id, org_id))
        selected_project = cursor.fetchone()
        print("DEBUG: Selected project:", selected_project)

        if selected_project:
            cursor.execute("SELECT * FROM design_details WHERE project_id = %s", (project_id,))
            design = cursor.fetchone()
            print("DEBUG: Design details:", design)

            cursor.execute("SELECT * FROM structural_details WHERE project_id = %s", (project_id,))
            structure = cursor.fetchone()

            cursor.execute("SELECT * FROM material_specifications WHERE project_id = %s", (project_id,))
            material = cursor.fetchone()

            cursor.execute("SELECT * FROM site_conditions WHERE project_id = %s", (project_id,))
            site_conditions = cursor.fetchone()

            cursor.execute("SELECT * FROM utilities_services WHERE project_id = %s", (project_id,))
            utilities = cursor.fetchone()

            cursor.execute("SELECT * FROM cost_estimation WHERE project_id = %s", (project_id,))
            cost = cursor.fetchone()

            cursor.execute("SELECT * FROM drawing_documents WHERE project_id = %s", (project_id,))
            drawings = cursor.fetchall()

            return render_template("view_project_details.html",
                                   project_list=project_list,
                                   selected_project=selected_project,
                                   design=design,
                                   structure=structure,
                                   material=material,
                                   site_conditions=site_conditions,
                                   utilities=utilities,
                                   cost=cost,
                                   drawings=drawings,
                                   selected_project_id=int(project_id))

    cursor.close()
    conn.close()

    return render_template("view_project_details.html", project_list=project_list)


########################################### Submit Legal Compliances ######################################
@app.route('/submit_legal_compliances', methods=['GET', 'POST'])
def submit_legal_compliances():
    if 'role' not in session or session['role'] not in ['admin', 'site_engineer']:
        return redirect(url_for('login'))

    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    if request.method == 'POST':
        project_id = request.form['project_id']
        municipal_status = request.form['municipal_approval_status']
        environmental_clearance = request.form['environmental_clearance']

        municipal_pdf = None
        if municipal_status == 'Approved':
            municipal_pdf = save_file(request.files['municipal_approval_pdf'])

        building_permit_pdf = save_file(request.files['building_permit_pdf'])
        sanction_plan_pdf = save_file(request.files['sanction_plan_pdf'])
        fire_noc_pdf = save_file(request.files['fire_department_noc_pdf'])
        mngl_pdf = save_file(request.files['mngl_pdf']) if 'mngl_pdf' in request.files else None

        cur.execute("SELECT id FROM legal_and_compliances WHERE project_id = %s AND org_id = %s", (project_id, session['org_id']))
        existing = cur.fetchone()

        if existing:
            cur.execute("SELECT * FROM legal_and_compliances WHERE project_id = %s AND org_id = %s", (project_id, session['org_id']))
            old = cur.fetchone()

            municipal_pdf = municipal_pdf or old['municipal_approval_pdf']
            building_permit_pdf = building_permit_pdf or old['building_permit_pdf']
            sanction_plan_pdf = sanction_plan_pdf or old['sanction_plan_pdf']
            fire_noc_pdf = fire_noc_pdf or old['fire_department_noc_pdf']
            mngl_pdf = mngl_pdf or old['mngl_pdf']

            cur.execute("""
                UPDATE legal_and_compliances
                SET municipal_approval_status=%s,
                    municipal_approval_pdf=%s,
                    building_permit_pdf=%s,
                    sanction_plan_pdf=%s,
                    fire_department_noc_pdf=%s,
                    environmental_clearance=%s,
                    mngl_pdf=%s
                WHERE project_id=%s AND org_id = %s
            """, (
                municipal_status, municipal_pdf, building_permit_pdf,
                sanction_plan_pdf, fire_noc_pdf, environmental_clearance,
                mngl_pdf, project_id, session['org_id']
            ))
            flash('Legal compliances updated successfully.', 'success')
        else:
            cur.execute("""
                INSERT INTO legal_and_compliances (
                    project_id, municipal_approval_status, municipal_approval_pdf,
                    building_permit_pdf, sanction_plan_pdf, fire_department_noc_pdf,
                    environmental_clearance, mngl_pdf, org_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                project_id, municipal_status, municipal_pdf,
                building_permit_pdf, sanction_plan_pdf, fire_noc_pdf,
                environmental_clearance, mngl_pdf, session['org_id']
            ))
            flash('Legal compliances submitted successfully.', 'success')

        conn.commit()
        
        # ========== UPDATED NOTIFICATION CODE ==========
        org_id = session['org_id']
        
        # Get project details
        cur.execute("""
            SELECT p.project_name, p.architect_id, p.site_id
            FROM projects p
            WHERE p.id = %s
        """, (project_id,))
        project_data = cur.fetchone()
        
        if project_data:
            project_name = project_data['project_name']
            notification_message = f'Legal compliance documents updated for {project_name}'
            
            # ✅ 1. Notify Architect
            if project_data['architect_id']:
                create_notification(
                    user_id=project_data['architect_id'],
                    org_id=org_id,
                    notification_type='legal_updated',
                    reference_id=project_id,
                    message=notification_message
                )
            
            # ✅ 2. Notify Accountants assigned to this project
            cur.execute("""
                SELECT DISTINCT accountant_id 
                FROM accountant_projects 
                WHERE project_id = %s AND org_id = %s
            """, (project_id, org_id ))
            accountants = cur.fetchall()
            
            for acc in accountants:
                create_notification(
                    user_id=acc['accountant_id'],
                    org_id=org_id,
                    notification_type='legal_updated',
                    reference_id=project_id,
                    message=notification_message
                )
            
            # ✅ 3. Notify Site Engineers assigned to this project
            if project_data['site_id']:
                cur.execute("""
                    SELECT site_engineer_id 
                    FROM sites 
                    WHERE site_id = %s
                """, (project_data['site_id'],))
                site_engineers = cur.fetchall()
                
                for se in site_engineers:
                    # Don't notify the person who submitted it (avoid self-notification)
                    if se['site_engineer_id'] != session.get('user_id'):
                        create_notification(
                            user_id=se['site_engineer_id'],
                            org_id=org_id,
                            notification_type='legal_updated',
                            reference_id=project_id,
                            message=notification_message
                        )
        # ========== END NOTIFICATION CODE ==========
        
        cur.close()
        conn.close()
        
        return redirect(url_for('submit_legal_compliances'))

    # GET method - Fetch project list
    user_id = session.get('user_id')
    role = session.get('role')

    if role == 'admin':
        cur.execute("SELECT id, project_name FROM projects WHERE org_id = %s", (session['org_id'],))
    elif role == 'site_engineer':
        cur.execute("""
            SELECT p.id, p.project_name, p.org_id
            FROM projects p
            JOIN sites s ON p.site_id = s.site_id
            WHERE s.site_engineer_id = %s AND p.org_id = %s
        """, (user_id, session['org_id']))
    else:
        cur.close()
        conn.close()
        flash("Unauthorized access.", 'error')
        return redirect(url_for('login'))

    projects = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('submit_legal_compliances.html', projects=projects)

############################################ View Legal Compliances ######################################
@app.route('/view_legal_compliances')
def view_legal_compliances():
    if 'role' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    role = session['role']
    org_id = session['org_id']  # ✅ Get org_id from session

    # ========== MARK LEGAL COMPLIANCE NOTIFICATIONS AS READ ==========
    # Mark notifications based on role
    if role in ['architect', 'accountant', 'site_engineer']:  # ✅ Added site_engineer
        mark_notifications_as_read(user_id, org_id, 'legal_updated')
    # Admin and site_engineer typically don't receive legal_updated notifications
    # but we can mark them too if needed
    # ========== END NOTIFICATION MARK AS READ ==========

    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    if role == 'admin':
        cur.execute("""
            SELECT lc.*, p.project_name
            FROM legal_and_compliances lc
            JOIN projects p ON lc.project_id = p.id
            WHERE lc.org_id = %s
        """, (org_id,))
        
    elif role == 'site_engineer':
        cur.execute("""
            SELECT lc.*, p.project_name
            FROM legal_and_compliances lc
            JOIN projects p ON lc.project_id = p.id
            JOIN sites s ON p.site_id = s.site_id
            WHERE s.site_engineer_id = %s AND p.org_id = %s
        """, (user_id, org_id))
        
    else:
        cur.close()
        conn.close()
        return redirect(url_for('login'))

    compliances = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('view_legal_compliances.html', compliances=compliances)






def save_file(file):
    if file and file.filename:
        filename = secure_filename(file.filename)
        upload_folder = app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        # Return the relative path for use in the database
        return os.path.join('uploads', filename).replace("\\", "/")
    return None

################################################ Legal Compliances Dashboard#########################################

@app.route('/api/get_projects_by_org', methods=['GET'])
def get_projects_by_org():
    if 'org_id' not in session or 'role' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    org_id = session['org_id']
    user_id = session.get('user_id')
    role = session.get('role')

    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    try:
        if role == 'admin':
            cur.execute("SELECT id, project_name FROM projects WHERE org_id = %s", (org_id,))
            projects = cur.fetchall()

        elif role == 'site_engineer':
            cur.execute("""
                SELECT DISTINCT p.id, p.project_name
                FROM projects p
                JOIN sites s ON p.site_id = s.site_id
                WHERE s.site_engineer_id = %s AND p.org_id = %s
            """, (user_id, org_id))
            projects = cur.fetchall()

        elif role == 'architect':
            cur.execute("SELECT id FROM architects WHERE register_id = %s", (user_id,))
            architect = cur.fetchone()
            if not architect:
                return jsonify({'projects': []})
            cur.execute("""
                SELECT id, project_name
                FROM projects
                WHERE architect_id = %s AND org_id = %s
            """, (architect['id'], org_id))
            projects = cur.fetchall()

        elif role == 'accountant':
            cur.execute("""
                SELECT p.id, p.project_name
                FROM projects p
                JOIN accountant_projects ap ON p.id = ap.project_id
                WHERE ap.accountant_id = %s AND p.org_id = %s
            """, (user_id, org_id))
            projects = cur.fetchall()

        else:
            return jsonify({'error': 'Unauthorized role'}), 403

        return jsonify({'projects': projects}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        cur.close()
        conn.close()

@app.route('/legal_compliances_dashboard', methods=['GET', 'POST'])
def legal_compliances_dashboard():

    # conn = get_connection()
    # cur = conn.cursor(pymysql.cursors.DictCursor)

    user_id = session.get('user_id')
    role = session.get('role')
    org_id = session.get('org_id')

    if role in ['architect', 'accountant', 'site_engineer']:
        mark_notifications_as_read(user_id, org_id, 'legal_updated')

    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)    

    projects = []
    compliance_data = None
    selected_project = None
    not_approved = False

    if role == 'admin':
        cur.execute("""
            SELECT DISTINCT p.id, p.project_name 
            FROM projects p 
            JOIN legal_and_compliances l ON p.id = l.project_id
        """)
        projects = cur.fetchall()

    elif role == 'site_engineer':
        cur.execute("SELECT site_id FROM sites WHERE site_engineer_id = %s", (user_id))
        user_site_ids = [row['site_id'] for row in cur.fetchall()]
        if user_site_ids:
            format_strings = ','.join(['%s'] * len(user_site_ids))
            cur.execute(f"""
                SELECT DISTINCT p.id, p.project_name, p.site_id
                FROM projects p 
                JOIN legal_and_compliances l ON p.id = l.project_id
                 WHERE p.site_id IN ({format_strings})
            """, user_site_ids)
            projects = cur.fetchall()

    elif role == 'architect':
        cur.execute("SELECT * FROM architects WHERE register_id = %s", (user_id,))
        architect = cur.fetchone()

        if not architect:
            cur.close()
            conn.close()
            flash("Architect profile not found.")
            return redirect(url_for('login'))

        cur.execute("""
            SELECT DISTINCT p.id, p.project_name
            FROM projects p
            JOIN legal_and_compliances l ON p.id = l.project_id
             WHERE p.architect_id = %s
        """, (architect['register_id'],))
        projects = cur.fetchall()

    elif role == 'accountant':
        cur.execute("""
            SELECT DISTINCT p.id, p.project_name
            FROM projects p
            JOIN accountant_projects ap ON p.id = ap.project_id
             WHERE ap.accountant_id = %s
        """, (user_id,))
        projects = cur.fetchall()

    else:
        cur.close()
        conn.close()
        flash("Unauthorized access.")
        return redirect(url_for('login'))

    # 🔽 POST: View selected project details
    if request.method == 'POST':
        selected_project_id = request.form['project_id']

        if role == 'site_engineer':
            cur.execute("""
                SELECT COUNT(*) as count
                FROM projects p 
                JOIN sites s ON p.site_id = s.site_id
                WHERE p.id = %s AND s.site_engineer_id = %s
            """, (selected_project_id, user_id))
            if cur.fetchone()['count'] == 0:
                flash("Access denied to this project.")
                return redirect(url_for('legal_compliances_dashboard'))

        if role == 'architect':
            cur.execute("""
                SELECT COUNT(*) as count
                FROM projects
                 WHERE id = %s AND architect_id = %s
            """, (selected_project_id, user_id))  # user_id is register_id
            if cur.fetchone()['count'] == 0:
                flash("Access denied to this project.")
                return redirect(url_for('legal_compliances_dashboard'))

        if role == 'accountant':
            cur.execute("""
                SELECT COUNT(*) as count
                FROM accountant_projects
                WHERE project_id = %s AND accountant_id = %s
            """, (selected_project_id, user_id))
            if cur.fetchone()['count'] == 0:
                flash("Access denied to this project.")
                return redirect(url_for('legal_compliances_dashboard'))

        cur.execute("SELECT * FROM legal_and_compliances WHERE project_id = %s", (selected_project_id,))
        compliance_data = cur.fetchone()

        if compliance_data and compliance_data['municipal_approval_status'] != 'Approved':
            not_approved = True
            compliance_data = None

        cur.execute("SELECT * FROM projects WHERE id = %s", (selected_project_id,))
        selected_project = cur.fetchone()

    cur.close()
    conn.close()

    return render_template(
        'legal_compliances_dashboard.html',
        projects=projects,
        compliance=compliance_data,
        selected_project=selected_project,
        not_approved=not_approved
    )




## ###############################--- Generate Invoice --- #######################################
## ###############################--- Generate Invoice --- #######################################
@app.route('/engineer/generate_invoice', methods=['GET', 'POST'])
def generate_invoice():
    if session.get('role') != 'site_engineer':
        return redirect(url_for('login'))

    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # Fetch complete organization details including bank information
    org_id = session.get('org_id')
    cur.execute("""
        SELECT company_name, company_address, company_phone, company_email,
               gst_number, bank_name, bank_account, ifsc_code, terms_conditions
        FROM organization_master 
        WHERE org_id = %s
    """, (org_id,))
    org_details = cur.fetchone()
    
    if not org_details:
        flash('Organization details not found', 'danger')
        return redirect(url_for('site_engineer_dashboard'))

    # Fetch projects assigned to the site engineer
    site_engineer_id = session['user_id']
    cur.execute("""
        SELECT p.id, p.project_name
        FROM projects p
        JOIN sites s ON p.site_id = s.site_id
        WHERE s.site_engineer_id = %s AND s.org_id = %s
    """, (site_engineer_id, org_id))
    projects = cur.fetchall()

    if request.method == 'POST':
        try:
            # ── ONLY CHANGE: guard project_id before anything else ──
            project_id = request.form.get('project_id')
            if not project_id:
                flash("Please select a project before generating an invoice.", "danger")
                
                return redirect(request.url)
            # ────────────────────────────────────────────────────────

            vendor_name = request.form.get('vendor_name')
            client_name = request.form.get('bill_to_name')
            client_address = request.form.get('bill_to_address') or ""
            client_phone = request.form.get('bill_to_phone') or ""
            subtotal = float(request.form.get('subtotal', 0))
            total_amount = float(request.form.get('total_amount', 0))
            site_engineer_id = session.get('user_id')
            invoice_date = datetime.now().strftime("%Y-%m-%d")

            # GST calculation - exactly like the first API
            gst_percentage = float(request.form.get('gst_percentage', 0))
            gst_amount = subtotal * gst_percentage / 100
            grand_total = total_amount

            # Generate invoice number
            invoice_number = "INV" + datetime.now().strftime("%Y%m%d%H%M%S")
            pdf_filename = f"{invoice_number}.pdf"
            
            # Get line items
            descriptions = request.form.getlist('description[]')
            quantities = request.form.getlist('quantity[]')
            rates = request.form.getlist('rate[]')
            totals = request.form.getlist('total[]')

            # Handle image upload
            invoice_image_filename = None
            if 'invoice_image' in request.files:
                file = request.files['invoice_image']
                if file and file.filename and file.filename != '':
                    allowed_extensions = {'.png', '.jpg', '.jpeg'}
                    file_ext = os.path.splitext(file.filename)[1].lower()
                    if file_ext in allowed_extensions:
                        try:
                            safe_name = secure_filename(file.filename)
                            unique_name = f"{invoice_number}_{safe_name}"
                            invoice_images_dir = os.path.join(app.static_folder, 'invoice_images')
                            os.makedirs(invoice_images_dir, exist_ok=True)
                            file_path = os.path.join(invoice_images_dir, unique_name)
                            file.save(file_path)
                            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                                invoice_image_filename = unique_name
                            else:
                                flash("Failed to save image file", "error")
                        except Exception as e:
                            flash(f"Error saving image: {str(e)}", "error")
                            return redirect(request.url)
                    else:
                        flash("Please upload a valid image file (PNG, JPEG, JPG)", "error")
                        return redirect(request.url)

            # Database insertion
            cur.execute("""
                INSERT INTO invoices (
                    project_id, site_engineer_id, vendor_name, total_amount,
                    gst_amount, invoice_number, pdf_filename, generated_on,
                    bill_to_name, bill_to_address, bill_to_phone, subtotal,
                    invoice_image_filename, org_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                project_id, site_engineer_id, vendor_name, grand_total,
                gst_amount, invoice_number, pdf_filename, invoice_date,
                client_name, client_address, client_phone, subtotal,
                invoice_image_filename, org_id
            ))
            
            invoice_id = cur.lastrowid

            # Insert invoice items
            for desc, qty, rate, line_total in zip(descriptions, quantities, rates, totals):
                if desc and qty and rate:
                    cur.execute("""
                        INSERT INTO invoice_items (invoice_id, description, quantity, rate, subtotal, org_id)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (invoice_id, desc.strip(), float(qty), float(rate), float(line_total), org_id))

            # Commit transaction
            conn.commit()

            # ========== INVOICE SUBMISSION NOTIFICATION ==========
            cur.execute("""
                SELECT id FROM register 
                WHERE role = 'admin' AND org_id = %s
            """, (org_id,))
            admin_list = cur.fetchall()

            cur.execute("SELECT project_name FROM projects WHERE id = %s", (project_id,))
            proj = cur.fetchone()
            proj_name = proj['project_name'] if proj else 'Unknown Project'

            for admin in admin_list:
                create_notification(
                    user_id=admin['id'],
                    org_id=org_id,
                    notification_type='invoice_pending',
                    reference_id=invoice_id,
                    message=f'New invoice {invoice_number} submitted for {proj_name} by {session.get("name")} — ₹{grand_total:,.2f}'
                )

            # ---------------- PROFESSIONAL PDF GENERATION ---------------- #
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30)
            styles = getSampleStyleSheet()

            # Professional Color Scheme
            primary_color = colors.HexColor('#1e3a8a')      # Deep Blue
            secondary_color = colors.HexColor('#3b82f6')    # Bright Blue
            accent_color = colors.HexColor('#f59e0b')       # Golden Yellow
            text_dark = colors.HexColor('#1f2937')          # Dark Gray
            text_light = colors.HexColor('#6b7280')         # Light Gray
            bg_light = colors.HexColor('#f8fafc')           # Very Light Gray
            success_color = colors.HexColor('#059669')      # Green

            # Enhanced Custom Styles
            company_name_style = ParagraphStyle(
                'company_name',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=primary_color,
                fontName='Helvetica-Bold',
                alignment=0,
                spaceAfter=5
            )
            
            company_info_style = ParagraphStyle(
                'company_info',
                parent=styles['Normal'],
                fontSize=11,
                textColor=text_light,
                fontName='Helvetica',
                alignment=0,
                spaceAfter=3
            )
            
            invoice_title_style = ParagraphStyle(
                'invoice_title',
                parent=styles['Heading1'],
                fontSize=28,
                textColor=accent_color,
                fontName='Helvetica-Bold',
                alignment=2,
                spaceAfter=10
            )
            
            section_header_style = ParagraphStyle(
                'section_header',
                parent=styles['Heading3'],
                fontSize=14,
                textColor=primary_color,
                fontName='Helvetica-Bold',
                spaceBefore=15,
                spaceAfter=8,
                borderWidth=0,
                borderColor=primary_color,
                backColor=bg_light,
                leftIndent=10,
                rightIndent=10,
                topPadding=8,
                bottomPadding=8
            )
            
            client_info_style = ParagraphStyle(
                'client_info',
                parent=styles['Normal'],
                fontSize=11,
                textColor=text_dark,
                fontName='Helvetica',
                spaceAfter=4
            )
            
            footer_style = ParagraphStyle(
                'footer',
                parent=styles['Normal'],
                fontSize=10,
                textColor=text_light,
                fontName='Helvetica-Oblique',
                alignment=1,
                spaceBefore=20
            )

            elements = []

            # Professional Header with Company Branding
            header_table_data = [
                [
                    [
                        Paragraph(org_details['company_name'], company_name_style),
                        Paragraph(org_details['company_address'], company_info_style),
                        Paragraph(f"Phone: {org_details['company_phone'] or 'N/A'}", company_info_style),
                        Paragraph(f"Email: {org_details['company_email'] or 'N/A'}", company_info_style),
                        Paragraph(f"GST: {org_details['gst_number'] or 'N/A'}", company_info_style)
                    ],
                    Paragraph("INVOICE", invoice_title_style)
                ]
            ]
            
            header_table = Table(header_table_data, colWidths=[300, 250])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ]))
            elements.append(header_table)
            elements.append(Spacer(1, 20))

            # Invoice Details with Professional Styling
            invoice_details_data = [
                ['Invoice Number:', invoice_number, 'Invoice Date:', invoice_date]
            ]
            
            invoice_details_table = Table(invoice_details_data, colWidths=[100, 150, 100, 150])
            invoice_details_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), bg_light),
                ('TEXTCOLOR', (0, 0), (-1, -1), text_dark),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),  # Labels bold
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),       # Values normal
                ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),  # Labels bold
                ('FONTNAME', (3, 0), (3, -1), 'Helvetica'),       # Values normal
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('GRID', (0, 0), (-1, -1), 1, primary_color),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('ALIGN', (2, 0), (2, -1), 'LEFT'),
                ('ALIGN', (3, 0), (3, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ]))
            elements.append(invoice_details_table)
            elements.append(Spacer(1, 20))

            # Bill To Section with Enhanced Design
            elements.append(Paragraph("BILL TO", section_header_style))
            bill_to_data = [
                [
                    [
                        Paragraph(f"<b>{client_name}</b>", client_info_style),
                        Paragraph(client_address, client_info_style),
                        Paragraph(f"Phone: {client_phone}" if client_phone else "", client_info_style)
                    ]
                ]
            ]
            
            bill_to_table = Table(bill_to_data, colWidths=[470])
            bill_to_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), bg_light),
                ('LEFTPADDING', (0, 0), (-1, -1), 15),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('BOX', (0, 0), (-1, -1), 1, primary_color),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            elements.append(bill_to_table)
            elements.append(Spacer(1, 25))

            # Professional Line Items Table
            item_data = [['#', 'Description', 'Rate', 'Qty', 'Amount']]
            for i, (desc, qty, rate, total) in enumerate(zip(descriptions, quantities, rates, totals), start=1):
                item_data.append([
                    str(i), 
                    desc, 
                    f"₹{float(rate):,.2f}", 
                    str(qty), 
                    f"₹{float(total):,.2f}"
                ])

            item_table = Table(item_data, colWidths=[30, 220, 80, 50, 90])
            item_table.setStyle(TableStyle([
                # Header row styling
                ('BACKGROUND', (0, 0), (-1, 0), primary_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                
                # Data rows styling
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Serial number center
                ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),  # Numbers right-aligned
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # Description left-aligned
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                
                # Alternating row colors
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_light]),
                
                # Grid and borders
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
                ('BOX', (0, 0), (-1, -1), 2, primary_color),
                
                # Padding
                ('TOPPADDING', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(item_table)
            elements.append(Spacer(1, 20))

            # Professional Totals Section
            totals_data = [['Subtotal', f'₹{subtotal:,.2f}']]

            if gst_amount > 0:
                # Calculate SGST and CGST like in the first API
                sgst = gst_amount / 2
                cgst = gst_amount / 2
                print(f"DEBUG: SGST: {sgst}, CGST: {cgst}")
                
                totals_data.extend([
                    [f'GST ({gst_percentage}%)', f'₹{gst_amount:,.2f}'],
                    [f'SGST ({gst_percentage/2}%)', f'₹{sgst:,.2f}'],
                    [f'CGST ({gst_percentage/2}%)', f'₹{cgst:,.2f}']
                ])

            totals_data.append(['TOTAL AMOUNT', f'₹{grand_total:,.2f}'])
            
            totals_table = Table(totals_data, colWidths=[350, 120])
            totals_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -2), 11),
                ('FONTSIZE', (0, -1), (-1, -1), 14),
                ('TEXTCOLOR', (0, 0), (-1, -2), text_dark),
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
                ('BACKGROUND', (0, -1), (-1, -1), success_color),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 15),
                ('LEFTPADDING', (0, 0), (-1, -1), 15),
                ('BOX', (0, 0), (-1, -1), 1, primary_color),
                ('INNERGRID', (0, 0), (-1, -2), 0.5, colors.HexColor('#e5e7eb')),
            ]))
            elements.append(totals_table)
            elements.append(Spacer(1, 30))

            # Bank Details Section
            elements.append(Paragraph("BANK ACCOUNT DETAILS", section_header_style))
            bank_details = [
                f"Account Holder: {org_details['company_name']}",
                f"Bank Name: {org_details['bank_name'] or 'N/A'}",
                f"Account Number: {org_details['bank_account'] or 'N/A'}",
                f"IFSC Code: {org_details['ifsc_code'] or 'N/A'}"
            ]
            
            bank_info_data = [['\n'.join(bank_details)]]
            bank_info_table = Table(bank_info_data, colWidths=[470])
            bank_info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), bg_light),
                ('LEFTPADDING', (0, 0), (-1, -1), 15),
                ('TOPPADDING', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('BOX', (0, 0), (-1, -1), 1, primary_color),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TEXTCOLOR', (0, 0), (-1, -1), text_dark),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            elements.append(bank_info_table)
            elements.append(Spacer(1, 25))

            # Terms and Conditions Section
            elements.append(Paragraph("TERMS & CONDITIONS", section_header_style))
            if org_details['terms_conditions']:
                terms_text = org_details['terms_conditions'].replace('\n', '<br/>')
            else:
                terms_text = "• Payment due within 14 days from invoice date<br/>• Late payments subject to 4% monthly interest<br/>• All disputes subject to local jurisdiction"
            
            terms_data = [[Paragraph(terms_text, client_info_style)]]
            terms_table = Table(terms_data, colWidths=[470])
            terms_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), bg_light),
                ('LEFTPADDING', (0, 0), (-1, -1), 15),
                ('TOPPADDING', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('BOX', (0, 0), (-1, -1), 1, primary_color),
            ]))
            elements.append(terms_table)
            elements.append(Spacer(1, 30))

            # Professional Footer
            elements.append(Paragraph(
                "Thank you for your business! We appreciate your trust in our services.",
                footer_style
            ))
            
            # Add a subtle line above footer
            footer_line = Table([['']], colWidths=[470])
            footer_line.setStyle(TableStyle([
                ('LINEABOVE', (0, 0), (-1, -1), 2, accent_color),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
            ]))
            elements.append(footer_line)

            # Build PDF
            doc.build(elements)
            buffer.seek(0)

            # Save PDF to static folder
            pdf_dir = os.path.join(app.static_folder, 'invoice_pdfs')
            os.makedirs(pdf_dir, exist_ok=True)
            pdf_path = os.path.join(pdf_dir, pdf_filename)
            with open(pdf_path, 'wb') as f:
                f.write(buffer.getvalue())

            flash("Invoice generated successfully!", "success")
            return send_file(
                buffer,
                mimetype='application/pdf',
                as_attachment=False,
                download_name=pdf_filename
            )

        except Exception as e:
            conn.rollback()
            flash(f"Error generating invoice: {str(e)}", "danger")
            return redirect(request.url)
        finally:
            conn.close()

    # GET request - show the form
    conn.close()
    return render_template('generate_invoice.html', 
                         projects=projects, 
                         current_date=datetime.now().strftime("%Y-%m-%d"), 
                         user_role='site_engineer')
###################################################### Invoice Submission Route ##########################
@app.route('/submit_invoice_alt', methods=['GET','POST'])
def submit_invoice_alt():
    if session.get('role') != 'site_engineer':
        return redirect(url_for('login'))

    site_engineer_id = session.get('user_id')
    vendor_name = request.form.get('vendor_name')
    item_names = request.form.getlist('item_name')
    quantities = request.form.getlist('quantity')
    rates = request.form.getlist('rate')

    subtotal = 0
    items = []

    for name, qty, rate in zip(item_names, quantities, rates):
        qty = int(qty)
        rate = float(rate)
        amount = qty * rate
        subtotal += amount
        items.append((name, qty, rate, amount))

    gst_amount = round(subtotal * 0.18, 2)
    grand_total = subtotal + gst_amount

    try:
        cursor = get_connection()
        db = cursor.cursor(pymysql.cursors.DictCursor)
        with db.cursor() as cursor:
            # Insert invoice entry first
            cursor.execute("""
                INSERT INTO invoices (site_engineer_id, vendor_name, total_amount, gst_amount)
                VALUES (%s, %s, %s, %s)
            """, (site_engineer_id, vendor_name, subtotal, gst_amount))

            invoice_id = cursor.lastrowid

            # Now insert the items
            for name, qty, rate, amount in items:
                cursor.execute("""
                    INSERT INTO invoice_items (invoice_id, description, quantity, rate, subtotal)
                    VALUES (%s, %s, %s, %s, %s)
                """, (invoice_id, name, qty, rate, amount))

            db.commit()
            flash("Invoice submitted successfully.", "success")
            return redirect(url_for('site_engineer_dashboard'))

    except Exception as e:
        db.rollback()
        flash(f"Error: {e}", "danger")
        return redirect(request.url)
    

###################################################### Admin View Invoices Route ##########################@app.route('/admin/invoices', methods=['GET', 'POST'])
@app.route('/admin/invoices', methods=['GET', 'POST'])
def admin_view_invoices():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    status_filter = request.args.get('status', 'All')
    db = get_connection()
    admin_id = session.get('user_id')
    org_id = session.get('org_id')

    if request.method == 'POST':
        invoice_id = request.form.get('invoice_id')
        action = request.form.get('action')
        rejection_reason = request.form.get('rejection_reason', '')

        with db.cursor() as cursor:
            if action == 'approve':
                cursor.execute("""
                    UPDATE invoices 
                    SET status='Approved', approved_by=%s, approved_on=NOW(), rejection_reason=NULL 
                    WHERE id=%s AND org_id = %s
                """, (admin_id, invoice_id, org_id))
                db.commit()
                flash("Invoice approved.", "success")

                cursor.execute("""
                    SELECT i.invoice_number, i.total_amount, i.site_engineer_id, i.project_id
                    FROM invoices i WHERE i.id = %s AND i.org_id = %s
                """, (invoice_id, org_id))
                inv = cursor.fetchone()
                if inv:
                    create_notification(
                        user_id=inv['site_engineer_id'],
                        org_id=org_id,
                        notification_type='invoice_approved',
                        reference_id=invoice_id,
                        message=f'Your invoice {inv["invoice_number"]} (₹{inv["total_amount"]:,.2f}) has been approved'
                    )

                    cursor.execute("""
                        SELECT DISTINCT accountant_id FROM accountant_projects 
                        WHERE project_id = %s AND org_id = %s
                    """, (inv['project_id'], org_id))
                    accountants = cursor.fetchall()
                    for acc in accountants:
                        create_notification(
                            user_id=acc['accountant_id'],
                            org_id=org_id,
                            notification_type='invoice_approved',
                            reference_id=invoice_id,
                            message=f'Invoice {inv["invoice_number"]} approved for project — ₹{inv["total_amount"]:,.2f}'
                        )




            elif action == 'reject':
                cursor.execute("""
                    UPDATE invoices 
                    SET status='Rejected', rejection_reason=%s, approved_by=%s, approved_on=NOW() 
                    WHERE id=%s AND org_id = %s
                """, (rejection_reason, admin_id, invoice_id, org_id))
                db.commit()
                flash("Invoice rejected.", "danger")
                 # Notify site engineer of rejection
                cursor.execute("""
                    SELECT invoice_number, total_amount, site_engineer_id
                    FROM invoices WHERE id = %s AND org_id = %s
                """, (invoice_id, org_id))
                inv = cursor.fetchone()
                if inv:
                     reason_text = f' Reason: {rejection_reason}' if rejection_reason else ''
                     create_notification(
                            user_id=inv['site_engineer_id'],
                            org_id=org_id,
                            notification_type='invoice_rejected',
                            reference_id=invoice_id,
                            message=f'Your invoice {inv["invoice_number"]} (₹{inv["total_amount"]:,.2f}) has been rejected.{reason_text}'
                        )

            elif action == 'edit':
                return redirect(url_for('admin_edit_invoice', invoice_id=invoice_id))

    with db.cursor(pymysql.cursors.DictCursor) as cursor:
        if status_filter in ['Pending', 'Approved', 'Rejected']:
            cursor.execute("""
                SELECT i.*, r.name as engineer_name 
                FROM invoices i 
                LEFT JOIN register r ON i.site_engineer_id = r.id 
                WHERE i.status = %s AND i.org_id = %s
                ORDER BY i.generated_on DESC
            """, (status_filter, org_id))
        else:
            cursor.execute("""
                SELECT i.*, r.name as engineer_name 
                FROM invoices i 
                LEFT JOIN register r ON i.site_engineer_id = r.id 
                WHERE i.org_id = %s
                ORDER BY i.generated_on DESC
            """, (org_id,))
        invoices = cursor.fetchall()

        cursor.execute("""
            SELECT * FROM invoice_items 
            WHERE org_id = %s 
            ORDER BY invoice_id
        """, (org_id,))
        all_items = cursor.fetchall()

    db.close()

    # Group items by invoice ID
    items_by_invoice = {}
    for item in all_items:
        items_by_invoice.setdefault(item['invoice_id'], []).append(item)

    return render_template(
        'invoice_detail.html',
        invoices=invoices,
        items_by_invoice=items_by_invoice,
        selected_status=status_filter
    )

#################################### Admin Invoice Detail View ######################################
@app.route('/admin/invoice/<int:invoice_id>')
def admin_invoice_detail(invoice_id):
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM invoices WHERE id=%s and org_id = %s", (invoice_id, session['org_id']))
    invoice = cursor.fetchone()
    cursor.execute("SELECT * FROM invoice_items WHERE invoice_id=%s and org_id = %s", (invoice_id,session['org_id']))
    items = cursor.fetchall()
    conn.close()
    return render_template('invoice_detail.html', invoice=invoice, items=items)

################################## Site Engineer Generate Invoice ######################################
# @app.route('/site_engineer/invoice/new', methods=['GET', 'POST'])
# def site_engineer_generate_invoice():
#     if session.get('role') != 'site_engineer':
#         return redirect(url_for('login'))

#     if request.method == 'POST':
#         try:
#             site_engineer_id = session.get('user_id')
#             vendor_name = request.form['vendor_name']
#             # Always use current date for invoice_date
#             invoice_date = datetime.now().strftime("%Y-%m-%d")
#             bill_to_name = request.form['bill_to_name']
#             bill_to_address = request.form['bill_to_address']
#             bill_to_phone = request.form['bill_to_phone']
#             subtotal = float(request.form['subtotal'])
#             total_amount = float(request.form['total_amount'])  # This is grand total from form

#             apply_gst = request.form.get('apply_gst')
#             gst_percentage = 18
#             gst_amount = 0
#             if apply_gst:
#                 gst_amount = subtotal * gst_percentage / 100
#             else:
#                 gst_amount = 0

#             descriptions = request.form.getlist('description[]')
#             quantities = request.form.getlist('quantity[]')
#             item_prices = request.form.getlist('rate[]')
#             totals = request.form.getlist('total[]')

#             invoice_number = "INV" + datetime.now().strftime("%Y%m%d%H%M%S")
#             pdf_filename = f"invoice_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"

#             with db.cursor() as cursor:
#                 cursor.execute("""
#                     INSERT INTO invoices (
#                         site_engineer_id, vendor_name, total_amount, gst_amount, pdf_filename, generated_on,
#                         bill_to_name, bill_to_address, bill_to_phone, subtotal, invoice_number
#                     )
#                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
#                 """, (
#                     site_engineer_id, vendor_name, total_amount, gst_amount, pdf_filename, invoice_date,
#                     bill_to_name, bill_to_address, bill_to_phone, subtotal, invoice_number
#                 ))

#                 invoice_id = cursor.lastrowid

#                 items_inserted = 0
#                 for i, (desc, qty, price, total) in enumerate(zip(descriptions, quantities, item_prices, totals)):
#                     if not desc.strip():
#                         continue
#                     try:
#                         qty_val = float(qty) if qty else 0
#                         price_val = float(price) if price else 0
#                         total_val = float(total) if total else (qty_val * price_val)
#                         cursor.execute("""
#                             INSERT INTO invoice_items (invoice_id, description, quantity, rate, subtotal)
#                             VALUES (%s, %s, %s, %s, %s)
#                         """, (invoice_id, desc.strip(), qty_val, price_val, total_val))
#                         items_inserted += 1
#                     except (ValueError, TypeError):
#                         continue

#                 if items_inserted == 0:
#                     raise Exception("No valid items were inserted")

#                 db.commit()

#             flash(f"Invoice generated successfully! ({items_inserted} items added)", "success")
#             return redirect(url_for('site_engineer_invoices'))

#         except Exception as e:
#             db.rollback()
#             flash(f"Error: {str(e)}", "danger")

#     # Pass current date to template for display
#     return render_template('generate_invoice.html', current_date=datetime.now().strftime("%Y-%m-%d"), user_role='site_engineer')


####################################################### Submit Invoice Route for Site Engineer ##########################################

@app.route('/submit_invoice', methods=['GET','POST'])
def submit_invoice():
    if session.get('role') != 'site_engineer':
        return redirect(url_for('login'))

    site_engineer_id = session.get('user_id')
    vendor_name = request.form.get('vendor_name')
    item_names = request.form.getlist('item_name[]')
    quantities = request.form.getlist('quantity[]')
    rates = request.form.getlist('rate[]')

    subtotal = 0
    items = []

    for name, qty, rate in zip(item_names, quantities, rates):
        qty = int(qty)
        rate = float(rate)
        amount = qty * rate
        subtotal += amount
        items.append((name, qty, rate, amount))

    gst_amount = round(subtotal * 0.18, 2)
    grand_total = subtotal + gst_amount

    try:
        cursor = get_connection()
        db = cursor.cursor(pymysql.cursors.DictCursor)
        with db.cursor() as cursor:
            # Insert invoice entry first
            cursor.execute("""
                INSERT INTO invoices (site_engineer_id, vendor_name, total_amount, gst_amount)
                VALUES (%s, %s, %s, %s)
            """, (site_engineer_id, vendor_name, subtotal, gst_amount))

            invoice_id = cursor.lastrowid

            # Now insert the items
            for name, qty, rate, amount in items:
                cursor.execute("""
                    INSERT INTO invoice_items (invoice_id, description, quantity, rate, subtotal)
                    VALUES (%s, %s, %s, %s, %s)
                """, (invoice_id, name, qty, rate, amount))

            db.commit()
            flash("Invoice submitted successfully.", "success")
            return redirect(url_for('site_engineer_dashboard'))

    except Exception as e:
        db.rollback()
        flash(f"Error: {e}", "danger")
        return redirect(request.url)
    
######################################### Serve Invoice PDF ########################################    
@app.route('/uploads/invoices/<path:filename>')

def serve_invoice_pdf(filename):

    # Allow admin, accountant, site_engineer, architect

    if session.get('role') not in ['admin', 'accountant', 'site_engineer', 'architect']:

        flash("Unauthorized access", "danger")

        return redirect(url_for('login'))

    return send_from_directory('static/invoices', filename)
@app.route('/dashboard')
def dashboard():
    role = session.get('role')
    if role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif role == 'site_engineer':
        return redirect(url_for('site_engineer_dashboard'))
    elif role == 'architect':
        return redirect(url_for('architect_dashboard'))
    elif role == 'accountant':
        return redirect(url_for('accountant_dashboard'))
    else:
        return redirect(url_for('login'))
    from datetime import datetime, date

@app.route('/admin/generate_invoice', methods=['GET', 'POST'])
def admin_generate_invoice():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    db = get_connection()

    with db.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT id, name FROM register WHERE role = 'site_engineer' and org_id = %s", (session['org_id'],))
        engineers = cursor.fetchall()

        cursor.execute("""
            SELECT MIN(id) as id, project_name 
            FROM projects 
            WHERE org_id = %s 
            GROUP BY project_name 
            ORDER BY project_name
        """, (session['org_id'],))
        projects = cursor.fetchall()

        # Fetch organization details
        cursor.execute("""
            SELECT company_name, company_address, company_phone, company_email,
                   gst_number, bank_name, bank_account, ifsc_code, terms_conditions
            FROM organization_master 
            WHERE org_id = %s
        """, (session['org_id'],))
        org_details = cursor.fetchone()

        if not org_details:
            flash('Organization details not found.', 'danger')
            return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        try:
            project_id = request.form.get('project_id')
            site_engineer_id = request.form.get('site_engineer_id')
            vendor_name = request.form.get('vendor_name')
            client_name = request.form.get('bill_to_name')
            client_address = request.form.get('bill_to_address') or ""
            client_phone = request.form.get('bill_to_phone') or ""
            total_amount = float(request.form.get('total_amount') or 0)
            invoice_date = request.form.get('invoice_date')
            admin_id = session.get('user_id')
            org_id = session['org_id']

            grand_total = total_amount

            subtotal_raw = request.form.get('subtotal', 0)
            subtotal = float(subtotal_raw) if subtotal_raw else 0.0

            # GST calculation exactly like the second API
            gst_percentage = float(request.form.get('gst_percentage', 0))
            gst_amount = subtotal * gst_percentage / 100

            # Calculate SGST and CGST
            sgst = gst_amount / 2
            cgst = gst_amount / 2

            invoice_number = "INV" + datetime.now().strftime("%Y%m%d%H%M%S")
            pdf_filename = f"{invoice_number}.pdf"

            descriptions = request.form.getlist('description[]')
            quantities = request.form.getlist('quantity[]')
            rates = request.form.getlist('rate[]')
            totals = request.form.getlist('total[]')

            image_filename = None
            if 'invoice_image' in request.files:
                image_file = request.files['invoice_image']
                if image_file and image_file.filename != '':
                    image_directory = os.path.join('static', 'invoice_images')
                    if not os.path.exists(image_directory):
                        os.makedirs(image_directory)

                    file_extension = os.path.splitext(image_file.filename)[1].lower()
                    image_filename = f"invoice_img_{invoice_number}{file_extension}"
                    image_path = os.path.join(image_directory, image_filename)

                    allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp', '.svg', '.jfif', '.heic'}
                    if file_extension not in allowed_extensions:
                        raise Exception("Invalid file type. Only PNG, JPG, and JPEG files are allowed.")

                    image_file.seek(0, 2)
                    file_size = image_file.tell()
                    image_file.seek(0)

                    if file_size > 5 * 1024 * 1024:
                        raise Exception("File size too large. Maximum size is 5MB.")

                    image_file.save(image_path)

            with db.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO invoices (
                        project_id, site_engineer_id, vendor_name, total_amount, gst_amount, invoice_number, pdf_filename,
                        generated_on, bill_to_name, bill_to_address, bill_to_phone, status, approved_by, approved_on, invoice_image_filename,
                        org_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Approved', %s, NOW(), %s, %s)
                """, (
                    project_id, site_engineer_id, vendor_name, grand_total, gst_amount, invoice_number, pdf_filename,
                    invoice_date, client_name, client_address, client_phone, admin_id, image_filename, org_id
                ))
                invoice_id = cursor.lastrowid

                items_inserted = 0
                for desc, qty, rate, subtotal_item in zip(descriptions, quantities, rates, totals):
                    if desc and qty and rate:
                        cursor.execute("""
                            INSERT INTO invoice_items (invoice_id, description, quantity, rate, subtotal, org_id)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (invoice_id, desc.strip(), float(qty), float(rate), float(subtotal_item), org_id))
                        items_inserted += 1

                if items_inserted == 0:
                    raise Exception("No valid invoice items found")

                # ========== NOTIFICATION CODE ==========
                # Get project name and site engineer name
                cursor.execute("""
                    SELECT p.project_name, r.name as engineer_name
                    FROM projects p
                    LEFT JOIN register r ON %s = r.id
                    WHERE p.id = %s
                """, (site_engineer_id, project_id))
                project_data = cursor.fetchone()
                
                project_name = project_data['project_name'] if project_data else 'Unknown Project'
                engineer_name = project_data['engineer_name'] if project_data and project_data['engineer_name'] else 'Site Engineer'

                # 1. Notify the assigned site engineer
                if site_engineer_id:
                    create_notification(
                        user_id=site_engineer_id,
                        org_id=org_id,
                        notification_type='invoice_approved',  # Using 'approved' since admin auto-approves
                        reference_id=invoice_id,
                        message=f'Invoice {invoice_number} generated for {project_name} — ₹{grand_total:,.2f}'
                    )

                # 2. Notify accountants assigned to this project
                cursor.execute("""
                    SELECT DISTINCT accountant_id 
                    FROM accountant_projects 
                    WHERE project_id = %s AND org_id = %s
                """, (project_id, org_id))
                accountants = cursor.fetchall()
                
                for acc in accountants:
                    create_notification(
                        user_id=acc['accountant_id'],
                        org_id=org_id,
                        notification_type='invoice_approved',
                        reference_id=invoice_id,
                        message=f'Invoice {invoice_number} approved for {project_name} — ₹{grand_total:,.2f}'
                    )
                # ========================================

                db.commit()

            # ---------------- PROFESSIONAL PDF GENERATION ---------------- #
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30)
            styles = getSampleStyleSheet()

            # Professional Color Scheme
            primary_color = colors.HexColor('#1e3a8a')      # Deep Blue
            secondary_color = colors.HexColor('#3b82f6')    # Bright Blue
            accent_color = colors.HexColor('#f59e0b')       # Golden Yellow
            text_dark = colors.HexColor('#1f2937')          # Dark Gray
            text_light = colors.HexColor('#6b7280')         # Light Gray
            bg_light = colors.HexColor('#f8fafc')           # Very Light Gray
            success_color = colors.HexColor('#059669')      # Green

            # Enhanced Custom Styles
            company_name_style = ParagraphStyle(
                'company_name',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=primary_color,
                fontName='Helvetica-Bold',
                alignment=0,
                spaceAfter=5
            )
            
            company_info_style = ParagraphStyle(
                'company_info',
                parent=styles['Normal'],
                fontSize=11,
                textColor=text_light,
                fontName='Helvetica',
                alignment=0,
                spaceAfter=3
            )
            
            invoice_title_style = ParagraphStyle(
                'invoice_title',
                parent=styles['Heading1'],
                fontSize=28,
                textColor=accent_color,
                fontName='Helvetica-Bold',
                alignment=2,
                spaceAfter=10
            )
            
            section_header_style = ParagraphStyle(
                'section_header',
                parent=styles['Heading3'],
                fontSize=14,
                textColor=primary_color,
                fontName='Helvetica-Bold',
                spaceBefore=15,
                spaceAfter=8,
                borderWidth=0,
                borderColor=primary_color,
                backColor=bg_light,
                leftIndent=10,
                rightIndent=10,
                topPadding=8,
                bottomPadding=8
            )
            
            client_info_style = ParagraphStyle(
                'client_info',
                parent=styles['Normal'],
                fontSize=11,
                textColor=text_dark,
                fontName='Helvetica',
                spaceAfter=4
            )
            
            footer_style = ParagraphStyle(
                'footer',
                parent=styles['Normal'],
                fontSize=10,
                textColor=text_light,
                fontName='Helvetica-Oblique',
                alignment=1,
                spaceBefore=20
            )

            elements = []

            # Professional Header with Company Branding
            header_table_data = [
                [
                    [
                        Paragraph(org_details['company_name'], company_name_style),
                        Paragraph(org_details['company_address'], company_info_style),
                        Paragraph(f"Phone: {org_details['company_phone'] or 'N/A'}", company_info_style),
                        Paragraph(f"Email: {org_details['company_email'] or 'N/A'}", company_info_style),
                        Paragraph(f"GST: {org_details['gst_number'] or 'N/A'}", company_info_style)
                    ],
                    Paragraph("INVOICE", invoice_title_style)
                ]
            ]
            
            header_table = Table(header_table_data, colWidths=[300, 250])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ]))
            elements.append(header_table)
            elements.append(Spacer(1, 20))

            # Invoice Details with Professional Styling (removed due date)
            invoice_details_data = [
                ['Invoice Number:', invoice_number, 'Invoice Date:', invoice_date]
            ]
            
            invoice_details_table = Table(invoice_details_data, colWidths=[100, 150, 100, 150])
            invoice_details_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), bg_light),
                ('TEXTCOLOR', (0, 0), (-1, -1), text_dark),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
                ('FONTNAME', (3, 0), (3, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('GRID', (0, 0), (-1, -1), 1, primary_color),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('ALIGN', (2, 0), (2, -1), 'LEFT'),
                ('ALIGN', (3, 0), (3, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ]))
            elements.append(invoice_details_table)
            elements.append(Spacer(1, 20))

            # Bill To Section with Enhanced Design
            elements.append(Paragraph("BILL TO", section_header_style))
            bill_to_data = [
                [
                    [
                        Paragraph(f"<b>{client_name}</b>", client_info_style),
                        Paragraph(client_address, client_info_style),
                        Paragraph(f"Phone: {client_phone}" if client_phone else "", client_info_style)
                    ]
                ]
            ]
            
            bill_to_table = Table(bill_to_data, colWidths=[470])
            bill_to_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), bg_light),
                ('LEFTPADDING', (0, 0), (-1, -1), 15),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('BOX', (0, 0), (-1, -1), 1, primary_color),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            elements.append(bill_to_table)
            elements.append(Spacer(1, 25))

            # Professional Line Items Table
            item_data = [['#', 'Description', 'Rate', 'Qty', 'Amount']]
            for i, (desc, qty, rate, total) in enumerate(zip(descriptions, quantities, rates, totals), start=1):
                item_data.append([
                    str(i), 
                    desc, 
                    f"₹{float(rate):,.2f}", 
                    str(qty), 
                    f"₹{float(total):,.2f}"
                ])

            item_table = Table(item_data, colWidths=[30, 220, 80, 50, 90])
            item_table.setStyle(TableStyle([
                # Header row styling
                ('BACKGROUND', (0, 0), (-1, 0), primary_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                
                # Data rows styling
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),
                ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                
                # Alternating row colors
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_light]),
                
                # Grid and borders
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
                ('BOX', (0, 0), (-1, -1), 2, primary_color),
                
                # Padding
                ('TOPPADDING', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(item_table)
            elements.append(Spacer(1, 20))

            # Professional Totals Section with GST Logic
            totals_data = [['Subtotal', f'₹{subtotal:,.2f}']]

            if gst_amount > 0:
                totals_data.extend([
                    [f'GST ({gst_percentage}%)', f'₹{gst_amount:,.2f}'],
                    [f'SGST ({gst_percentage/2}%)', f'₹{sgst:,.2f}'],
                    [f'CGST ({gst_percentage/2}%)', f'₹{cgst:,.2f}']
                ])

            totals_data.append(['TOTAL AMOUNT', f'₹{grand_total:,.2f}'])
            
            totals_table = Table(totals_data, colWidths=[350, 120])
            totals_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -2), 11),
                ('FONTSIZE', (0, -1), (-1, -1), 14),
                ('TEXTCOLOR', (0, 0), (-1, -2), text_dark),
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
                ('BACKGROUND', (0, -1), (-1, -1), success_color),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 15),
                ('LEFTPADDING', (0, 0), (-1, -1), 15),
                ('BOX', (0, 0), (-1, -1), 1, primary_color),
                ('INNERGRID', (0, 0), (-1, -2), 0.5, colors.HexColor('#e5e7eb')),
            ]))
            elements.append(totals_table)
            elements.append(Spacer(1, 30))

            # Bank Details Section (removed bold tags)
            elements.append(Paragraph("BANK ACCOUNT DETAILS", section_header_style))
            bank_details = [
                f"Account Holder: {org_details['company_name']}",
                f"Bank Name: {org_details['bank_name'] or 'N/A'}",
                f"Account Number: {org_details['bank_account'] or 'N/A'}",
                f"IFSC Code: {org_details['ifsc_code'] or 'N/A'}"
            ]
            
            bank_info_data = [['\n'.join(bank_details)]]
            bank_info_table = Table(bank_info_data, colWidths=[470])
            bank_info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), bg_light),
                ('LEFTPADDING', (0, 0), (-1, -1), 15),
                ('TOPPADDING', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('BOX', (0, 0), (-1, -1), 1, primary_color),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TEXTCOLOR', (0, 0), (-1, -1), text_dark),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            elements.append(bank_info_table)
            elements.append(Spacer(1, 25))

            # Terms and Conditions Section
            elements.append(Paragraph("TERMS & CONDITIONS", section_header_style))
            if org_details['terms_conditions']:
                terms_text = org_details['terms_conditions'].replace('\n', '<br/>')
            else:
                terms_text = "• Payment due within 14 days from invoice date<br/>• Late payments subject to 4% monthly interest<br/>• All disputes subject to local jurisdiction"
            
            terms_data = [[Paragraph(terms_text, client_info_style)]]
            terms_table = Table(terms_data, colWidths=[470])
            terms_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), bg_light),
                ('LEFTPADDING', (0, 0), (-1, -1), 15),
                ('TOPPADDING', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('BOX', (0, 0), (-1, -1), 1, primary_color),
            ]))
            elements.append(terms_table)
            elements.append(Spacer(1, 30))

            # Professional Footer
            elements.append(Paragraph(
                "Thank you for your business! We appreciate your trust in our services.",
                footer_style
            ))
            
            # Add a subtle line above footer
            footer_line = Table([['']], colWidths=[470])
            footer_line.setStyle(TableStyle([
                ('LINEABOVE', (0, 0), (-1, -1), 2, accent_color),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
            ]))
            elements.append(footer_line)

            # Build PDF
            doc.build(elements)
            buffer.seek(0)

            pdf_directory = os.path.join('static', 'invoice_pdfs')
            if not os.path.exists(pdf_directory):
                os.makedirs(pdf_directory)
            pdf_path = os.path.join(pdf_directory, pdf_filename)
            with open(pdf_path, 'wb') as f:
                f.write(buffer.read())
            buffer.seek(0)

            flash("Admin invoice generated and auto-approved.", "success")
            return redirect(url_for('admin_view_invoices'))

        except Exception as e:
            db.rollback()
            flash(f"Error: {str(e)}", "danger")
            return redirect(request.url)

    return render_template('generate_invoice.html', engineers=engineers, projects=projects, user_role='admin', current_date=date.today().isoformat())
@app.route('/api/get_engineer_projects/<int:engineer_id>')
def get_engineer_projects(engineer_id):
    """Get projects assigned to a specific site engineer"""
    if 'role' not in session or session['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    org_id = session['org_id']
    
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    try:
        # Get projects where this site engineer is assigned via sites table
        cur.execute("""
            SELECT DISTINCT p.id, p.project_name
            FROM projects p
            JOIN sites s ON p.site_id = s.site_id
            WHERE s.site_engineer_id = %s AND s.org_id = %s
            ORDER BY p.project_name
        """, (engineer_id, org_id))
        
        projects = cur.fetchall()
        
        return jsonify({
            'success': True,
            'projects': projects
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        cur.close()
        conn.close()
@app.route('/site_engineer/invoices')
def site_engineer_invoices():
    if session.get('role') != 'site_engineer':
        return redirect(url_for('login'))
    

    site_engineer_id = session.get('user_id')
    org_id = session['org_id']

    mark_notifications_as_read(site_engineer_id, org_id, 'invoice_rejected')
    mark_notifications_as_read(site_engineer_id, org_id, 'invoice_approved')
    db = get_connection()
    with db.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("""
            SELECT 
                id, invoice_number, generated_on, total_amount, status, rejection_reason, pdf_filename
            FROM invoices
            WHERE site_engineer_id = %s and org_id = %s
            ORDER BY generated_on DESC
        """, (site_engineer_id,session['org_id']))
        invoices = cursor.fetchall()

        for invoice in invoices:
            cursor.execute("""
                SELECT description, quantity, rate 
                FROM invoice_items 
                WHERE invoice_id = %s and org_id = %s
            """, (invoice['id'],session['org_id']))
            invoice['items'] = cursor.fetchall()

    return render_template('site_engineer_invoices.html', invoices=invoices)
# @app.route('/admin/edit_invoice/<int:invoice_id>', methods=['GET', 'POST'])
# def admin_edit_invoice(invoice_id):
#     if session.get('role') != 'admin':
#         return redirect(url_for('login'))

#     with db.cursor(pymysql.cursors.DictCursor) as cursor:
#         cursor.execute("SELECT * FROM invoices WHERE id = %s", (invoice_id,))
#         invoice = cursor.fetchone()

#         if not invoice:
#             flash("Invoice not found.", "danger")
#             return redirect(url_for('admin_view_invoices'))

#         cursor.execute("SELECT * FROM invoice_items WHERE invoice_id = %s", (invoice_id,))
#         items = cursor.fetchall()

#         if request.method == 'POST':
#             vendor_name = request.form.get('vendor_name')
#             total_amount = request.form.get('total_amount')
#             gst_amount = request.form.get('gst_amount')
#             pdf_filename = request.form.get('pdf_filename')

#             cursor.execute("""
#                 UPDATE invoices 
#                 SET vendor_name=%s, total_amount=%s, gst_amount=%s, pdf_filename=%s,
#                     status='Pending', rejection_reason=NULL
#                 WHERE id=%s
#             """, (vendor_name, total_amount, gst_amount, pdf_filename, invoice_id))
#             db.commit()

#             flash("Invoice updated and reset to Pending for review.", "success")
#             return redirect(url_for('admin_view_invoices'))

#     return render_template('admin_edit_invoice.html', invoice=invoice, items=items)
@app.route('/admin/edit_invoice/<int:invoice_id>', methods=['GET', 'POST'])
def admin_edit_invoice(invoice_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    db = get_connection()
    with db.cursor(pymysql.cursors.DictCursor) as cursor:
        # Get invoice
        cursor.execute("SELECT * FROM invoices WHERE id = %s", (invoice_id,))
        invoice = cursor.fetchone()
        if not invoice:
            flash("Invoice not found.", "danger")
            return redirect(url_for('admin_view_invoices'))
         
        # Get invoice items
        cursor.execute("SELECT * FROM invoice_items WHERE invoice_id = %s", (invoice_id,))
        items = cursor.fetchall()
         
        if request.method == 'POST':
            vendor_name = request.form.get('vendor_name')
            total_amount = float(request.form.get('total_amount'))
            gst_amount = float(request.form.get('gst_amount'))
             
            # Generate PDF using ReportLab
            new_pdf_filename = f"invoice_{uuid.uuid4().hex}.pdf"
            pdf_path = os.path.join("static", "invoices", new_pdf_filename)
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
             
            c = canvas.Canvas(pdf_path, pagesize=letter)
            width, height = letter
            
            # Start from top of page
            y = height - 50
            
            # Add content with proper Unicode support
            c.drawString(50, y, f"Invoice Number: {invoice['invoice_number']}")
            y -= 30
            c.drawString(50, y, f"Vendor Name: {vendor_name}")
            y -= 30
            c.drawString(50, y, f"Total Amount: ₹{total_amount:.2f}")
            y -= 30
            c.drawString(50, y, f"GST Amount: ₹{gst_amount:.2f}")
            y -= 50
            c.drawString(50, y, "Items:")
            y -= 30
            
            for item in items:
                line = f"{item['description']} - Qty: {item['quantity']} x ₹{item['rate']} = ₹{item['subtotal']}"
                c.drawString(70, y, line)
                y -= 25
            
            c.save()
             
            # Store only filename (not full path) in DB
            cursor.execute("""
                UPDATE invoices 
                SET vendor_name=%s, total_amount=%s, gst_amount=%s, pdf_filename=%s,
                    status='Pending', rejection_reason=NULL
                WHERE id=%s
            """, (vendor_name, total_amount, gst_amount, new_pdf_filename, invoice_id))
            db.commit()
             
            flash("Invoice updated. New PDF generated. Status reset to Pending.", "success")
            return redirect(url_for('admin_view_invoices'))
     
    return render_template('admin_edit_invoice.html', invoice=invoice, items=items)

@app.route('/edit_invoice/<int:invoice_id>', methods=['GET', 'POST'])
def edit_invoice(invoice_id):
    if session.get('role') != 'site_engineer':
        return redirect(url_for('login'))
    
    engineer_id = session.get('user_id')
    db = get_connection()
    with db.cursor(pymysql.cursors.DictCursor) as cursor:
        # Verify the invoice belongs to this engineer
        cursor.execute("""
            SELECT * FROM invoices 
            WHERE id = %s AND  site_engineer_id= %s AND status = 'Rejected' AND org_id = %s
        """, (invoice_id, engineer_id, session['org_id']))
        invoice = cursor.fetchone()
        
        if not invoice:
            flash("Invoice not found or not eligible for update.", "danger")
            return redirect(url_for('site_engineer_invoices'))
        
        # Get invoice items
        cursor.execute("SELECT * FROM invoice_items WHERE invoice_id = %s and org_id = %s", (invoice_id,session['org_id']))
        items = cursor.fetchall()
        
        if request.method == 'POST':
            vendor_name = request.form.get('vendor_name')
            total_amount = float(request.form.get('total_amount'))
            gst_amount = float(request.form.get('gst_amount'))
            
            # Generate new PDF
            new_pdf_filename = f"invoice_{uuid.uuid4().hex}.pdf"
            pdf_path = os.path.join("static", "invoice_pdfs", new_pdf_filename)
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            
            c = canvas.Canvas(pdf_path, pagesize=letter)
            width, height = letter
            
            # PDF content (same as admin version)
            y = height - 50
            c.drawString(50, y, f"Invoice Number: {invoice['invoice_number']}")
            y -= 30
            c.drawString(50, y, f"Vendor Name: {vendor_name}")
            y -= 30
            c.drawString(50, y, f"Total Amount: ₹{total_amount:.2f}")
            y -= 30
            c.drawString(50, y, f"GST Amount: ₹{gst_amount:.2f}")
            y -= 50
            c.drawString(50, y, "Items:")
            y -= 30
            
            for item in items:
                line = f"{item['description']} - Qty: {item['quantity']} x ₹{item['rate']} = ₹{item['subtotal']}"
                c.drawString(70, y, line)
                y -= 25
            
            c.save()
            
            # Update invoice with new details and reset status
            cursor.execute("""
                UPDATE invoices 
                SET vendor_name=%s, total_amount=%s, gst_amount=%s, pdf_filename=%s,
                    status='Pending', rejection_reason=NULL
                WHERE id=%s
            """, (vendor_name, total_amount, gst_amount, new_pdf_filename, invoice_id))
            db.commit()
            
            flash("Invoice updated and resubmitted for approval.", "success")
            return redirect(url_for('site_engineer_invoices'))
    
    return render_template('edit_invoice.html', invoice=invoice, items=items)
    
@app.route('/admin/assign_accountant', methods=['GET', 'POST'])
def assign_accountant():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    org_id = session.get('org_id')

    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    if request.method == 'POST':
        accountant_id = request.form['accountant_id']
        project_ids = request.form.getlist('project_ids')

        try:
            # ✅ INSERT IGNORE prevents duplicate rows without deleting existing assignments
            for project_id in project_ids:
                cur.execute(
                    """INSERT IGNORE INTO accountant_projects (accountant_id, project_id, org_id) 
                       VALUES (%s, %s, %s)""",
                    (accountant_id, project_id, org_id)
                )

            project_count = len(project_ids)
            create_notification(
                user_id=accountant_id,
                org_id=org_id,
                notification_type='project_assigned',
                reference_id=int(accountant_id),
                message=f'{project_count} project(s) assigned to you'
            )

            conn.commit()
            flash('Projects assigned successfully.', 'success')

        except Exception as e:
            conn.rollback()
            flash(f'Error assigning projects: {str(e)}', 'danger')

    # Fetch all accountants belonging to this org
    cur.execute("SELECT id, name FROM register WHERE role = 'accountant' AND org_id = %s", (org_id,))
    accountants = cur.fetchall()

    # Fetch all projects belonging to this org
    cur.execute("SELECT id, project_name FROM projects WHERE org_id = %s", (org_id,))
    projects = cur.fetchall()

    # Get current assignments to check the boxes in the template
    assignments = {}
    if accountants:
        cur.execute("SELECT accountant_id, project_id FROM accountant_projects WHERE org_id = %s", (org_id,))
        all_assignments = cur.fetchall()
        for a in all_assignments:
            if a['accountant_id'] not in assignments:
                assignments[a['accountant_id']] = []
            assignments[a['accountant_id']].append(a['project_id'])

    cur.close()
    conn.close()

    selected_accountant_id = request.args.get('accountant_id', '')
    return render_template(
        'assign_accountant.html',
        accountants=accountants,
        projects=projects,
        assignments=assignments,
        selected_accountant_id=selected_accountant_id
    )
@app.route('/')
def landing(): 
  return render_template('landing_page.html')

from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import json
from datetime import datetime, date

def default_json_serializer(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))

@app.route('/communication')
def communication():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # user_id = session['user_id']
    # org_id = session['org_id']
    # mark_notifications_as_read(user_id, org_id, 'communication_message')
    
    return render_template('communication.html')

@app.route('/get_current_user_role')
def get_current_user_role():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'})
    
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT role FROM register WHERE id = %s and org_id = %s", (session['user_id'], session['org_id']))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return jsonify({'role': result['role']})
    return jsonify({'error': 'User not found'})

@app.route('/get_users')
def get_users():
    if 'user_id' not in session:
        return jsonify([])

    current_user_id = session['user_id']
    org_id = session.get('org_id')

    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Get current user's role
    cursor.execute("SELECT role FROM register WHERE id = %s AND org_id = %s", (current_user_id, org_id))
    result = cursor.fetchone()
    if not result:
        return jsonify([])
    current_user_role = result['role']

    # Get users
    if current_user_role == 'admin':
        cursor.execute("""
            SELECT r.id, r.name, r.role,
                   (SELECT COUNT(*) FROM messages 
                    WHERE receiver_id = %s AND sender_id = r.id AND is_read = FALSE) AS unread_count
            FROM register r
            WHERE r.id != %s AND r.role != 'super_admin' AND r.org_id = %s
            ORDER BY r.name
        """, (current_user_id, current_user_id, org_id))
    elif current_user_role == 'accountant':
        cursor.execute("""
            SELECT r.id, r.name, r.role,
                   (SELECT COUNT(*) FROM messages 
                    WHERE receiver_id = %s AND sender_id = r.id AND is_read = FALSE) AS unread_count
            FROM register r
            WHERE r.role = 'admin' AND r.id != %s AND r.org_id = %s
            ORDER BY r.name
        """, (current_user_id, current_user_id, org_id))
    else:
        cursor.execute("""
            SELECT r.id, r.name, r.role,
                   (SELECT COUNT(*) FROM messages 
                    WHERE receiver_id = %s AND sender_id = r.id AND is_read = FALSE) AS unread_count
            FROM register r
            WHERE (
                r.role = %s OR r.role = 'admin' OR 
                (r.role = 'site_engineer' AND %s = 'architect') OR
                (r.role = 'architect' AND %s = 'site_engineer')
            )
            AND r.id != %s AND r.role != 'super_admin' AND r.org_id = %s
            ORDER BY r.name
        """, (
            current_user_id,
            current_user_role,
            current_user_role,
            current_user_role,
            current_user_id,
            org_id
        ))

    users = cursor.fetchall()
    conn.close()

    # Rename site_engineer to project_manager
    for user in users:
        if user['role'] == 'site_engineer':
            user['role'] = 'project_manager'

    return jsonify(users)

@app.route('/get_messages/<int:receiver_id>')
def get_messages(receiver_id):
    if 'user_id' not in session:
        return jsonify([])
    
    sender_id = session['user_id']
    org_id = session['org_id']
    
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Get all messages
    cursor.execute("""
        SELECT * FROM messages
        WHERE ((sender_id = %s AND receiver_id = %s) OR (sender_id = %s AND receiver_id = %s)) AND org_id = %s
        ORDER BY timestamp ASC
    """, (sender_id, receiver_id, receiver_id, sender_id, org_id))
    messages = cursor.fetchall()
    
    # ✅ Check if there are unread messages BEFORE marking as read
    cursor.execute("""
        SELECT COUNT(*) as unread_count
        FROM messages 
        WHERE sender_id = %s AND receiver_id = %s AND is_read = FALSE
    """, (receiver_id, sender_id))
    
    unread_result = cursor.fetchone()
    had_unread = unread_result['unread_count'] > 0 if unread_result else False
    
    # Mark messages as read
    cursor.execute("""
        UPDATE messages 
        SET is_read = TRUE 
        WHERE sender_id = %s AND receiver_id = %s AND is_read = FALSE
    """, (receiver_id, sender_id))
    
    # ✅ NEW: Also mark communication notifications as read
    # This is critical - without this, the badge will persist until page refresh
    if had_unread:
        cursor.execute("""
            UPDATE notifications 
            SET is_read = TRUE 
            WHERE user_id = %s 
            AND org_id = %s 
            AND notification_type = 'communication_message'
            AND is_read = FALSE
        """, (sender_id, org_id))
    
    conn.commit()
    conn.close()
    
    # Convert datetime to ISO format
    for message in messages:
        if 'timestamp' in message and message['timestamp']:
            if isinstance(message['timestamp'], (datetime, date)):
                message['timestamp'] = message['timestamp'].isoformat()
    
    # ✅ Return with marked_as_read flag
    return jsonify({
        'messages': messages,
        'marked_as_read': had_unread
    })
@app.route('/send_message', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Invalid JSON'})
        
    receiver_id = data.get('receiver_id')
    message = data.get('message')
    sender_id = session['user_id']
    org_id = session['org_id']

    if not receiver_id or not message:
        return jsonify({'success': False, 'error': 'Missing data'})

    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Don't specify timestamp - let DEFAULT CURRENT_TIMESTAMP handle it
        cursor.execute("""
            INSERT INTO messages (sender_id, receiver_id, message, org_id)
            VALUES (%s, %s, %s, %s)
        """, (sender_id, receiver_id, message, org_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
@app.route('/mark_as_read', methods=['POST'])
def mark_as_read():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Invalid JSON'})
    
    sender_id = data.get('sender_id')
    receiver_id = session['user_id']
    
    if not sender_id:
        return jsonify({'success': False, 'error': 'Missing sender_id'})
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE messages 
            SET is_read = TRUE 
            WHERE sender_id = %s AND receiver_id = %s AND is_read = FALSE
        """, (sender_id, receiver_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
@app.route('/mark_messages_read/<int:sender_id>', methods=['POST'])
def mark_messages_read(sender_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})
    
    receiver_id = session['user_id']
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE messages 
            SET is_read = TRUE 
            WHERE sender_id = %s AND receiver_id = %s AND is_read = FALSE
        """, (sender_id, receiver_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Add this new route to your Flask app
# @app.route('/add_advance', methods=['POST'])
# def add_advance():
#     if 'role' not in session or session['role'] != 'accountant':
#         return jsonify({'success': False, 'error': 'Unauthorized'}), 403

#     try:
#         data = request.get_json()
#         user_id = data['user_id']
#         project_id = data['project_id']
#         role = data['role']
#         month_year = data['month_year']
#         advance_amount = float(data['advance_amount'])
        
#         org_id = session['org_id']
#         accountant_id = session['user_id']

#         conn = get_connection()
#         cur = conn.cursor(pymysql.cursors.DictCursor)

#         # For advance payments: net_salary = advance_amount (since base_salary = 0)
#         # This represents the amount given to employee
#         net_salary = advance_amount

#         # Insert advance record (base_salary = 0 for pure advance entries)
#         cur.execute("""
#             INSERT INTO salaries (
#                 project_id, user_id, role, month_year, base_salary, allowance, pf,
#                 advance, net_salary, description, payment_mode, cheque_number, created_by, created_on, org_id
#             ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s, NOW(), %s)
#         """, (
#             project_id, user_id, role, month_year, 0, 0, 0,
#             advance_amount, net_salary, 'Advance Payment', 'cash', None, accountant_id, org_id
#         ))

#         conn.commit()
#         cur.close()
#         conn.close()
        
#         return jsonify({'success': True})
        
#     except Exception as e:
#         if 'conn' in locals():
#             conn.rollback()
#             cur.close()
#             conn.close()
#         return jsonify({'success': False, 'error': str(e)}), 500
# @app.route('/get_user_advance', methods=['POST'])
# def get_user_advance():
#     if 'role' not in session or session['role'] != 'accountant':
#         return jsonify({'success': False, 'error': 'Unauthorized'}), 403

#     try:
#         data = request.get_json()
#         if not data:
#             return jsonify({'success': False, 'error': 'No data provided'}), 400
            
#         user_id = data.get('user_id')
#         if not user_id:
#             return jsonify({'success': False, 'error': 'User ID is required'}), 400
            
#         project_id = data.get('project_id')
#         month_year = data.get('month_year')  # Optional for history view
        
#         org_id = session['org_id']

#         conn = get_connection()
#         cur = conn.cursor(pymysql.cursors.DictCursor)

#         # Get user details
#         cur.execute("""
#             SELECT name, role FROM register WHERE id = %s AND org_id = %s
#         """, (user_id, org_id))
#         user_details = cur.fetchone()

#         response_data = {
#             'success': True,
#             'user_details': user_details,
#             'total_advance': 0.00,
#             'total_advance_given': 0.00,
#             'advance_history': []
#         }

#         # If month_year is provided, get current advance for that specific month
#         if month_year and project_id:
#             cur.execute("""
#                 SELECT COALESCE(SUM(advance), 0) as total_advance
#                 FROM salaries 
#                 WHERE user_id = %s AND project_id = %s AND month_year = %s 
#                 AND org_id = %s AND base_salary = 0 AND advance > 0
#             """, (user_id, project_id, month_year, org_id))
            
#             result = cur.fetchone()
#             current_advance = float(result['total_advance']) if result and result['total_advance'] else 0.00
#             response_data['total_advance'] = current_advance

#         # FIXED: Get advance history - include ALL records with advance > 0, regardless of base_salary
#         if project_id:
#             history_query = """
#                 SELECT s.month_year, s.advance, s.base_salary, s.description, s.created_on, 
#                        p.project_name,
#                        CASE 
#                            WHEN s.base_salary = 0 THEN 'Advance Payment'
#                            ELSE 'Salary Deduction'
#                        END as entry_type
#                 FROM salaries s
#                 JOIN projects p ON s.project_id = p.id
#                 WHERE s.user_id = %s AND s.project_id = %s AND s.org_id = %s 
#                 AND s.advance > 0
#                 ORDER BY s.created_on DESC
#             """
#             cur.execute(history_query, (user_id, project_id, org_id))
#         else:
#             # If no project_id, get all advances for this user
#             history_query = """
#                 SELECT s.month_year, s.advance, s.base_salary, s.description, s.created_on, 
#                        p.project_name,
#                        CASE 
#                            WHEN s.base_salary = 0 THEN 'Advance Payment'
#                            ELSE 'Salary Deduction'
#                        END as entry_type
#                 FROM salaries s
#                 JOIN projects p ON s.project_id = p.id
#                 WHERE s.user_id = %s AND s.org_id = %s 
#                 AND s.advance > 0
#                 ORDER BY s.created_on DESC
#             """
#             cur.execute(history_query, (user_id, org_id))
        
#         advance_history = cur.fetchall()
        
#         # Convert Decimal to float for JSON serialization
#         for item in advance_history:
#             if 'advance' in item and item['advance'] is not None:
#                 item['advance'] = float(item['advance'])
#             if 'base_salary' in item and item['base_salary'] is not None:
#                 item['base_salary'] = float(item['base_salary'])
#             if 'created_on' in item and item['created_on'] is not None:
#                 item['created_on'] = item['created_on'].isoformat() if hasattr(item['created_on'], 'isoformat') else str(item['created_on'])
        
#         response_data['advance_history'] = advance_history
        
#         # Calculate total advance given (sum of all advances where base_salary = 0, i.e., pure advances)
#         total_given = sum(float(item['advance']) for item in advance_history if item['advance'] and item['base_salary'] == 0)
#         response_data['total_advance_given'] = total_given

#         cur.close()
#         conn.close()
        
#         return jsonify(response_data)
        
#     except Exception as e:
#         if 'conn' in locals():
#             cur.close()
#             conn.close()
#         return jsonify({'success': False, 'error': str(e)}), 500

# @app.route('/update_advance', methods=['POST'])
# def update_advance():
#     if 'role' not in session or session['role'] != 'accountant':
#         return jsonify({'success': False, 'error': 'Unauthorized'}), 403

#     try:
#         data = request.get_json()
#         user_id = data['user_id']
#         project_id = data['project_id']
#         month_year = data['month_year']
#         advance_deduction = float(data['advance_deduction'])
        
#         org_id = session['org_id']

#         conn = get_connection()
#         cur = conn.cursor(pymysql.cursors.DictCursor)

#         # Get current advance total for this month (only pure advance entries)
#         cur.execute("""
#             SELECT SUM(advance) as total_advance
#             FROM salaries 
#             WHERE user_id = %s AND project_id = %s AND month_year = %s 
#             AND org_id = %s AND base_salary = 0
#         """, (user_id, project_id, month_year, org_id))
        
#         result = cur.fetchone()
#         current_advance = float(result['total_advance']) if result and result['total_advance'] else 0.00
        
#         # Calculate remaining advance
#         remaining_advance = current_advance - advance_deduction
        
#         if remaining_advance < 0:
#             cur.close()
#             conn.close()
#             return jsonify({'success': False, 'error': 'Advance deduction cannot exceed total advance'})
        
#         # Strategy: Reduce advances starting from the most recent entry (only pure advance entries)
#         cur.execute("""
#             SELECT id, advance FROM salaries 
#             WHERE user_id = %s AND project_id = %s AND month_year = %s 
#             AND org_id = %s AND base_salary = 0 AND advance > 0
#             ORDER BY created_on DESC
#         """, (user_id, project_id, month_year, org_id))
        
#         advance_records = cur.fetchall()
#         deduction_left = advance_deduction
        
#         for record in advance_records:
#             if deduction_left <= 0:
#                 break
                
#             record_advance = float(record['advance'])
#             record_id = record['id']
            
#             if deduction_left >= record_advance:
#                 # Delete this record completely
#                 cur.execute("DELETE FROM salaries WHERE id = %s", (record_id,))
#                 deduction_left -= record_advance
#             else:
#                 # Reduce this record's advance
#                 new_advance = record_advance - deduction_left
#                 cur.execute("UPDATE salaries SET advance = %s WHERE id = %s", (new_advance, record_id))
#                 deduction_left = 0
        
#         conn.commit()
#         cur.close()
#         conn.close()
        
#         return jsonify({'success': True, 'remaining_advance': remaining_advance})
        
#     except Exception as e:
#         if 'conn' in locals():
#             conn.rollback()
#             cur.close()
#             conn.close()
#         return jsonify({'success': False, 'error': str(e)}), 500


######################enhanced advance salary routes#############################
@app.route('/advance_management')
def advance_management():
    """Display advance management page for accountant"""
    if 'role' not in session or session['role'] != 'accountant':
        return redirect(url_for('login'))
    
    accountant_id = session['user_id']
    org_id = session['org_id']
    
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    # Get all advances with employee details
    cur.execute("""
        SELECT 
            a.id,
            a.advance_amount,
            a.remaining_amount,
            a.created_on,
            r.name as employee_name,
            r.role as employee_role,
            creator.name as created_by_name
        FROM advances a
        JOIN register r ON a.user_id = r.id
        JOIN register creator ON a.created_by = creator.id
        WHERE a.org_id = %s AND r.role != 'admin'
        ORDER BY a.created_on DESC
    """, (org_id,))
    
    advances = cur.fetchall()
    
    # Format data
    for advance in advances:
        if advance['created_on']:
            advance['created_on'] = advance['created_on'].strftime('%Y-%m-%d %H:%M:%S')
        advance['advance_amount'] = float(advance['advance_amount'])
        advance['remaining_amount'] = float(advance['remaining_amount'])
        advance['deducted_amount'] = advance['advance_amount'] - advance['remaining_amount']
    
    # Get employees for the form dropdown
    cur.execute("""
        SELECT DISTINCT r.id, r.name, r.role
        FROM accountant_projects ap
        JOIN projects p ON ap.project_id = p.id
        JOIN sites s ON p.site_id = s.site_id
        JOIN register r ON r.id = s.site_engineer_id
        WHERE ap.accountant_id = %s AND ap.org_id = %s

        UNION

        SELECT DISTINCT r.id, r.name, r.role
        FROM accountant_projects ap
        JOIN projects p ON ap.project_id = p.id
        JOIN register r ON r.id = p.architect_id
        WHERE ap.accountant_id = %s AND ap.org_id = %s

        UNION

        SELECT DISTINCT r.id, r.name, r.role
        FROM register r
        WHERE r.id = %s AND r.role = 'accountant' AND r.org_id = %s

        ORDER BY name ASC
    """, (accountant_id, org_id, accountant_id, org_id, accountant_id, org_id))
    employees = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('advance_management.html', advances=advances, employees=employees)


@app.route('/add_advance', methods=['POST'])
def add_advance():
    """Add a new advance"""
    if 'role' not in session or session['role'] != 'accountant':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        advance_amount = float(data.get('advance_amount', 0))
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID is required'}), 400
        
        if advance_amount <= 0:
            return jsonify({'success': False, 'error': 'Advance amount must be greater than 0'}), 400
        
        accountant_id = session['user_id']
        org_id = session['org_id']
        
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        # Verify user belongs to organization
        cur.execute("""
            SELECT id FROM register WHERE id = %s AND org_id = %s AND role != 'admin'
        """, (user_id, org_id))
        
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Employee not found in organization'}), 404
        
        # Insert advance record
        cur.execute("""
            INSERT INTO advances (user_id, advance_amount, remaining_amount, created_by, org_id, created_on)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (user_id, advance_amount, advance_amount, accountant_id, org_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Advance added successfully'
        })
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            cur.close()
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/get_user_total_advance', methods=['POST'])
def get_user_total_advance():
    """Get total remaining advance for a user"""
    if 'role' not in session or session['role'] != 'accountant':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID is required'}), 400
        
        org_id = session['org_id']
        
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        # Get user details
        cur.execute("""
            SELECT name, role FROM register WHERE id = %s AND org_id = %s 
        """, (user_id, org_id))
        user_details = cur.fetchone()
        
        # Get total remaining advance
        cur.execute("""
            SELECT 
                COALESCE(SUM(advance_amount), 0) as total_given,
                COALESCE(SUM(remaining_amount), 0) as total_remaining
            FROM advances
            WHERE user_id = %s AND org_id = %s
        """, (user_id, org_id))
        
        advance_data = cur.fetchone()
        
        # Get advance history
        cur.execute("""
            SELECT 
                id,
                advance_amount,
                remaining_amount,
                created_on
            FROM advances
            WHERE user_id = %s AND org_id = %s 
            ORDER BY created_on DESC
        """, (user_id, org_id))
        
        history = cur.fetchall()
        
        # Format history
        for item in history:
            item['advance_amount'] = float(item['advance_amount'])
            item['remaining_amount'] = float(item['remaining_amount'])
            item['deducted_amount'] = item['advance_amount'] - item['remaining_amount']
            if item['created_on']:
                item['created_on'] = item['created_on'].strftime('%Y-%m-%d %H:%M:%S')
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'user_details': user_details,
            'total_given': float(advance_data['total_given']),
            'total_remaining': float(advance_data['total_remaining']),
            'total_deducted': float(advance_data['total_given']) - float(advance_data['total_remaining']),
            'history': history
        })
        
    except Exception as e:
        if 'conn' in locals():
            cur.close()
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/deduct_advance_from_salary', methods=['POST'])
def deduct_advance_from_salary():
    """Deduct advance amount when processing salary (internal function)"""
    # This is called automatically from add_salary route
    try:
        user_id = request.json.get('user_id')
        deduction_amount = float(request.json.get('deduction_amount', 0))
        org_id = session['org_id']
        
        if deduction_amount <= 0:
            return jsonify({'success': True, 'message': 'No deduction needed'})
        
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        # Get advances with remaining balance (oldest first - FIFO)
        cur.execute("""
            SELECT id, advance_amount, remaining_amount
            FROM advances
            WHERE user_id = %s AND org_id = %s AND remaining_amount > 0
            ORDER BY created_on ASC
        """, (user_id, org_id))
        
        advances = cur.fetchall()
        
        if not advances:
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': 'No advance available for this employee'}), 400
        
        # Calculate total available
        total_available = sum(float(adv['remaining_amount']) for adv in advances)
        
        if deduction_amount > total_available:
            cur.close()
            conn.close()
            return jsonify({
                'success': False, 
                'error': f'Deduction amount (₹{deduction_amount:.2f}) exceeds available advance (₹{total_available:.2f})'
            }), 400
        
        # Deduct from advances (FIFO)
        remaining_to_deduct = deduction_amount
        
        for advance in advances:
            if remaining_to_deduct <= 0:
                break
            
            advance_id = advance['id']
            advance_remaining = float(advance['remaining_amount'])
            
            if remaining_to_deduct >= advance_remaining:
                # Fully deduct this advance
                new_remaining = 0
                remaining_to_deduct -= advance_remaining
            else:
                # Partially deduct
                new_remaining = advance_remaining - remaining_to_deduct
                remaining_to_deduct = 0
            
            # Update advance
            cur.execute("""
                UPDATE advances
                SET remaining_amount = %s
                WHERE id = %s
            """, (new_remaining, advance_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Advance deducted successfully',
            'deducted_amount': deduction_amount
        })
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            cur.close()
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500
# Add this route to handle advance updates

@app.route('/update_advance_amount/<int:advance_id>', methods=['POST'])
def update_advance_amount(advance_id):
    """Update advance amount - add more to existing advance"""
    if 'role' not in session or session['role'] != 'accountant':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        additional_amount = float(data.get('additional_amount', 0))
        
        if additional_amount <= 0:
            return jsonify({'success': False, 'error': 'Additional amount must be greater than 0'}), 400
        
        org_id = session['org_id']
        
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        # Get current advance details
        cur.execute("""
            SELECT advance_amount, remaining_amount, user_id
            FROM advances
            WHERE id = %s AND org_id = %s 
        """, (advance_id, org_id))
        
        advance = cur.fetchone()
        
        if not advance:
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Advance not found'}), 404
        
        # Calculate new amounts
        new_advance_amount = float(advance['advance_amount']) + additional_amount
        new_remaining_amount = float(advance['remaining_amount']) + additional_amount
        
        # Update advance record
        cur.execute("""
            UPDATE advances
            SET advance_amount = %s, remaining_amount = %s
            WHERE id = %s
        """, (new_advance_amount, new_remaining_amount, advance_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Advance updated successfully',
            'new_advance_amount': new_advance_amount,
            'new_remaining_amount': new_remaining_amount
        })
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            cur.close()
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/get_employee_advance', methods=['POST'])
def get_employee_advance():
    """Get employee's remaining advance from advances table - NEW ROUTE FOR ADD SALARY PAGE"""
    if 'role' not in session or session['role'] != 'accountant':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID is required'}), 400
            
        org_id = session['org_id']

        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)

        # Get total remaining advance from advances table
        cur.execute("""
            SELECT COALESCE(SUM(remaining_amount), 0) as total_remaining
            FROM advances
            WHERE user_id = %s AND org_id = %s 
        """, (user_id, org_id))
        
        result = cur.fetchone()
        remaining_advance = float(result['total_remaining']) if result else 0.00

        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'remaining_advance': remaining_advance
        })
        
    except Exception as e:
        if 'conn' in locals():
            cur.close()
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/get_advance_details/<int:advance_id>', methods=['GET'])
def get_advance_details(advance_id):
    """Get details of a specific advance"""
    if 'role' not in session or session['role'] != 'accountant':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        org_id = session['org_id']
        
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        cur.execute("""
            SELECT 
                a.id,
                a.advance_amount,
                a.remaining_amount,
                a.created_on,
                r.name as employee_name,
                r.role as employee_role,
                creator.name as created_by_name
            FROM advances a
            JOIN register r ON a.user_id = r.id
            JOIN register creator ON a.created_by = creator.id
            WHERE a.id = %s AND a.org_id = %s 
        """, (advance_id, org_id))
        
        advance = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if not advance:
            return jsonify({'success': False, 'error': 'Advance not found'}), 404
        
        # Format data
        advance['advance_amount'] = float(advance['advance_amount'])
        advance['remaining_amount'] = float(advance['remaining_amount'])
        advance['deducted_amount'] = advance['advance_amount'] - advance['remaining_amount']
        if advance['created_on']:
            advance['created_on'] = advance['created_on'].strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify({
            'success': True,
            'advance': advance
        })
        
    except Exception as e:
        if 'conn' in locals():
            cur.close()
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500


# Simplified add_salary route with advance integration

@app.route('/add_salary', methods=['GET', 'POST'])
def add_salary():
    if 'role' not in session or session['role'] != 'accountant':
        return redirect(url_for('login'))

    accountant_id = session['user_id']
    org_id = session['org_id']

    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # Fetch assigned projects
    cur.execute("""
        SELECT DISTINCT p.id, p.project_name
        FROM accountant_projects ap
        JOIN projects p ON ap.project_id = p.id
        WHERE ap.accountant_id = %s AND ap.org_id = %s
        GROUP BY p.id, p.project_name
    """, (accountant_id, org_id))
    projects = cur.fetchall()

    # Fetch relevant users
    cur.execute("""
        SELECT DISTINCT r.id, r.name, r.role
        FROM accountant_projects ap
        JOIN projects p ON ap.project_id = p.id
        JOIN sites s ON p.site_id = s.site_id
        JOIN register r ON r.id = s.site_engineer_id
        WHERE ap.accountant_id = %s AND ap.org_id = %s
        
        UNION
        
        SELECT DISTINCT r.id, r.name, r.role
        FROM accountant_projects ap
        JOIN projects p ON ap.project_id = p.id
        JOIN register r ON r.id = p.architect_id
        WHERE ap.accountant_id = %s AND ap.org_id = %s
        
        UNION
        
        SELECT DISTINCT r.id, r.name, r.role
        FROM register r
        WHERE r.id = %s AND r.role = 'accountant' AND r.org_id = %s
    """, (accountant_id, org_id, accountant_id, org_id, accountant_id, org_id))
    users = cur.fetchall()

    if request.method == 'POST':
        try:
            project_id = request.form['project_id']
            user_id = request.form['user_id']
            role = request.form['role']
            month_year = request.form['month_year']
            base_salary = float(request.form['base_salary'])
            allowance = float(request.form.get('allowance', 0) or 0)
            pf = float(request.form.get('pf', 0) or 0)
            other_deductions = float(request.form.get('other_deductions', 0) or 0)
            advance_deduction = float(request.form.get('advance', 0) or 0)
            description = request.form.get('description', '').strip()
            payment_mode = request.form['payment_mode']
            cheque_number = request.form.get('cheque_number', '').strip() if payment_mode == 'cheque' else None

            # Calculate net salary
            net_salary = base_salary + allowance - pf - advance_deduction - other_deductions

            # Check if salary already exists
            cur.execute("""
                SELECT id FROM salaries 
                WHERE user_id = %s AND project_id = %s AND month_year = %s 
                AND org_id = %s AND base_salary > 0
            """, (user_id, project_id, month_year, org_id))
            
            existing_salary = cur.fetchone()
            if existing_salary:
                flash('Salary already exists for this user, project, and month.', 'warning')
                return render_template('add_salary.html', projects=projects, users=users)

            # Insert salary record
            cur.execute("""
                INSERT INTO salaries (
                    project_id, user_id, role, month_year, base_salary, allowance, pf,
                    advance, other_deductions, description, net_salary, payment_mode, 
                    cheque_number, created_by, created_on, org_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
            """, (
                project_id, user_id, role, month_year, base_salary, allowance, pf,
                advance_deduction, other_deductions, description, net_salary, payment_mode, 
                cheque_number, accountant_id, org_id
            ))

            # If advance deduction was made, update advances table
            if advance_deduction > 0:
                # Get advances with remaining balance (oldest first - FIFO)
                cur.execute("""
                    SELECT id, advance_amount, remaining_amount
                    FROM advances
                    WHERE user_id = %s AND org_id = %s AND remaining_amount > 0
                    ORDER BY created_on ASC
                """, (user_id, org_id))
                
                advances = cur.fetchall()
                
                if not advances:
                    conn.rollback()
                    flash('No advance available for this employee.', 'danger')
                    return render_template('add_salary.html', projects=projects, users=users)
                
                # Calculate total available
                total_available = sum(float(adv['remaining_amount']) for adv in advances)
                
                if advance_deduction > total_available:
                    conn.rollback()
                    flash(f'Advance deduction (₹{advance_deduction:.2f}) exceeds available advance (₹{total_available:.2f})', 'danger')
                    return render_template('add_salary.html', projects=projects, users=users)
                
                # Deduct from advances (FIFO)
                remaining_to_deduct = advance_deduction
                
                for advance in advances:
                    if remaining_to_deduct <= 0:
                        break
                    
                    advance_id = advance['id']
                    advance_remaining = float(advance['remaining_amount'])
                    
                    if remaining_to_deduct >= advance_remaining:
                        # Fully deduct this advance
                        new_remaining = 0
                        remaining_to_deduct -= advance_remaining
                    else:
                        # Partially deduct
                        new_remaining = advance_remaining - remaining_to_deduct
                        remaining_to_deduct = 0
                    
                    # Update advance
                    cur.execute("""
                        UPDATE advances
                        SET remaining_amount = %s
                        WHERE id = %s
                    """, (new_remaining, advance_id))

            conn.commit()
            # 1.Notify the employee about their salary entry
            create_notification(
                user_id=user_id,
                org_id=org_id,
                notification_type='salary_new',
                reference_id=None,  # We don't have salary ID in your current structure
                message=f'Salary entry for {month_year} has been processed. Net: ₹{net_salary:,.2f}'
            )
            # 2. Notify all admins about the new salary entry
            cur.execute("""
                SELECT id FROM register 
                WHERE role = 'admin' AND org_id = %s
            """, (org_id,))
            admins = cur.fetchall()
            
            # Get employee name for admin notification
            cur.execute("SELECT name FROM register WHERE id = %s", (user_id,))
            emp_data = cur.fetchone()
            emp_name = emp_data['name'] if emp_data else 'Employee'
            
            # Get project name
            cur.execute("SELECT project_name FROM projects WHERE id = %s", (project_id,))
            proj_data = cur.fetchone()
            project_name = proj_data['project_name'] if proj_data else 'Unknown Project'
            
            for admin in admins:
                create_notification(
                    user_id=admin['id'],
                    org_id=org_id,
                    notification_type='salary_added',
                    reference_id=None,
                    message=f'Salary added: {emp_name} - {project_name} ({month_year}) - Net: ₹{net_salary:,.2f}'
                )

            flash('Salary entry added successfully.', 'success')

        except Exception as e:
            conn.rollback()
            flash(f'Error: {str(e)}', 'danger')
        finally:
            cur.close()
            conn.close()

        return redirect(url_for('add_salary'))

    cur.close()
    conn.close()
    return render_template('add_salary.html', projects=projects, users=users)


@app.route('/api/get_users_by_project/<int:project_id>')
def get_users_by_project(project_id):
    if 'role' not in session or session['role'] != 'accountant':
        return jsonify({'error': 'Unauthorized'}), 401
    
    accountant_id = session['user_id']
    org_id = session['org_id']
    
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    try:
        cur.execute("""
            SELECT DISTINCT r.id, r.name, r.role
            FROM accountant_projects ap
            JOIN projects p ON ap.project_id = p.id
            JOIN sites s ON p.site_id = s.site_id
            JOIN register r ON r.id = s.site_engineer_id
            WHERE ap.accountant_id = %s AND ap.org_id = %s AND p.id = %s

            UNION

            SELECT DISTINCT r.id, r.name, r.role
            FROM accountant_projects ap
            JOIN projects p ON ap.project_id = p.id
            JOIN register r ON r.id = p.architect_id
            WHERE ap.accountant_id = %s AND ap.org_id = %s AND p.id = %s

            UNION

            SELECT DISTINCT r.id, r.name, r.role
            FROM register r
            WHERE r.id = %s AND r.role = 'accountant' AND r.org_id = %s
        """, (accountant_id, org_id, project_id,
              accountant_id, org_id, project_id,
              accountant_id, org_id))
        
        users = cur.fetchall()
        return jsonify({'users': users})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

# Accountant: View Own Entered Salaries
@app.route('/view_salaries')
def view_salaries():
    if 'role' not in session or session['role'] != 'accountant':
        return redirect(url_for('login'))
    
    accountant_id = session['user_id']
    org_id = session['org_id']

    # ✅ MARK SALARY NOTIFICATIONS AS READ when accountant views this page
    mark_notifications_as_read(accountant_id, org_id, 'salary_new')

    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    
    # Updated query to include both salary entries and advance payments
    cur.execute("""
        SELECT 
            s.*, 
            p.project_name, 
            r.name AS user_name, 
            cr.name AS created_by_name
        FROM salaries s
        JOIN projects p ON s.project_id = p.id
        JOIN register r ON s.user_id = r.id
        JOIN register cr ON s.created_by = cr.id
        WHERE s.created_by = %s AND s.org_id = %s
        ORDER BY s.created_on DESC, s.month_year DESC, p.project_name
    """, (accountant_id, org_id))
    
    salaries = cur.fetchall()
    
    # Process each salary record to add computed fields
    for salary in salaries:
        # Determine entry type
        if salary['base_salary'] == 0 and salary['advance'] > 0:
            salary['entry_type'] = 'Advance Payment'
        elif salary['base_salary'] > 0 and salary['advance'] > 0:
            salary['entry_type'] = 'Salary with Advance Deduction'
        elif salary['base_salary'] > 0 and (salary['advance'] == 0 or salary['advance'] is None):
            salary['entry_type'] = 'Salary Payment'
        else:
            salary['entry_type'] = 'Other'
        
        # Calculate net amount
        if salary['base_salary'] == 0:
            salary['net_amount'] = float(salary['advance'] or 0)
        else:
            base = float(salary['base_salary'] or 0)
            allowance = float(salary['allowance'] or 0)
            pf = float(salary['pf'] or 0)
            advance = float(salary['advance'] or 0)
            other_deductions = float(salary.get('other_deductions', 0) or 0)
            salary['net_amount'] = base + allowance - pf - advance - other_deductions
    
    conn.close()
    return render_template('view_salaries.html', salaries=salaries)

@app.route('/admin/view_salaries')
def admin_view_salaries():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    admin_id = session['user_id']
    org_id = session.get('org_id')
    
    # ✅ MARK SALARY NOTIFICATIONS AS READ when admin views this page
    # (In case you want admin to see salary notifications too)
    mark_notifications_as_read(admin_id, org_id, 'salary_added')
    
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    # Include payment mode and cheque number in the query
    cur.execute("""
        SELECT s.*, p.project_name, r.name AS user_name, cr.name AS created_by_name
        FROM salaries s
        JOIN projects p ON s.project_id = p.id
        JOIN register r ON s.user_id = r.id
        JOIN register cr ON s.created_by = cr.id
        WHERE s.org_id = %s
        ORDER BY s.month_year DESC, p.project_name
    """, (org_id,))
    salaries = cur.fetchall()
    conn.close()
    return render_template('admin_view_salaries.html', salaries=salaries)



##########base salary ##############################

@app.route('/base_salary_management')
def base_salary_management():
    """Display base salary management page for accountant"""
    if 'role' not in session or session['role'] != 'accountant':
        return redirect(url_for('login'))
    
    accountant_id = session['user_id']
    org_id = session['org_id']
    
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    # Get all employees from the organization with their current base salary
    cur.execute("""
        SELECT DISTINCT
            r.id,
            r.name,
            r.role,
            COALESCE(bs.salary, 0.00) as base_salary,
            bs.created_on,
            bs.updated_on,
            creator.name as created_by_name,
            updater.name as updated_by_name
    FROM register r
    LEFT JOIN base_salaries bs ON r.id = bs.user_id AND bs.org_id = %s
    LEFT JOIN register creator ON bs.created_by = creator.id
    LEFT JOIN register updater ON bs.updated_by = updater.id
    WHERE r.org_id = %s
    AND r.role != 'admin'
    AND r.id IN (
        -- Site engineers from accountant's projects
        SELECT DISTINCT s.site_engineer_id
        FROM accountant_projects ap
        JOIN projects p ON ap.project_id = p.id
        JOIN sites s ON p.site_id = s.site_id
        WHERE ap.accountant_id = %s AND ap.org_id = %s
        AND s.site_engineer_id IS NOT NULL

        UNION

        -- Architects from accountant's projects
        SELECT DISTINCT p.architect_id
        FROM accountant_projects ap
        JOIN projects p ON ap.project_id = p.id
        WHERE ap.accountant_id = %s AND ap.org_id = %s
        AND p.architect_id IS NOT NULL

        UNION

        -- The accountant themselves
        SELECT %s
    )
    ORDER BY r.name ASC
""", (org_id, org_id, accountant_id, org_id, accountant_id, org_id, accountant_id))
    
    employees = cur.fetchall()
    
    # Convert datetime objects to strings for JSON serialization
    for emp in employees:
        if emp['created_on']:
            emp['created_on'] = emp['created_on'].strftime('%Y-%m-%d %H:%M:%S')
        if emp['updated_on']:
            emp['updated_on'] = emp['updated_on'].strftime('%Y-%m-%d %H:%M:%S')
    
    cur.close()
    conn.close()
    
    return render_template('base_salary_management.html', employees=employees)


@app.route('/get_employee_base_salary', methods=['POST'])
def get_employee_base_salary():
    """Get base salary for a specific employee"""
    if 'role' not in session or session['role'] != 'accountant':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        org_id = session['org_id']
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID is required'}), 400
        
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        # Get employee details with base salary
        cur.execute("""
            SELECT 
                r.id,
                r.name,
                r.role,
                COALESCE(bs.salary, 0.00) as base_salary,
                bs.created_on,
                bs.updated_on,
                creator.name as created_by_name,
                updater.name as updated_by_name
            FROM register r
            LEFT JOIN base_salaries bs ON r.id = bs.user_id AND bs.org_id = %s
            LEFT JOIN register creator ON bs.created_by = creator.id
            LEFT JOIN register updater ON bs.updated_by = updater.id
            WHERE r.id = %s AND r.org_id = %s AND r.role != 'admin'
        """, (org_id, user_id, org_id))
        
        employee = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if not employee:
            return jsonify({'success': False, 'error': 'Employee not found'}), 404
        
        # Convert datetime objects to strings
        if employee['created_on']:
            employee['created_on'] = employee['created_on'].strftime('%Y-%m-%d %H:%M:%S')
        if employee['updated_on']:
            employee['updated_on'] = employee['updated_on'].strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify({
            'success': True,
            'employee': employee
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/update_base_salary', methods=['POST'])
def update_base_salary():
    """Update or create base salary for an employee"""
    if 'role' not in session or session['role'] != 'accountant':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        new_salary = data.get('salary')
        
        if not user_id or new_salary is None:
            return jsonify({'success': False, 'error': 'User ID and salary are required'}), 400
        
        # Validate salary amount
        try:
            new_salary = float(new_salary)
            if new_salary < 0:
                return jsonify({'success': False, 'error': 'Salary cannot be negative'}), 400
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid salary amount'}), 400
        
        accountant_id = session['user_id']
        org_id = session['org_id']
        
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        # Check if employee exists in the organization
        cur.execute("""
            SELECT id FROM register WHERE id = %s AND org_id = %s AND role != 'admin'
        """, (user_id, org_id))
        
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Employee not found in organization'}), 404
        
        # Check if base salary record exists
        cur.execute("""
            SELECT id FROM base_salaries WHERE user_id = %s AND org_id = %s
        """, (user_id, org_id))
        
        existing_record = cur.fetchone()
        
        if existing_record:
            # Update existing record
            cur.execute("""
                UPDATE base_salaries 
                SET salary = %s, updated_by = %s, updated_on = NOW()
                WHERE user_id = %s AND org_id = %s
            """, (new_salary, accountant_id, user_id, org_id))
            message = 'Base salary updated successfully'
        else:
            # Insert new record
            cur.execute("""
                INSERT INTO base_salaries (user_id, salary, created_by, org_id, created_on)
                VALUES (%s, %s, %s, %s, NOW())
            """, (user_id, new_salary, accountant_id, org_id))
            message = 'Base salary added successfully'
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            cur.close()
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500
####################salary slip download ###########################

@app.route('/download_salary_slip/<int:salary_id>')
def download_salary_slip(salary_id):
    """Generate and download salary slip PDF - SINGLE PAGE VERSION"""
    if 'role' not in session or session['role'] not in ['accountant', 'admin']:
        return redirect(url_for('login'))
    
    org_id = session['org_id']
    
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    try:
        # Get salary details WITH contact_no from register table (JOIN)
        cur.execute("""
            SELECT s.*, 
                   p.project_name, 
                   r.name AS employee_name,
                   r.email AS employee_email,
                   r.contact_no AS employee_contact,
                   r.role AS employee_role
            FROM salaries s
            JOIN projects p ON s.project_id = p.id
            JOIN register r ON s.user_id = r.id
            WHERE s.id = %s AND s.org_id = %s
        """, (salary_id, org_id))
        
        salary = cur.fetchone()
        
        if not salary:
            flash('Salary record not found', 'danger')
            return redirect(url_for('view_salaries'))
        
        # Get organization details
        cur.execute("""
            SELECT company_name, company_address, company_phone, company_email, gst_number
            FROM organization_master 
            WHERE org_id = %s
        """, (org_id,))
        
        org = cur.fetchone()
        
        if not org:
            flash('Organization details not found', 'danger')
            return redirect(url_for('view_salaries'))
        
        cur.close()
        conn.close()
        
        # Generate PDF with optimized margins for single page
        buffer = BytesIO()
        # ✅ REDUCED MARGINS: 20 instead of 30 for more space
        doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
        styles = getSampleStyleSheet()
        
        # Professional Color Scheme
        primary_color = colors.HexColor('#1e3a8a')
        secondary_color = colors.HexColor('#3b82f6')
        accent_color = colors.HexColor('#f59e0b')
        text_dark = colors.HexColor('#1f2937')
        text_light = colors.HexColor('#6b7280')
        bg_light = colors.HexColor('#f8fafc')
        
        # ✅ COMPACT STYLES: Reduced font sizes and spacing
        company_name_style = ParagraphStyle(
            'company_name',
            parent=styles['Heading1'],
            fontSize=18,  # ✅ Reduced from 24
            textColor=primary_color,
            fontName='Helvetica-Bold',
            alignment=1,
            spaceAfter=3  # ✅ Reduced from 5
        )
        
        title_style = ParagraphStyle(
            'title',
            parent=styles['Heading2'],
            fontSize=16,  # ✅ Reduced from 20
            textColor=accent_color,
            fontName='Helvetica-Bold',
            alignment=1,
            spaceAfter=10  # ✅ Reduced from 20
        )
        
        section_header_style = ParagraphStyle(
            'section_header',
            parent=styles['Heading3'],
            fontSize=12,  # ✅ Reduced from 14
            textColor=primary_color,
            fontName='Helvetica-Bold',
            spaceBefore=8,  # ✅ Reduced from 15
            spaceAfter=5,  # ✅ Reduced from 8
            backColor=bg_light,
            leftIndent=8,
            rightIndent=8,
            topPadding=5,  # ✅ Reduced from 8
            bottomPadding=5
        )
        
        normal_style = ParagraphStyle(
            'normal',
            parent=styles['Normal'],
            fontSize=9,  # ✅ Reduced from 11
            textColor=text_dark,
            fontName='Helvetica',
            spaceAfter=2  # ✅ Reduced from 4
        )
        
        elements = []
        
        # ✅ COMPACT HEADER
        elements.append(Paragraph(org['company_name'], company_name_style))
        elements.append(Paragraph(org['company_address'], normal_style))
        elements.append(Paragraph(f"Phone: {org['company_phone']}", normal_style))
        elements.append(Paragraph(f"Email: {org['company_email']}", normal_style))
        if org['gst_number']:
            elements.append(Paragraph(f"GST: {org['gst_number']}", normal_style))
        elements.append(Spacer(1, 10))  # ✅ Reduced from 20
        
        # Title
        elements.append(Paragraph("SALARY SLIP", title_style))
        elements.append(Spacer(1, 5))  # ✅ Reduced from 10
        
        # Salary Period
        from datetime import datetime
        month_year = salary['month_year']
        month_name = datetime.strptime(month_year, '%Y-%m').strftime('%B %Y')
        
        period_data = [[f'For the month of: {month_name}']]
        period_table = Table(period_data, colWidths=[515])  # ✅ Adjusted for smaller margins
        period_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg_light),
            ('TEXTCOLOR', (0, 0), (-1, -1), primary_color),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),  # ✅ Reduced from 12
            ('TOPPADDING', (0, 0), (-1, -1), 6),  # ✅ Reduced from 10
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('BOX', (0, 0), (-1, -1), 1, primary_color),
        ]))
        elements.append(period_table)
        elements.append(Spacer(1, 10))  # ✅ Reduced from 20
        
        # ✅ COMPACT EMPLOYEE DETAILS
        elements.append(Paragraph("EMPLOYEE DETAILS", section_header_style))
        emp_data = [
            ['Employee Name:', salary['employee_name'], 'Employee ID:', str(salary['user_id'])],
            ['Role:', salary['employee_role'], 'Project:', salary['project_name']],
            ['Email:', salary['employee_email'] or 'N/A', 'Contact:', salary['employee_contact'] or 'N/A'],
            ['Payment Mode:', salary['payment_mode'].upper(), '', '']
        ]
        
        if salary['payment_mode'] == 'cheque' and salary['cheque_number']:
            emp_data.append(['Cheque Number:', salary['cheque_number'], '', ''])
        
        emp_table = Table(emp_data, colWidths=[120, 150, 100, 145])  # ✅ Adjusted widths
        emp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg_light),
            ('TEXTCOLOR', (0, 0), (-1, -1), text_dark),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),  # ✅ Reduced from 10
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
            ('BOX', (0, 0), (-1, -1), 2, primary_color),
            ('TOPPADDING', (0, 0), (-1, -1), 5),  # ✅ Reduced from 8
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),  # ✅ Reduced from 10
        ]))
        elements.append(emp_table)
        elements.append(Spacer(1, 10))  # ✅ Reduced from 20
        
        # Salary Breakdown
        elements.append(Paragraph("SALARY BREAKDOWN", section_header_style))
        
        # ✅ COMPACT EARNINGS TABLE
        earnings_data = [
            ['EARNINGS', 'AMOUNT (₹)'],
            ['Basic Salary', f'{float(salary["base_salary"] or 0):,.2f}'],
            ['Allowances', f'{float(salary["allowance"] or 0):,.2f}'],
        ]
        
        earnings_table = Table(earnings_data, colWidths=[385, 130])  # ✅ Adjusted widths
        earnings_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),  # ✅ Reduced from 11
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),  # ✅ Reduced from 10
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_light]),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
            ('BOX', (0, 0), (-1, -1), 2, primary_color),
            ('TOPPADDING', (0, 0), (-1, -1), 5),  # ✅ Reduced from 8
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),  # ✅ Reduced from 10
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(earnings_table)
        elements.append(Spacer(1, 8))  # ✅ Reduced from 15
        
        # ✅ COMPACT DEDUCTIONS TABLE
        deductions_data = [
            ['DEDUCTIONS', 'AMOUNT (₹)'],
            ['PF Deduction', f'{float(salary["pf"] or 0):,.2f}'],
            ['Advance Deduction', f'{float(salary["advance"] or 0):,.2f}'],
            ['Other Deductions', f'{float(salary["other_deductions"] or 0):,.2f}'],
        ]
        
        deductions_table = Table(deductions_data, colWidths=[385, 130])  # ✅ Adjusted widths
        deductions_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc3545')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),  # ✅ Reduced from 11
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),  # ✅ Reduced from 10
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_light]),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
            ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#dc3545')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),  # ✅ Reduced from 8
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),  # ✅ Reduced from 10
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(deductions_table)
        elements.append(Spacer(1, 10))  # ✅ Reduced from 20
        
        # ✅ COMPACT NET SALARY SUMMARY
        gross_salary = float(salary['base_salary'] or 0) + float(salary['allowance'] or 0)
        total_deductions = float(salary['pf'] or 0) + float(salary['advance'] or 0) + float(salary['other_deductions'] or 0)
        net_salary = float(salary['net_salary'] or 0)
        
        summary_data = [
            ['Gross Salary', f'₹{gross_salary:,.2f}'],
            ['Total Deductions', f'₹{total_deductions:,.2f}'],
            ['NET SALARY', f'₹{net_salary:,.2f}']
        ]
        
        summary_table = Table(summary_data, colWidths=[385, 130])  # ✅ Adjusted widths
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -2), bg_light),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#059669')),
            ('TEXTCOLOR', (0, 0), (-1, -2), text_dark),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
            ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -2), 10),  # ✅ Reduced from 11
            ('FONTSIZE', (0, -1), (-1, -1), 12),  # ✅ Reduced from 14
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
            ('BOX', (0, 0), (-1, -1), 2, primary_color),
            ('TOPPADDING', (0, 0), (-1, -1), 8),  # ✅ Reduced from 10
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),  # ✅ Reduced from 10
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(summary_table)
        # ✅ REMOVED EXTRA SPACER - elements.append(Spacer(1, 30))
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        
        # Generate filename
        filename = f"SalarySlip_{salary['employee_name'].replace(' ', '_')}_{month_year}.pdf"
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        if 'conn' in locals():
            cur.close()
            conn.close()
        flash(f'Error generating salary slip: {str(e)}', 'danger')
        return redirect(url_for('view_salaries'))
    

@app.route('/download_salary_report', methods=['POST'])
def download_salary_report():
    """Generate salary disbursement report for selected month"""
    if 'role' not in session or session['role'] not in ['accountant', 'admin']:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        month_year = data.get('month_year')
        
        if not month_year:
            return jsonify({'success': False, 'error': 'Month-year is required'}), 400
        
        org_id = session['org_id']
        
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        # Get organization details
        cur.execute("""
            SELECT company_name, company_address, company_phone, company_email, gst_number
            FROM organization_master 
            WHERE org_id = %s
        """, (org_id,))
        org = cur.fetchone()
        
        if not org:
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Organization not found'}), 404
        
        # Get all salaries for the month
        cur.execute("""
            SELECT s.*, 
                   p.project_name, 
                   r.name AS employee_name,
                   r.role AS employee_role
            FROM salaries s
            JOIN projects p ON s.project_id = p.id
            JOIN register r ON s.user_id = r.id
            WHERE s.month_year = %s AND s.org_id = %s AND s.base_salary > 0
            ORDER BY p.project_name, r.name
        """, (month_year, org_id))
        
        salaries = cur.fetchall()
        
        if not salaries:
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': 'No salary records found for the selected month'}), 404
        
        cur.close()
        conn.close()
        
        # Generate PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), 
                               leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
        styles = getSampleStyleSheet()
        
        # Professional Color Scheme
        primary_color = colors.HexColor('#1e3a8a')
        accent_color = colors.HexColor('#f59e0b')
        text_dark = colors.HexColor('#1f2937')
        text_light = colors.HexColor('#6b7280')
        bg_light = colors.HexColor('#f8fafc')
        
        # Custom Styles
        company_name_style = ParagraphStyle(
            'company_name',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=primary_color,
            fontName='Helvetica-Bold',
            alignment=1,
            spaceAfter=5
        )
        
        title_style = ParagraphStyle(
            'title',
            parent=styles['Heading2'],
            fontSize=18,
            textColor=accent_color,
            fontName='Helvetica-Bold',
            alignment=1,
            spaceAfter=15
        )
        
        normal_style = ParagraphStyle(
            'normal',
            parent=styles['Normal'],
            fontSize=9,
            textColor=text_dark,
            fontName='Helvetica',
            spaceAfter=3
        )
        
        elements = []
        
        # Header
        elements.append(Paragraph(org['company_name'], company_name_style))
        elements.append(Paragraph(org['company_address'], normal_style))
        elements.append(Paragraph(f"Phone: {org['company_phone']} | Email: {org['company_email']}", normal_style))
        if org['gst_number']:
            elements.append(Paragraph(f"GST: {org['gst_number']}", normal_style))
        elements.append(Spacer(1, 15))
        
        # Title
        month_name = datetime.strptime(month_year, '%Y-%m').strftime('%B %Y')
        elements.append(Paragraph(f"SALARY DISBURSEMENT REPORT - {month_name.upper()}", title_style))
        elements.append(Spacer(1, 10))
        
        # Salary Table
        table_data = [
            ['S.No', 'Employee Name', 'Role', 'Project', 'Base Salary', 
             'Allowance', 'PF', 'Advance', 'Other Ded.', 'Net Salary', 'Payment Mode']
        ]
        
        total_base = 0
        total_allowance = 0
        total_pf = 0
        total_advance = 0
        total_other_ded = 0
        total_net = 0
        
        for idx, s in enumerate(salaries, 1):
            base_salary = float(s['base_salary'] or 0)
            allowance = float(s['allowance'] or 0)
            pf = float(s['pf'] or 0)
            advance = float(s['advance'] or 0)
            other_ded = float(s['other_deductions'] or 0)
            net_salary = float(s['net_salary'] or 0)
            
            total_base += base_salary
            total_allowance += allowance
            total_pf += pf
            total_advance += advance
            total_other_ded += other_ded
            total_net += net_salary
            
            table_data.append([
                str(idx),
                s['employee_name'][:20],  # Truncate long names
                s['employee_role'][:15],
                s['project_name'][:20],
                f"₹{base_salary:,.2f}",
                f"₹{allowance:,.2f}",
                f"₹{pf:,.2f}",
                f"₹{advance:,.2f}",
                f"₹{other_ded:,.2f}",
                f"₹{net_salary:,.2f}",
                s['payment_mode'].upper()[:6]
            ])
        
        # Add totals row
        table_data.append([
            '',
            '',
            '',
            'TOTAL:',
            f"₹{total_base:,.2f}",
            f"₹{total_allowance:,.2f}",
            f"₹{total_pf:,.2f}",
            f"₹{total_advance:,.2f}",
            f"₹{total_other_ded:,.2f}",
            f"₹{total_net:,.2f}",
            ''
        ])
        
        # Create table
        col_widths = [30, 80, 60, 80, 70, 60, 50, 55, 55, 75, 55]
        salary_table = Table(table_data, colWidths=col_widths)
        
        # Table styling
        table_style = TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 8),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # S.No center
            ('ALIGN', (4, 1), (-2, -1), 'RIGHT'),  # Amount columns right
            ('ALIGN', (-1, 1), (-1, -1), 'CENTER'),  # Payment mode center
            
            # Totals row
            ('BACKGROUND', (0, -1), (-1, -1), bg_light),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 9),
            ('TEXTCOLOR', (0, -1), (-1, -1), primary_color),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('BOX', (0, 0), (-1, -1), 2, primary_color),
            
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, bg_light]),
        ])
        
        salary_table.setStyle(table_style)
        elements.append(salary_table)
        elements.append(Spacer(1, 20))
        
        # Summary
        summary_text = f"<b>Total Employees:</b> {len(salaries)} | <b>Total Disbursement:</b> ₹{total_net:,.2f}"
        summary_para = Paragraph(summary_text, ParagraphStyle(
            'summary',
            parent=styles['Normal'],
            fontSize=11,
            textColor=primary_color,
            fontName='Helvetica-Bold',
            alignment=1
        ))
        elements.append(summary_para)
        elements.append(Spacer(1, 15))
        
        # Footer
        footer_text = f"Generated on: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}"
        footer_para = Paragraph(footer_text, ParagraphStyle(
            'footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=text_light,
            fontName='Helvetica-Oblique',
            alignment=1
        ))
        elements.append(footer_para)
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        
        # Generate filename
        filename = f"Salary_Disbursement_Report_{month_year}.pdf"
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        if 'conn' in locals():
            cur.close()
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/get_compliance_data')
def get_compliance_data():
    if 'role' not in session or session['role'] not in ['admin', 'site_engineer']:
        return jsonify({'error': 'Unauthorized'}), 401

    project_id = request.args.get('project_id')
    if not project_id:
        return jsonify({'error': 'Project ID required'}), 400

    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    try:
        cur.execute("""
            SELECT * FROM legal_and_compliances 
            WHERE project_id = %s AND org_id = %s
        """, (project_id, session['org_id']))
        
        compliance = cur.fetchone()
        
        if compliance:
            return jsonify({
                'exists': True,
                'municipal_approval_status': compliance['municipal_approval_status'],
                'municipal_approval_pdf': compliance['municipal_approval_pdf'],
                'building_permit_pdf': compliance['building_permit_pdf'],
                'sanction_plan_pdf': compliance['sanction_plan_pdf'],
                'fire_department_noc_pdf': compliance['fire_department_noc_pdf'],
                'mngl_pdf': compliance['mngl_pdf'],
                'environmental_clearance': compliance['environmental_clearance']
            })
        else:
            return jsonify({'exists': False})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        cur.close()
        conn.close()

@app.route('/site_engineer/expenses', methods=['GET', 'POST'])
def site_engineer_expenses():
    if 'user_id' not in session or session.get('role') != 'site_engineer':
        return redirect('/login')

    site_engineer_id = session['user_id']
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Get org_id for the current site engineer
    cursor.execute("SELECT org_id FROM register WHERE id = %s", (site_engineer_id,))
    org = cursor.fetchone()
    org_id = org['org_id'] if org else None

    view_type = request.args.get('view', 'submit')
    if view_type == 'status':
        # Mark expense status notifications as read when viewing updates
        mark_notifications_as_read(site_engineer_id, org_id, 'expense_status')

    # Handle expense form submission
    if request.method == 'POST':
        date = request.form['date']
        description = request.form['description']
        amount = request.form['amount']
        project_id = request.form['project_id']

        # Validate: ensure project belongs to this engineer and org
        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM projects p
            JOIN sites s ON p.site_id = s.site_id
            WHERE p.id = %s AND s.site_engineer_id = %s AND s.org_id = %s
        """, (project_id, site_engineer_id, org_id))
        valid = cursor.fetchone()

        if valid and valid['count'] > 0:
            cursor.execute("""
                INSERT INTO daily_expenses 
                (site_engineer_id, org_id, project_id, date, description, amount) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (site_engineer_id, org_id, project_id, date, description, amount))
            expense_id = cursor.lastrowid
            conn.commit()
            #########notification code#########
            cursor.execute("""
                SELECT id FROM register 
                WHERE role = 'admin' AND org_id = %s
            """, (org_id,))
            admins = cursor.fetchall()
            
            # Get project name
            cursor.execute("SELECT project_name FROM projects WHERE id = %s", (project_id,))
            project = cursor.fetchone()
            project_name = project['project_name'] if project else 'Unknown Project'
            
            for admin in admins:
                create_notification(
                    user_id=admin['id'],
                    org_id=org_id,
                    notification_type='expense_submitted',
                    reference_id=expense_id,
                    message=f'New expense ₹{amount} submitted for {project_name} by {session.get("name")}'
                )
            
            flash('Expense added successfully.', 'success')
        else:
            flash('Invalid project selection. You can only add expenses for your assigned projects.', 'error')

    # Fetch expenses submitted by this engineer
    cursor.execute("""
        SELECT de.*, p.project_name 
        FROM daily_expenses de
        JOIN projects p ON de.project_id = p.id
        WHERE de.site_engineer_id = %s AND de.org_id = %s
        ORDER BY de.date DESC
    """, (site_engineer_id, org_id))
    expenses = cursor.fetchall()

    # Fetch projects assigned to this site engineer
    cursor.execute("""
        SELECT p.id, p.project_name
        FROM projects p
        JOIN sites s ON p.site_id = s.site_id
        WHERE s.site_engineer_id = %s AND s.org_id = %s
    """, (site_engineer_id, org_id))
    projects = cursor.fetchall()

    conn.close()
    return render_template("expenses.html", expenses=expenses, projects=projects)


@app.route('/site_engineer_expenses_view')
def site_engineer_expenses_view():
    # ✅ FIX 1: Use lowercase 'site_engineer' to match your existing route
    if 'user_id' not in session or session.get('role') != 'site_engineer':
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # ✅ FIX 2: Get org_id from database like your existing route does
    cursor.execute("SELECT org_id FROM register WHERE id = %s", (user_id,))
    org = cursor.fetchone()
    org_id = org['org_id'] if org else None
    
    # ✅ FIX 3: Get projects using the same query structure as your existing route
    cursor.execute("""
        SELECT p.id, p.project_name
        FROM projects p
        JOIN sites s ON p.site_id = s.site_id
        WHERE s.site_engineer_id = %s AND s.org_id = %s
    """, (user_id, org_id))
    projects = cursor.fetchall()
    
    # ✅ FIX 4: Query daily_expenses table (not expenses) and use site_engineer_id
    cursor.execute("""
        SELECT de.*, p.project_name
        FROM daily_expenses de
        JOIN projects p ON de.project_id = p.id
        WHERE de.site_engineer_id = %s AND de.org_id = %s
        ORDER BY de.date DESC, de.created_at DESC
    """, (user_id, org_id))
    expenses = cursor.fetchall()
    
    conn.close()
    
    # Categorize expenses
    pending_expenses = [exp for exp in expenses if exp['status'] == 'Pending']
    approved_expenses = [exp for exp in expenses if exp['status'] == 'Approved']
    rejected_expenses = [exp for exp in expenses if exp['status'] == 'Rejected']
    
    return render_template('site_engineer_expenses_view.html',
                         expenses=expenses,
                         pending_expenses=pending_expenses,
                         approved_expenses=approved_expenses,
                         rejected_expenses=rejected_expenses,
                         projects=projects)
##################################### Admin View Expenses #####################################
@app.route('/admin/expenses', methods=['GET', 'POST'])
def admin_view_expenses():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    admin_id = session['user_id']
    org_id = session.get('org_id')

    mark_notifications_as_read(admin_id, org_id, 'expense_submitted')
    
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Handle approval/rejection
    if request.method == 'POST':
        expense_id = request.form['expense_id']
        action = request.form['action']
        comment = request.form.get('admin_comment', '')

        if action in ['Approved', 'Rejected']:

            # Fetch expense details before updating
            cursor.execute("""
                SELECT de.*, r.name AS engineer_name, de.site_engineer_id, de.amount, p.project_name
                FROM daily_expenses de
                JOIN register r ON de.site_engineer_id = r.id
                JOIN projects p ON de.project_id = p.id
                WHERE de.id = %s
            """, (expense_id,))
            expense_data = cursor.fetchone()

            # Update status
            cursor.execute("""
                UPDATE daily_expenses 
                SET status = %s, admin_comment = %s 
                WHERE id = %s AND org_id = %s
            """, (action, comment, expense_id, org_id))
            conn.commit()

            # Send notifications
            if expense_data and expense_data['site_engineer_id']:
                notification_message = f'Expense ₹{expense_data["amount"]} for {expense_data["project_name"]} {action.lower()}'
                if comment:
                    notification_message += f'. Comment: {comment}'

                # Notify the site engineer
                create_notification(
                    user_id=expense_data['site_engineer_id'],
                    org_id=org_id,
                    notification_type='expense_status',
                    reference_id=expense_id,
                    message=notification_message
                )

                # If approved, also notify accountants assigned to this project
                if action == 'Approved':
                    cursor.execute("""
                        SELECT DISTINCT ap.accountant_id
                        FROM daily_expenses de
                        JOIN accountant_projects ap ON de.project_id = ap.project_id
                        WHERE de.id = %s AND de.org_id = %s
                    """, (expense_id, org_id))
                    accountants = cursor.fetchall()

                    for acc in accountants:
                        create_notification(
                            user_id=acc['accountant_id'],
                            org_id=org_id,
                            notification_type='expense_approved',
                            reference_id=expense_id,
                            message=f'Expense ₹{expense_data["amount"]} approved for {expense_data["project_name"]}'
                        )

        flash(f'Expense {action.lower()} successfully.', 'success')
        return redirect(url_for('admin_view_expenses'))

    # GET - Fetch all expenses for this org
    cursor.execute("""
        SELECT de.*, r.name AS engineer_name, p.project_name
        FROM daily_expenses de
        JOIN register r ON de.site_engineer_id = r.id
        JOIN projects p ON de.project_id = p.id
        WHERE de.org_id = %s
        ORDER BY de.created_at DESC
    """, (org_id,))
    expenses = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template("admin_view_expenses.html", expenses=expenses)


##################################### Accountant View Expenses #####################################
@app.route('/accountant/expenses')
def accountant_view_expenses():
    if 'user_id' not in session or session.get('role') != 'accountant':
        return redirect('/login')

    accountant_id = session['user_id']
    org_id = session.get('org_id')  # ← moved here, before the function call below

    # ✅ ADD THIS LINE - Mark expense_approved notifications as read
    mark_notifications_as_read(accountant_id, org_id, 'expense_approved')

    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    

    # Get assigned project IDs for this accountant
    cursor.execute("""
        SELECT project_id FROM accountant_projects 
        WHERE accountant_id = %s
    """, (accountant_id,))
    project_ids = [row['project_id'] for row in cursor.fetchall()]

    if not project_ids:
        expenses = []
    else:
        format_strings = ','.join(['%s'] * len(project_ids))
        query = f"""
            SELECT de.*, r.name AS engineer_name, p.project_name
            FROM daily_expenses de
            JOIN register r ON de.site_engineer_id = r.id
            JOIN projects p ON de.project_id = p.id
            WHERE de.org_id = %s AND de.status = 'Approved' 
            AND de.project_id IN ({format_strings})
            ORDER BY de.created_at DESC
        """
        cursor.execute(query, [org_id] + project_ids)
        expenses = cursor.fetchall()

    conn.close()
    return render_template("accountant_expenses.html", expenses=expenses)


@app.route('/admin/change_password', methods=['GET', 'POST'])
def admin_change_password():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        admin_id = session['user_id']
        
        conn = None  # Initialize conn
        try:
            conn = get_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Verify current password
            cursor.execute("SELECT password_hash FROM register WHERE id = %s", (admin_id,))
            user = cursor.fetchone()
            
            if not user:
                flash('User not found.', 'danger')
                return redirect(url_for('admin_change_password'))
            
            if not check_password_hash(user['password_hash'], current_password):
                flash('Current password is incorrect.', 'danger')
                return redirect(url_for('admin_change_password'))
            
            if new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
                return redirect(url_for('admin_change_password'))
            
            if len(new_password) < 6:
                flash('Password must be at least 6 characters long.', 'warning')
                return redirect(url_for('admin_change_password'))
            
            # Update password
            hashed_pw = generate_password_hash(new_password)
            cursor.execute("UPDATE register SET password_hash = %s WHERE id = %s", (hashed_pw, admin_id))
            conn.commit()
            
            flash('Password changed successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
            
        except Exception as e:
            if conn:
                conn.rollback()
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('admin_change_password'))
            
        finally:
            if conn:
                conn.close()
    
    return render_template('admin_change_password.html')

################################### NOTIFICATION API ROUTES ###################################
@app.route('/api/notifications/count')
def get_notification_counts():
    if 'user_id' not in session or 'org_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = session['user_id']
    org_id = session['org_id']
    role = session.get('role', '')
    
    # print(f"\n{'='*50}")
    # print(f"📱 API REQUEST - /api/notifications/count")
    # print(f"👤 User ID: {user_id}")
    # print(f"🏢 Org ID: {org_id}")
    # print(f"👔 Role: {role}")
    # print(f"{'='*50}\n")
    
    counts = {}
    
    try:
        # ✅ Get unread messages count directly from messages table (same for all roles)
        conn_msg = get_connection()
        cur_msg = conn_msg.cursor(pymysql.cursors.DictCursor)
        cur_msg.execute("""
            SELECT COUNT(*) as unread_count 
            FROM messages 
            WHERE receiver_id = %s AND org_id = %s AND is_read = FALSE
        """, (user_id, org_id))
        msg_result = cur_msg.fetchone()
        cur_msg.close()
        conn_msg.close()
        unread_messages = int(msg_result['unread_count']) if msg_result else 0

        if role == 'site_engineer':
            counts['projects'] = get_unread_notifications_count(user_id, org_id, 'project_assigned')
            counts['invoices'] = get_unread_notifications_count(user_id, org_id, 'invoice_rejected') + get_unread_notifications_count(user_id, org_id, 'invoice_approved')
            counts['expenses'] = get_unread_notifications_count(user_id, org_id, 'expense_status')
            counts['vendor_inventory'] = get_unread_notifications_count(user_id, org_id, 'vendor_approved')
            counts['legal'] = get_unread_notifications_count(user_id, org_id, 'legal_updated')
            counts['communication'] = unread_messages  # ✅ from messages table

        elif role == 'admin':
            counts['invoices'] = get_unread_notifications_count(user_id, org_id, 'invoice_pending')
            counts['expenses'] = get_unread_notifications_count(user_id, org_id, 'expense_submitted')
            counts['worker_reports'] = get_unread_notifications_count(user_id, org_id, 'worker_report_new')
            counts['vendor_inventory'] = get_unread_notifications_count(user_id, org_id, 'vendor_pending')
            counts['enquiries'] = get_unread_notifications_count(user_id, org_id, 'enquiry_new')
            counts['salaries'] = get_unread_notifications_count(user_id, org_id, 'salary_added')
            counts['progress'] = get_unread_notifications_count(user_id, org_id, 'progress_report')
            counts['inventory'] = get_unread_notifications_count(user_id, org_id, 'inventory_added')
            counts['communication'] = unread_messages  # ✅ from messages table
            counts['bills'] = get_unread_notifications_count(user_id, org_id, 'bill_added')

        elif role == 'architect':
            counts['projects'] = get_unread_notifications_count(user_id, org_id, 'project_assigned')
            counts['legal'] = get_unread_notifications_count(user_id, org_id, 'legal_updated')
            counts['communication'] = unread_messages  # ✅ from messages table

        elif role == 'accountant':
            counts['invoices'] = get_unread_notifications_count(user_id, org_id, 'invoice_approved')
            counts['expenses'] = get_unread_notifications_count(user_id, org_id, 'expense_approved')
            counts['salary'] = get_unread_notifications_count(user_id, org_id, 'salary_new')
            counts['projects'] = get_unread_notifications_count(user_id, org_id, 'project_assigned')
            counts['legal'] = get_unread_notifications_count(user_id, org_id, 'legal_updated')
            counts['communication'] = unread_messages  # ✅ from messages table
            counts['bills'] = get_unread_notifications_count(user_id, org_id, 'bill_added')

        else:
            counts['info'] = 'No role-specific counts available'

        counts['total'] = get_unread_notifications_count(user_id, org_id)

        # print(f"\n✅ FINAL COUNTS: {counts}\n")

        return jsonify(counts), 200

    except Exception as e:
        print(f"❌ Error in get_notification_counts: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal server error'}), 500
@app.route('/api/notifications/recent')
def get_recent_notifications_api():
    """
    API endpoint to get recent notifications for current user
    """
    if 'user_id' not in session or 'org_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = session['user_id']
    org_id = session['org_id']
    limit = request.args.get('limit', 10, type=int)
    
    try:
        notifications = get_recent_notifications(user_id, org_id, limit)
        return jsonify({
            'success': True,
            'notifications': notifications,
            'count': len(notifications)
        }), 200
        
    except Exception as e:
        print(f"Error in get_recent_notifications_api: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/notifications/mark-read', methods=['POST'])
def mark_notifications_read_api():
    """
    API endpoint to mark notifications as read by type
    Expects JSON: { "notification_type": "project_assigned" }
    """
    if 'user_id' not in session or 'org_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    if not data or 'notification_type' not in data:
        return jsonify({'error': 'notification_type is required'}), 400
    
    user_id = session['user_id']
    org_id = session['org_id']
    notification_type = data['notification_type']
    
    try:
        affected = mark_notifications_as_read(user_id, org_id, notification_type)
        return jsonify({
            'success': True,
            'message': f'{affected} notifications of type {notification_type} marked as read'
        }), 200
        
    except Exception as e:
        print(f"Error in mark_notifications_read_api: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/notifications/mark-all-read', methods=['POST'])
def mark_all_notifications_read():
    """
    API endpoint to mark ALL notifications as read for current user
    """
    if 'user_id' not in session or 'org_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = session['user_id']
    org_id = session['org_id']
    
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE notifications 
            SET is_read = 1 
            WHERE user_id = %s AND org_id = %s AND is_read = 0
        """, (user_id, org_id))
        
        affected_rows = cur.rowcount
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'{affected_rows} notifications marked as read'
        }), 200
        
    except Exception as e:
        print(f"Error in mark_all_notifications_read: {e}")
        conn.rollback()
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/notifications/delete/<int:notification_id>', methods=['DELETE'])
def delete_notification_api(notification_id):
    """
    API endpoint to delete a specific notification
    """
    if 'user_id' not in session or 'org_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = session['user_id']
    org_id = session['org_id']
    
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            DELETE FROM notifications 
            WHERE id = %s AND user_id = %s AND org_id = %s
        """, (notification_id, user_id, org_id))
        
        if cur.rowcount > 0:
            conn.commit()
            return jsonify({
                'success': True,
                'message': 'Notification deleted'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Notification not found or unauthorized'
            }), 404
            
    except Exception as e:
        print(f"Error in delete_notification_api: {e}")
        conn.rollback()
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/notifications/debug-all')
def debug_all_notifications():
    """DEBUG ONLY - See all notifications in database"""
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    # Get ALL notifications (not filtered by user)
    cur.execute("""
        SELECT 
            n.id,
            n.user_id,
            n.org_id,
            n.notification_type,
            n.reference_id,
            n.message,
            n.is_read,
            n.created_at,
            r.name as user_name,
            r.role as user_role
        FROM notifications n
        LEFT JOIN register r ON n.user_id = r.id
        ORDER BY n.created_at DESC
        LIMIT 50
    """)
    
    all_notifs = cur.fetchall()
    
    # Convert datetime
    for n in all_notifs:
        if n['created_at']:
            n['created_at'] = n['created_at'].strftime('%Y-%m-%d %H:%M:%S')
    
    cur.close()
    conn.close()
    
    return jsonify({
        'total_count': len(all_notifs),
        'notifications': all_notifs,
        'session_user_id': session.get('user_id'),
        'session_org_id': session.get('org_id'),
        'session_role': session.get('role')
    })


    ################################### NOTIFICATION TYPE CONSTANTS ###################################

# Notification Types Reference
NOTIFICATION_TYPES = {
    # Site Engineer notifications
    'project_assigned': 'New project assigned to you',
    'invoice_rejected': 'Your invoice was rejected',
    'invoice_approved': 'Your invoice was approved',
    'expense_status': 'Your expense status updated',
    'vendor_approved': 'Vendor inventory approved',
    
    # Admin notifications
    'invoice_pending': 'New invoice pending approval',
    'expense_submitted': 'New expense submitted',
    'worker_report_new': 'New worker report submitted',
    'vendor_pending': 'Vendor inventory pending approval',
    'enquiry_new': 'New visitor enquiry submitted',
    'salary_added': 'New salary entry added',
    
    # Architect notifications
    'legal_updated': 'Legal compliance updated',
    
    # Accountant notifications
    'salary_new': 'New salary entry',
    
    # Common notifications
    'message_new': 'New message received',
    'progress_report': 'New progress report uploaded'
}

############bills and payments routes#####################
import os
import time
from io import BytesIO
from datetime import datetime
from werkzeug.utils import secure_filename

# ReportLab imports
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import mm

# ── Upload folder for bill files ──────────────────────────────
UPLOAD_FOLDER_BILLS = 'static/bill_uploads'
os.makedirs(UPLOAD_FOLDER_BILLS, exist_ok=True)

def allowed_bill_file(filename):
    ALLOWED = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED


# ── Route: Bills & Payments (Add + History) ───────────────────
@app.route('/bills_and_payments', methods=['GET', 'POST'])
def bills_and_payments():
    """Bill & Payment Management – Admin and Accountant only"""
    if 'role' not in session or session['role'] not in ['admin', 'accountant']:
        return redirect(url_for('login'))

    user_id = session['user_id']
    role    = session['role']
    org_id  = session['org_id']

    conn = get_connection()
    cur  = conn.cursor(pymysql.cursors.DictCursor)
    # Fetch accountants for dropdown (admin only)
    accountants = []
    projects = []
    if role == 'admin':
        cur.execute("""
            SELECT id, name FROM register 
            WHERE role = 'accountant' AND org_id = %s
            ORDER BY name
        """, (org_id,))
        accountants = cur.fetchall()
        
        cur.execute("""
            SELECT id, project_name FROM projects 
            WHERE org_id = %s
            ORDER BY project_name
        """, (org_id,))
        projects = cur.fetchall()

    if request.method == 'POST':
        bill_id = None  
        try:
            # ── Collect form fields ──────────────────────────
            bill_no                  = request.form['bill_no'].strip()
            bill_date                = request.form['bill_date']
            bill_type                = request.form['bill_type']
            advance_amount           = float(request.form.get('advance_amount', 0) or 0)
            running_account_amount   = float(request.form.get('running_account_amount', 0) or 0)
            final_amount             = float(request.form.get('final_amount', 0) or 0)
            work_name                = request.form['work_name'].strip()
            project_id               = request.form.get('project_id')  # ✅ NEW
            accountant_id            = request.form.get('accountant_id')  # ✅ NEW
            work_order_number        = request.form['work_order_number'].strip()
            work_order_date          = request.form['work_order_date']
            tender_name              = request.form.get('tender_name', '').strip()
            tender_number            = request.form.get('tender_number', '').strip()
            gross_amount             = float(request.form['gross_amount'])
            gst_percentage           = float(request.form['gst_percentage'])
            security_deposit         = float(request.form.get('security_deposit', 0) or 0)
            payment_status           = request.form['payment_status']

            # ── Calculations ─────────────────────────────────
            gst_amount      = round((gross_amount * gst_percentage) / 100, 2)
            labour_charges  = round((gross_amount * 1.1) / 100, 2)
            net_amount      = round(gross_amount + gst_amount - security_deposit - labour_charges, 2)

            # ── File upload ──────────────────────────────────
            bill_file_path = None
            bill_file_type = None

            if 'bill_file' in request.files:
                file = request.files['bill_file']
                if file and file.filename and allowed_bill_file(file.filename):
                    filename    = secure_filename(file.filename)
                    file_ext    = filename.rsplit('.', 1)[1].lower()
                    unique_name = f"bill_{bill_no.replace('/', '_')}_{int(time.time())}.{file_ext}"
                    save_path   = os.path.join(UPLOAD_FOLDER_BILLS, unique_name)
                    file.save(save_path)
                    bill_file_path = f"bill_uploads/{unique_name}"
                    bill_file_type = 'pdf' if file_ext == 'pdf' else 'image'

            # ── Insert into DB ───────────────────────────────
            cur.execute("""
                INSERT INTO bills_and_payments (
                    bill_no, bill_date, bill_type, bill_file_path, bill_file_type,
                    advance_amount, running_account_amount, final_amount,
                    work_name, work_order_number, work_order_date,
                    tender_name, tender_number,
                    gross_amount, gst_percentage, gst_amount,
                    security_deposit, labour_charges, net_amount,
                    payment_status, created_by, created_by_role, org_id,
                    project_id, accountant_id
                ) VALUES (
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,
                    %s,%s,%s,
                    %s,%s,
                    %s,%s,%s,
                    %s,%s,%s,
                    %s,%s,%s,%s,
                    %s,%s
                )
            """, (
                bill_no, bill_date, bill_type, bill_file_path, bill_file_type,
                advance_amount, running_account_amount, final_amount,
                work_name, work_order_number, work_order_date,
                tender_name, tender_number,
                gross_amount, gst_percentage, gst_amount,
                security_deposit, labour_charges, net_amount,
                payment_status, user_id, role, org_id,
                project_id, accountant_id
            ))
            bill_id = cur.lastrowid
            conn.commit()
            # ══════════════════════════════════════════════════════════
            # 🔔 NOTIFICATION SYSTEM - ADD THIS BLOCK


            # Get creator's name
            cur.execute("SELECT name FROM register WHERE id = %s", (user_id,))
            creator_data = cur.fetchone()
            creator_name = creator_data['name'] if creator_data else 'User'

            # Build notification message
            notification_message = (
                f'New {bill_type} added: {bill_no} - {work_name} '
                f'(₹{net_amount:,.2f}) by {creator_name}'
            )

            if role == 'admin':
                
                if accountant_id:
                    create_notification(
                        user_id=int(accountant_id),
                        org_id=org_id,
                        notification_type='bill_added',
                        reference_id=bill_id,
                        message=notification_message
                    )
                    
            elif role == 'accountant':
                # Accountant added bill → Notify all admins
                cur.execute("""
                    SELECT id FROM register 
                    WHERE role = 'admin' AND org_id = %s
                """, (org_id,))
                admins = cur.fetchall()
                
                for admin in admins:
                    create_notification(
                        user_id=admin['id'],
                        org_id=org_id,
                        notification_type='bill_added',
                        reference_id=bill_id,
                        message=notification_message
                    )

            flash('Bill added successfully!', 'success')
            return redirect(url_for('bills_and_payments', tab='history'))

        except Exception as e:
            conn.rollback()
            flash(f'Error adding bill: {str(e)}', 'danger')
            return redirect(url_for('bills_and_payments'))

        finally:
            cur.close()
            conn.close()
    mark_notifications_as_read(user_id, org_id, 'bill_added')        

    # ── GET – fetch all bills for this org ───────────────────
    # ── GET – fetch bills based on role ───────────────────
    if role == 'admin':
        # Admin sees ALL bills
        cur.execute("""
            SELECT bp.*, r.name AS created_by_name
            FROM bills_and_payments bp
            JOIN register r ON bp.created_by = r.id
            WHERE bp.org_id = %s
            ORDER BY bp.created_at DESC
        """, (org_id,))
    elif role == 'accountant':
        # Accountant sees ONLY bills assigned to them OR bills they created
        cur.execute("""
            SELECT bp.*, r.name AS created_by_name
            FROM bills_and_payments bp
            JOIN register r ON bp.created_by = r.id
            WHERE bp.org_id = %s 
            AND (bp.accountant_id = %s OR bp.created_by = %s)
            ORDER BY bp.created_at DESC
        """, (org_id, user_id, user_id))

    bills = cur.fetchall()

    active_tab = request.args.get('tab', 'add')
    cur.close()
    conn.close()

    return render_template('bills_and_payments.html', 
                       bills=bills, 
                       active_tab=active_tab,
                       accountants=accountants,
                       projects=projects)


# ── Route: Download Bill as PDF ──────────────────────────────
@app.route('/download_bill_pdf/<int:bill_id>')
def download_bill_pdf(bill_id):
    """Generate and download a professional PDF for a bill."""
    if 'role' not in session or session['role'] not in ['admin', 'accountant']:
        return redirect(url_for('login'))

    org_id = session['org_id']
    conn   = get_connection()
    cur    = conn.cursor(pymysql.cursors.DictCursor)

    try:
        cur.execute("""
            SELECT bp.*, r.name AS created_by_name,
                   om.company_name, om.company_address
            FROM bills_and_payments bp
            JOIN register r ON bp.created_by = r.id
            LEFT JOIN organization_master om ON bp.org_id = om.org_id
            WHERE bp.id = %s AND bp.org_id = %s
        """, (bill_id, org_id))
        bill = cur.fetchone()
        cur.close()
        conn.close()

        if not bill:
            flash('Bill not found.', 'danger')
            return redirect(url_for('bills_and_payments', tab='history'))

        # ─── Build PDF ───────────────────────────────────────
        buffer = BytesIO()
        doc    = SimpleDocTemplate(
            buffer, pagesize=A4,
            leftMargin=20*mm, rightMargin=20*mm,
            topMargin=15*mm, bottomMargin=15*mm
        )
        styles = getSampleStyleSheet()
        W = 170 * mm  # usable page width

        # ── Unified Professional Color Palette ──────────────
        # ONE primary navy used everywhere for headers/labels
        C_PRIMARY    = colors.HexColor('#1e3a8a')   # navy  – all section headers & label cols
        C_PRIMARY_LT = colors.HexColor('#2d4fa3')   # slightly lighter navy – sub-headers
        C_ROW_ALT    = colors.HexColor('#eef2ff')   # very light indigo – alternate rows
        C_ROW_WHITE  = colors.white                  # white rows
        C_BORDER     = colors.HexColor('#c7d2fe')   # indigo-tinted border
        C_LABEL_BG   = colors.HexColor('#dbe4ff')   # label cell background (info grid)
        C_TEXT       = colors.HexColor('#1e293b')   # near-black body text
        C_GREY       = colors.HexColor('#64748b')   # muted grey for address / footer
        C_GREEN      = colors.HexColor('#059669')   # net payable / paid
        C_RED        = colors.HexColor('#dc2626')   # unpaid
        C_SUBTOTAL   = colors.HexColor('#1e4d8c')   # subtotal highlight row (same family)

        # Bill-type accent – same navy family, varying shade
        BT_COLOR = {
            'Advance Bill':        colors.HexColor('#1e3a8a'),
            'Running Account Bill':colors.HexColor('#1d4ed8'),
            'Final Bill':          colors.HexColor('#1e40af'),
        }.get(bill['bill_type'], C_PRIMARY)

        # ── Reusable padding shorthand ──
        PAD = [
            ('TOPPADDING',    (0,0),(-1,-1), 7),
            ('BOTTOMPADDING', (0,0),(-1,-1), 7),
            ('LEFTPADDING',   (0,0),(-1,-1), 9),
            ('RIGHTPADDING',  (0,0),(-1,-1), 9),
        ]

        # ── Helper: section header bar ──
        def sec_hdr(title):
            t = Table([[title]], colWidths=[W])
            t.setStyle(TableStyle([
                ('BACKGROUND',    (0,0),(-1,-1), C_PRIMARY),
                ('TEXTCOLOR',     (0,0),(-1,-1), colors.white),
                ('FONTNAME',      (0,0),(-1,-1), 'Helvetica-Bold'),
                ('FONTSIZE',      (0,0),(-1,-1), 10),
                ('ALIGN',         (0,0),(-1,-1), 'LEFT'),
                ('TOPPADDING',    (0,0),(-1,-1), 7),
                ('BOTTOMPADDING', (0,0),(-1,-1), 7),
                ('LEFTPADDING',   (0,0),(-1,-1), 10),
            ]))
            return t

        # ── Helper: two-column key-value table ──
        def kv_table(data, col_w):
            """Label col uses C_LABEL_BG, value col alternates white/C_ROW_ALT."""
            t = Table(data, colWidths=col_w)
            style = [
                ('FONTNAME',      (0,0),(0,-1),  'Helvetica-Bold'),
                ('FONTNAME',      (1,0),(1,-1),  'Helvetica'),
                ('FONTSIZE',      (0,0),(-1,-1), 9),
                ('TEXTCOLOR',     (0,0),(-1,-1), C_TEXT),
                ('BACKGROUND',    (0,0),(0,-1),  C_LABEL_BG),
                ('GRID',          (0,0),(-1,-1), 0.5, C_BORDER),
                ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
            ] + PAD
            # alternate value rows
            for i in range(len(data)):
                bg = C_ROW_WHITE if i % 2 == 0 else C_ROW_ALT
                style.append(('BACKGROUND', (1,i),(1,i), bg))
            t.setStyle(TableStyle(style))
            return t

        # ── Helper: financial table with col-header row ──
        def fin_table(data, col_w, subtotal_row=None):
            t = Table(data, colWidths=col_w)
            style = [
                # Header row
                ('BACKGROUND',    (0,0),(-1,0),  C_PRIMARY),
                ('TEXTCOLOR',     (0,0),(-1,0),  colors.white),
                ('FONTNAME',      (0,0),(-1,0),  'Helvetica-Bold'),
                ('FONTSIZE',      (0,0),(-1,0),  9),
                # Body
                ('FONTNAME',      (0,1),(-1,-1), 'Helvetica'),
                ('FONTSIZE',      (0,1),(-1,-1), 9),
                ('TEXTCOLOR',     (0,1),(-1,-1), C_TEXT),
                ('ALIGN',         (1,0),(1,-1),  'RIGHT'),
                ('GRID',          (0,0),(-1,-1), 0.5, C_BORDER),
                ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
            ] + PAD
            # alternate body rows
            for i in range(1, len(data)):
                bg = C_ROW_WHITE if i % 2 == 1 else C_ROW_ALT
                style.append(('BACKGROUND', (0,i),(-1,i), bg))
            # subtotal highlight
            if subtotal_row is not None:
                style += [
                    ('BACKGROUND', (0,subtotal_row),(-1,subtotal_row), C_SUBTOTAL),
                    ('TEXTCOLOR',  (0,subtotal_row),(-1,subtotal_row), colors.white),
                    ('FONTNAME',   (0,subtotal_row),(-1,subtotal_row), 'Helvetica-Bold'),
                ]
            t.setStyle(TableStyle(style))
            return t

        elems = []

        # ════════════════════════════════════════════════════
        # HEADER  –  company name + address, clean & aligned
        # ════════════════════════════════════════════════════
        company_name    = bill.get('company_name') or 'Company Name'
        company_address = bill.get('company_address') or ''

        s_name = ParagraphStyle('cn', parent=styles['Normal'],
                                 fontSize=22, textColor=C_PRIMARY,
                                 fontName='Helvetica-Bold', alignment=1,
                                 spaceBefore=0, spaceAfter=3)
        s_addr = ParagraphStyle('ca', parent=styles['Normal'],
                                 fontSize=9,  textColor=C_GREY,
                                 fontName='Helvetica', alignment=1,
                                 spaceBefore=0, spaceAfter=0)

        hdr_data = [[Paragraph(company_name, s_name)],
                    [Paragraph(company_address, s_addr)]]
        hdr_tbl  = Table(hdr_data, colWidths=[W])
        hdr_tbl.setStyle(TableStyle([
            ('ALIGN',         (0,0),(-1,-1), 'CENTER'),
            ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
            ('TOPPADDING',    (0,0),(-1,-1), 5),
            ('BOTTOMPADDING', (0,0),(-1,-1), 5),
            ('LEFTPADDING',   (0,0),(-1,-1), 0),
            ('RIGHTPADDING',  (0,0),(-1,-1), 0),
            ('LINEBELOW',     (0,1),(-1,1),  1.5, C_PRIMARY),   # underline below address
        ]))
        elems.append(hdr_tbl)
        elems.append(Spacer(1, 5*mm))

        # ════════════════════════════════════════════════════
        # TITLE BAR
        # ════════════════════════════════════════════════════
        title_tbl = Table([['BILL & PAYMENT DETAILS']], colWidths=[W])
        title_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(-1,-1), C_PRIMARY),
            ('TEXTCOLOR',     (0,0),(-1,-1), colors.white),
            ('FONTNAME',      (0,0),(-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE',      (0,0),(-1,-1), 14),
            ('ALIGN',         (0,0),(-1,-1), 'CENTER'),
            ('TOPPADDING',    (0,0),(-1,-1), 11),
            ('BOTTOMPADDING', (0,0),(-1,-1), 11),
        ]))
        elems.append(title_tbl)
        elems.append(Spacer(1, 2*mm))

        # ════════════════════════════════════════════════════
        # BILL TYPE BANNER  (navy shade variant)
        # ════════════════════════════════════════════════════
        bt_tbl = Table([[bill['bill_type']]], colWidths=[W])
        bt_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(-1,-1), BT_COLOR),
            ('TEXTCOLOR',     (0,0),(-1,-1), colors.white),
            ('FONTNAME',      (0,0),(-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE',      (0,0),(-1,-1), 11),
            ('ALIGN',         (0,0),(-1,-1), 'CENTER'),
            ('TOPPADDING',    (0,0),(-1,-1), 7),
            ('BOTTOMPADDING', (0,0),(-1,-1), 7),
        ]))
        elems.append(bt_tbl)
        elems.append(Spacer(1, 4*mm))

        # ════════════════════════════════════════════════════
        # BILL & WORK ORDER INFO  (4-column grid)
        # ════════════════════════════════════════════════════
        c1, c2, c3, c4 = W*0.22, W*0.28, W*0.22, W*0.28
        info_data = [
            ['Bill No',       bill['bill_no'],
             'Bill Date',     bill['bill_date'].strftime('%d-%m-%Y')],
            ['Work Order No', bill['work_order_number'],
             'Work Order Date', bill['work_order_date'].strftime('%d-%m-%Y')],
        ]
        info_tbl = Table(info_data, colWidths=[c1, c2, c3, c4])
        info_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(0,-1),  C_LABEL_BG),   # col 0 label
            ('BACKGROUND',    (2,0),(2,-1),  C_LABEL_BG),   # col 2 label
            ('BACKGROUND',    (1,0),(1,-1),  C_ROW_WHITE),
            ('BACKGROUND',    (3,0),(3,-1),  C_ROW_ALT),
            ('FONTNAME',      (0,0),(0,-1),  'Helvetica-Bold'),
            ('FONTNAME',      (2,0),(2,-1),  'Helvetica-Bold'),
            ('FONTNAME',      (1,0),(1,-1),  'Helvetica'),
            ('FONTNAME',      (3,0),(3,-1),  'Helvetica'),
            ('FONTSIZE',      (0,0),(-1,-1), 9),
            ('TEXTCOLOR',     (0,0),(-1,-1), C_TEXT),
            ('GRID',          (0,0),(-1,-1), 0.5, C_BORDER),
            ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
        ] + PAD))
        elems.append(info_tbl)
        elems.append(Spacer(1, 2*mm))

        # ════════════════════════════════════════════════════
        # WORK DETAILS
        # ════════════════════════════════════════════════════
        work_data = [
            ['Work Name',     bill['work_name']],
            ['Tender Name',   bill.get('tender_name') or 'N/A'],
            ['Tender Number', bill.get('tender_number') or 'N/A'],
        ]
        elems.append(kv_table(work_data, [W*0.30, W*0.70]))
        elems.append(Spacer(1, 4*mm))

        # ════════════════════════════════════════════════════
        # AMOUNT DETAILS
        # ════════════════════════════════════════════════════
        elems.append(sec_hdr('AMOUNT DETAILS'))
        elems.append(Spacer(1, 1*mm))

        amt_data = [
            ['Description',           'Amount (₹)'],
            ['Advance Amount',         f"₹{float(bill['advance_amount']):,.2f}"],
            ['Running Account Amount', f"₹{float(bill['running_account_amount']):,.2f}"],
            ['Final Amount',           f"₹{float(bill['final_amount']):,.2f}"],
        ]
        elems.append(fin_table(amt_data, [W*0.70, W*0.30]))
        elems.append(Spacer(1, 4*mm))

        # ════════════════════════════════════════════════════
        # FINANCIAL BREAKDOWN
        # ════════════════════════════════════════════════════
        elems.append(sec_hdr('FINANCIAL BREAKDOWN'))
        elems.append(Spacer(1, 1*mm))

        subtotal = float(bill['gross_amount']) + float(bill['gst_amount'])
        fin_data = [
            ['Description',                    'Amount (₹)'],
            ['Gross Amount',                    f"₹{float(bill['gross_amount']):,.2f}"],
            [f"(+) GST @ {float(bill['gst_percentage'])}%", f"₹{float(bill['gst_amount']):,.2f}"],
            ['Sub Total',                       f"₹{subtotal:,.2f}"],
            ['(−) Security Deposit',            f"₹{float(bill['security_deposit']):,.2f}"],
            ['(−) Labour Charges (1.1%)',        f"₹{float(bill['labour_charges']):,.2f}"],
        ]
        elems.append(fin_table(fin_data, [W*0.70, W*0.30], subtotal_row=3))
        elems.append(Spacer(1, 2*mm))

        # ════════════════════════════════════════════════════
        # NET PAYABLE AMOUNT
        # ════════════════════════════════════════════════════
        net_tbl = Table([['NET PAYABLE AMOUNT', f"₹{float(bill['net_amount']):,.2f}"]],
                         colWidths=[W*0.70, W*0.30])
        net_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(-1,-1), C_GREEN),
            ('TEXTCOLOR',     (0,0),(-1,-1), colors.white),
            ('FONTNAME',      (0,0),(-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE',      (0,0),(-1,-1), 13),
            ('ALIGN',         (1,0),(1,-1),  'RIGHT'),
            ('TOPPADDING',    (0,0),(-1,-1), 11),
            ('BOTTOMPADDING', (0,0),(-1,-1), 11),
            ('LEFTPADDING',   (0,0),(-1,-1), 10),
            ('RIGHTPADDING',  (0,0),(-1,-1), 10),
        ]))
        elems.append(net_tbl)
        elems.append(Spacer(1, 3*mm))

        # ════════════════════════════════════════════════════
        # PAYMENT STATUS BANNER
        # ════════════════════════════════════════════════════
        status_color = C_GREEN if bill['payment_status'] == 'Paid' else C_RED
        status_text  = 'PAID' if bill['payment_status'] == 'Paid' else 'UNPAID'
        st_tbl = Table([[f"Payment Status :  {status_text}"]], colWidths=[W])
        st_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(-1,-1), status_color),
            ('TEXTCOLOR',     (0,0),(-1,-1), colors.white),
            ('FONTNAME',      (0,0),(-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE',      (0,0),(-1,-1), 11),
            ('ALIGN',         (0,0),(-1,-1), 'CENTER'),
            ('TOPPADDING',    (0,0),(-1,-1), 9),
            ('BOTTOMPADDING', (0,0),(-1,-1), 9),
        ]))
        elems.append(st_tbl)
        elems.append(Spacer(1, 5*mm))

        # Footer
        footer_txt = (f"Created by: {bill['created_by_name']} ({bill['created_by_role'].title()})   |   "
                      f"Generated: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}")
        elems.append(Paragraph(footer_txt,
            ParagraphStyle('ft', parent=styles['Normal'],
                           fontSize=8, textColor=C_GREY, alignment=1)))

        doc.build(elems)
        buffer.seek(0)

        safe_no  = bill['bill_no'].replace('/', '_').replace(' ', '_')
        filename = f"Bill_{safe_no}.pdf"

        return send_file(buffer, mimetype='application/pdf',
                         as_attachment=True, download_name=filename)

    except Exception as e:
        if 'cur' in locals(): cur.close()
        if 'conn' in locals(): conn.close()
        flash(f'Error generating PDF: {str(e)}', 'danger')
        return redirect(url_for('bills_and_payments', tab='history'))
    
@app.route('/api/get_accountant_projects/<int:accountant_id>')
def get_accountant_projects(accountant_id):
    """Get projects assigned to a specific accountant"""
    if 'role' not in session or session['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    org_id = session['org_id']
    
    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    try:
        # Get projects assigned to this accountant
        cur.execute("""
            SELECT DISTINCT p.id, p.project_name
            FROM projects p
            JOIN accountant_projects ap ON p.id = ap.project_id
            WHERE ap.accountant_id = %s AND ap.org_id = %s
            ORDER BY p.project_name
        """, (accountant_id, org_id))
        
        projects = cur.fetchall()
        
        return jsonify({
            'success': True,
            'projects': projects
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    app.run(debug=True)
