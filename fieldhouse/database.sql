-- =========================================================
-- Fieldhouse — Equipment Operations
-- MySQL Database Schema
-- =========================================================

DROP DATABASE IF EXISTS fieldhouse;
CREATE DATABASE fieldhouse CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE fieldhouse;

-- =========================================================
-- TABLE: users  (Admin / Staff accounts)
-- =========================================================
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(120) NOT NULL,
    role ENUM('Admin', 'Staff') NOT NULL DEFAULT 'Staff',
    is_active TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE INDEX idx_users_active ON users(is_active);

-- =========================================================
-- TABLE: categories
-- =========================================================
CREATE TABLE categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- =========================================================
-- TABLE: equipment
-- =========================================================
CREATE TABLE equipment (
    equipment_id INT AUTO_INCREMENT PRIMARY KEY,
    equipment_name VARCHAR(150) NOT NULL,
    category_id INT NOT NULL,
    brand VARCHAR(100),
    model VARCHAR(100),
    description TEXT,
    total_quantity INT NOT NULL DEFAULT 0,
    available_quantity INT NOT NULL DEFAULT 0,
    purchase_date DATE,
    purchase_price DECIMAL(10,2) DEFAULT 0.00,
    condition_status ENUM('New','Good','Fair','Damaged','Under Maintenance') NOT NULL DEFAULT 'New',
    location VARCHAR(150),
    status ENUM('Available','Partially Available','Issued','Maintenance','Lost') NOT NULL DEFAULT 'Available',
    supplier VARCHAR(150),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_equipment_category FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE RESTRICT,
    CONSTRAINT chk_available_qty CHECK (available_quantity >= 0 AND available_quantity <= total_quantity),
    CONSTRAINT chk_total_qty CHECK (total_quantity >= 0),
    CONSTRAINT chk_purchase_price CHECK (purchase_price >= 0)
) ENGINE=InnoDB;

CREATE INDEX idx_equipment_name ON equipment(equipment_name);
CREATE INDEX idx_equipment_category ON equipment(category_id);
CREATE INDEX idx_equipment_status ON equipment(status);

-- =========================================================
-- TABLE: members
-- =========================================================
CREATE TABLE members (
    member_id INT AUTO_INCREMENT PRIMARY KEY,
    student_code VARCHAR(50) NOT NULL UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(120) UNIQUE,
    phone VARCHAR(20),
    gender ENUM('Male','Female','Other'),
    date_of_birth DATE,
    department VARCHAR(100),
    course_class VARCHAR(100),
    address VARCHAR(255),
    emergency_contact VARCHAR(50),
    status ENUM('Active','Inactive') NOT NULL DEFAULT 'Active',
    registration_date DATE DEFAULT (CURRENT_DATE),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE INDEX idx_member_name ON members(full_name);
CREATE INDEX idx_member_code ON members(student_code);

-- =========================================================
-- TABLE: equipment_issues
-- =========================================================
CREATE TABLE equipment_issues (
    issue_id INT AUTO_INCREMENT PRIMARY KEY,
    member_id INT NOT NULL,
    equipment_id INT NOT NULL,
    quantity INT NOT NULL,
    issue_date DATE NOT NULL DEFAULT (CURRENT_DATE),
    expected_return_date DATE NOT NULL,
    actual_return_date DATE NULL,
    issued_by INT NOT NULL,
    return_status ENUM('Issued','Returned','Partially Returned','Overdue','Damaged','Lost') NOT NULL DEFAULT 'Issued',
    condition_before_issue VARCHAR(50),
    condition_after_return VARCHAR(50),
    remarks VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_issue_member FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE RESTRICT,
    CONSTRAINT fk_issue_equipment FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id) ON DELETE RESTRICT,
    CONSTRAINT fk_issue_user FOREIGN KEY (issued_by) REFERENCES users(user_id) ON DELETE RESTRICT,
    CONSTRAINT chk_issue_qty CHECK (quantity > 0)
) ENGINE=InnoDB;

