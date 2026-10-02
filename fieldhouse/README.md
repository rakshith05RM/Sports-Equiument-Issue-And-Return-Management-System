# Fieldhouse — Equipment Operations

A production-oriented web application for running a sports facility's
equipment operation: what exists, who has it, when it's due back, what's
broken, and what's gone missing. Built to replace manual registers and
spreadsheets with one system of record.

---

## 1. What this is

Fieldhouse is a Flask + MySQL app for equipment-heavy sports operations —
clubs, academies, athletic departments, gyms — to run their gear the way a
depot runs inventory: every checkout and check-in is a transaction, every
account is reviewed before it gets access, and every number on the
dashboard is computed live from the database.

Access is closed by design. There is no open sign-up that hands out live
credentials. Anyone can **request** an account; nobody can **use** one
until an administrator approves it from the Team screen.

## 2. Features

- **Accounts** — self-service registration, but every new account is created
  inactive with Staff-level access. An Admin approves it, can promote it to
  Admin, deactivate it, or remove it — all from a dedicated Team screen.
  Passwords are hashed with Werkzeug; nothing is ever stored in plain text.
- **Overview console** — live stat tiles and charts computed straight from
  MySQL, plus a status ticker in the sidebar showing checked-out, overdue,
  and in-repair counts on every page.
- **Equipment** — add/edit/delete/view, search, filter, sort, pagination.
- **Categories** — add/edit/delete, protected against deleting a category
  that still has equipment assigned to it.
- **Members** — add/edit/delete/view, search, filter, per-member custody history.
- **Check-out (issue)** — a confirmation step before anything commits, then
  an atomic, row-locked database transaction so two staff can never
  over-commit the same item.
- **Check-in (return)** — partial returns, damage/loss handling inline,
  automatic inventory restoration.
- **Damage / Loss tracking** — status workflow from Reported through
  Repaired / Replaced / Written Off / Resolved.
- **Maintenance** — equipment taken out of service is automatically
  excluded from what's available to check out.
- **Reports** — 10 report types with filters and CSV export.
- **Role enforcement** — every sensitive route checks the role server-side,
  not just in the UI. Staff can operate day-to-day but can't delete
  equipment, members, categories, or manage accounts.
- **Error handling** — custom 404 / 403 / 500 pages, flash messages for
  every action, database-failure handling.

## 3. Technologies

| Layer            | Technology                                  |
|-------------------|-----------------------------------------------|
| Backend           | Python 3, Flask                               |
| Database          | MySQL 8+                                      |
| DB connectivity   | PyMySQL                                       |
| Frontend          | HTML5, CSS3 (custom design system), Bootstrap 5 components, JavaScript |
| Templating        | Jinja2                                        |
| Charts            | Chart.js                                      |
| Type              | Oswald (display), Inter (body), JetBrains Mono (codes/data) |
| Auth              | Flask sessions + Werkzeug password hashing    |

## 4. Requirements

- Python 3.10+
- MySQL Server 8.0+ (or MariaDB 10.5+)
- MySQL Workbench (recommended)
- pip

---

## 5. Setup

### Step 1 — Install MySQL

Install MySQL Server and, optionally, MySQL Workbench:
https://dev.mysql.com/downloads/mysql/ and
https://dev.mysql.com/downloads/workbench/

### Step 2 — Create the database

**MySQL Workbench:** open `database.sql` and click Execute.

**Command line:**
```bash
mysql -u root -p < database.sql
```

This creates the `fieldhouse` database, all tables, and seed data.

### Step 3 — Python virtual environment

```bash
python -m venv venv
```

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/macOS:**
```bash
source venv/bin/activate
```

### Step 4 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 5 — Configure environment variables

```bash
cp .env.example .env      # Windows: copy .env.example .env
```

