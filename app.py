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
from werkzeug.utils import secure_filename
import os
from PIL import Image as PILImage
from reportlab.platypus import Image as RLImage

UPLOAD_FOLDER_INVOICES = 'static/invoices'
os.makedirs(UPLOAD_FOLDER_INVOICES, exist_ok=True)

app = Flask(__name__)
app.secret_key = 'your_secret_key'

moment = Moment(app)

EMAIL = "rudhisoft@gmail.com"
EMAIL_PASSWORD = "adko lzta nznk chms"

# Connect to MySQL using pymysql
db = pymysql.connect(
    host="localhost",
    user="root",
    password="omgodse200378",  # <-- put your actual MySQL root password here
    database="construction_site_management",
    cursorclass=pymysql.cursors.DictCursor
)
cursor = db.cursor()
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
    return "123456"  # Static OTP for testing

def send_otp_email(email, otp):
    try:
        msg = MIMEText(f"Hello,\nYour OTP is {otp}. It will expire in 5 minutes.")
        msg['Subject'] = "Your OTP for Login"
        msg['From'] = EMAIL
        msg['To'] = email

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL, EMAIL_PASSWORD)
        server.sendmail(EMAIL, email, msg.as_string())
        server.quit()
        return True, None
    except Exception as e:
        return False, str(e)
    
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        cursor.execute("SELECT * FROM register WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user:
            otp = generate_otp()
            success, error = send_otp_email(email, otp)

            if success:
                session['reset_email'] = email
                session['reset_otp'] = otp
                # ✅ Store expiry in session
                session['reset_otp_expiry'] = (datetime.now() + timedelta(minutes=5)).timestamp()

                flash('OTP sent to your email.')
                return redirect(url_for('verify_reset_otp'))
            else:
                flash(f"Error sending OTP: {error}")
        else:
            flash("Email not registered.")
    
    return render_template('forgot_password.html')

@app.route('/verify_reset_otp', methods=['GET', 'POST'])
def verify_reset_otp():
    if request.method == 'POST':
        otp_input = request.form.get('otp')
        if 'reset_otp' not in session or 'reset_email' not in session:
            flash("Session expired. Please try again.")
            return redirect(url_for('forgot_password'))

        if time.time() > session.get('reset_otp_expiry', 0):
            flash("OTP expired.")
            return redirect(url_for('forgot_password'))

        if otp_input == session['reset_otp']:
            flash("OTP verified. Set a new password.")
            return redirect(url_for('reset_password'))  # ✅ Redirects to password reset
        else:
            flash("Invalid OTP.")
    return render_template("verify_reset_otp.html")

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        new_password = request.form['password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for('reset_password'))

        hashed_pw = generate_password_hash(new_password)
        email = session.get('reset_email')

        cursor.execute("UPDATE register SET password_hash = %s WHERE email = %s", (hashed_pw, email))
        db.commit()

        # Clear session values
        session.pop('reset_email', None)
        session.pop('reset_otp', None)
        session.pop('reset_otp_expiry', None)

        flash("Password reset successful. You can now login.")
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
            conn = db_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            # Insert into register table
            cursor.execute("""
                INSERT INTO register (name, email, password_hash, role)
                VALUES (%s, %s, %s, %s)
            """, (name, email, password_hash, role))
            register_id = cursor.lastrowid
            conn.commit()

            # If architect, insert into architects table
            if role == 'architect':
                cursor.execute("""
                    INSERT INTO architects (name, email, license_number, contact_no, register_id)
                    VALUES (%s, %s, %s, %s, %s)
                """, (name, email, license_number, contact_no, register_id))
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

        conn = db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM register WHERE email=%s", (email,))
        user = cursor.fetchone()
        conn.close()

        print("Fetched user:", user)  # Debug line

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['name'] = user['name']
            flash('Login successful!')

             # ✅ Generate and send OTP
            otp = generate_otp()
            success, error = send_otp_email(email, otp)
            session['user_id'] = user['id']
            session['role'] = user['role']
            flash('Login successful!')

            if success:
                session['pending_user'] = {
                    'id': user['id'],
                    'role': user['role'],
                    'email': email,
                    'otp': otp,
                    'otp_expiry': (datetime.now() + timedelta(minutes=5)).timestamp()
                }
                flash('OTP sent to your email. Please verify.')
                return redirect(url_for('verify_otp'))
            else:
                flash(f'Error sending OTP: {error}')

            # Redirect based on role
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'architect':
                return redirect(url_for('architect_dashboard'))
            elif user['role'] == 'site_engineer':
                return redirect(url_for('site_engineer_dashboard'))
            elif user['role'] == 'accountant':
                return redirect(url_for('accountant_dashboard'))
        else:
            flash('Invalid email or password.')

    return render_template('login.html')
@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        user_otp = request.form.get('otp')
        pending_user = session.get('pending_user')

        if not pending_user:
            flash("Session expired or invalid.")
            return redirect(url_for('login'))

        if time.time() > pending_user['otp_expiry']:
            flash("OTP expired. Please login again.")
            return redirect(url_for('login'))

        if user_otp == pending_user['otp']:
            # ✅ OTP correct: promote to logged-in user
            session['user_id'] = pending_user['id']
            session['role'] = pending_user['role']
            session.pop('pending_user', None)

            # Redirect based on role
            role = session['role']
            if role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif role == 'site_engineer':
                return redirect(url_for('site_engineer_dashboard'))
            elif role == 'architect':
                return redirect(url_for('architect_dashboard'))
            elif role == 'accountant':
                return redirect(url_for('accountant_dashboard'))

        else:
            flash("Invalid OTP.")
    return render_template("verify.html")
########################################admin routes######################################
@app.route('/admin1')
def admin_dashboard():
    if 'role' in session and session['role'] == 'admin':
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
    conn = db_connection()
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

        conn = db_connection()
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
        conn = db_connection()
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



@app.route('/accountant_dashboard')

def accountant_dashboard():

    if 'role' not in session or session['role'] != 'accountant':

        return redirect(url_for('login'))



    accountant_id = session['user_id']

    conn = db_connection()

    cur = conn.cursor(pymysql.cursors.DictCursor)



    # Fetch projects and their invoices assigned to the accountant

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

        LEFT JOIN invoices i ON p.id = i.project_id

        LEFT JOIN register se ON i.site_engineer_id = se.id

        WHERE ap.accountant_id = %s

        ORDER BY p.project_name, i.generated_on DESC

    """, (accountant_id,))

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
        # ... (get other form data)
        building_usage = request.form['building_usage']
        num_floors = request.form['num_floors']
        area_sqft = request.form['area_sqft']
        plot_area = request.form['plot_area']
        fsi = request.form['fsi']

        conn = db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO design_details (project_id, building_usage, num_floors, area_sqft, plot_area, fsi)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            building_usage = VALUES(building_usage),
            num_floors = VALUES(num_floors),
            area_sqft = VALUES(area_sqft),
            plot_area = VALUES(plot_area),
            fsi = VALUES(fsi)
        """, (project_id, building_usage, num_floors, area_sqft, plot_area, fsi))
        conn.commit()
        conn.close()
        flash("Design details saved successfully.")
        return redirect(url_for('architect_dashboard', project_id=project_id))

    return redirect(url_for('login'))

########################################### Add Structural Details ######################################

@app.route('/add_structural_details', methods=['POST'])
def add_structural_details():
    if 'role' in session and session['role'] == 'architect':
        project_id = request.form['project_id']
        # ... (get other form data)
        foundation_type = request.form['foundation_type']
        framing_system = request.form['framing_system']
        slab_type = request.form['slab_type']
        beam_details = request.form['beam_details']
        load_calculation = request.form['load_calculation']

        conn = db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO structural_details (project_id, foundation_type, framing_system, slab_type, beam_details, load_calculation)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            foundation_type = VALUES(foundation_type),
            framing_system = VALUES(framing_system),
            slab_type = VALUES(slab_type),
            beam_details = VALUES(beam_details),
            load_calculation = VALUES(load_calculation)
        """, (project_id, foundation_type, framing_system, slab_type, beam_details, load_calculation))
        conn.commit()
        conn.close()
        flash("Structural details saved successfully.")
        return redirect(url_for('architect_dashboard', project_id=project_id))

    return redirect(url_for('login'))


########################################## Add Material Specifications ######################################

@app.route('/add_material_specification', methods=['POST'])
def add_material_specification():
    if 'role' in session and session['role'] == 'architect':
        project_id = request.form['project_id']
        # ... (get other form data)
        primary_material = request.form['primary_material']
        wall_material = request.form['wall_material']
        roofing_material = request.form['roofing_material']
        flooring_material = request.form['flooring_material']
        fire_safety_materials = request.form['fire_safety_materials']

        conn = db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO material_specifications (project_id, primary_material, wall_material, roofing_material, flooring_material, fire_safety_materials)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            primary_material = VALUES(primary_material),
            wall_material = VALUES(wall_material),
            roofing_material = VALUES(roofing_material),
            flooring_material = VALUES(flooring_material),
            fire_safety_materials = VALUES(fire_safety_materials)
        """, (project_id, primary_material, wall_material, roofing_material, flooring_material, fire_safety_materials))
        conn.commit()
        conn.close()
        flash("Material specifications saved successfully.")
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

        required_types = ['Architectural Layout', 'Elevation Drawing', 'Section/Structural']

        # Validate file for required types
        if layout_type in required_types and (not file or not allowed_file(file.filename)):
            flash("PDF file is required for selected layout type.")
            return redirect(url_for('architect_dashboard'))

        file_path = ""
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)

            # Normalize path for URL (important for Flask routing)
            file_path = os.path.join('uploads', filename).replace("\\", "/")
            print("Debug - File path stored in DB:", file_path)
        elif layout_type in required_types:
            flash("File upload failed or missing.")
            return redirect(url_for('architect_dashboard'))

        # Save to DB
        conn = db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO drawing_documents (
                project_id, layout_type, document_title, file_path, uploaded_by
            ) VALUES (%s, %s, %s, %s, %s)
        """, (project_id, layout_type, document_title, file_path, uploaded_by))
        conn.commit()
        conn.close()

        flash("Drawing document uploaded successfully.")
        return redirect(url_for('architect_dashboard'))

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

        # Save Soil Report
        if soil_file and allowed_file(soil_file.filename):
            soil_filename = secure_filename("soil_" + soil_file.filename)
            soil_save_path = os.path.join(app.config['UPLOAD_FOLDER'], soil_filename)
            soil_file.save(soil_save_path)
            soil_path = os.path.join('uploads', soil_filename).replace("\\", "/")

        # Save Topo Map
        if topo_file and allowed_file(topo_file.filename):
            topo_filename = secure_filename("topo_" + topo_file.filename)
            topo_save_path = os.path.join(app.config['UPLOAD_FOLDER'], topo_filename)
            topo_file.save(topo_save_path)
            topo_path = os.path.join('uploads', topo_filename).replace("\\", "/")

        conn = db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO site_conditions (project_id, soil_report_path, water_table_level, topo_counter_map_path)
            VALUES (%s, %s, %s, %s)
        """, (project_id, soil_path, water_table_level, topo_path))
        conn.commit()
        conn.close()

        flash("Site condition documents uploaded successfully.")
        return redirect(url_for('architect_dashboard'))

    flash("Unauthorized access.")
    return redirect(url_for('login'))




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

