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
from reportlab.lib.pagesizes import A4
from flask import send_from_directory
from reportlab.lib.styles import ParagraphStyle
from config import get_connection
from dotenv import load_dotenv
from decimal import Decimal
from PIL import Image as PILImage
from reportlab.platypus import Image as RLImage
import requests

load_dotenv()

UPLOAD_FOLDER_INVOICES = 'static/invoices'
os.makedirs(UPLOAD_FOLDER_INVOICES, exist_ok=True)

app = Flask(__name__)
app.secret_key = 'your_secret_key'

moment = Moment(app)

ZEPTOMAIL_API_URL = "https://api.zeptomail.in/v1.1/email"
ZEPTOMAIL_API_TOKEN = "PHtE6r1fFu65gzMt8UAJ5/7rHsGsN40m+uJufQkRtYxAXKABS01XrNooxGfkq018A/cXF/DPwNpque6ateiAd23lYGpNVGqyqK3sx/VYSPOZsbq6x00ftFsadUXVV4brdtRv0SXXvdrbNA=="  # Replace with your actual token
ZEPTOMAIL_FROM_EMAIL = "contact@rudhisoft.com"
ZEPTOMAIL_FROM_NAME = "SAM"

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
                                <strong>SAM Team</strong>
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
        contact_no = request.form.get('contact_no') if role == 'architect' else None

        password_hash = generate_password_hash(password)

        try:
            conn = get_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            # ✅ Get admin's org_id using session['user_id']
            admin_id = session['user_id']
            cursor.execute("SELECT org_id FROM register WHERE id = %s", (admin_id,))
            admin_data = cursor.fetchone()
            if not admin_data:
                flash("Unable to retrieve admin's organization.")
                return redirect(url_for('register'))
            org_id = admin_data['org_id']

            # ✅ Insert user with org_id
            cursor.execute("""
                INSERT INTO register (name, email, password_hash, role, org_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (name, email, password_hash, role, org_id))
            register_id = cursor.lastrowid
            conn.commit()

            # If architect, insert into architects table
            if role == 'architect':
                cursor.execute("""
                    INSERT INTO architects (name, email, license_number, contact_no, register_id,org_id)
                    VALUES (%s, %s, %s, %s, %s,%s)
                """, (name, email, license_number, contact_no, register_id,org_id))
                conn.commit()

            flash('User registered successfully.')
            return redirect(url_for('admin_dashboard'))

        except pymysql.err.IntegrityError:
            conn.rollback()
            flash('Email already exists.')

        except Exception as e:
            conn.rollback()
            flash(f'Registration failed: {e}')

        finally:
            conn.close()

    return render_template('register.html')

#######################################login routes######################################
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM register WHERE email=%s", (email,))
        user = cursor.fetchone()
        conn.close()

        print("Fetched user:", user)  # Debug line

        if user and check_password_hash(user['password_hash'], password):
            print("Password verified, generating OTP...")  # Debug line
            
            # Generate and send OTP
            otp = generate_otp()  # Generate random 6-digit OTP
            success, error = send_otp_email(email, otp)

            if success:
                # Store pending user data for OTP verification
                session['pending_user'] = {
                    'id': user['id'],
                    'role': user['role'],
                    'name': user['name'],
                    'org_id': user['org_id'],
                    'email': email,
                    'otp': otp,
                    'otp_expiry': (datetime.now() + timedelta(minutes=5)).timestamp()
                }
                flash('OTP sent to your email. Please verify to complete login.')
                return redirect(url_for('verify_otp'))
            else:
                flash(f'Error sending OTP: {error}')
                return render_template('login.html')
        else:
            flash('Invalid email or password.')

    return render_template('login.html')

##########################################verify OTP######################################
@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        user_otp = request.form.get('otp', '').strip()
        pending_user = session.get('pending_user')

        if not pending_user:
            flash("Session expired or invalid. Please login again.")
            return redirect(url_for('login'))

        # Check if OTP has expired
        if time.time() > pending_user['otp_expiry']:
            flash("OTP expired. Please login again.")
            session.pop('pending_user', None)
            return redirect(url_for('login'))

        # Verify OTP
        if user_otp == pending_user['otp']:
            # OTP correct: promote to logged-in user
            session['user_id'] = pending_user['id']
            session['role'] = pending_user['role']
            session['name'] = pending_user['name']
            session['org_id'] = pending_user['org_id']
            session.pop('pending_user', None)

            flash('Login successful!')
            
            # Redirect based on role
            role = session['role']
            if role == 'admin':
                response = redirect(url_for('admin_dashboard'))
            elif role == 'site_engineer':
                response = redirect(url_for('site_engineer_dashboard'))
            elif role == 'architect':
                response = redirect(url_for('architect_dashboard'))
            elif role == 'accountant':
                response = redirect(url_for('accountant_dashboard'))
            else:
                flash('Invalid user role.')
                return redirect(url_for('login'))
            
            # Clear flash messages before redirecting
            session.pop('_flashes', None)
            return response
        else:
            flash("Invalid OTP. Please try again.")
            
    return render_template("verify.html")
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

    # Fetch projects and their APPROVED invoices assigned to the accountant
    cur.execute("""
        SELECT
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
        LEFT JOIN invoices i ON p.id = i.project_id AND i.status = 'Approved'  # Only approved invoices
        LEFT JOIN register se ON i.site_engineer_id = se.id
        WHERE ap.accountant_id = %s and ap.org_id = %s
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
                'invoices': []
            }
        if row['invoice_id']:
            projects_with_invoices[project_id]['invoices'].append(row)

    conn.close()

    return render_template(
        'accountant_dashboard.html',
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
    return redirect('/')

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

    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # Handle POST submission
    if request.method == 'POST':
        project_id = request.form['project_id']
        worker_count = request.form['worker_count']
        report_date = request.form['report_date']

        try:
            cur.execute("""
                INSERT INTO daily_worker_report (site_engineer_id, project_id, worker_count, report_date,org_id)
                VALUES (%s, %s, %s, %s,%s)
            """, (site_engineer_id, project_id, worker_count, report_date,session['org_id']))
            conn.commit()
            flash('Worker report submitted successfully.')
        except Exception as e:
            flash(f'Error submitting report: {str(e)}')

    # Fetch only projects assigned to this site engineer (by admin)
    cur.execute("""
        SELECT p.*
        FROM projects p
        JOIN sites s ON p.project_name = s.site_name
        WHERE s.site_engineer_id = %s and s.org_id = %s
    """, (site_engineer_id,session['org_id']))
    projects = cur.fetchall()

    return render_template('submit_worker_report.html', projects=projects)


########################################## View Worker Reports ######################################
@app.route('/view_worker_reports')
def view_worker_reports():
    if 'role' not in session or session['role'] not in ['admin', 'site_engineer']:
        return redirect(url_for('login'))

    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # Step 1: Get the logged-in user's org_id
    user_id = session.get('user_id')
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






#---record attendance---

@app.route('/home')
def index():
    return redirect(url_for('record_attendance'))

@app.route('/attendance', methods=['GET', 'POST'])
def record_attendance():
    if request.method == 'POST':
        worker_name = request.form['worker_name']
        status = request.form['status']
        attendance_date = request.form['date']

        try:
            cursor = get_connection()
            db = cursor.cursor(pymysql.cursors.DictCursor)
            cursor.execute(
                "INSERT INTO attendance (worker_name, date, status) VALUES (%s, %s, %s)",
                (worker_name, attendance_date, status)
            )
            db.commit()
            flash("Attendance recorded successfully!", "success")
        except Exception as e:
            db.rollback()
            flash("Failed to record attendance. Error: " + str(e), "danger")

    return render_template('attendance_form.html', today=date.today())


@app.route('/view_attendance')
def view_attendance():
    cursor = get_connection()
    cursor.execute("SELECT * FROM attendance ORDER BY date DESC")
    records = cursor.fetchall()
    return render_template('view_attendance.html', records=records)

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
            
            if items_added == 0:
                flash('Error: No valid items to add', 'danger')
                conn.rollback()
                return redirect(url_for('add_inventory'))
            
            conn.commit()
            
            # Success message based on number of items added
            if items_added == 1:
                flash('1 inventory item added successfully!', 'success')
            else:
                flash(f'{items_added} inventory items added successfully!', 'success')
                
            return redirect(url_for('site_engineer_view_inventory'))

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
    return response


########################---assign sites---#######################################
@app.route('/assign_site', methods=['GET', 'POST'])
def assign_site():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    db = get_connection()
    cursor = db.cursor(pymysql.cursors.DictCursor)

    # ✅ Correctly pass org_id as a tuple
    cursor.execute(
        "SELECT id, name FROM register WHERE role = 'site_engineer' AND org_id = %s",
        (session['org_id'],)  # ← tuple with comma
    )
    engineers = cursor.fetchall()

    if request.method == 'POST':
        site_name = request.form['site_name']
        location = request.form['location']
        engineer_id = request.form['site_engineer_id']

        # ✅ Insert new site with associated engineer and org
        cursor.execute(
            "INSERT INTO sites (site_name, location, site_engineer_id, org_id) VALUES (%s, %s, %s, %s)",
            (site_name, location, engineer_id, session['org_id'])
        )
        db.commit()
        flash('Site assigned successfully.', 'success')
        return redirect(url_for('assign_site'))

    return render_template('assign_site.html', engineers=engineers)


################################--- View Assigned Sites ---###################

@app.route('/view_assigned_sites')
def view_assigned_sites():
    if session.get('role') != 'site_engineer':
        return redirect(url_for('login'))

    engineer_id = session['user_id']  # Make sure user_id is set on login

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



        added = 0

        for i in range(len(materials)):

            if not materials[i].strip():

                continue  # skip empty rows



            file = files[i]

            filename = None

            if file and allowed (file.filename):

                filename = f"{int(time.time())}_{secure_filename(file.filename)}"

                file.save(os.path.join(UPLOAD_FOLDER_VENDOR, filename))

            else:

                flash('Please upload a valid PDF for every item.', 'danger')

                return redirect(url_for('add_vendor_inventory'))

            # Insert into vendor_inventory table
            db = get_connection()
            cursor = db.cursor(pymysql.cursors.DictCursor)

            cursor.execute("""

                INSERT INTO vendor_inventory

                (material_description, quantity, date, status,

                 vendor_name, vendor_type, vendor_quotation_pdf,org_id)

                VALUES (%s, %s, CURDATE(), %s, %s, %s, %s, %s)

            """, (

                materials[i],

                int(quantities[i]),

                statuses[i],

                vendors[i],

                v_types[i],

                filename,

                session['org_id']

            ))

            db.commit()

            added += 1



        flash(f'{added} item(s) added successfully!', 'success')

        return redirect(url_for('add_vendor_inventory'))



    return render_template('add_vendor_inventory.html')


###################### --- Admin View Vendor Inventory --- ####################################################

@app.route('/admin/vendor_inventory', methods=['GET', 'POST'])
def admin_vendor_inventory():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    db = get_connection()
    cursor = db.cursor(pymysql.cursors.DictCursor)
    org_id = session.get('org_id')  # Get org_id from session

    if request.method == 'POST':
        rec_id = request.form['id']
        remark = request.form['remark']
        approval = request.form['approval']

        # ✅ Ensure org_id match during update
        cursor.execute("""
            UPDATE vendor_inventory 
            SET admin_remark=%s, admin_approval=%s 
            WHERE id=%s AND org_id=%s
        """, (remark, approval, rec_id, org_id))
        db.commit()

    # ✅ Only fetch records for the current organization
    cursor.execute("SELECT * FROM vendor_inventory WHERE org_id = %s", (org_id,))
    inv = cursor.fetchall()
    
    return render_template('admin_vendor_inventory.html', inventory=inv)




#@app.route('/site_engineer/workers')
#def site_engineer_workers():
#    if session.get('role') != 'site_engineer':
 #       return redirect(url_for('login'))

 #   with db.cursor() as cursor:
 #       cursor.execute("SELECT id, name, contact_no, aaapp.dhar_no FROM workers")
 #       workers = cursor.fetchall()

 #   return render_template('site_engineer_worker.html', workers=workers)


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
    db = get_connection()

    with db.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("""
            SELECT * FROM vendor_inventory
            WHERE admin_approval = 'approved' AND org_id = %s
            ORDER BY date DESC
        """, (org_id,))
        approved_inventory = cursor.fetchall()

    return render_template('site_engineer_approved_vendor_quotations.html', inventory=approved_inventory)

# def db_connection():

#     return pymysql.connect(
#         host='localhost',
#         user='root',         # <-- replace with your DB username
#         password='omgodse200378', # <-- replace with your DB password
#         db='construction_site_management',           # <-- replace with your DB name
#         cursorclass=pymysql.cursors.DictCursor
#     )

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
            conn.commit()
            conn.close()
            flash('Enquiry submitted successfully.')
            return redirect(url_for('site_engineer_dashboard'))

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

# @app.route('/view_architects')
# def view_architects():
#     if 'role' in session and session['role'] in ['admin', 'site_engineer']:
#         conn = None
#         try:
#             conn = db_connection()
#             cur = conn.cursor(pymysql.cursors.DictCursor)

#             if session['role'] == 'site_engineer':
#                 site_engineer_id = session['user_id']
#                 cur.execute("SELECT * FROM architects WHERE site_engineer_id = %s", (site_engineer_id,))
#             else:
#                 cur.execute("SELECT * FROM architects")

#             architects = cur.fetchall()
#             return render_template('view_architects.html', architects=architects)
            
#         except Exception as e:
#             flash(f'Error fetching architects: {str(e)}', 'error')
#             return render_template('view_architects.html', architects=[])
#         finally:
#             if conn:
#                 conn.close()
#     return redirect(url_for('login'))


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
            relative_path = f"uploads/{filename}"  # ✅ Forward slashes for URL

            # Create PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt="Cost Estimation Report", ln=True, align="C")
            pdf.ln(10)
            pdf.cell(200, 10, txt=f"Project ID: {project_id}", ln=True)
            pdf.cell(200, 10, txt=f"Architectural Design Cost: Rs. {architectural_cost}", ln=True)
            pdf.cell(200, 10, txt=f"Structural Design Cost: Rs. {structural_cost}", ln=True)
            pdf.cell(200, 10, txt=f"Cost per Sqft: Rs. {cost_per_sqft}", ln=True)
            pdf.cell(200, 10, txt=f"BOQ Reference: {boq_reference}", ln=True)
            pdf.multi_cell(0, 10, txt=f"Estimation Summary: {estimation_summary}")
            pdf.output(filepath)

            # Save PDF path to database
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT id FROM cost_estimation WHERE project_id = %s and org_id = %s", (project_id,org_id))
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
                """, (architectural_cost, structural_cost, estimation_summary, boq_reference, cost_per_sqft, relative_path, project_id,org_id))
            else:
                cur.execute("""
                    INSERT INTO cost_estimation 
                    (project_id, architectural_design_cost, structural_design_cost, 
                     estimation_summary, boq_reference, cost_per_sqft, report_pdf_path, generated_on,org_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(),%s)
                """, (project_id, architectural_cost, structural_cost, estimation_summary,
                      boq_reference, cost_per_sqft, relative_path,org_id))
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

            # Fetch architects from register table
            cursor.execute("SELECT id, name FROM register WHERE role = 'architect' and org_id = %s", (session['org_id'],))
            architects = cursor.fetchall()

            if request.method == 'POST':
                site_id = request.form['project_id']
                architect_id = request.form['architect_id']

                # Start a new transaction for the insert operation
                conn.begin()
                
                try:
                    # Get the site name for project name
                    cursor.execute("SELECT site_name FROM sites WHERE site_id = %s and org_id = %s", (site_id,session['org_id']))
                    site = cursor.fetchone()
                    
                    if site:
                        project_name = site['site_name']

                        # Insert into projects
                        cursor.execute("""
                            INSERT INTO projects (project_name, architect_id, site_id,org_id)
                            VALUES (%s, %s, %s, %s)
                        """, (project_name, architect_id, site_id, session['org_id']))

                        conn.commit()
                        flash('Project and Architect assigned successfully.')
                    else:
                        conn.rollback()
                        flash('Site not found.', 'error')
                        
                except Exception as e:
                    conn.rollback()
                    flash(f'Error assigning project: {str(e)}', 'error')

            # Pass session data to template
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

            # Use column names instead of indexes
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
        cur.close()
        conn.close()
        
        # SOLUTION 1: Redirect back to the same page to show flash message
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

    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    user_id = session.get('user_id')
    role = session.get('role')

    projects = []
    compliance_data = None
    selected_project = None
    not_approved = False

    if role == 'admin':
        cur.execute("""
            SELECT p.id, p.project_name 
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
                SELECT p.id, p.project_name, p.site_id
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
            SELECT p.id, p.project_name
            FROM projects p
            JOIN legal_and_compliances l ON p.id = l.project_id
             WHERE p.architect_id = %s
        """, (architect['register_id'],))
        projects = cur.fetchall()

    elif role == 'accountant':
        cur.execute("""
            SELECT p.id, p.project_name
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
            # Get form data
            project_id = request.form.get('project_id')
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
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),    # Labels left
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),    # Values left
                ('ALIGN', (2, 0), (2, -1), 'LEFT'),    # Labels left
                ('ALIGN', (3, 0), (3, -1), 'LEFT'),    # Values left
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

            elif action == 'reject':
                cursor.execute("""
                    UPDATE invoices 
                    SET status='Rejected', rejection_reason=%s, approved_by=%s, approved_on=NOW() 
                    WHERE id=%s AND org_id = %s
                """, (rejection_reason, admin_id, invoice_id, org_id))
                db.commit()
                flash("Invoice rejected.", "danger")

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

        cursor.execute("SELECT id, project_name FROM projects WHERE org_id = %s", (session['org_id'],))
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
                    invoice_date, client_name, client_address, client_phone, admin_id, image_filename, session['org_id']
                ))
                invoice_id = cursor.lastrowid

                items_inserted = 0
                for desc, qty, rate, subtotal_item in zip(descriptions, quantities, rates, totals):
                    if desc and qty and rate:
                        cursor.execute("""
                            INSERT INTO invoice_items (invoice_id, description, quantity, rate, subtotal, org_id)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (invoice_id, desc.strip(), float(qty), float(rate), float(subtotal_item), session['org_id']))
                        items_inserted += 1

                if items_inserted == 0:
                    raise Exception("No valid invoice items found")

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
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),  # Labels bold
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),       # Values normal
                ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),  # Labels bold
                ('FONTNAME', (3, 0), (3, -1), 'Helvetica'),       # Values normal
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('GRID', (0, 0), (-1, -1), 1, primary_color),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),    # Labels left
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),    # Values left
                ('ALIGN', (2, 0), (2, -1), 'LEFT'),    # Labels left
                ('ALIGN', (3, 0), (3, -1), 'LEFT'),    # Values left
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
@app.route('/site_engineer/invoices')
def site_engineer_invoices():
    if session.get('role') != 'site_engineer':
        return redirect(url_for('login'))

    site_engineer_id = session.get('user_id')
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

    org_id = session.get('org_id')  # Get the current admin's org_id

    conn = get_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    if request.method == 'POST':
        accountant_id = request.form['accountant_id']
        project_ids = request.form.getlist('project_ids')

        # Clear existing assignments for this accountant
        cur.execute("DELETE FROM accountant_projects WHERE accountant_id = %s", (accountant_id,))

        # Insert new assignments
        for project_id in project_ids:
            cur.execute(
                "INSERT INTO accountant_projects (accountant_id, project_id, org_id) VALUES (%s, %s, %s)",
                (accountant_id, project_id, org_id)
            )
        conn.commit()
        flash('Projects assigned successfully.')

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

    conn.close()

    return render_template(
        'assign_accountant.html',
        accountants=accountants,
        projects=projects,
        assignments=assignments
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
    
    # Get all messages between the two users
    cursor.execute("""
        SELECT * FROM messages
        WHERE ((sender_id = %s AND receiver_id = %s) OR (sender_id = %s AND receiver_id = %s)) AND org_id = %s
        ORDER BY timestamp ASC
    """, (sender_id, receiver_id, receiver_id, sender_id, org_id))
    messages = cursor.fetchall()
    
    # Mark messages as read where current user is the receiver
    cursor.execute("""
        UPDATE messages 
        SET is_read = TRUE 
        WHERE sender_id = %s AND receiver_id = %s AND is_read = FALSE
    """, (receiver_id, sender_id))
    
    conn.commit()
    conn.close()
    
    # Convert datetime objects to ISO format strings for proper JSON serialization
    for message in messages:
        if 'timestamp' in message and message['timestamp']:
            if isinstance(message['timestamp'], (datetime, date)):
                message['timestamp'] = message['timestamp'].isoformat()
    
    return jsonify(messages)

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
@app.route('/add_advance', methods=['POST'])
def add_advance():
    if 'role' not in session or session['role'] != 'accountant':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    try:
        data = request.get_json()
        user_id = data['user_id']
        project_id = data['project_id']
        role = data['role']
        month_year = data['month_year']
        advance_amount = float(data['advance_amount'])
        
        org_id = session['org_id']
        accountant_id = session['user_id']

        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)

        # Insert advance record (base_salary = 0 for pure advance entries)
        cur.execute("""
            INSERT INTO salaries (
                project_id, user_id, role, month_year, base_salary, allowance, pf,
                advance, description, payment_mode, cheque_number, created_by, created_on, org_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
        """, (
            project_id, user_id, role, month_year, 0, 0, 0,
            advance_amount, 'Advance Payment', 'cash', None, accountant_id, org_id
        ))

        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            cur.close()
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get_user_advance', methods=['POST'])
def get_user_advance():
    if 'role' not in session or session['role'] != 'accountant':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
            
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID is required'}), 400
            
        project_id = data.get('project_id')
        month_year = data.get('month_year')  # Optional for history view
        
        org_id = session['org_id']

        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)

        # Get user details
        cur.execute("""
            SELECT name, role FROM register WHERE id = %s AND org_id = %s
        """, (user_id, org_id))
        user_details = cur.fetchone()

        response_data = {
            'success': True,
            'user_details': user_details,
            'total_advance': 0.00,
            'total_advance_given': 0.00,
            'advance_history': []
        }

        # If month_year is provided, get current advance for that specific month
        if month_year and project_id:
            cur.execute("""
                SELECT COALESCE(SUM(advance), 0) as total_advance
                FROM salaries 
                WHERE user_id = %s AND project_id = %s AND month_year = %s 
                AND org_id = %s AND base_salary = 0 AND advance > 0
            """, (user_id, project_id, month_year, org_id))
            
            result = cur.fetchone()
            current_advance = float(result['total_advance']) if result and result['total_advance'] else 0.00
            response_data['total_advance'] = current_advance

        # FIXED: Get advance history - include ALL records with advance > 0, regardless of base_salary
        if project_id:
            history_query = """
                SELECT s.month_year, s.advance, s.base_salary, s.description, s.created_on, 
                       p.project_name,
                       CASE 
                           WHEN s.base_salary = 0 THEN 'Advance Payment'
                           ELSE 'Salary Deduction'
                       END as entry_type
                FROM salaries s
                JOIN projects p ON s.project_id = p.id
                WHERE s.user_id = %s AND s.project_id = %s AND s.org_id = %s 
                AND s.advance > 0
                ORDER BY s.created_on DESC
            """
            cur.execute(history_query, (user_id, project_id, org_id))
        else:
            # If no project_id, get all advances for this user
            history_query = """
                SELECT s.month_year, s.advance, s.base_salary, s.description, s.created_on, 
                       p.project_name,
                       CASE 
                           WHEN s.base_salary = 0 THEN 'Advance Payment'
                           ELSE 'Salary Deduction'
                       END as entry_type
                FROM salaries s
                JOIN projects p ON s.project_id = p.id
                WHERE s.user_id = %s AND s.org_id = %s 
                AND s.advance > 0
                ORDER BY s.created_on DESC
            """
            cur.execute(history_query, (user_id, org_id))
        
        advance_history = cur.fetchall()
        
        # Convert Decimal to float for JSON serialization
        for item in advance_history:
            if 'advance' in item and item['advance'] is not None:
                item['advance'] = float(item['advance'])
            if 'base_salary' in item and item['base_salary'] is not None:
                item['base_salary'] = float(item['base_salary'])
            if 'created_on' in item and item['created_on'] is not None:
                item['created_on'] = item['created_on'].isoformat() if hasattr(item['created_on'], 'isoformat') else str(item['created_on'])
        
        response_data['advance_history'] = advance_history
        
        # Calculate total advance given (sum of all advances where base_salary = 0, i.e., pure advances)
        total_given = sum(float(item['advance']) for item in advance_history if item['advance'] and item['base_salary'] == 0)
        response_data['total_advance_given'] = total_given

        cur.close()
        conn.close()
        
        return jsonify(response_data)
        
    except Exception as e:
        if 'conn' in locals():
            cur.close()
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/update_advance', methods=['POST'])
def update_advance():
    if 'role' not in session or session['role'] != 'accountant':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    try:
        data = request.get_json()
        user_id = data['user_id']
        project_id = data['project_id']
        month_year = data['month_year']
        advance_deduction = float(data['advance_deduction'])
        
        org_id = session['org_id']

        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)

        # Get current advance total for this month (only pure advance entries)
        cur.execute("""
            SELECT SUM(advance) as total_advance
            FROM salaries 
            WHERE user_id = %s AND project_id = %s AND month_year = %s 
            AND org_id = %s AND base_salary = 0
        """, (user_id, project_id, month_year, org_id))
        
        result = cur.fetchone()
        current_advance = float(result['total_advance']) if result and result['total_advance'] else 0.00
        
        # Calculate remaining advance
        remaining_advance = current_advance - advance_deduction
        
        if remaining_advance < 0:
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Advance deduction cannot exceed total advance'})
        
        # Strategy: Reduce advances starting from the most recent entry (only pure advance entries)
        cur.execute("""
            SELECT id, advance FROM salaries 
            WHERE user_id = %s AND project_id = %s AND month_year = %s 
            AND org_id = %s AND base_salary = 0 AND advance > 0
            ORDER BY created_on DESC
        """, (user_id, project_id, month_year, org_id))
        
        advance_records = cur.fetchall()
        deduction_left = advance_deduction
        
        for record in advance_records:
            if deduction_left <= 0:
                break
                
            record_advance = float(record['advance'])
            record_id = record['id']
            
            if deduction_left >= record_advance:
                # Delete this record completely
                cur.execute("DELETE FROM salaries WHERE id = %s", (record_id,))
                deduction_left -= record_advance
            else:
                # Reduce this record's advance
                new_advance = record_advance - deduction_left
                cur.execute("UPDATE salaries SET advance = %s WHERE id = %s", (new_advance, record_id))
                deduction_left = 0
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'remaining_advance': remaining_advance})
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            cur.close()
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

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
        SELECT p.id, p.project_name
        FROM accountant_projects ap
        JOIN projects p ON ap.project_id = p.id
        WHERE ap.accountant_id = %s AND ap.org_id = %s
    """, (accountant_id, org_id))
    projects = cur.fetchall()

    # Fetch relevant users: site engineers, architects, self (accountant)
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
            advance_deduction = float(request.form.get('advance', 0) or 0)  # This is the deduction amount
            description = request.form.get('description', '').strip()
            payment_mode = request.form['payment_mode']
            cheque_number = request.form.get('cheque_number', '').strip() if payment_mode == 'cheque' else None

            # Check if salary already exists for this user, project, and month (with base_salary > 0)
            cur.execute("""
                SELECT id FROM salaries 
                WHERE user_id = %s AND project_id = %s AND month_year = %s 
                AND org_id = %s AND base_salary > 0
            """, (user_id, project_id, month_year, org_id))
            
            existing_salary = cur.fetchone()
            if existing_salary:
                flash('Salary already exists for this user, project, and month.', 'warning')
                return render_template('add_salary.html', projects=projects, users=users)

            # Insert salary record - advance deduction will be recorded as a positive value
            # This represents money deducted from salary (advance that was already given)
            cur.execute("""
                INSERT INTO salaries (
                    project_id, user_id, role, month_year, base_salary, allowance, pf,
                    advance, description, payment_mode, cheque_number, created_by, created_on, org_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
            """, (
                project_id, user_id, role, month_year, base_salary, allowance, pf,
                advance_deduction, description, payment_mode, cheque_number, accountant_id, org_id
            ))

            conn.commit()
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

# Accountant: View Own Entered Salaries
@app.route('/view_salaries')
def view_salaries():
    if 'role' not in session or session['role'] != 'accountant':
        return redirect(url_for('login'))
    
    accountant_id = session['user_id']
    org_id = session['org_id']

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
            salary['net_amount'] = base + allowance - pf - advance
    
    conn.close()
    return render_template('view_salaries.html', salaries=salaries)
@app.route('/admin/view_salaries')
def admin_view_salaries():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    org_id = session.get('org_id')
    
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
            conn.commit()
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


##################################### Admin View Expenses #####################################
@app.route('/admin/expenses', methods=['GET', 'POST'])
def admin_view_expenses():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')

    admin_id = session['user_id']
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Get org_id for admin
    cursor.execute("SELECT org_id FROM register WHERE id = %s", (admin_id,))
    org = cursor.fetchone()
    org_id = org['org_id'] if org else None

    # Handle approval/rejection
    if request.method == 'POST':
        expense_id = request.form['expense_id']
        action = request.form['action']
        comment = request.form.get('admin_comment', '')

        if action in ['Approved', 'Rejected']:
            cursor.execute("""
                UPDATE daily_expenses 
                SET status = %s, admin_comment = %s 
                WHERE id = %s AND org_id = %s
            """, (action, comment, expense_id, org_id))
            conn.commit()

    # Fetch all expenses for this org
    cursor.execute("""
        SELECT de.*, r.name AS engineer_name, p.project_name
        FROM daily_expenses de
        JOIN register r ON de.site_engineer_id = r.id
        JOIN projects p ON de.project_id = p.id
        WHERE de.org_id = %s
        ORDER BY de.created_at DESC
    """, (org_id,))
    expenses = cursor.fetchall()

    conn.close()
    return render_template("admin_view_expenses.html", expenses=expenses)

##################################### Accountant View Expenses #####################################
@app.route('/accountant/expenses')
def accountant_view_expenses():
    if 'user_id' not in session or session.get('role') != 'accountant':
        return redirect('/login')

    accountant_id = session['user_id']
    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Get org_id
    cursor.execute("SELECT org_id FROM register WHERE id = %s", (accountant_id,))
    org = cursor.fetchone()
    org_id = org['org_id'] if org else None

    # Get assigned project IDs for this accountant
    cursor.execute("""
        SELECT project_id FROM accountant_projects 
        WHERE accountant_id = %s
    """, (accountant_id,))
    project_ids = [row['project_id'] for row in cursor.fetchall()]

    if not project_ids:
        expenses = []  # No assigned projects, no expenses
    else:
        # Use IN clause to filter only assigned projects
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




if __name__ == "__main__":
    app.run(debug=True)