Edit `.env`:

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_actual_mysql_password
DB_NAME=fieldhouse
SECRET_KEY=some_long_random_string
```

Generate a secret key:
```bash
python -c "import secrets; print(secrets.token_hex(16))"
```

### Step 6 — Set the two seed passwords

```bash
python seed_admin.py
```

`database.sql` inserts the seed `admin` and `staff1` rows with placeholder
password hashes (SQL can't compute a Werkzeug hash by itself). This script
sets their real, securely hashed passwords.

### Step 7 — Run it

```bash
python app.py
```

Open **http://127.0.0.1:5000**

---

## 6. Getting in

**Seed accounts** (pre-approved, ready immediately):

| Role  | Username | Password    |
|-------|----------|-------------|
| Admin | `admin`  | `Admin@123` |
| Staff | `staff1` | `Staff@123` |

**Everyone else** goes through `/register`:
1. They submit their name, username, email, and password.
2. The account is created immediately but **inactive** — they can't sign in yet.
3. An Admin opens **Team** in the sidebar, sees the pending request, and clicks **Approve**.
4. From that same screen, an Admin can also change someone's role (Staff ↔ Admin), deactivate an account, or delete one that has no historical records attached to it.

There is no path from the registration form to Admin access — every new
account starts as Staff, and only an existing Admin can promote anyone.

> ⚠️ Change the seed passwords in a real deployment.

---

## 7. Project structure

```
fieldhouse/
│
├── app.py                    # Entry point, blueprint registration, sidebar ticker
├── config.py                  # Reads settings from .env
├── database.py                  # Centralized PyMySQL connection helper
├── utils.py                      # login_required / admin_required, helpers
├── seed_admin.py                  # One-time script to set seed password hashes
├── requirements.txt
├── .env.example
├── .gitignore
├── database.sql                   # Full schema + seed data
│
├── routes/
│   ├── auth.py                    # Login, registration, logout
│   ├── team.py                     # Admin: approve/deactivate/promote/delete accounts
│   ├── dashboard.py                 # Live stats + chart data
│   ├── equipment.py                  # Equipment CRUD, search/filter/sort/paginate
│   ├── categories.py                  # Category CRUD
│   ├── members.py                      # Member CRUD
│   ├── issues.py                        # Check-out workflow (confirm + transaction)
│   ├── returns.py                        # Check-in workflow (transaction, damage/loss)
│   ├── maintenance.py                     # Maintenance records
│   ├── damage.py                           # Damage/lost reports
│   └── reports.py                           # 10 report types + CSV export
│
├── templates/
│   ├── base.html, login.html, register.html, dashboard.html
│   ├── team/       (list)
│   ├── equipment/  (list, add, edit, view)
│   ├── categories/ (list, add, edit)
│   ├── members/    (list, add, edit, view)
│   ├── issues/     (list, add, confirm, view)
│   ├── returns/    (list, pending, add)
│   ├── maintenance/(list, add, edit)
│   ├── damage/     (list, add, edit)
│   ├── reports/    (index)
│   └── errors/     (404, 403, 500)
│
└── static/
    ├── css/style.css     # Design system: tokens, sidebar shell, scoreboard tiles
    ├── js/script.js
    └── images/
```

---

## 8. Core business logic

**On check-out:**
```
available_quantity = available_quantity - issued_quantity
```

**On check-in:**
```
available_quantity = available_quantity + returned_quantity
```

`available_quantity` can never drop below 0 or exceed `total_quantity` —
enforced in the route logic (inside a transaction with `SELECT ... FOR
UPDATE` to prevent two staff members racing each other) and again as a
`CHECK` constraint at the database level.

**Overdue detection:**
```sql
expected_return_date < CURDATE() AND return_status IN ('Issued', 'Partially Returned')
```

**Account activation:**
```
is_active starts at 0 on self-registration
is_active = 1 only after an Admin clicks Approve on the Team screen
```

---

## 9. Testing checklist

- [ ] **Register** a new account, confirm it can't sign in yet
- [ ] **Admin approves** it from Team, confirm it can now sign in
- [ ] **Admin login** (`admin` / `Admin@123`) reaches the Overview console
- [ ] **Staff login** (`staff1` / `Staff@123`) succeeds with restricted access
- [ ] **Invalid login** shows "Invalid login credentials"
- [ ] **Staff cannot** reach Add/Edit/Delete Equipment, Categories, Members, or Team
- [ ] **Equipment CRUD** — add, edit, confirm delete is blocked with active custody, delete once returned
- [ ] **Category CRUD** — add, confirm delete is blocked while equipment is assigned, delete once empty
- [ ] **Member CRUD** — add, edit, delete
- [ ] **Check out equipment** — confirm screen shows correct before/after quantities, `available_quantity` decreases
- [ ] **Insufficient inventory** is blocked with a message
- [ ] **Overdue items** show on the dashboard and in red on the Check Out list
- [ ] **Check in equipment** — `available_quantity` increases
- [ ] **Damaged on return** — auto-creates a damage report, stock not restored for damaged units
- [ ] **Lost on return** — auto-creates a lost report
- [ ] **Maintenance** — taking units out of service drops availability; completing with "return to service" restores it
- [ ] **Reports** — each of the 10 types renders and exports to CSV
- [ ] **Team** — promote a Staff account to Admin, then confirm it can access Team
- [ ] **Team** — an Admin can't deactivate or remove their own account
- [ ] **Logout** — session clears, protected pages redirect to login

---

## 10. Common errors and fixes

| Problem | Cause | Fix |
|---|---|---|
| `Can't connect to MySQL server` | MySQL not running or wrong host/port | Start MySQL; check `DB_HOST`/`DB_PORT` |
| `Access denied for user` | Wrong `DB_USER`/`DB_PASSWORD` | Check `.env` against your MySQL credentials |
| `Unknown database 'fieldhouse'` | `database.sql` not run yet | Re-run Step 2 |
| Login always fails for `admin`/`staff1` | `seed_admin.py` never run | Run `python seed_admin.py` |
| New registration can't sign in | Working as intended — pending approval | Sign in as an Admin and approve it on **Team** |
| `ModuleNotFoundError` | venv not active or deps not installed | Activate `venv`, `pip install -r requirements.txt` |
| Blank/500 page | Check the terminal for the traceback | Usually a bad or missing form field |

---

## 11. Security notes

- No open registration-to-access path — every account is reviewed.
- Passwords hashed with Werkzeug (`generate_password_hash` / `check_password_hash`), never stored in plain text.
- All SQL uses parameterized placeholders — no string-built queries.
- `SECRET_KEY` and DB credentials come from `.env`, excluded from version control.
- Role checks (`admin_required`) run server-side on every sensitive route.
- Inventory-changing operations run inside transactions with row locking (`FOR UPDATE`) to prevent race conditions between concurrent staff.

## 12. License

Provided as a reference implementation — adapt it for your own facility.