@app.route('/submit_worker_report', methods=['GET', 'POST'])
def submit_worker_report():
    if 'role' not in session or session['role'] != 'site_engineer':
        return redirect(url_for('login'))

    site_engineer_id = session['user_id']

    conn = db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # Handle POST submission
    if request.method == 'POST':
        project_id = request.form['project_id']
        worker_count = request.form['worker_count']
        report_date = request.form['report_date']

        try:
            cur.execute("""
                INSERT INTO daily_worker_report (site_engineer_id, project_id, worker_count, report_date)
                VALUES (%s, %s, %s, %s)
            """, (site_engineer_id, project_id, worker_count, report_date))
            conn.commit()
            flash('Worker report submitted successfully.')
        except Exception as e:
            flash(f'Error submitting report: {str(e)}')

    # Fetch only projects assigned to this site engineer (by admin)
    cur.execute("""
        SELECT p.*
        FROM projects p
        JOIN sites s ON p.project_name = s.site_name
        WHERE s.site_engineer_id = %s
    """, (site_engineer_id,))
    projects = cur.fetchall()

    return render_template('submit_worker_report.html', projects=projects)

@app.route('/view_worker_reports')
def view_worker_reports():
    if 'role' not in session or session['role'] not in ['admin', 'site_engineer']:
        return redirect(url_for('login'))

    conn = db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    if session['role'] == 'admin':
        # Admin view: show all reports with site engineer name
        cur.execute("""
            SELECT 
                dr.id, 
                r.name AS site_engineer, 
                p.project_name, 
                dr.worker_count, 
                dr.report_date
            FROM daily_worker_report dr
            JOIN projects p ON dr.project_id = p.id
            JOIN register r ON dr.site_engineer_id = r.id
            ORDER BY dr.report_date DESC
        """)
        reports = cur.fetchall()
    
    else:
        # Site Engineer view: show their own reports along with their own name
        site_engineer_id = session['user_id']

        # First fetch the site engineer's name
        cur.execute("SELECT name FROM register WHERE id = %s", (site_engineer_id,))
        engineer = cur.fetchone()
        engineer_name = engineer['name'] if engineer else 'Unknown'

        # Now fetch that engineer's worker reports
        cur.execute("""
            SELECT 
                dr.id, 
                p.project_name, 
                dr.worker_count, 
                dr.report_date
            FROM daily_worker_report dr
            JOIN projects p ON dr.project_id = p.id
            WHERE dr.site_engineer_id = %s
            ORDER BY dr.report_date DESC
        """, (site_engineer_id,))
        reports = cur.fetchall()

        # Inject the site engineer name into each row
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
    cursor.execute("SELECT * FROM attendance ORDER BY date DESC")
    records = cursor.fetchall()
    return render_template('view_attendance.html', records=records)

#---record inventory---
@app.route('/add_inventory', methods=['GET', 'POST'])
def add_inventory():
    if 'role' not in session or session['role'] != 'site_engineer':
        return redirect('/')

    conn = db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        try:
            desc = request.form['material_description']
            qty = int(request.form['quantity'])
            stat = request.form['status']
            inv_date = request.form['date']

            query = "INSERT INTO inventory (material_description, quantity, date, status) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (desc, qty, inv_date, stat))
            conn.commit()
            flash('Inventory added successfully!', 'success')
            return redirect(url_for('view_inventory'))  # <== Redirect here
        except Exception as e:
            conn.rollback()
            flash(f'Error: {e}', 'danger')
        finally:
            cursor.close()
            conn.close()

    return render_template('add_inventory.html')



######################################## View Inventory ######################################

