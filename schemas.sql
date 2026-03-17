--1 ############################## register table ##############################

CREATE TABLE IF NOT EXISTS register (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('super_admin', 'admin', 'project_manager', 'architect', 'accountant', 'site_engineer') NOT NULL,
    contact_no VARCHAR(20),
    org_id INT NOT NULL,
    status ENUM('active', 'disabled') DEFAULT 'active'
);

--2############################################## architects table ##########################################

CREATE TABLE IF NOT EXISTS architects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    license_number VARCHAR(50),
    contact_no VARCHAR(15),
    email VARCHAR(100),
    project_name VARCHAR(255),
    site_engineer_id INT,
    register_id INT,
    org_id INT NOT NULL,
    FOREIGN KEY (register_id) REFERENCES register(id) ON DELETE SET NULL
);

-- 3######################################## architect_projects table ##########################################

CREATE TABLE IF NOT EXISTS  architect_projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    architect_id INT,
    project_name VARCHAR(255),
    building_usage VARCHAR(100),
    num_floors INT,
    area_sqft FLOAT,
    plot_area FLOAT,
    fsi VARCHAR(50),
    architect_name VARCHAR(100),
    org_id INT NOT NULL,
    FOREIGN KEY (architect_id) REFERENCES architects(id) ON DELETE SET NULL
);

--4 ########################## projects table ###################################

CREATE TABLE IF NOT EXISTS   projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_name VARCHAR(255) NOT NULL,
    architect_id INT,
    site_engineer_id INT,
    site_id INT,
    org_id INT NOT NULL
);


-- 5############################## daily_worker_report table ######################################

CREATE TABLE  IF NOT EXISTS daily_worker_report (
    id INT AUTO_INCREMENT PRIMARY KEY,
    site_engineer_id INT NOT NULL,
    project_id INT NOT NULL,
    worker_count INT NOT NULL,
    report_date DATE NOT NULL,
    org_id INT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);


-- 6#################################### design_details table ####################################

CREATE TABLE  IF NOT EXISTS design_details (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT,
    architect_id INT,
    building_usage VARCHAR(100),
    num_floors INT,
    area_sqft FLOAT,
    plot_area FLOAT,
    fsi VARCHAR(50),
    org_id INT NOT NULL
);


-- 7############################################### drawing_documents table ###################################

CREATE TABLE IF NOT EXISTS drawing_documents (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    architect_id INT,
    layout_type ENUM(
        'Architectural Layout',
        'Elevation Drawing',
        'Section/Structural',
        'Electrical',
        'Plumbing/Sanitation'
    ) NOT NULL,
    document_title VARCHAR(255) NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    uploaded_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    uploaded_by INT,
    org_id INT NOT NULL
);




-- 8################################## enquiries table ########################################

CREATE TABLE IF NOT EXISTS enquiries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    site_engineer_id INT,
    name VARCHAR(100) NOT NULL,
    address TEXT NOT NULL,
    contact_no VARCHAR(15) NOT NULL,
    requirement TEXT NOT NULL,
    enquiry_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    org_id INT NOT NULL
);

-- 9########################################### inventory table #############################################
CREATE TABLE  IF NOT EXISTS inventory (
    material_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    material_description VARCHAR(255) NOT NULL,
    quantity INT NOT NULL,
    date DATE NOT NULL,
    org_id INT NOT NULL,
    status ENUM('available', 'low', 'out_of_stock', 'ordered') NOT NULL,
    site_engineer_id INT NOT NULL,
);



-- 10############################# invoice_items table ##################################

CREATE TABLE IF NOT EXISTS invoice_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_id INT NOT NULL,
    description VARCHAR(255) NOT NULL,
    quantity INT NOT NULL,
    rate DECIMAL(10,2) NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL,
    org_id INT NOT NULL,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
);


-- 11###################################### invoices table ###########################

CREATE TABLE IF NOT EXISTS invoices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    site_engineer_id INT NOT NULL,
    vendor_name VARCHAR(255),
    total_amount DECIMAL(10,2) NOT NULL,
    generated_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    pdf_filename VARCHAR(255),
    gst_amount DECIMAL(10,2) DEFAULT 0.00,
    invoice_number VARCHAR(50),
    bill_to_name VARCHAR(255),
    bill_to_address TEXT,
    bill_to_phone VARCHAR(20),
    subtotal DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'Pending',
    rejection_reason TEXT,
    approved_by INT,
    approved_on DATETIME,
    project_id INT,
    invoice_image_filename VARCHAR(255),
    org_id INT NOT NULL,
    FOREIGN KEY (approved_by) REFERENCES register(id) ON DELETE SET NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
);

-- 12############################### legal_and_compliances table #########################################

