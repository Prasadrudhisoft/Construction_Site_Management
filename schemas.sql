
-- ########################################architect_projects table ##########################################

CREATE TABLE architect_projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    architect_id INT,
    project_name VARCHAR(255),
    building_usage VARCHAR(100),
    num_floors INT,
    area_sqft FLOAT,
    plot_area FLOAT,
    fsi VARCHAR(50),
    architect_name VARCHAR(100),
    FOREIGN KEY (architect_id) REFERENCES architects(id) ON DELETE SET NULL
);

);

--############################################## architects table ##########################################

CREATE TABLE architects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    license_number VARCHAR(50),
    contact_no VARCHAR(15),
    email VARCHAR(100),
    project_name VARCHAR(255),
    site_engineer_id INT,
    register_id INT,
    FOREIGN KEY (register_id) REFERENCES register(id) ON DELETE SET NULL
);


--################################ attendance table #######################################

CREATE TABLE attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    worker_name VARCHAR(100) NOT NULL,
    date DATE NOT NULL,
    status ENUM('present', 'absent', 'halfday') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ############################## daily_worker_report table ######################################

CREATE TABLE daily_worker_report (
    id INT AUTO_INCREMENT PRIMARY KEY,
    site_engineer_id INT NOT NULL,
    project_id INT NOT NULL,
    worker_count INT NOT NULL,
    report_date DATE NOT NULL,
    FOREIGN KEY (site_engineer_id) REFERENCES site_engineers(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);


--#################################### design_details table ####################################

CREATE TABLE design_details (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT,
    architect_id INT,
    building_usage VARCHAR(100),
    num_floors INT,
    area_sqft FLOAT,
    plot_area FLOAT,
    fsi VARCHAR(50),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (architect_id) REFERENCES architects(id) ON DELETE SET NULL
);

--############################################### drawing_documents table ###################################

CREATE TABLE drawing_documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    architect_id INT,
    layout_type ENUM('Architectural Layout', 'Elevation Drawing', 'Section/Structural', 'Electrical', 'Plumbing/Sanitation') NOT NULL,
    document_title VARCHAR(255) NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    uploaded_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (architect_id) REFERENCES architects(id) ON DELETE SET NULL
);


-- ################################## enquiries table ########################################

CREATE TABLE enquiries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    site_engineer_id INT,
    name VARCHAR(100) NOT NULL,
    address TEXT NOT NULL,
    contact_no VARCHAR(15) NOT NULL,
    requirement TEXT NOT NULL,
    enquiry_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (site_engineer_id) REFERENCES site_engineers(id) ON DELETE SET NULL
);

--########################################### inventory table #############################################

CCREATE TABLE inventory (
    material_id INT AUTO_INCREMENT PRIMARY KEY,
    material_description VARCHAR(255) NOT NULL,
    quantity INT NOT NULL,
    date DATE NOT NULL,
    status ENUM('available', 'low', 'out_of_stock', 'ordered') NOT NULL
);

-- ############################# invoice_items table ##################################

CREATE TABLE invoice_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_id INT NOT NULL,
    description VARCHAR(255) NOT NULL,
    quantity INT NOT NULL,
    rate DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
);

-- i###################################### invoices table ###########################

CREATE TABLE invoices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    site_engineer_id INT NOT NULL,
    vendor_name VARCHAR(255),
    total_amount DECIMAL(10, 2) NOT NULL,
    generated_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    pdf_filename VARCHAR(255),
    gst_amount DECIMAL(10, 2) DEFAULT 0.00,
    invoice_number VARCHAR(50),
    bill_to_name VARCHAR(255),
    bill_to_address TEXT,
    bill_to_phone VARCHAR(20),
    subtotal DECIMAL(10, 2),
    status VARCHAR(20) DEFAULT 'Pending',
    rejection_reason TEXT,
    approved_by INT,
    approved_on DATETIME,
    project_id INT,
    FOREIGN KEY (site_engineer_id) REFERENCES register(id) ON DELETE CASCADE,
    FOREIGN KEY (approved_by) REFERENCES register(id) ON DELETE SET NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
);

-- ###############################legal_and_compliances table#########################################