CREATE INDEX idx_issue_member ON equipment_issues(member_id);
CREATE INDEX idx_issue_equipment ON equipment_issues(equipment_id);
CREATE INDEX idx_issue_status ON equipment_issues(return_status);
CREATE INDEX idx_issue_expected_return ON equipment_issues(expected_return_date);

-- =========================================================
-- TABLE: equipment_returns
-- =========================================================
CREATE TABLE equipment_returns (
    return_id INT AUTO_INCREMENT PRIMARY KEY,
    issue_id INT NOT NULL,
    returned_quantity INT NOT NULL,
    return_date DATE NOT NULL DEFAULT (CURRENT_DATE),
    condition_after_return VARCHAR(50),
    is_damaged TINYINT(1) NOT NULL DEFAULT 0,
    remarks VARCHAR(255),
    received_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_return_issue FOREIGN KEY (issue_id) REFERENCES equipment_issues(issue_id) ON DELETE RESTRICT,
    CONSTRAINT fk_return_user FOREIGN KEY (received_by) REFERENCES users(user_id) ON DELETE RESTRICT,
    CONSTRAINT chk_return_qty CHECK (returned_quantity > 0)
) ENGINE=InnoDB;

CREATE INDEX idx_return_issue ON equipment_returns(issue_id);

-- =========================================================
-- TABLE: damage_reports
-- =========================================================
CREATE TABLE damage_reports (
    report_id INT AUTO_INCREMENT PRIMARY KEY,
    equipment_id INT NOT NULL,
    member_id INT NULL,
    issue_id INT NULL,
    report_type ENUM('Damaged','Lost') NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    description VARCHAR(255),
    report_date DATE NOT NULL DEFAULT (CURRENT_DATE),
    estimated_cost DECIMAL(10,2) DEFAULT 0.00,
    status ENUM('Reported','Investigating','Repaired','Replaced','Written Off','Resolved') NOT NULL DEFAULT 'Reported',
    resolution VARCHAR(255),
    remarks VARCHAR(255),
    reported_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_damage_equipment FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id) ON DELETE RESTRICT,
    CONSTRAINT fk_damage_member FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE SET NULL,
    CONSTRAINT fk_damage_issue FOREIGN KEY (issue_id) REFERENCES equipment_issues(issue_id) ON DELETE SET NULL,
    CONSTRAINT fk_damage_user FOREIGN KEY (reported_by) REFERENCES users(user_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE INDEX idx_damage_equipment ON damage_reports(equipment_id);
CREATE INDEX idx_damage_status ON damage_reports(status);

-- =========================================================
-- TABLE: maintenance_records
-- =========================================================
CREATE TABLE maintenance_records (
    maintenance_id INT AUTO_INCREMENT PRIMARY KEY,
    equipment_id INT NOT NULL,
    maintenance_type VARCHAR(100),
    problem_description VARCHAR(255),
    start_date DATE NOT NULL DEFAULT (CURRENT_DATE),
    expected_completion_date DATE,
    actual_completion_date DATE,
    cost DECIMAL(10,2) DEFAULT 0.00,
    technician_vendor VARCHAR(150),
    status ENUM('Pending','In Progress','Completed','Cancelled') NOT NULL DEFAULT 'Pending',
    remarks VARCHAR(255),
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_maintenance_equipment FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id) ON DELETE RESTRICT,
    CONSTRAINT fk_maintenance_user FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE INDEX idx_maintenance_equipment ON maintenance_records(equipment_id);
CREATE INDEX idx_maintenance_status ON maintenance_records(status);

-- =========================================================
-- SEED DATA
-- =========================================================

-- Default users (both pre-approved, is_active = 1)
-- Username: admin   | Password: Admin@123
-- Username: staff1  | Password: Staff@123
-- Real passwords are set by running `python seed_admin.py` after this script
-- (SQL cannot compute Werkzeug's password hash on its own).
-- Anyone who registers through the app afterwards starts is_active = 0
-- and must be approved from the Team screen before they can sign in.
INSERT INTO users (username, email, password_hash, full_name, role, is_active) VALUES
('admin', 'admin@fieldhouse.app', 'pbkdf2:sha256:600000$placeholder$will_be_reset', 'System Administrator', 'Admin', 1),
('staff1', 'staff1@fieldhouse.app', 'pbkdf2:sha256:600000$placeholder$will_be_reset', 'Ravi Kumar', 'Staff', 1);

-- Categories
INSERT INTO categories (category_name, description) VALUES
('Cricket', 'Cricket equipment and accessories'),
('Football', 'Football equipment and accessories'),
('Basketball', 'Basketball equipment and accessories'),
('Volleyball', 'Volleyball equipment and accessories'),
('Badminton', 'Badminton equipment and accessories'),
('Tennis', 'Tennis equipment and accessories'),
('Hockey', 'Hockey equipment and accessories'),
('Gym', 'Gym and fitness equipment'),
('Athletics', 'Track and field equipment'),
('Table Tennis', 'Table tennis equipment');

-- Equipment
INSERT INTO equipment (equipment_name, category_id, brand, model, description, total_quantity, available_quantity, purchase_date, purchase_price, condition_status, location, status, supplier) VALUES
('Cricket Bat', 1, 'SG', 'RSD Xtreme', 'English willow cricket bat', 10, 10, '2024-01-15', 3500.00, 'New', 'Store Room A', 'Available', 'SG Sports'),
('Cricket Ball', 1, 'SG', 'Test', 'Leather cricket ball, red', 30, 30, '2024-01-15', 450.00, 'New', 'Store Room A', 'Available', 'SG Sports'),
('Football', 2, 'Nivia', 'Storm', 'Size 5 match football', 15, 15, '2024-02-10', 1200.00, 'Good', 'Store Room B', 'Available', 'Nivia Sports'),
('Basketball', 3, 'Spalding', 'NBA Street', 'Size 7 basketball', 12, 12, '2024-02-10', 1800.00, 'Good', 'Store Room B', 'Available', 'Spalding India'),
('Volleyball', 4, 'Nivia', 'Winner', 'Standard volleyball', 10, 10, '2024-02-15', 900.00, 'New', 'Store Room B', 'Available', 'Nivia Sports'),
('Tennis Racket', 6, 'Yonex', 'Ezone 100', 'Graphite tennis racket', 8, 8, '2024-03-01', 4500.00, 'Good', 'Store Room C', 'Available', 'Yonex India'),
('Badminton Racket', 5, 'Yonex', 'Arcsaber 11', 'Lightweight badminton racket', 20, 20, '2024-03-01', 2200.00, 'Good', 'Store Room C', 'Available', 'Yonex India'),
('Shuttlecock', 5, 'Yonex', 'Mavis 350', 'Nylon shuttlecock (box of 6)', 25, 25, '2024-03-05', 350.00, 'New', 'Store Room C', 'Available', 'Yonex India'),
('Hockey Stick', 7, 'Grays', 'GX2000', 'Composite hockey stick', 10, 10, '2024-01-20', 3200.00, 'Good', 'Store Room A', 'Available', 'Grays Sports'),
('Table Tennis Bat', 10, 'Stiga', 'Pro Carbon', 'Table tennis paddle', 15, 15, '2024-02-20', 900.00, 'Good', 'Store Room C', 'Available', 'Stiga India'),
('Table Tennis Ball', 10, 'Stiga', '3-Star', 'ITTF approved ball (pack of 6)', 40, 40, '2024-02-20', 250.00, 'New', 'Store Room C', 'Available', 'Stiga India'),
('Gym Dumbbells', 8, 'Cosco', 'Cast Iron 5kg', 'Pair of 5kg dumbbells', 12, 12, '2024-01-05', 1500.00, 'Good', 'Gym Hall', 'Available', 'Cosco India'),
('Skipping Rope', 8, 'Cosco', 'Speed Rope', 'Adjustable skipping rope', 20, 20, '2024-01-05', 200.00, 'New', 'Gym Hall', 'Available', 'Cosco India'),
('Sports Cones', 9, 'Cosco', 'Training Cones', 'Set of agility cones', 30, 30, '2024-01-10', 150.00, 'New', 'Store Room A', 'Available', 'Cosco India'),
('Goalkeeper Gloves', 2, 'Nivia', 'Shield', 'Football goalkeeper gloves', 6, 6, '2024-02-10', 800.00, 'Good', 'Store Room B', 'Available', 'Nivia Sports');

-- Members
INSERT INTO members (student_code, full_name, email, phone, gender, date_of_birth, department, course_class, address, emergency_contact, status) VALUES
('STU2024001', 'Aarav Sharma', 'aarav.sharma@college.edu', '9876543210', 'Male', '2003-05-14', 'Computer Science', 'B.Tech 3rd Year', 'Bengaluru, KA', '9876500001', 'Active'),
('STU2024002', 'Diya Patel', 'diya.patel@college.edu', '9876543211', 'Female', '2004-02-21', 'Electronics', 'B.Tech 2nd Year', 'Bengaluru, KA', '9876500002', 'Active'),
('STU2024003', 'Rohan Verma', 'rohan.verma@college.edu', '9876543212', 'Male', '2002-11-09', 'Mechanical', 'B.Tech 4th Year', 'Bengaluru, KA', '9876500003', 'Active'),
('STU2024004', 'Ananya Iyer', 'ananya.iyer@college.edu', '9876543213', 'Female', '2003-08-30', 'Civil', 'B.Tech 3rd Year', 'Bengaluru, KA', '9876500004', 'Active'),
('STU2024005', 'Karthik Reddy', 'karthik.reddy@college.edu', '9876543214', 'Male', '2004-01-17', 'Computer Science', 'B.Tech 2nd Year', 'Bengaluru, KA', '9876500005', 'Inactive');

-- Sample issue (currently active, not overdue)
INSERT INTO equipment_issues (member_id, equipment_id, quantity, issue_date, expected_return_date, issued_by, return_status, condition_before_issue) VALUES
(1, 1, 1, CURDATE() - INTERVAL 3 DAY, CURDATE() + INTERVAL 4 DAY, 1, 'Issued', 'New');
UPDATE equipment SET available_quantity = available_quantity - 1, status = 'Partially Available' WHERE equipment_id = 1;

-- Sample issue (overdue)
INSERT INTO equipment_issues (member_id, equipment_id, quantity, issue_date, expected_return_date, issued_by, return_status, condition_before_issue) VALUES
(2, 7, 2, CURDATE() - INTERVAL 10 DAY, CURDATE() - INTERVAL 3 DAY, 1, 'Issued', 'Good');
UPDATE equipment SET available_quantity = available_quantity - 2, status = 'Partially Available' WHERE equipment_id = 7;

-- Sample completed issue + return
INSERT INTO equipment_issues (member_id, equipment_id, quantity, issue_date, expected_return_date, actual_return_date, issued_by, return_status, condition_before_issue, condition_after_return) VALUES
(3, 3, 1, CURDATE() - INTERVAL 15 DAY, CURDATE() - INTERVAL 8 DAY, CURDATE() - INTERVAL 9 DAY, 2, 'Returned', 'Good', 'Good');
INSERT INTO equipment_returns (issue_id, returned_quantity, return_date, condition_after_return, is_damaged, received_by) VALUES
(3, 1, CURDATE() - INTERVAL 9 DAY, 'Good', 0, 2);

-- Sample maintenance record
INSERT INTO maintenance_records (equipment_id, maintenance_type, problem_description, start_date, expected_completion_date, cost, technician_vendor, status, created_by) VALUES
(9, 'Repair', 'Cracked hockey stick handle', CURDATE() - INTERVAL 5 DAY, CURDATE() + INTERVAL 2 DAY, 500.00, 'Local Sports Repair Shop', 'In Progress', 1);
UPDATE equipment SET available_quantity = available_quantity - 1, condition_status = 'Under Maintenance' WHERE equipment_id = 9;

-- Sample damage report
INSERT INTO damage_reports (equipment_id, member_id, issue_id, report_type, quantity, description, estimated_cost, status, reported_by) VALUES
(9, 3, NULL, 'Damaged', 1, 'Handle cracked during practice session', 500.00, 'Investigating', 1);