CREATE TABLE IF NOT EXISTS legal_and_compliances (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    municipal_approval_status ENUM('Approved', 'Not Approved') NOT NULL,
    municipal_approval_pdf VARCHAR(255),
    building_permit_pdf VARCHAR(255),
    sanction_plan_pdf VARCHAR(255),
    fire_department_noc_pdf VARCHAR(255),
    environmental_clearance TEXT,
    uploaded_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    mngl_pdf VARCHAR(255),
    org_id INT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);


-- 13############################ material_specifications table ######################################### 

CREATE TABLE  IF NOT EXISTS material_specifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT,
    architect_id INT,
    primary_material VARCHAR(100),
    wall_material VARCHAR(100),
    roofing_material VARCHAR(100),
    flooring_material VARCHAR(100),
    fire_safety_materials TEXT,
    org_id INT NOT NULL
);

-- 14################################ progress_reports table ############################

CREATE TABLE IF NOT EXISTS progress_reports (
    report_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    site_id INT NOT NULL,
    progress_percent INT NOT NULL,
    image_path VARCHAR(255) DEFAULT NULL,
    pdf_path VARCHAR(255) DEFAULT NULL,
    report_date DATE NOT NULL,
    remark VARCHAR(255) DEFAULT NULL,
    org_id INT NOT NULL,
    INDEX (site_id),
    INDEX (org_id)
);

-- 15########################################## messages table ##########################################
CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sender_id INT NOT NULL,
    receiver_id INT NOT NULL,
    message TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_read TINYINT(1) DEFAULT 0,
    org_id INT NOT NULL,
    FOREIGN KEY (sender_id) REFERENCES register(id) ON DELETE CASCADE,
    FOREIGN KEY (receiver_id) REFERENCES register(id) ON DELETE CASCADE
);

-- 16############### salaries table ##############################

CREATE TABLE IF NOT EXISTS salaries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT,
    user_id INT,
    role VARCHAR(50),
    month_year VARCHAR(7),  -- Format: YYYY-MM
    base_salary DECIMAL(10,2),
    allowance DECIMAL(10,2),
    pf DECIMAL(10,2),
    advance DECIMAL(10,2) DEFAULT 0.00,
    other_deductions DECIMAL(10,2) DEFAULT 0.00,
    net_salary DECIMAL(10,2) DEFAULT 0.00,
    description VARCHAR(255),
    created_by INT,
    created_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    payment_mode ENUM('cash', 'cheque') NOT NULL DEFAULT 'cash',
    cheque_number VARCHAR(50),
    org_id INT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES register(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES register(id) ON DELETE SET NULL
);


-- 17#################################### site_conditions table #######################################

CREATE TABLE IF NOT EXISTS site_conditions (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL UNIQUE,
    architect_id INT,
    soil_report_path VARCHAR(255),
    water_table_level VARCHAR(100),
    topo_counter_map_path VARCHAR(255),
    uploaded_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    org_id INT NOT NULL
);

-- 18######################################## sites table ###############################################

CREATE TABLE IF NOT EXISTS sites (
    site_id INT AUTO_INCREMENT PRIMARY KEY,
    site_name VARCHAR(100) NOT NULL,
    location VARCHAR(255) NOT NULL,
    site_engineer_id INT NOT NULL,
    architect_id INT,
    org_id INT NOT NULL,
    FOREIGN KEY (architect_id) REFERENCES architects(id) ON DELETE SET NULL
);



-- 19#############################structural_details table###############################################

CREATE TABLE IF NOT EXISTS structural_details (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT,
    architect_id INT,
    foundation_type VARCHAR(100),
    framing_system VARCHAR(100),
    slab_type VARCHAR(100),
    beam_details TEXT,
    load_calculation TEXT,
    org_id INT NOT NULL
);



-- 20#######################utilities_services table#############################################

CREATE TABLE IF NOT EXISTS utilities_services (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL UNIQUE,
    architect_id INT,
    water_supply_source VARCHAR(255),
    drainage_system_type VARCHAR(255),
    power_supply_source VARCHAR(255),
    uploaded_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    org_id INT NOT NULL
);




-- 21####################vendor_inventory table##################################

CREATE TABLE IF NOT EXISTS vendor_inventory (
    id INT AUTO_INCREMENT PRIMARY KEY,
    material_description VARCHAR(255) NOT NULL,
    quantity INT NOT NULL,
    date DATE NOT NULL,
    status ENUM('available', 'low', 'out_of_stock', 'ordered') NOT NULL,
    vendor_name VARCHAR(100) NOT NULL,
    vendor_quotation_pdf VARCHAR(255),
    admin_remark VARCHAR(255),
    site_engineer_id INT NULL,
    admin_approval ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    vendor_type ENUM('electrical', 'plumber', 'carpenter', 'painter', 'other') NOT NULL DEFAULT 'other',
    org_id INT NOT NULL

);


-- 22##################################### accountant_projects table ######################################