@app.route('/view_inventory')
def view_inventory():
    db = db_connection()  # Reopen DB connection freshly
    
    cursor = db.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM inventory ORDER BY date DESC")
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

    cursor.execute("SELECT id, name FROM register WHERE role = 'site_engineer'")
    engineers = cursor.fetchall()

    if request.method == 'POST':
        site_name = request.form['site_name']
        location = request.form['location']
        engineer_id = request.form['site_engineer_id']

        query = "INSERT INTO sites (site_name, location, site_engineer_id) VALUES (%s, %s, %s)"
        cursor.execute(query, (site_name, location, engineer_id))
        db.commit()
        flash('Site assigned successfully.')

    return render_template('assign_site.html', engineers=engineers)

################################--- View Assigned Sites ---###################

@app.route('/view_assigned_sites')
def view_assigned_sites():
    if session.get('role') != 'site_engineer':
        return redirect(url_for('login'))

    engineer_id = session['user_id']  # Make sure user_id is set on login

    cursor.execute("SELECT * FROM sites WHERE site_engineer_id = %s", (engineer_id,))
    sites = cursor.fetchall()
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
        cursor.execute("""
            INSERT INTO progress_reports 
            (site_id, progress_percent, image_path, pdf_path, report_date, remark) 
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (site_id, progress, img_filename, pdf_filename, today, remark))
        db.commit()
        flash('Progress report uploaded successfully!', 'success')
        return redirect(url_for('upload_progress'))

    # Get assigned sites
    cursor.execute("SELECT * FROM sites WHERE site_engineer_id = %s", (site_engineer_id,))
    sites = cursor.fetchall()
    return render_template('upload_progress.html', sites=sites)
################################### View Progress Reports (ADMIN)
@app.route('/view_progress')
def view_progress():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    cursor.execute("""SELECT pr.*, s.site_name, pr.report_date AS upload_date
                      FROM progress_reports pr 
                      JOIN sites s ON pr.site_id = s.site_id
                      ORDER BY pr.report_date DESC""")
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



            cursor.execute("""

                INSERT INTO vendor_inventory

                (material_description, quantity, date, status,

                 vendor_name, vendor_type, vendor_quotation_pdf)

                VALUES (%s, %s, CURDATE(), %s, %s, %s, %s)

            """, (

                materials[i],

                int(quantities[i]),

                statuses[i],

                vendors[i],

                v_types[i],

                filename

            ))

            db.commit()

            added += 1



        flash(f'{added} item(s) added successfully!', 'success')

        return redirect(url_for('add_vendor_inventory'))



    return render_template('add_vendor_inventory.html')


###################### --- Admin View Vendor Inventory --- ######################

@app.route('/admin/vendor_inventory', methods=['GET','POST'])
def admin_vendor_inventory():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    if request.method == 'POST':
        rec_id = request.form['id']
        remark = request.form['remark']
        approval = request.form['approval']
        cursor.execute("UPDATE vendor_inventory SET admin_remark=%s, admin_approval=%s WHERE id=%s",
                       (remark, approval, rec_id))
        db.commit()
    cursor.execute("SELECT * FROM vendor_inventory")
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

@app.route('/site_engineer/view_inventory')
def site_engineer_view_inventory():
    if 'role' not in session or session['role'] != 'site_engineer':
        return redirect('/')
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM inventory ORDER BY date DESC")
        data = cursor.fetchall()
    return render_template('view_inventory.html', inventory=data)

@app.route('/site_engineer/approved_vendor_inventory')
def site_engineer_approved_vendor_quotations():
    if session.get('role') != 'site_engineer':
        return redirect(url_for('login'))
    cursor.execute("SELECT * FROM vendor_inventory WHERE admin_approval='approved'")
    approved_inventory = cursor.fetchall()
    return render_template('site_engineer_approved_vendor_quotations.html', inventory=approved_inventory)
def db_connection():

    return pymysql.connect(
        host='localhost',
        user='root',         # <-- replace with your DB username
        password='omgodse200378', # <-- replace with your DB password
        db='construction_site_management',           # <-- replace with your DB name
        cursorclass=pymysql.cursors.DictCursor
    )

@app.route('/add_enquiry', methods=['GET', 'POST'])
def add_enquiry():
    if 'role' in session and session['role'] == 'site_engineer':
        if request.method == 'POST':
            name = request.form['name']
            address = request.form['address']
            contact_no = request.form['contact_no']
            requirement = request.form['requirement']
            engineer_id = session['user_id']

            conn = db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO enquiries (site_engineer_id, name, address, contact_no, requirement) VALUES (%s, %s, %s, %s, %s)",
                (engineer_id, name, address, contact_no, requirement)
            )
            conn.commit()
            conn.close()
            flash('Enquiry submitted successfully.')
            return redirect(url_for('site_engineer_dashboard'))

        return render_template('add_enquiry.html')

    else:
        return redirect(url_for('login'))

@app.route('/admin/enquiries')
def view_enquiries():
    if 'role' in session and session['role'] in ['admin', 'site_engineer']:
        conn = db_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        if session['role'] == 'admin':
            cur.execute("""
                SELECT e.*, r.name AS engineer_name 
                FROM enquiries e
                JOIN register r ON e.site_engineer_id = r.id
                ORDER BY e.enquiry_date DESC
            """)
        else:  # site_engineer
            site_engineer_id = session['user_id']
            cur.execute("""
                SELECT e.*, r.name AS engineer_name 
                FROM enquiries e
                JOIN register r ON e.site_engineer_id = r.id
                WHERE e.site_engineer_id = %s
                ORDER BY e.enquiry_date DESC
            """, (site_engineer_id,))
        enquiries = cur.fetchall()
        conn.close()
        return render_template('view_enquiry.html', enquiries=enquiries)
    else:
        return redirect(url_for('login'))
    
@app.route('/add_architect', methods=['GET', 'POST'])
def add_architect():
    conn = db_connection()
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

@app.route('/view_architects')
def view_architects():
    if 'role' in session and session['role'] in ['admin', 'site_engineer']:
        conn = db_connection()
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

@app.route('/view_architect_details/<int:architect_id>')
def view_architect_details(architect_id):
    if 'role' in session and session['role'] in ['admin', 'site_engineer']:
        conn = None
        try:
            conn = db_connection()
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

@app.route('/upload_utilities_services', methods=['POST'])
def upload_utilities_services():
    if 'role' in session and session['role'] == 'architect':
        project_id = request.form.get('project_id')
        water_supply = request.form.get('water_supply_source')
        drainage_system = request.form.get('drainage_system_type')
        power_supply = request.form.get('power_supply_source')

        conn = db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO utilities_services (
                project_id, water_supply_source, drainage_system_type, power_supply_source
            ) VALUES (%s, %s, %s, %s)
        """, (project_id, water_supply, drainage_system, power_supply))

        conn.commit()
        conn.close()
        flash("Utilities Services uploaded successfully.")
        return redirect(url_for('architect_dashboard'))
    else:
        flash("Unauthorized access.")
        return redirect(url_for('login'))