CREATE TABLE legal_and_compliances (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    municipal_approval_status ENUM('Approved', 'Not Approved') NOT NULL,
    municipal_approval_pdf VARCHAR(255),
    building_permit_pdf VARCHAR(255),
    sanction_plan_pdf VARCHAR(255),
    fire_department_noc_pdf VARCHAR(255),
    environmental_clearance TEXT,
    uploaded_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- ############################material_specifications table######################################### 

CREATE TABLE material_specifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT UNIQUE,
    architect_id INT,
    primary_material VARCHAR(100),
    wall_material VARCHAR(100),
    roofing_material VARCHAR(100),
    flooring_material VARCHAR(100),
    fire_safety_materials TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (architect_id) REFERENCES register(id)
);
--################################progress_reports table############################

CREATE TABLE progress_reports (
    report_id INT AUTO_INCREMENT PRIMARY KEY,
    site_id INT NOT NULL,
    progress_percent INT NOT NULL,
    image_path VARCHAR(255),
    pdf_path VARCHAR(255),
    report_date DATE NOT NULL,
    remark VARCHAR(255),
    FOREIGN KEY (site_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- ##########################projects table###################################

CREATE TABLE projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_name VARCHAR(255) NOT NULL,
    architect_id INT,
    site_engineer_id INT,
    FOREIGN KEY (architect_id) REFERENCES register(id),
    FOREIGN KEY (site_engineer_id) REFERENCES register(id)
);

-- ##############################register table##############################

CREATE TABLE register (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('super_admin', 'admin', 'project_manager', 'architect', 'accountant', 'site_engineer') NOT NULL,
    contact_no VARCHAR(20),
    status ENUM('active', 'disabled') DEFAULT 'active'
);



-- ####################################site_conditions table#######################################

CREATE TABLE site_conditions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    architect_id INT,
    soil_report_path VARCHAR(255),
    water_table_level VARCHAR(100),
    topo_counter_map_path VARCHAR(255),
    uploaded_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (architect_id) REFERENCES architects(id) ON DELETE SET NULL
);

-- ########################################sites table ###############################################

CREATE TABLE sites (
    site_id INT AUTO_INCREMENT PRIMARY KEY,
    site_name VARCHAR(100) NOT NULL,
    location VARCHAR(255) NOT NULL,
    site_engineer_id INT NOT NULL,
    architect_id INT,
    FOREIGN KEY (site_engineer_id) REFERENCES site_engineers(id) ON DELETE CASCADE,
    FOREIGN KEY (architect_id) REFERENCES architects(id) ON DELETE SET NULL
);


-- #############################structural_details table###############################################

CREATE TABLE structural_details (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT,
    architect_id INT,
    foundation_type VARCHAR(100),
    framing_system VARCHAR(100),
    slab_type VARCHAR(100),
    beam_details TEXT,
    load_calculation TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (architect_id) REFERENCES architects(id) ON DELETE SET NULL
);


-- #######################utilities_services table#############################################

CREATE TABLE utilities_services (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    architect_id INT,
    water_supply_source VARCHAR(255),
    drainage_system_type VARCHAR(255),
    power_supply_source VARCHAR(255),
    uploaded_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (architect_id) REFERENCES architects(id) ON DELETE SET NULL
);



-- ####################vendor_inventory table##################################

CREATE TABLE vendor_inventory (
    id INT AUTO_INCREMENT PRIMARY KEY,
    material_description VARCHAR(255) NOT NULL,
    quantity INT NOT NULL,
    date DATE NOT NULL,
    status ENUM('available', 'low', 'out_of_stock', 'ordered') NOT NULL,
    vendor_name VARCHAR(100) NOT NULL,
    vendor_quotation_pdf VARCHAR(255),
    admin_remark VARCHAR(255),
    admin_approval ENUM('pending', 'approved', 'rejected') DEFAULT 'pending'
);












-- ##################################### accountant_projects table ######################################

CREATE TABLE accountant_projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    accountant_id INT NOT NULL,
    project_id INT NOT NULL,
    FOREIGN KEY (accountant_id) REFERENCES register(id),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

ALTER TABLE invoices
ADD COLUMN project_id INT,
ADD FOREIGN KEY (project_id) REFERENCES projects(id);

-----------############cost_estimation table#########################

CCREATE TABLE cost_estimation (
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
    FOREIGN KEY (architect_id) REFERENCES architects(id) ON DELETE SET NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