CREATE TABLE IF NOT EXISTS accountant_projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    accountant_id INT NOT NULL,
    project_id INT NOT NULL,
    org_id INT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);



-- 23############ cost_estimation table #######################################################

CREATE TABLE IF NOT EXISTS cost_estimation (
    id INT AUTO_INCREMENT PRIMARY KEY,
    architectural_design_cost FLOAT,
    structural_design_cost FLOAT,
    estimation_summary TEXT,
    boq_reference TEXT,
    cost_per_sqft FLOAT,
    report_pdf_path VARCHAR(255),
    uploaded_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    project_id INT,
    architect_id INT,
    generated_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    org_id INT NOT NULL
);

-- 24################################### ORGANIZATION TABLE ##########################################
CREATE TABLE IF NOT EXISTS organization_master (
    org_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    admin_id INT DEFAULT NULL,
    role ENUM('super_admin', 'admin', 'project_manager', 'architect', 'accountant', 'site_engineer') NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    company_address VARCHAR(255) NOT NULL,
    company_phone VARCHAR(20) NOT NULL,
    company_email VARCHAR(100) NOT NULL,
    bank_name VARCHAR(100),
    bank_account VARCHAR(50),
    ifsc_code VARCHAR(20),
    gst_number VARCHAR(20),
    terms_conditions VARCHAR(200)
);
-- 25######################################## daily_expenses table ##########################################
CREATE TABLE IF NOT EXISTS daily_expenses (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    site_engineer_id INT,
    org_id INT,
    project_id INT,
    date DATE,
    description TEXT,
    amount DECIMAL(10,2),
    status ENUM('Pending', 'Approved', 'Rejected') DEFAULT 'Pending',
    admin_comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);



   --- 26####################### base salary #############

   CREATE TABLE IF NOT EXISTS base_salaries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    salary DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    created_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INT NOT NULL,
    updated_on DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    updated_by INT DEFAULT NULL,
    org_id INT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES register(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES register(id),
    FOREIGN KEY (updated_by) REFERENCES register(id),
    UNIQUE KEY unique_user_org (user_id, org_id),
    INDEX idx_org_id (org_id),
    INDEX idx_user_id (user_id)
) ;



-- 27####################### advance table ##############################

CREATE TABLE IF NOT EXISTS advances (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    user_id             INT NOT NULL,
    advance_amount      DECIMAL(10,2) NOT NULL,    -- ✅ Total advance given
    remaining_amount    DECIMAL(10,2) NOT NULL,    -- ✅ What's left to deduct
    created_by          INT NOT NULL,
    created_on          DATETIME,
    org_id              INT NOT NULL
);

-- 28############################### notifications table ##########################################
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    org_id INT NOT NULL,
    notification_type VARCHAR(50) NOT NULL,  -- 'project_assigned', 'invoice_generated', etc.
    reference_id INT,  -- ID of the related record (project_id, invoice_id, etc.)
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES register(id),
    INDEX idx_user_unread (user_id, is_read),
    INDEX idx_org (org_id)
);



-- 29############################# bills_and_payments table ##########################################

CREATE TABLE IF NOT EXISTS bills_and_payments (
    id INT AUTO_INCREMENT PRIMARY KEY,

    bill_no VARCHAR(100) NOT NULL,
    bill_date DATE NOT NULL,

    bill_type ENUM('Advance Bill','Running Account Bill','Final Bill') NOT NULL,

    bill_file_path VARCHAR(500) NULL,
    bill_file_type ENUM('pdf','image') NULL,

    advance_amount DECIMAL(15,2) DEFAULT 0.00,
    running_account_amount DECIMAL(15,2) DEFAULT 0.00,
    final_amount DECIMAL(15,2) DEFAULT 0.00,

    work_name VARCHAR(255) NOT NULL,
    work_order_number VARCHAR(100) NOT NULL,
    work_order_date DATE NOT NULL,

    tender_name VARCHAR(255) NULL,
    tender_number VARCHAR(100) NULL,

    gross_amount DECIMAL(15,2) NOT NULL,
    gst_percentage DECIMAL(5,2) NOT NULL,
    gst_amount DECIMAL(15,2) NOT NULL,

    security_deposit DECIMAL(15,2) DEFAULT 0.00,
    labour_charges DECIMAL(15,2) NOT NULL,

    net_amount DECIMAL(15,2) NOT NULL,

    payment_status ENUM('Paid','Unpaid') DEFAULT 'Unpaid',

    created_by INT NOT NULL,
    created_by_role ENUM('admin','accountant') NOT NULL,

    org_id INT NOT NULL,
    project_id INT NULL,
    accountant_id INT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_bill_type (bill_type),
    INDEX idx_payment_status (payment_status),
    INDEX idx_created_by (created_by),
    INDEX idx_org_id (org_id),
    INDEX idx_project_id (project_id),
    INDEX idx_accountant_id (accountant_id)
);