@app.route('/upload_cost_estimation', methods=['POST'])
def upload_cost_estimation():
    if 'role' in session and session['role'] == 'architect':
        project_id = request.form.get('project_id')
        arch_cost = request.form.get('architectural_design_cost')
        struct_cost = request.form.get('structural_design_cost')
        summary = request.form.get('estimation_summary')
        boq = request.form.get('boq_reference')
        cost_per_sqft = request.form.get('cost_per_sqft')

        # Ensure the upload directory exists
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

        # Generate unique PDF filename
        filename = f"estimation_{uuid.uuid4().hex[:8]}.pdf"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        #relative_path = os.path.join('uploads', os.path.basename(app.config['UPLOAD_FOLDER']), filename).replace("\\", "/")
        relative_path = os.path.join('uploads', filename).replace("\\", "/")


        # Create PDF from submitted data
        pdf_data = {
            "Project ID": project_id,
            "Architectural Design Cost": arch_cost,
            "Structural Design Cost": struct_cost,
            "Estimation Summary": summary,
            "BOQ Reference": boq,
            "Cost per Sqft": cost_per_sqft
        }
        generate_estimation_pdf(pdf_data, save_path)

        # Save to DB
        conn = db_connection()
        cur = conn.cursor()

        # Update if project already has entry
        cur.execute("SELECT id FROM cost_estimation WHERE project_id = %s", (project_id,))
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
                WHERE project_id = %s
            """, (arch_cost, struct_cost, summary, boq, cost_per_sqft, relative_path, project_id))
        else:
            cur.execute("""
                INSERT INTO cost_estimation
                    (project_id, architectural_design_cost, structural_design_cost,
                     estimation_summary, boq_reference, cost_per_sqft, report_pdf_path)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (project_id, arch_cost, struct_cost, summary, boq, cost_per_sqft, relative_path))

        conn.commit()
        conn.close()

        flash("Cost estimation saved and PDF generated.")
        return redirect(url_for('architect_dashboard'))

    flash("Unauthorized access.")
    return redirect(url_for('login'))




# # Define the function first
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
            conn = db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id FROM cost_estimation WHERE project_id = %s", (project_id,))
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
                    WHERE project_id = %s
                """, (architectural_cost, structural_cost, estimation_summary, boq_reference, cost_per_sqft, relative_path, project_id))
            else:
                cur.execute("""
                    INSERT INTO cost_estimation 
                    (project_id, architectural_design_cost, structural_design_cost, 
                     estimation_summary, boq_reference, cost_per_sqft, report_pdf_path, generated_on)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                """, (project_id, architectural_cost, structural_cost, estimation_summary,
                      boq_reference, cost_per_sqft, relative_path))
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

@app.route('/assign_architect', methods=['GET', 'POST'])
def assign_architect():
    if 'role' in session and session['role'] in ['admin', 'site_engineer']:
        conn = None
        try:
            conn = db_connection()
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
            cursor.execute("SELECT id, name FROM register WHERE role = 'architect'")
            architects = cursor.fetchall()

            if request.method == 'POST':
                site_id = request.form['project_id']
                architect_id = request.form['architect_id']

                # Start a new transaction for the insert operation
                conn.begin()
                
                try:
                    # Get the site name for project name
                    cursor.execute("SELECT site_name FROM sites WHERE site_id = %s", (site_id,))
                    site = cursor.fetchone()
                    
                    if site:
                        project_name = site['site_name']

                        # Insert into projects
                        cursor.execute("""
                            INSERT INTO projects (project_name, architect_id, site_id)
                            VALUES (%s, %s, %s)
                        """, (project_name, architect_id, site_id))

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
@app.route('/admin/assigned_sites')
def admin_assigned_sites():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    cursor.execute("SELECT * FROM sites WHERE site_engineer_id IS NOT NULL")
    sites = cursor.fetchall()
    return render_template('admin_assigned_sites.html', sites=sites)

@app.route('/view_assigned_architects')
def view_assigned_architects():
    if 'role' not in session or session['role'] not in ['admin', 'site_engineer']:
        return redirect(url_for('login'))

    conn = db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    if session['role'] == 'admin':
        cur.execute("""
            SELECT s.site_id, s.site_name, p.id AS project_id, r.name AS architect_name, r.email AS architect_email
            FROM sites s
            LEFT JOIN projects p ON s.site_id = p.site_id
            LEFT JOIN register r ON p.architect_id = r.id
            WHERE s.site_engineer_id IS NOT NULL
        """)
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
@app.route('/view_project_details', methods=['GET', 'POST'])
def view_project_details():
    if 'role' not in session or session['role'] not in ['admin', 'site_engineer']:
        return redirect(url_for('login'))

    user_id = session['user_id']
    role = session['role']

    conn = db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Get all project options for dropdown
    if role == 'admin':
        cursor.execute("SELECT id, project_name FROM projects")
        project_list = cursor.fetchall()
    elif role == 'site_engineer':
        cursor.execute("""
            SELECT p.id, p.project_name
            FROM projects p
            JOIN sites s ON p.site_id = s.site_id
            WHERE s.site_engineer_id = %s
        """, (user_id,))
        project_list = cursor.fetchall()
    else:
        project_list = []

    selected_project = None
    project_id = request.form.get('project_id')

    if request.method == 'POST' and project_id:
        # Fetch all details related to the selected project
        cursor.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
        selected_project = cursor.fetchone()

        cursor.execute("SELECT * FROM design_details WHERE project_id = %s", (project_id,))
        design = cursor.fetchone()

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

@app.route('/submit_legal_compliances', methods=['GET', 'POST'])

def submit_legal_compliances():

    if 'role' not in session or session['role'] not in ['admin', 'site_engineer']:

        return redirect(url_for('login'))



    conn = db_connection()

    cur = conn.cursor()



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



        cur.execute("SELECT id FROM legal_and_compliances WHERE project_id = %s", (project_id,))

        existing = cur.fetchone()



        if existing:

            cur.execute("SELECT * FROM legal_and_compliances WHERE project_id = %s", (project_id,))

            old = cur.fetchone()

            municipal_pdf = municipal_pdf or old[2]

            building_permit_pdf = building_permit_pdf or old[3]

            sanction_plan_pdf = sanction_plan_pdf or old[4]

            fire_noc_pdf = fire_noc_pdf or old[5]

            mngl_pdf = mngl_pdf or old[6]  # Adjust index as per your table structure



            cur.execute("""

                UPDATE legal_and_compliances

                SET municipal_approval_status=%s,

                    municipal_approval_pdf=%s,

                    building_permit_pdf=%s,

                    sanction_plan_pdf=%s,

                    fire_department_noc_pdf=%s,

                    environmental_clearance=%s,

                    mngl_pdf=%s

                WHERE project_id=%s

            """, (

                municipal_status, municipal_pdf, building_permit_pdf,

                sanction_plan_pdf, fire_noc_pdf, environmental_clearance,

                mngl_pdf, project_id

            ))

            flash('Legal compliances updated successfully.')

        else:

            cur.execute("""

                INSERT INTO legal_and_compliances (

                    project_id, municipal_approval_status, municipal_approval_pdf,

                    building_permit_pdf, sanction_plan_pdf, fire_department_noc_pdf,

                    environmental_clearance, mngl_pdf

                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)

            """, (

                project_id, municipal_status, municipal_pdf,

                building_permit_pdf, sanction_plan_pdf, fire_noc_pdf,

                environmental_clearance, mngl_pdf

            ))

            flash('Legal compliances submitted successfully.')



        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('admin_dashboard'))



    # ✅ GET method - Fetch project list

    user_id = session.get('user_id')

    role = session.get('role')



    print("✅ SESSION DEBUG --> user_id:", user_id, "| role:", role)



    if role == 'admin':

        cur.execute("SELECT id, project_name FROM projects")

    elif role == 'site_engineer':

        # ✅ Use JOIN to get projects assigned through sites table

        cur.execute("""

            SELECT p.id, p.project_name

            FROM projects p

            JOIN sites s ON p.site_id = s.site_id

            WHERE s.site_engineer_id = %s

        """, (user_id,))

    else:
        cur.close()
        conn.close()
        flash("Unauthorized access.")
        return redirect(url_for('login'))



    projects = cur.fetchall()
    print("✅ Projects fetched:", projects)

    cur.close()
    conn.close()

    return render_template('submit_legal_compliances.html', projects=projects)


# View Route (for all roles)
@app.route('/view_legal_compliances')
def view_legal_compliances():
    if 'role' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    role = session['role']
    conn = db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    if role == 'admin':
        cur.execute("""
            SELECT lc.*, p.project_name
            FROM legal_and_compliances lc
            JOIN projects p ON lc.project_id = p.id
        """)
    elif role == 'site_engineer':
        cur.execute("""
            SELECT lc.*, p.project_name
            FROM legal_and_compliances lc
            JOIN projects p ON lc.project_id = p.id
            WHERE p.site_engineer_id = %s
        """, (user_id,))
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

## Legal Compliances Dashboard#########################################
@app.route('/legal_compliances_dashboard', methods=['GET', 'POST'])
def legal_compliances_dashboard():
    print("DEBUG: session =", dict(session))
    if 'role' not in session or session['role'] not in ['admin', 'site_engineer', 'architect', 'accountant']:
        return redirect(url_for('login'))

    conn = db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    user_id = session.get('user_id')
    role = session.get('role')

    print("✅ DASHBOARD DEBUG --> user_id:", user_id, "| role:", role)

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
        cur.execute("SELECT site_id FROM sites WHERE site_engineer_id = %s", (user_id,))
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
        # ✅ Fetch architect using register_id
        cur.execute("SELECT * FROM architects WHERE register_id = %s", (user_id,))
        architect = cur.fetchone()

        if not architect:
            cur.close()
            conn.close()
            flash("Architect profile not found.")
            return redirect(url_for('login'))

        # ✅ Now match using architect's register_id since project.architect_id refers to register.id
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

        # ✅ Security: Site engineer
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

        # ✅ Security: Architect (check if project.architect_id == register_id)
        if role == 'architect':
            cur.execute("""
                SELECT COUNT(*) as count
                FROM projects
                WHERE id = %s AND architect_id = %s
            """, (selected_project_id, user_id))  # user_id is register_id
            if cur.fetchone()['count'] == 0:
                flash("Access denied to this project.")
                return redirect(url_for('legal_compliances_dashboard'))

        # ✅ Security: Accountant (assigned only)
        if role == 'accountant':
            cur.execute("""
                SELECT COUNT(*) as count
                FROM accountant_projects
                WHERE project_id = %s AND accountant_id = %s
            """, (selected_project_id, user_id))
            if cur.fetchone()['count'] == 0:
                flash("Access denied to this project.")
                return redirect(url_for('legal_compliances_dashboard'))

        # 🔍 Fetch compliance data
        cur.execute("SELECT * FROM legal_and_compliances WHERE project_id = %s", (selected_project_id,))
        compliance_data = cur.fetchone()

        if compliance_data and compliance_data['municipal_approval_status'] != 'Approved':
            not_approved = True

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

    conn = db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # Fetch projects assigned to the site engineer
    site_engineer_id = session['user_id']
    cur.execute("""
        SELECT p.id, p.project_name
        FROM projects p
        JOIN sites s ON p.site_id = s.site_id
        WHERE s.site_engineer_id = %s
    """, (site_engineer_id,))
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

            # GST calculation
            gst_percentage = 18
            apply_gst = request.form.get('apply_gst')
            gst_amount = subtotal * gst_percentage / 100 if apply_gst else 0
            grand_total = total_amount

            # Generate invoice number
            invoice_number = "INV" + datetime.now().strftime("%Y%m%d%H%M%S")
            pdf_filename = f"{invoice_number}.pdf"
            
            print(f"DEBUG: Generated invoice number: {invoice_number}")

            # Get line items
            descriptions = request.form.getlist('description[]')
            quantities = request.form.getlist('quantity[]')
            rates = request.form.getlist('rate[]')
            totals = request.form.getlist('total[]')

            # Handle image upload
            invoice_image_filename = None
            if 'invoice_image' in request.files:
                file = request.files['invoice_image']
                print(f"DEBUG: File uploaded: {file.filename}")
                
                if file and file.filename and file.filename != '':
                    # Check file extension
                    allowed_extensions = {'.png', '.jpg', '.jpeg'}
                    file_ext = os.path.splitext(file.filename)[1].lower()
                    print(f"DEBUG: File extension: {file_ext}")
                    
                    if file_ext in allowed_extensions:
                        try:
                            # Create secure filename
                            safe_name = secure_filename(file.filename)
                            unique_name = f"{invoice_number}_{safe_name}"
                            print(f"DEBUG: Unique filename: {unique_name}")
                            
                            # Ensure directory exists
                            invoice_images_dir = os.path.join(app.static_folder, 'invoice_images')
                            os.makedirs(invoice_images_dir, exist_ok=True)
                            print(f"DEBUG: Images directory: {invoice_images_dir}")
                            
                            # Full file path
                            file_path = os.path.join(invoice_images_dir, unique_name)
                            print(f"DEBUG: Full file path: {file_path}")
                            
                            # Save the file
                            file.save(file_path)
                            print(f"DEBUG: File saved")
                            
                            # Verify file was saved successfully
                            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                                invoice_image_filename = unique_name
                                print(f"DEBUG: Image saved successfully: {file_path}")
                            else:
                                print(f"DEBUG: Failed to save image: {file_path}")
                                flash("Failed to save image file", "error")
                                
                        except Exception as e:
                            print(f"DEBUG: Error saving image: {str(e)}")
                            flash(f"Error saving image: {str(e)}", "error")
                            return redirect(request.url)
                    else:
                        flash("Please upload a valid image file (PNG, JPEG, JPG)", "error")
                        return redirect(request.url)
                else:
                    print("DEBUG: No file uploaded or empty filename")
            else:
                print("DEBUG: No 'invoice_image' in request.files")

            # Database insertion
            print(f"DEBUG: Inserting to database with image filename: {invoice_image_filename}")
            cur.execute("""
                INSERT INTO invoices (
                    project_id, site_engineer_id, vendor_name, total_amount,
                    gst_amount, invoice_number, pdf_filename, generated_on,
                    bill_to_name, bill_to_address, bill_to_phone, subtotal,
                    invoice_image_filename
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                project_id, site_engineer_id, vendor_name, grand_total,
                gst_amount, invoice_number, pdf_filename, invoice_date,
                client_name, client_address, client_phone, subtotal,
                invoice_image_filename
            ))
            
            invoice_id = cur.lastrowid
            print(f"DEBUG: Invoice inserted with ID: {invoice_id}")

            # Insert invoice items
            for desc, qty, rate, line_total in zip(descriptions, quantities, rates, totals):
                if desc and qty and rate:
                    cur.execute("""
                        INSERT INTO invoice_items (invoice_id, description, quantity, rate, subtotal)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (invoice_id, desc.strip(), float(qty), float(rate), float(line_total)))

            # Commit transaction
            conn.commit()
            print("DEBUG: Transaction committed successfully")

            # ---------------- PDF Generation ---------------- #
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=25, rightMargin=25, topMargin=25, bottomMargin=25)
            styles = getSampleStyleSheet()

            # Custom Styles
            header_style = ParagraphStyle('header', parent=styles['Heading1'], fontSize=20, alignment=1, textColor=colors.HexColor('#1a365d'))
            info_style = ParagraphStyle('info', parent=styles['Normal'], fontSize=10, alignment=1, textColor=colors.HexColor('#4a5568'))
            section_title = ParagraphStyle('section_title', parent=styles['Heading3'], fontSize=13, textColor=colors.HexColor('#2b6cb0'))
            client_style = ParagraphStyle('client', parent=styles['Normal'], fontSize=11, textColor=colors.HexColor('#2d3748'))
            total_style = ParagraphStyle('total', parent=styles['Normal'], fontSize=11, textColor=colors.HexColor('#000000'))

            elements = []

            # Header
            elements.append(Paragraph("YOUR COMPANY NAME", header_style))
            elements.append(Paragraph("Your Address, City ZIP", info_style))
            elements.append(Paragraph("Phone | Email", info_style))
            elements.append(Spacer(1, 15))

            # Invoice meta
            invoice_info = [
                ['Invoice Number:', invoice_number],
                ['Invoice Date:', invoice_date],
                ['Due Date:', invoice_date]
            ]
            elements.append(Table(invoice_info, colWidths=[100, 300], hAlign='LEFT'))
            elements.append(Spacer(1, 10))

            # Bill To
            elements.append(Paragraph("Bill To", section_title))
            elements.append(Paragraph(client_name, client_style))
            elements.append(Paragraph(client_address, client_style))
            if client_phone:
                elements.append(Paragraph(f"Phone: {client_phone}", client_style))
            elements.append(Spacer(1, 10))

            # Line Items
            item_data = [['#', 'Description', 'Price', 'QTY', 'Total']]
            for i, (desc, qty, rate, total) in enumerate(zip(descriptions, quantities, rates, totals), start=1):
                item_data.append([str(i), desc, f"₹{float(rate):.2f}", qty, f"₹{float(total):.2f}"])

            item_table = Table(item_data, colWidths=[30, 260, 80, 50, 100])
            item_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2b6cb0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ]))
            elements.append(item_table)
            elements.append(Spacer(1, 10))

            # Totals
            totals_data = [
                ['Subtotal', f'₹{subtotal:.2f}'],
                ['Discount', '₹0.00'],
                [f'Tax ({gst_percentage}%)', f'₹{gst_amount:.2f}'],
                ['Total', f'₹{grand_total:.2f}']
            ]
            totals_table = Table(totals_data, colWidths=[350, 150])
            totals_table.setStyle(TableStyle([
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 3), (-1, 3), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 3), (-1, 3), 12),
                ('TEXTCOLOR', (0, 3), (-1, 3), colors.HexColor('#2d3748')),
            ]))
            elements.append(totals_table)
            elements.append(Spacer(1, 15))

            # # Show uploaded image in PDF (if exists)
            # if invoice_image_filename:
            #     img_path = os.path.join(app.static_folder, 'invoice_images', invoice_image_filename)
            #     if os.path.exists(img_path):
            #         try:
            #             elements.append(Paragraph("Uploaded Invoice Image", section_title))
            #             elements.append(RLImage(img_path, width=300, height=200))
            #             elements.append(Spacer(1, 10))
            #             print(f"DEBUG: Image added to PDF: {img_path}")
            #         except Exception as e:
            #             print(f"DEBUG: Error adding image to PDF: {str(e)}")

            # Bank Details
            elements.append(Paragraph("Bank Account Details", section_title))
            elements.append(Paragraph("Company Name", client_style))
            elements.append(Paragraph("Account Number: 1234567890", client_style))
            elements.append(Paragraph("Bank Name: XYZ Bank", client_style))
            elements.append(Paragraph("IFSC Code: XYZB0001234", client_style))
            elements.append(Paragraph("SWIFT Code: XYZSW123", client_style))
            elements.append(Spacer(1, 15))

            # Terms
            elements.append(Paragraph("Terms and Conditions", section_title))
            elements.append(Paragraph("Payment due within 14 days. Late payments are subject to a 4% monthly fee.", client_style))
            elements.append(Spacer(1, 20))

            # Footer
            elements.append(Paragraph("Thank you for choosing our services!", ParagraphStyle('footer', parent=styles['Normal'], alignment=1, fontSize=9, textColor=colors.HexColor('#718096'))))

            # Build and Save PDF
            doc.build(elements)
            buffer.seek(0)

            # Save PDF to static folder
            pdf_dir = os.path.join(app.static_folder, 'invoice_pdfs')
            if not os.path.exists(pdf_dir):
                os.makedirs(pdf_dir)
            
            pdf_path = os.path.join(pdf_dir, pdf_filename)
            with open(pdf_path, 'wb') as f:
                f.write(buffer.getvalue())
            
            print(f"DEBUG: PDF saved to: {pdf_path}")

            flash("Invoice generated successfully!", "success")
            return send_file(
                buffer,
                mimetype='application/pdf',
                as_attachment=False,
                download_name=pdf_filename
            )

        except Exception as e:
            conn.rollback()
            print(f"DEBUG: Error occurred: {str(e)}")
            flash(f"Error: {str(e)}", "danger")
            return redirect(request.url)
        finally:
            conn.close()

    # GET request - show the form
    conn.close()
    return render_template('generate_invoice.html', 
                         projects=projects, 
                         current_date=datetime.now().strftime("%Y-%m-%d"), 
                         user_role='site_engineer')
########################### Invoice Submission Route ##########################
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

@app.route('/admin/invoices', methods=['GET', 'POST'])
def admin_view_invoices():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    status_filter = request.args.get('status', 'All')
    if request.method == 'POST':
        invoice_id = request.form.get('invoice_id')
        action = request.form.get('action')
        rejection_reason = request.form.get('rejection_reason', '')
        admin_id = session.get('user_id')

        with db.cursor() as cursor:
            if action == 'approve':
                cursor.execute("""
                    UPDATE invoices 
                    SET status='Approved', approved_by=%s, approved_on=NOW(), rejection_reason=NULL 
                    WHERE id=%s
                """, (admin_id, invoice_id))
                db.commit()
                flash("Invoice approved.", "success")

            elif action == 'reject':
                cursor.execute("""
                    UPDATE invoices 
                    SET status='Rejected', rejection_reason=%s, approved_by=%s, approved_on=NOW() 
                    WHERE id=%s
                """, (rejection_reason, admin_id, invoice_id))
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
                WHERE i.status = %s 
                ORDER BY i.generated_on DESC
            """, (status_filter,))
        else:
            cursor.execute("""
                SELECT i.*, r.name as engineer_name 
                FROM invoices i 
                LEFT JOIN register r ON i.site_engineer_id = r.id 
                ORDER BY i.generated_on DESC
            """)
        invoices = cursor.fetchall()

        cursor.execute("SELECT * FROM invoice_items ORDER BY invoice_id")
        all_items = cursor.fetchall()

    items_by_invoice = {}
    for item in all_items:
        items_by_invoice.setdefault(item['invoice_id'], []).append(item)

    return render_template('invoice_detail.html', invoices=invoices, items_by_invoice=items_by_invoice, selected_status=status_filter)

#################################### Admin Invoice Detail View ######################################
@app.route('/admin/invoice/<int:invoice_id>')
def admin_invoice_detail(invoice_id):
    conn = db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM invoices WHERE id=%s", (invoice_id,))
    invoice = cursor.fetchone()
    cursor.execute("SELECT * FROM invoice_items WHERE invoice_id=%s", (invoice_id,))
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

    with db.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT id, name FROM register WHERE role = 'site_engineer'")
        engineers = cursor.fetchall()
        
        cursor.execute("SELECT id, project_name FROM projects")
        projects = cursor.fetchall()

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

            apply_gst = request.form.get('apply_gst')
            gst_percentage = 18
            gst_amount = 0

            subtotal_raw = request.form.get('subtotal', 0)
            subtotal = float(subtotal_raw) if subtotal_raw else 0.0
            if apply_gst:
                gst_amount = subtotal * gst_percentage / 100
            else:
                gst_amount = 0

            invoice_number = "INV" + datetime.now().strftime("%Y%m%d%H%M%S")
            pdf_filename = f"{invoice_number}.pdf"

            descriptions = request.form.getlist('description[]')
            quantities = request.form.getlist('quantity[]')
            rates = request.form.getlist('rate[]')
            totals = request.form.getlist('total[]')

            with db.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO invoices (
                        project_id, site_engineer_id, vendor_name, total_amount, gst_amount, invoice_number, pdf_filename,
                        generated_on, bill_to_name, bill_to_address, bill_to_phone, status, approved_by, approved_on
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Approved', %s, NOW())
                """, (
                    project_id, site_engineer_id, vendor_name, grand_total, gst_amount, invoice_number, pdf_filename,
                    invoice_date, client_name, client_address, client_phone, admin_id
                ))
                invoice_id = cursor.lastrowid

                items_inserted = 0
                for desc, qty, rate, subtotal_item in zip(descriptions, quantities, rates, totals):
                    if desc and qty and rate:
                        cursor.execute("""
                            INSERT INTO invoice_items (invoice_id, description, quantity, rate, subtotal)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (invoice_id, desc.strip(), float(qty), float(rate), float(subtotal_item)))
                        items_inserted += 1

                if items_inserted == 0:
                    raise Exception("No valid invoice items found")

                db.commit()

            # PDF Generation
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30)
            styles = getSampleStyleSheet()
            elements = []

            elements.append(Paragraph("YOUR COMPANY NAME", styles["Title"]))
            elements.append(Paragraph("Address - CITY ZIP Code", styles["Normal"]))
            elements.append(Paragraph("Phone - Email-address", styles["Normal"]))
            elements.append(Spacer(1, 12))

            elements.append(Paragraph(f"<b>INVOICE NUMBER:</b> {invoice_number}", styles["Normal"]))
            elements.append(Paragraph(f"<b>INVOICE DATE:</b> {invoice_date}", styles["Normal"]))
            elements.append(Paragraph(f"<b>DUE DATE:</b> {invoice_date}", styles["Normal"]))
            elements.append(Spacer(1, 12))

            elements.append(Paragraph("<b>BILLED TO</b>", styles["Heading4"]))
            elements.append(Paragraph(client_name, styles["Normal"]))
            elements.append(Paragraph(client_address, styles["Normal"]))
            if client_phone:
                elements.append(Paragraph(f"Phone: {client_phone}", styles["Normal"]))
            elements.append(Spacer(1, 12))

            # Line items table
            table_data = [['ID', 'Description', 'Price', 'QTY', 'Total']]
            for i, (desc, qty, rate, total) in enumerate(zip(descriptions, quantities, rates, totals), start=1):
                table_data.append([
                    str(i),
                    desc,
                    f"₹{float(rate):.2f}",
                    str(qty),
                    f"₹{float(total):.2f}"
                ])

            invoice_table = Table(table_data, colWidths=[30, 200, 60, 40, 60])
            invoice_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#3498db")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
            ]))
            elements.append(invoice_table)
            elements.append(Spacer(1, 16))

            # Totals section
            totals_table = Table([
                ["Subtotal", f"₹{subtotal:.2f}"],
                ["Discount", "₹0.00"],
                [f"Tax ({gst_percentage}%)", f"₹{gst_amount:.2f}"],
                ["INVOICE TOTAL", f"₹{grand_total:.2f}"]
            ], colWidths=[380, 100])
            totals_table.setStyle(TableStyle([
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#e8f4ff")),
            ]))
            elements.append(totals_table)
            elements.append(Spacer(1, 20))

            # Bank Info
            elements.append(Paragraph("<b>BANK ACCOUNT</b>", styles["Heading4"]))
            elements.append(Paragraph("Company name", styles["Normal"]))
            elements.append(Paragraph("Account number: 1234567890", styles["Normal"]))
            elements.append(Paragraph("Bank name and address", styles["Normal"]))
            elements.append(Paragraph("SWIFT Code: ABCD1234", styles["Normal"]))
            elements.append(Paragraph("IBAN Number: IN00BANK000123456", styles["Normal"]))
            elements.append(Spacer(1, 20))

            # Terms
            elements.append(Paragraph("<b>TERMS AND CONDITIONS</b>", styles["Heading4"]))
            elements.append(Paragraph(
                "Thank you for your business! Please make the payment within 14 days. "
                "There will be a 4% interest charge per month on late invoices.",
                styles["Normal"]
            ))

            doc.build(elements)
            buffer.seek(0)

            pdf_path = os.path.join(UPLOAD_FOLDER_INVOICES, pdf_filename)
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
    with db.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("""
            SELECT 
                id, invoice_number, generated_on, total_amount, status, rejection_reason, pdf_filename
            FROM invoices
            WHERE site_engineer_id = %s
            ORDER BY generated_on DESC
        """, (site_engineer_id,))
        invoices = cursor.fetchall()

        for invoice in invoices:
            cursor.execute("""
                SELECT description, quantity, rate 
                FROM invoice_items 
                WHERE invoice_id = %s
            """, (invoice['id'],))
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
    
    with db.cursor(pymysql.cursors.DictCursor) as cursor:
        # Verify the invoice belongs to this engineer
        cursor.execute("""
            SELECT * FROM invoices 
            WHERE id = %s AND  site_engineer_id= %s AND status = 'Rejected'
        """, (invoice_id, engineer_id))
        invoice = cursor.fetchone()
        
        if not invoice:
            flash("Invoice not found or not eligible for update.", "danger")
            return redirect(url_for('site_engineer_invoices'))
        
        # Get invoice items
        cursor.execute("SELECT * FROM invoice_items WHERE invoice_id = %s", (invoice_id,))
        items = cursor.fetchall()
        
        if request.method == 'POST':
            vendor_name = request.form.get('vendor_name')
            total_amount = float(request.form.get('total_amount'))
            gst_amount = float(request.form.get('gst_amount'))
            
            # Generate new PDF
            new_pdf_filename = f"invoice_{uuid.uuid4().hex}.pdf"
            pdf_path = os.path.join("static", "invoices", new_pdf_filename)
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

    conn = db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    if request.method == 'POST':
        accountant_id = request.form['accountant_id']
        project_ids = request.form.getlist('project_ids')

        # Clear existing assignments for this accountant
        cur.execute("DELETE FROM accountant_projects WHERE accountant_id = %s", (accountant_id,))

        # Insert new assignments
        for project_id in project_ids:
            cur.execute("INSERT INTO accountant_projects (accountant_id, project_id) VALUES (%s, %s)",
                        (accountant_id, project_id))
        conn.commit()
        flash('Projects assigned successfully.')

    # Fetch all accountants and projects for the form
    cur.execute("SELECT id, name FROM register WHERE role = 'accountant'")
    accountants = cur.fetchall()

    cur.execute("SELECT id, project_name FROM projects")
    projects = cur.fetchall()

    # Get current assignments to check the boxes in the template
    assignments = {}
    if accountants:
        cur.execute("SELECT accountant_id, project_id FROM accountant_projects")
        all_assignments = cur.fetchall()
        for a in all_assignments:
            if a['accountant_id'] not in assignments:
                assignments[a['accountant_id']] = []
            assignments[a['accountant_id']].append(a['project_id'])

    conn.close()

    return render_template('assign_accountant.html', accountants=accountants, projects=projects, assignments=assignments)
@app.route('/')
def landing(): 
  return render_template('landing_page.html')

@app.route('/communication')

def communication():

    if 'user_id' not in session:

        return redirect(url_for('login'))

    return render_template('communication.html')



@app.route('/get_current_user_role')

def get_current_user_role():

    if 'user_id' not in session:

        return jsonify({'error': 'Not logged in'})

    

    conn = db_connection()

    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute("SELECT role FROM register WHERE id = %s", (session['user_id'],))

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

    

    conn = db_connection()

    cursor = conn.cursor(pymysql.cursors.DictCursor)

    

    # Get current user's role

    cursor.execute("SELECT role FROM register WHERE id = %s", (current_user_id,))

    current_user_role = cursor.fetchone()['role']

    

    # Get all users with unread counts - exclude super_admin

    if current_user_role == 'admin':

        cursor.execute("""

            SELECT r.id, r.name, r.role, 

                   (SELECT COUNT(*) FROM messages 

                    WHERE receiver_id = %s AND sender_id = r.id AND is_read = FALSE) as unread_count

            FROM register r

            WHERE r.id != %s AND r.role != 'super_admin'

            ORDER BY r.name

        """, (current_user_id, current_user_id))

    else:

        if current_user_role == 'accountant':

            cursor.execute("""

                SELECT r.id, r.name, r.role, 

                       (SELECT COUNT(*) FROM messages 

                        WHERE receiver_id = %s AND sender_id = r.id AND is_read = FALSE) as unread_count

                FROM register r

                WHERE r.role = 'admin' AND r.id != %s

                ORDER BY r.name

            """, (current_user_id, current_user_id))

        else:

            cursor.execute("""

                SELECT r.id, r.name, r.role, 

                       (SELECT COUNT(*) FROM messages 

                        WHERE receiver_id = %s AND sender_id = r.id AND is_read = FALSE) as unread_count

                FROM register r

                WHERE (r.role = %s OR r.role = 'admin' OR 

                      (r.role = 'site_engineer' AND %s = 'architect') OR

                      (r.role = 'architect' AND %s = 'site_engineer')) 

                AND r.id != %s AND r.role != 'super_admin'

                ORDER BY r.name

            """, (current_user_id, current_user_role, current_user_role, current_user_role, current_user_id))

    

    users = cursor.fetchall()

    

    # Convert site_engineer role to project_manager for display

    for user in users:

        if user['role'] == 'site_engineer':

            user['role'] = 'project_manager'

    

    conn.close()

    return jsonify(users)



@app.route('/get_messages/<int:receiver_id>')

def get_messages(receiver_id):

    if 'user_id' not in session:

        return jsonify([])

    

    sender_id = session['user_id']

    

    conn = db_connection()

    cursor = conn.cursor(pymysql.cursors.DictCursor)

    

    # Get all messages between the two users

    cursor.execute("""

        SELECT * FROM messages

        WHERE (sender_id = %s AND receiver_id = %s) OR (sender_id = %s AND receiver_id = %s)

        ORDER BY timestamp ASC

    """, (sender_id, receiver_id, receiver_id, sender_id))

    messages = cursor.fetchall()

    

    # Mark messages as read where current user is the receiver

    cursor.execute("""

        UPDATE messages 

        SET is_read = TRUE 

        WHERE sender_id = %s AND receiver_id = %s AND is_read = FALSE

    """, (receiver_id, sender_id))

    

    conn.commit()

    conn.close()

    

    import json

    from datetime import datetime, date

    return jsonify(messages)
from flask import Flask, render_template, request, session, redirect, url_for, jsonify



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



    if not receiver_id or not message:

        return jsonify({'success': False, 'error': 'Missing data'})



    try:

        conn = db_connection()

        cursor = conn.cursor()

        cursor.execute("""

            INSERT INTO messages (sender_id, receiver_id, message)

            VALUES (%s, %s, %s)

        """, (sender_id, receiver_id, message))

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

        conn = db_connection()

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
    


@app.route('/add_salary', methods=['GET', 'POST'])
def add_salary():
    if 'role' not in session or session['role'] != 'accountant':
        return redirect(url_for('login'))

    accountant_id = session['user_id']
    conn = db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # Fetch assigned projects
    cur.execute("""
        SELECT p.id, p.project_name
        FROM accountant_projects ap
        JOIN projects p ON ap.project_id = p.id
        WHERE ap.accountant_id = %s
    """, (accountant_id,))
    projects = cur.fetchall()

    # Fetch users for assigned projects (site engineer via sites, architect, accountant self)
    cur.execute("""
        SELECT DISTINCT r.id, r.name, r.role
        FROM accountant_projects ap
        JOIN projects p ON ap.project_id = p.id
        JOIN sites s ON p.site_id = s.site_id
        JOIN register r ON r.id = s.site_engineer_id
        WHERE ap.accountant_id = %s

        UNION

        SELECT DISTINCT r.id, r.name, r.role
        FROM accountant_projects ap
        JOIN projects p ON ap.project_id = p.id
        JOIN register r ON r.id = p.architect_id
        WHERE ap.accountant_id = %s

        UNION

        SELECT DISTINCT r.id, r.name, r.role
        FROM register r
        WHERE r.id = %s AND r.role = 'accountant'
    """, (accountant_id, accountant_id, accountant_id))
    users = cur.fetchall()

    if request.method == 'POST':
        project_id = request.form['project_id']
        user_id = request.form['user_id']
        role = request.form['role']
        month_year = request.form['month_year']
        base_salary = request.form['base_salary']
        allowance = request.form.get('allowance', 0) or 0
        pf = request.form.get('pf', 0) or 0
        description = request.form.get('description', '')
        payment_mode = request.form['payment_mode']
        cheque_number = request.form.get('cheque_number', '') if payment_mode == 'cheque' else None

        # Insert with payment mode and cheque number
        cur.execute("""
            INSERT INTO salaries (project_id, user_id, role, month_year, base_salary, allowance, pf, description, payment_mode, cheque_number, created_by, created_on)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (project_id, user_id, role, month_year, base_salary, allowance, pf, description, payment_mode, cheque_number, accountant_id))
        conn.commit()
        flash('Salary entry added successfully.')
        conn.close()
        return redirect(url_for('add_salary'))

    conn.close()
    return render_template('add_salary.html', projects=projects, users=users)


# Accountant: View Own Entered Salaries
@app.route('/view_salaries')
def view_salaries():
    if 'role' not in session or session['role'] != 'accountant':
        return redirect(url_for('login'))
    
    accountant_id = session['user_id']
    conn = db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    # Include payment mode and cheque number in the query
    cur.execute("""
        SELECT s.*, p.project_name, r.name AS user_name, cr.name AS created_by_name
        FROM salaries s
        JOIN projects p ON s.project_id = p.id
        JOIN register r ON s.user_id = r.id
        JOIN register cr ON s.created_by = cr.id
        WHERE s.created_by = %s
        ORDER BY s.month_year DESC, p.project_name
    """, (accountant_id,))
    salaries = cur.fetchall()
    conn.close()
    return render_template('view_salaries.html', salaries=salaries)


# Admin: View All Salaries
@app.route('/admin/view_salaries')
def admin_view_salaries():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    conn = db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    # Include payment mode and cheque number in the query
    cur.execute("""
        SELECT s.*, p.project_name, r.name AS user_name, cr.name AS created_by_name
        FROM salaries s
        JOIN projects p ON s.project_id = p.id
        JOIN register r ON s.user_id = r.id
        JOIN register cr ON s.created_by = cr.id
        ORDER BY s.month_year DESC, p.project_name
    """)
    salaries = cur.fetchall()
    conn.close()
    return render_template('admin_view_salaries.html', salaries=salaries)



if __name__ == "__main__":
    app.run(debug=True)