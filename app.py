import os, sqlite3, json, io, socket, secrets, shutil, hashlib
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, render_template, send_file, g, Response, session, redirect, url_for
from openpyxl import load_workbook, Workbook
import qrcode
from qrcode.image.svg import SvgPathImage
from werkzeug.security import generate_password_hash, check_password_hash

APP_VERSION = "19.2.1"
APP_STAGE = "Stage 19.2.1 - API /api/me and Table Map Stability"
ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "evangelism.db")
XLSX_PATH = os.path.join(DATA_DIR, "Delta_South_Diocese_Evangelism_Fundraising_System.xlsx")
SECRET_PATH = os.path.join(DATA_DIR, ".session_secret")
app = Flask(__name__)
os.makedirs(DATA_DIR, exist_ok=True)
if os.path.exists(SECRET_PATH):
    app.secret_key = open(SECRET_PATH, "r", encoding="utf-8").read().strip()
else:
    secret = secrets.token_hex(32)
    with open(SECRET_PATH, "w", encoding="utf-8") as f:
        f.write(secret)
    app.secret_key = secret
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

ROLES = {
    "Admin": "Full system access",
    "Bishop / Diocesan Executive": "Read-only diocesan oversight",
    "Evangelism Minister": "Diocesan evangelism, membership and church-planting management",
    "Planting Officer": "Diocesan church-planting and outreach management",
    "Diocesan Secretary": "Reporting, meetings and accountability records",
    "Circuit Coordinator": "Manage assigned circuit mission records",
    "Local Church Evangelism Officer": "Manage assigned church mission records",
    "Finance Officer": "Manage evangelism finance records",
    "Auditor": "Read-only access to reports and records",
}


DIOSAN_ROLES = {"Admin", "Bishop / Diocesan Executive", "Evangelism Minister", "Planting Officer", "Diocesan Secretary", "Finance Officer", "Auditor"}

def validate_user_assignment(role, circuit, church_name):
    circuit = (circuit or "").strip()
    church_name = (church_name or "").strip()

    if role == "Circuit Coordinator":
        if not circuit or circuit == "Diocesan":
            return "A Circuit Coordinator must be assigned to a circuit."
        if church_name:
            return "A Circuit Coordinator should not be assigned to a local church."

    elif role == "Local Church Evangelism Officer":
        if not circuit or circuit == "Diocesan":
            return "A Local Church Evangelism Officer must be assigned to a circuit."
        if not church_name:
            return "A Local Church Evangelism Officer must be assigned to a local church."

        church = db().execute(
            "SELECT 1 FROM churches WHERE circuit=? AND church_name=?",
            (circuit, church_name)
        ).fetchone()

        if not church:
            return "The assigned local church does not belong to the selected circuit."

    elif role in DIOSAN_ROLES:
        if circuit or church_name:
            return "This diocesan role should not be assigned to a circuit or local church."

    return None

FINANCE_TABLES = {"commitments", "income", "expenses", "sponsors", "equipment", "trust_fund", "mission_budgets", "procurement_requests"}
MISSION_TABLES = {"churches", "church_plants", "planting_prospects", "outreach", "mission_calendar", "mission_teams", "mission_contacts", "report_periods", "circuit_reports", "action_points", "meetings", "diocesan_reviews", "notifications"}
MEMBERSHIP_TABLES = {"members", "testimonies", "appreciations", "mission_contacts"}
ALL_TABLES = {"churches", "commitments", "income", "expenses", "equipment", "trust_fund", "mission_budgets", "procurement_requests", "church_plants", "planting_prospects", "outreach", "mission_calendar", "mission_teams", "mission_contacts", "sponsors", "members", "testimonies", "appreciations", "report_periods", "circuit_reports", "action_points", "meetings", "diocesan_reviews", "notifications"}


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


@app.teardown_appcontext
def close_db(exc):
    conn = g.pop("db", None)
    if conn:
        conn.close()


def ensure_column(conn, table, column, definition):
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS churches(
      id INTEGER PRIMARY KEY AUTOINCREMENT, circuit TEXT NOT NULL, church_name TEXT NOT NULL,
      annual_target REAL DEFAULT 100000, contact_person TEXT DEFAULT '', phone TEXT DEFAULT '',
      notes TEXT DEFAULT '', church_status TEXT DEFAULT 'Local Church',
      is_circuit_headquarters INTEGER DEFAULT 0, upgraded_at TEXT DEFAULT '',
      UNIQUE(circuit, church_name));
    CREATE TABLE IF NOT EXISTS circuits(
      id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL,
      headquarters_church_id INTEGER DEFAULT NULL, status TEXT DEFAULT 'Active',
      created_at TEXT DEFAULT '', notes TEXT DEFAULT '',
      FOREIGN KEY(headquarters_church_id) REFERENCES churches(id) ON DELETE SET NULL);
    CREATE TABLE IF NOT EXISTS commitments(
      id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, donor_name TEXT NOT NULL, donor_type TEXT DEFAULT 'Partner',
      phone TEXT DEFAULT '', purpose TEXT DEFAULT 'General Evangelism', amount REAL DEFAULT 0,
      frequency TEXT DEFAULT 'One-time', status TEXT DEFAULT 'Pledged', notes TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS income(
      id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, donor_name TEXT DEFAULT '',
      source TEXT DEFAULT 'Donation', fund TEXT DEFAULT 'General Evangelism', amount REAL NOT NULL,
      method TEXT DEFAULT 'Transfer', reference TEXT DEFAULT '', received_by TEXT DEFAULT '', notes TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS expenses(
      id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, category TEXT NOT NULL,
      description TEXT NOT NULL, circuit TEXT DEFAULT '', amount REAL NOT NULL,
      approved_by TEXT DEFAULT '', paid_by TEXT DEFAULT '', receipt_ref TEXT DEFAULT '', notes TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS equipment(
      id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT NOT NULL, category TEXT DEFAULT '',
      quantity REAL DEFAULT 1, unit_cost REAL DEFAULT 0, condition TEXT DEFAULT 'Planned',
      priority TEXT DEFAULT 'Medium', phase TEXT DEFAULT 'Phase 1',
      location TEXT DEFAULT '', purchase_date TEXT DEFAULT '', notes TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS trust_fund(
      id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, transaction_type TEXT DEFAULT 'Income',
      source_or_payee TEXT DEFAULT '', purpose TEXT DEFAULT 'General Evangelism Trust Fund',
      amount REAL NOT NULL DEFAULT 0, method TEXT DEFAULT 'Transfer', reference TEXT DEFAULT '',
      approved_by TEXT DEFAULT '', received_or_paid_by TEXT DEFAULT '', notes TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS mission_budgets(
      id INTEGER PRIMARY KEY AUTOINCREMENT, year INTEGER NOT NULL, budget_name TEXT NOT NULL,
      circuit TEXT DEFAULT 'Diocesan', category TEXT DEFAULT 'Outreach', planned_amount REAL DEFAULT 0,
      spent_amount REAL DEFAULT 0, status TEXT DEFAULT 'Planned', notes TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS procurement_requests(
      id INTEGER PRIMARY KEY AUTOINCREMENT, request_date TEXT NOT NULL, item TEXT NOT NULL, category TEXT DEFAULT 'Sound',
      quantity REAL DEFAULT 1, estimated_unit_cost REAL DEFAULT 0, priority TEXT DEFAULT 'High',
      needed_by TEXT DEFAULT '', requested_by TEXT DEFAULT '', approval_status TEXT DEFAULT 'Pending',
      supplier TEXT DEFAULT '', notes TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS planting_prospects(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      prospect_id TEXT UNIQUE NOT NULL,
      year INTEGER DEFAULT 0,
      circuit TEXT DEFAULT '',
      location TEXT NOT NULL,
      proposed_church_name TEXT DEFAULT '',
      population_estimate INTEGER DEFAULT 0,
      existing_methodist_presence TEXT DEFAULT 'None',
      nearest_methodist_distance REAL DEFAULT 0,
      contact_person TEXT DEFAULT '',
      phone TEXT DEFAULT '',
      evangelism_status TEXT DEFAULT 'Identified',
      outreach_status TEXT DEFAULT 'Not Started',
      priority TEXT DEFAULT 'Medium',
      proposed_planting_year INTEGER DEFAULT 0,
      responsible_officer TEXT DEFAULT '',
      status TEXT DEFAULT 'Prospect',
      notes TEXT DEFAULT '',
      created_at TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS church_plants(
      id INTEGER PRIMARY KEY AUTOINCREMENT, year INTEGER NOT NULL, axis TEXT DEFAULT '',
      location TEXT NOT NULL, status TEXT DEFAULT 'Planned', budget REAL DEFAULT 0,
      leader TEXT DEFAULT '', start_date TEXT DEFAULT '', members INTEGER DEFAULT 0, notes TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS outreach(
      id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, circuit TEXT DEFAULT '',
      location TEXT NOT NULL, activity TEXT DEFAULT 'Outreach', attendance INTEGER DEFAULT 0,
      decisions INTEGER DEFAULT 0, followups INTEGER DEFAULT 0, cost REAL DEFAULT 0,
      lead_person TEXT DEFAULT '', notes TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS mission_calendar(
      id INTEGER PRIMARY KEY AUTOINCREMENT, event_date TEXT NOT NULL, event_time TEXT DEFAULT '',
      event_type TEXT DEFAULT 'Outreach', circuit TEXT DEFAULT '', location TEXT NOT NULL,
      activity TEXT DEFAULT '', mission_phase TEXT DEFAULT 'Preparation', church_plant_id INTEGER DEFAULT NULL,
      responsible_person TEXT DEFAULT '', expected_outcome TEXT DEFAULT '', followup_date TEXT DEFAULT '',
      status TEXT DEFAULT 'Scheduled', notes TEXT DEFAULT '', created_at TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS mission_teams(
      id INTEGER PRIMARY KEY AUTOINCREMENT, team_name TEXT NOT NULL, circuit TEXT DEFAULT '', church_name TEXT DEFAULT '',
      leader TEXT DEFAULT '', members TEXT DEFAULT '', mission_type TEXT DEFAULT 'Outreach', active TEXT DEFAULT 'Yes',
      phone TEXT DEFAULT '', notes TEXT DEFAULT '', created_at TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS mission_contacts(
      id INTEGER PRIMARY KEY AUTOINCREMENT, contact_name TEXT NOT NULL, phone TEXT DEFAULT '', address TEXT DEFAULT '',
      circuit TEXT DEFAULT '', church_name TEXT DEFAULT '', source_mission TEXT DEFAULT '', mission_date TEXT DEFAULT '',
      status TEXT DEFAULT 'New Contact', assigned_to TEXT DEFAULT '', next_followup_date TEXT DEFAULT '',
      followup_status TEXT DEFAULT 'Pending', outcome TEXT DEFAULT '', member_id TEXT DEFAULT '',
      church_plant_id INTEGER DEFAULT NULL, notes TEXT DEFAULT '', created_at TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS sponsors(
      id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, organization TEXT DEFAULT '',
      phone TEXT DEFAULT '', email TEXT DEFAULT '', sponsorship_type TEXT DEFAULT 'Financial',
      amount REAL DEFAULT 0, status TEXT DEFAULT 'Prospect', next_contact TEXT DEFAULT '', notes TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS members(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      member_id TEXT UNIQUE NOT NULL,
      role_position TEXT DEFAULT 'Other',
      circuit TEXT NOT NULL,
      church_name TEXT NOT NULL,
      full_name TEXT NOT NULL,
      address TEXT DEFAULT '',
      phone TEXT DEFAULT '',
      birthday TEXT DEFAULT '',
      fellowship TEXT DEFAULT '',
      baptised TEXT DEFAULT 'No',
      baptism_date TEXT DEFAULT '',
      confirmed TEXT DEFAULT 'No',
      confirmation_date TEXT DEFAULT '',
      marriage TEXT DEFAULT 'No',
      marriage_date TEXT DEFAULT '',
      relocated TEXT DEFAULT 'No',
      relocation_destination TEXT DEFAULT '',
      relocation_date TEXT DEFAULT '',
      transfer TEXT DEFAULT 'No',
      transfer_from TEXT DEFAULT '',
      transfer_to TEXT DEFAULT '',
      transfer_date TEXT DEFAULT '',
      work_address TEXT DEFAULT '',
      profession_business_trade TEXT DEFAULT '',
      death TEXT DEFAULT 'No',
      death_date TEXT DEFAULT '',
      seed_of_faith_payment REAL DEFAULT 0,
      tithe_payment REAL DEFAULT 0,
      notes TEXT DEFAULT '',
      created_at TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS testimonies(
      id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, member_name TEXT DEFAULT '',
      circuit TEXT DEFAULT '', church_name TEXT DEFAULT '', title TEXT DEFAULT '',
      testimony TEXT NOT NULL, recorded_by TEXT DEFAULT '', created_at TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS appreciations(
      id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, recipient TEXT NOT NULL,
      role_position TEXT DEFAULT '', circuit TEXT DEFAULT '', church_name TEXT DEFAULT '',
      reason TEXT DEFAULT '', message TEXT NOT NULL, recorded_by TEXT DEFAULT '', created_at TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS report_periods(
      id INTEGER PRIMARY KEY AUTOINCREMENT, period_name TEXT NOT NULL, period_type TEXT DEFAULT 'Monthly',
      start_date TEXT NOT NULL, end_date TEXT NOT NULL, submission_due TEXT DEFAULT '', status TEXT DEFAULT 'Open',
      instructions TEXT DEFAULT '', created_at TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS circuit_reports(
      id INTEGER PRIMARY KEY AUTOINCREMENT, period_id INTEGER DEFAULT NULL, period_name TEXT DEFAULT '',
      circuit TEXT NOT NULL, submitted_by TEXT DEFAULT '', submitted_at TEXT DEFAULT '',
      outreach_missions INTEGER DEFAULT 0, people_reached INTEGER DEFAULT 0, decisions INTEGER DEFAULT 0,
      followups_completed INTEGER DEFAULT 0, church_plants_active INTEGER DEFAULT 0, churches_launched INTEGER DEFAULT 0,
      testimonies INTEGER DEFAULT 0, challenges TEXT DEFAULT '', achievements TEXT DEFAULT '', needs_support TEXT DEFAULT '',
      financial_note TEXT DEFAULT '', status TEXT DEFAULT 'Submitted', reviewed_by TEXT DEFAULT '', reviewed_at TEXT DEFAULT '', review_note TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS action_points(
      id INTEGER PRIMARY KEY AUTOINCREMENT, period_id INTEGER DEFAULT NULL, circuit TEXT DEFAULT 'Diocesan',
      action_item TEXT NOT NULL, responsible_person TEXT DEFAULT '', due_date TEXT DEFAULT '', priority TEXT DEFAULT 'Medium',
      status TEXT DEFAULT 'Open', completion_note TEXT DEFAULT '', created_by TEXT DEFAULT '', created_at TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS meetings(
      id INTEGER PRIMARY KEY AUTOINCREMENT, meeting_date TEXT NOT NULL, meeting_type TEXT DEFAULT 'Evangelism Committee',
      circuit TEXT DEFAULT 'Diocesan', location TEXT DEFAULT '', chairperson TEXT DEFAULT '', secretary TEXT DEFAULT '',
      attendance TEXT DEFAULT '', agenda TEXT DEFAULT '', minutes TEXT DEFAULT '', decisions TEXT DEFAULT '', next_meeting TEXT DEFAULT '',
      created_by TEXT DEFAULT '', created_at TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS diocesan_reviews(
      id INTEGER PRIMARY KEY AUTOINCREMENT, period_id INTEGER DEFAULT NULL, period_name TEXT DEFAULT '', review_date TEXT NOT NULL,
      executive_summary TEXT NOT NULL, key_achievements TEXT DEFAULT '', major_challenges TEXT DEFAULT '', decisions TEXT DEFAULT '',
      support_required TEXT DEFAULT '', prepared_by TEXT DEFAULT '', approved_by TEXT DEFAULT '', status TEXT DEFAULT 'Draft', notes TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS notifications(
      id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, message TEXT NOT NULL,
      notification_type TEXT DEFAULT 'Reminder', target_circuit TEXT DEFAULT 'Diocesan',
      target_phone TEXT DEFAULT '', source_table TEXT DEFAULT '', source_id INTEGER DEFAULT NULL,
      due_date TEXT DEFAULT '', status TEXT DEFAULT 'Unread', created_at TEXT DEFAULT '', read_at TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL,
      role TEXT DEFAULT 'Admin', circuit TEXT DEFAULT '', church_name TEXT DEFAULT '',
      active INTEGER DEFAULT 1, must_change_password INTEGER DEFAULT 0, created_at TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS audit_log(
      id INTEGER PRIMARY KEY AUTOINCREMENT, happened_at TEXT NOT NULL, action TEXT NOT NULL,
      table_name TEXT NOT NULL, record_id INTEGER, details TEXT DEFAULT '', user_id INTEGER DEFAULT NULL,
      username TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS backup_history(
      id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, created_by TEXT DEFAULT '',
      filename TEXT NOT NULL, size_bytes INTEGER DEFAULT 0, sha256 TEXT DEFAULT '',
      backup_type TEXT DEFAULT 'Manual', status TEXT DEFAULT 'Ready');
    """)
    # Safe migration for databases created by earlier builds.
    # The app may be upgraded while retaining an existing evangelism.db, so
    # every column introduced by the membership/testimony modules must be
    # present before the API attempts an INSERT.
    member_migrations = {
        "member_id": "TEXT DEFAULT ''",
        "role_position": "TEXT DEFAULT 'Other'",
        "circuit": "TEXT DEFAULT ''",
        "church_name": "TEXT DEFAULT ''",
        "full_name": "TEXT DEFAULT ''",
        "address": "TEXT DEFAULT ''",
        "phone": "TEXT DEFAULT ''",
        "birthday": "TEXT DEFAULT ''",
        "fellowship": "TEXT DEFAULT ''",
        "baptised": "TEXT DEFAULT 'No'", "baptism_date": "TEXT DEFAULT ''",
        "confirmed": "TEXT DEFAULT 'No'", "confirmation_date": "TEXT DEFAULT ''",
        "marriage": "TEXT DEFAULT 'No'", "marriage_date": "TEXT DEFAULT ''",
        "relocated": "TEXT DEFAULT 'No'", "relocation_destination": "TEXT DEFAULT ''", "relocation_date": "TEXT DEFAULT ''",
        "transfer": "TEXT DEFAULT 'No'", "transfer_from": "TEXT DEFAULT ''", "transfer_to": "TEXT DEFAULT ''", "transfer_date": "TEXT DEFAULT ''",
        "work_address": "TEXT DEFAULT ''", "profession_business_trade": "TEXT DEFAULT ''",
        "death": "TEXT DEFAULT 'No'", "death_date": "TEXT DEFAULT ''",
        "seed_of_faith_payment": "REAL DEFAULT 0", "tithe_payment": "REAL DEFAULT 0",
        "notes": "TEXT DEFAULT ''", "created_at": "TEXT DEFAULT ''"
    }
    for col, definition in member_migrations.items():
        ensure_column(conn, "members", col, definition)
    testimony_migrations = {
        "date": "TEXT DEFAULT ''", "member_name": "TEXT DEFAULT ''", "circuit": "TEXT DEFAULT ''",
        "church_name": "TEXT DEFAULT ''", "title": "TEXT DEFAULT ''", "testimony": "TEXT DEFAULT ''",
        "recorded_by": "TEXT DEFAULT ''", "created_at": "TEXT DEFAULT ''"
    }
    for col, definition in testimony_migrations.items():
        ensure_column(conn, "testimonies", col, definition)
    church_plant_migrations = {
        "circuit": "TEXT DEFAULT ''",
        "phase": "TEXT DEFAULT 'Surveying'",
        "launch_date": "TEXT DEFAULT ''",
        "next_followup_date": "TEXT DEFAULT ''",
        "followup_end_date": "TEXT DEFAULT ''"
    }
    for col, definition in church_plant_migrations.items():
        ensure_column(conn, "church_plants", col, definition)
    outreach_migrations = {
        "mission_phase": "TEXT DEFAULT 'Outreach'",
        "next_followup_date": "TEXT DEFAULT ''",
        "church_plant_axis": "TEXT DEFAULT ''"
    }
    for col, definition in outreach_migrations.items():
        ensure_column(conn, "outreach", col, definition)
    appreciation_migrations = {
        "date": "TEXT DEFAULT ''", "recipient": "TEXT DEFAULT ''", "role_position": "TEXT DEFAULT ''",
        "circuit": "TEXT DEFAULT ''", "church_name": "TEXT DEFAULT ''", "reason": "TEXT DEFAULT ''",
        "message": "TEXT DEFAULT ''", "recorded_by": "TEXT DEFAULT ''", "created_at": "TEXT DEFAULT ''"
    }
    for col, definition in appreciation_migrations.items():
        ensure_column(conn, "appreciations", col, definition)
    mission_calendar_migrations = {
        "event_date": "TEXT DEFAULT ''", "event_time": "TEXT DEFAULT ''", "event_type": "TEXT DEFAULT 'Outreach'",
        "circuit": "TEXT DEFAULT ''", "location": "TEXT DEFAULT ''", "activity": "TEXT DEFAULT ''",
        "mission_phase": "TEXT DEFAULT 'Preparation'", "church_plant_id": "INTEGER DEFAULT NULL",
        "responsible_person": "TEXT DEFAULT ''", "expected_outcome": "TEXT DEFAULT ''",
        "followup_date": "TEXT DEFAULT ''", "status": "TEXT DEFAULT 'Scheduled'",
        "notes": "TEXT DEFAULT ''", "created_at": "TEXT DEFAULT ''"
    }
    for col, definition in mission_calendar_migrations.items():
        ensure_column(conn, "mission_calendar", col, definition)
    mission_team_migrations = {
        "team_name": "TEXT DEFAULT ''", "circuit": "TEXT DEFAULT ''", "church_name": "TEXT DEFAULT ''",
        "leader": "TEXT DEFAULT ''", "members": "TEXT DEFAULT ''", "mission_type": "TEXT DEFAULT 'Outreach'",
        "active": "TEXT DEFAULT 'Yes'", "phone": "TEXT DEFAULT ''", "notes": "TEXT DEFAULT ''", "created_at": "TEXT DEFAULT ''"
    }
    for col, definition in mission_team_migrations.items():
        ensure_column(conn, "mission_teams", col, definition)
    mission_contact_migrations = {
        "contact_name": "TEXT DEFAULT ''", "phone": "TEXT DEFAULT ''", "address": "TEXT DEFAULT ''",
        "circuit": "TEXT DEFAULT ''", "church_name": "TEXT DEFAULT ''", "source_mission": "TEXT DEFAULT ''",
        "mission_date": "TEXT DEFAULT ''", "status": "TEXT DEFAULT 'New Contact'", "assigned_to": "TEXT DEFAULT ''",
        "next_followup_date": "TEXT DEFAULT ''", "followup_status": "TEXT DEFAULT 'Pending'", "outcome": "TEXT DEFAULT ''",
        "member_id": "TEXT DEFAULT ''", "church_plant_id": "INTEGER DEFAULT NULL", "notes": "TEXT DEFAULT ''", "created_at": "TEXT DEFAULT ''"
    }
    for col, definition in mission_contact_migrations.items():
        ensure_column(conn, "mission_contacts", col, definition)
    ensure_column(conn, "churches", "church_status", "TEXT DEFAULT 'Local Church'")
    ensure_column(conn, "churches", "is_circuit_headquarters", "INTEGER DEFAULT 0")
    ensure_column(conn, "churches", "upgraded_at", "TEXT DEFAULT ''")
    ensure_column(conn, "users", "circuit", "TEXT DEFAULT ''")
    ensure_column(conn, "users", "church_name", "TEXT DEFAULT ''")
    ensure_column(conn, "users", "active", "INTEGER DEFAULT 1")
    ensure_column(conn, "users", "must_change_password", "INTEGER DEFAULT 0")
    ensure_column(conn, "users", "created_at", "TEXT DEFAULT ''")
    ensure_column(conn, "audit_log", "user_id", "INTEGER DEFAULT NULL")
    ensure_column(conn, "audit_log", "username", "TEXT DEFAULT ''")

    existing = conn.execute("SELECT COUNT(*) FROM churches").fetchone()[0]
    if existing == 0:
        seed = [
          ("Effurun Circuit","Effurun Local Church 1"),("Effurun Circuit","Effurun Local Church 2"),
          ("Effurun Circuit","Effurun Local Church 3"),("Effurun Circuit","Effurun Local Church 4"),
          ("Effurun Circuit","Effurun Local Church 5"),
          ("Warri Circuit","Warri Local Church 1"),("Warri Circuit","Warri Local Church 2"),
          ("Warri Circuit","Warri Local Church 3"),("Warri Circuit","Warri Local Church 4"),
          ("Sapele Circuit","Sapele Local Church 1"),("Sapele Circuit","Sapele Local Church 2"),
          ("Sapele Circuit","Sapele Local Church 3"),("Sapele Circuit","Sapele Local Church 4"),
          ("Steel Town Circuit","Steel Town Local Church 1"),("Steel Town Circuit","Steel Town Local Church 2"),
          ("Steel Town Circuit","Steel Town Local Church 3"),("Steel Town Circuit","Steel Town Local Church 4")]
        conn.executemany("INSERT INTO churches(circuit,church_name,annual_target) VALUES(?,?,100000)", seed)
    # Keep the current four diocesan circuits available as structured records.
    for circuit_name in ["Effurun Circuit", "Warri Circuit", "Sapele Circuit", "Steel Town Circuit"]:
        conn.execute("INSERT OR IGNORE INTO circuits(name,status,created_at) VALUES(?,?,?)",
                     (circuit_name, "Active", datetime.now().isoformat(timespec="seconds")))
    conn.execute("""UPDATE circuits SET headquarters_church_id = (
        SELECT c.id FROM churches c WHERE c.circuit=circuits.name AND c.is_circuit_headquarters=1 ORDER BY c.id LIMIT 1
    ) WHERE headquarters_church_id IS NULL""")
    if not conn.execute("SELECT COUNT(*) FROM church_plants").fetchone()[0]:
        conn.executemany("INSERT INTO church_plants(year,axis,location,status,budget) VALUES(?,?,?,?,?)",
                         [(y, "", f"Church Plant {i} - location to be confirmed", "Planned", 1000000)
                          for y in range(2027, 2032) for i in range(1, 6)])
    if not conn.execute("SELECT COUNT(*) FROM equipment").fetchone()[0] and os.path.exists(XLSX_PATH):
        try:
            source_wb = load_workbook(XLSX_PATH, data_only=True, read_only=True)
            source_ws = source_wb["Equipment Budget"]
            for row in source_ws.iter_rows(min_row=5, values_only=True):
                category, item, qty, unit_cost, total, priority, phase, notes = (list(row) + [None] * 8)[:8]
                if item:
                    conn.execute("""INSERT INTO equipment
                      (item,category,quantity,unit_cost,condition,priority,phase,notes)
                      VALUES(?,?,?,?,?,?,?,?)""",
                      (str(item), str(category or ""), float(qty or 1), float(unit_cost or 0),
                       "Planned", str(priority or "Medium"), str(phase or "Phase 1"), str(notes or "")))
            source_wb.close()
        except Exception:
            pass
    conn.commit()
    conn.close()



def ensure_runtime_schema():
    """Repair/upgrade the retained SQLite database before dashboard APIs run.
    This is intentionally safe for existing evangelism.db files.
    """
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS report_periods(
      id INTEGER PRIMARY KEY AUTOINCREMENT, period_name TEXT NOT NULL, period_type TEXT DEFAULT 'Monthly',
      start_date TEXT NOT NULL DEFAULT '', end_date TEXT NOT NULL DEFAULT '', submission_due TEXT DEFAULT '',
      status TEXT DEFAULT 'Open', instructions TEXT DEFAULT '', created_at TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS circuit_reports(
      id INTEGER PRIMARY KEY AUTOINCREMENT, period_id INTEGER DEFAULT NULL, period_name TEXT DEFAULT '',
      circuit TEXT NOT NULL DEFAULT '', submitted_by TEXT DEFAULT '', submitted_at TEXT DEFAULT '',
      outreach_missions INTEGER DEFAULT 0, people_reached INTEGER DEFAULT 0, decisions INTEGER DEFAULT 0,
      followups_completed INTEGER DEFAULT 0, church_plants_active INTEGER DEFAULT 0, churches_launched INTEGER DEFAULT 0,
      testimonies INTEGER DEFAULT 0, challenges TEXT DEFAULT '', achievements TEXT DEFAULT '', needs_support TEXT DEFAULT '',
      financial_note TEXT DEFAULT '', status TEXT DEFAULT 'Submitted', reviewed_by TEXT DEFAULT '', reviewed_at TEXT DEFAULT '', review_note TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS action_points(
      id INTEGER PRIMARY KEY AUTOINCREMENT, period_id INTEGER DEFAULT NULL, circuit TEXT DEFAULT 'Diocesan',
      action_item TEXT NOT NULL DEFAULT '', responsible_person TEXT DEFAULT '', due_date TEXT DEFAULT '', priority TEXT DEFAULT 'Medium',
      status TEXT DEFAULT 'Open', completion_note TEXT DEFAULT '', created_by TEXT DEFAULT '', created_at TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS meetings(
      id INTEGER PRIMARY KEY AUTOINCREMENT, meeting_date TEXT NOT NULL DEFAULT '', meeting_type TEXT DEFAULT 'Evangelism Committee',
      circuit TEXT DEFAULT 'Diocesan', location TEXT DEFAULT '', chairperson TEXT DEFAULT '', secretary TEXT DEFAULT '', attendance TEXT DEFAULT '',
      agenda TEXT DEFAULT '', minutes TEXT DEFAULT '', decisions TEXT DEFAULT '', next_meeting TEXT DEFAULT '', created_by TEXT DEFAULT '', created_at TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS diocesan_reviews(
      id INTEGER PRIMARY KEY AUTOINCREMENT, period_id INTEGER DEFAULT NULL, period_name TEXT DEFAULT '', review_date TEXT NOT NULL DEFAULT '',
      executive_summary TEXT NOT NULL DEFAULT '', key_achievements TEXT DEFAULT '', major_challenges TEXT DEFAULT '', decisions TEXT DEFAULT '',
      support_required TEXT DEFAULT '', prepared_by TEXT DEFAULT '', approved_by TEXT DEFAULT '', status TEXT DEFAULT 'Draft', notes TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS notifications(
      id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL DEFAULT '', message TEXT NOT NULL DEFAULT '',
      notification_type TEXT DEFAULT 'Reminder', target_circuit TEXT DEFAULT 'Diocesan', target_phone TEXT DEFAULT '',
      source_table TEXT DEFAULT '', source_id INTEGER DEFAULT NULL, due_date TEXT DEFAULT '', status TEXT DEFAULT 'Unread',
      created_at TEXT DEFAULT '', read_at TEXT DEFAULT ''
    );
    """)
    migrations = {
      'report_periods': {
        'period_name': "TEXT DEFAULT ''", 'period_type': "TEXT DEFAULT 'Monthly'", 'start_date': "TEXT DEFAULT ''", 'end_date': "TEXT DEFAULT ''",
        'submission_due': "TEXT DEFAULT ''", 'status': "TEXT DEFAULT 'Open'", 'instructions': "TEXT DEFAULT ''", 'created_at': "TEXT DEFAULT ''"},
      'circuit_reports': {
        'period_id': 'INTEGER DEFAULT NULL','period_name': "TEXT DEFAULT ''",'circuit': "TEXT DEFAULT ''",'submitted_by': "TEXT DEFAULT ''",'submitted_at': "TEXT DEFAULT ''",
        'outreach_missions':'INTEGER DEFAULT 0','people_reached':'INTEGER DEFAULT 0','decisions':'INTEGER DEFAULT 0','followups_completed':'INTEGER DEFAULT 0',
        'church_plants_active':'INTEGER DEFAULT 0','churches_launched':'INTEGER DEFAULT 0','testimonies':'INTEGER DEFAULT 0','challenges':"TEXT DEFAULT ''",'achievements':"TEXT DEFAULT ''",'needs_support':"TEXT DEFAULT ''",'financial_note':"TEXT DEFAULT ''",'status':"TEXT DEFAULT 'Submitted'",'reviewed_by':"TEXT DEFAULT ''",'reviewed_at':"TEXT DEFAULT ''",'review_note':"TEXT DEFAULT ''"},
      'action_points': {'period_id':'INTEGER DEFAULT NULL','circuit':"TEXT DEFAULT 'Diocesan'",'action_item':"TEXT DEFAULT ''",'responsible_person':"TEXT DEFAULT ''",'due_date':"TEXT DEFAULT ''",'priority':"TEXT DEFAULT 'Medium'",'status':"TEXT DEFAULT 'Open'",'completion_note':"TEXT DEFAULT ''",'created_by':"TEXT DEFAULT ''",'created_at':"TEXT DEFAULT ''"},
      'meetings': {'meeting_date':"TEXT DEFAULT ''",'meeting_type':"TEXT DEFAULT 'Evangelism Committee'",'circuit':"TEXT DEFAULT 'Diocesan'",'location':"TEXT DEFAULT ''",'chairperson':"TEXT DEFAULT ''",'secretary':"TEXT DEFAULT ''",'attendance':"TEXT DEFAULT ''",'agenda':"TEXT DEFAULT ''",'minutes':"TEXT DEFAULT ''",'decisions':"TEXT DEFAULT ''",'next_meeting':"TEXT DEFAULT ''",'created_by':"TEXT DEFAULT ''",'created_at':"TEXT DEFAULT ''"},
      'diocesan_reviews': {'period_id':'INTEGER DEFAULT NULL','period_name':"TEXT DEFAULT ''",'review_date':"TEXT DEFAULT ''",'executive_summary':"TEXT DEFAULT ''",'key_achievements':"TEXT DEFAULT ''",'major_challenges':"TEXT DEFAULT ''",'decisions':"TEXT DEFAULT ''",'support_required':"TEXT DEFAULT ''",'prepared_by':"TEXT DEFAULT ''",'approved_by':"TEXT DEFAULT ''",'status':"TEXT DEFAULT 'Draft'",'notes':"TEXT DEFAULT ''"},
      'notifications': {'title':"TEXT DEFAULT ''",'message':"TEXT DEFAULT ''",'notification_type':"TEXT DEFAULT 'Reminder'",'target_circuit':"TEXT DEFAULT 'Diocesan'",'target_phone':"TEXT DEFAULT ''",'source_table':"TEXT DEFAULT ''",'source_id':'INTEGER DEFAULT NULL','due_date':"TEXT DEFAULT ''",'status':"TEXT DEFAULT 'Unread'",'created_at':"TEXT DEFAULT ''",'read_at':"TEXT DEFAULT ''"}
    }
    for table, cols in migrations.items():
        for col, definition in cols.items():
            ensure_column(conn, table, col, definition)
    conn.commit()

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return db().execute("SELECT id,username,role,circuit,church_name,active,must_change_password,created_at FROM users WHERE id=?", (uid,)).fetchone()


def audit(action, table, rid=None, details=""):
    u = current_user()
    db().execute("INSERT INTO audit_log(happened_at,action,table_name,record_id,details,user_id,username) VALUES(?,?,?,?,?,?,?)",
                 (datetime.now().isoformat(timespec="seconds"), action, table, rid, details,
                  u["id"] if u else None, u["username"] if u else "system"))
    db().commit()


def rows(sql, args=()):
    return [dict(r) for r in db().execute(sql, args).fetchall()]


def is_setup_needed():
    return db().execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        u = current_user()
        if not u or not u["active"]:
            return jsonify({"error": "Authentication required"}), 401
        if u["must_change_password"] and request.endpoint not in {"api_change_password", "logout"}:
            return jsonify({"error": "Password change required", "code": "PASSWORD_CHANGE_REQUIRED"}), 403
        return fn(*args, **kwargs)
    return wrapper


def page_login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        u = current_user()
        if not u or not u["active"]:
            return redirect(url_for("login"))
        if u["must_change_password"]:
            return redirect(url_for("change_password"))
        return fn(*args, **kwargs)
    return wrapper


@app.before_request
def protect_app():
    public = {"login", "setup", "logout", "static", "manifest"}
    if request.endpoint in public or request.endpoint is None:
        return None
    if is_setup_needed():
        if request.path.startswith("/api/"):
            return jsonify({"error": "Initial setup required", "setup": True}), 403
        return redirect(url_for("setup"))
    if request.path.startswith("/api/"):
        return None
    u = current_user()
    if not u or not u["active"]:
        return redirect(url_for("login"))
    if u["must_change_password"]:
        return redirect(url_for("change_password"))
    return None


@app.route("/setup", methods=["GET", "POST"])
def setup():
    if not is_setup_needed():
        return redirect(url_for("login"))
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm") or ""
        if len(username) < 3 or len(password) < 8:
            return render_template("setup.html", error="Username must be at least 3 characters and password at least 8 characters.")
        if password != confirm:
            return render_template("setup.html", error="Passwords do not match.")
        now = datetime.now().isoformat(timespec="seconds")
        conn = db()
        cur = conn.execute("INSERT INTO users(username,password,role,circuit,church_name,active,must_change_password,created_at) VALUES(?,?,?,?,?,?,?,?)",
                           (username, generate_password_hash(password), "Admin", "", "", 1, 0, now))
        conn.commit()
        session.clear(); session["user_id"] = cur.lastrowid
        audit("LOGIN_SETUP", "users", cur.lastrowid, "Initial diocesan administrator created")
        return redirect(url_for("home"))
    return render_template("setup.html", error="")


@app.route("/login", methods=["GET", "POST"])
def login():
    if is_setup_needed():
        return redirect(url_for("setup"))
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        u = db().execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        ok = False
        if u and u["active"]:
            try:
                ok = check_password_hash(u["password"], password)
            except ValueError:
                ok = secrets.compare_digest(u["password"], password)
                if ok:
                    db().execute("UPDATE users SET password=? WHERE id=?", (generate_password_hash(password), u["id"]))
                    db().commit()
        if ok:
            session.clear(); session["user_id"] = u["id"]
            audit("LOGIN", "users", u["id"], "Successful login")
            if u["must_change_password"]:
                return redirect(url_for("change_password"))
            return redirect(url_for("home"))
        return render_template("login.html", error="Invalid username or password.")
    return render_template("login.html", error="")


@app.get("/logout")
def logout():
    u = current_user()
    if u:
        audit("LOGOUT", "users", u["id"], "Logout")
    session.clear()
    return redirect(url_for("login"))


@app.route("/change-password", methods=["GET", "POST"])
@page_login_required
def change_password():
    if request.method == "POST":
        u = current_user()
        old = request.form.get("old_password") or ""
        new = request.form.get("new_password") or ""
        confirm = request.form.get("confirm") or ""
        if not check_password_hash(u["password"], old):
            return render_template("change_password.html", error="Current password is incorrect.")
        if len(new) < 8:
            return render_template("change_password.html", error="New password must be at least 8 characters.")
        if new != confirm:
            return render_template("change_password.html", error="New passwords do not match.")
        db().execute("UPDATE users SET password=?,must_change_password=0 WHERE id=?", (generate_password_hash(new), u["id"]))
        db().commit(); audit("PASSWORD_CHANGE", "users", u["id"], "Password changed")
        return redirect(url_for("home"))
    return render_template("change_password.html", error="")


@app.route("/")
@page_login_required
def home():
    return render_template("index.html")


def role_allows_table(u, table, method):
    role = u["role"]
    if role == "Admin": return True
    if role in {"Bishop / Diocesan Executive", "Auditor"}: return method == "GET"
    if role == "Evangelism Minister":
        if table in FINANCE_TABLES: return method == "GET"
        return (table in MISSION_TABLES or table in MEMBERSHIP_TABLES) and method in {"GET", "POST", "PUT", "DELETE"}
    if role == "Planting Officer":
        if table in FINANCE_TABLES:
            return False
        if table == "diocesan_reviews":
            return method == "GET"
        return (table in MISSION_TABLES or table in MEMBERSHIP_TABLES) and method in {"GET", "POST", "PUT", "DELETE"}

    if role == "Diocesan Secretary":
        if table in {"report_periods", "circuit_reports", "action_points", "meetings", "diocesan_reviews"}:
            return method in {"GET", "POST", "DELETE"}
        return method == "GET"
    if role == "Finance Officer":
        return table in FINANCE_TABLES and method in {"GET", "POST", "PUT", "DELETE"}
    if role == "Circuit Coordinator":
        if table == "report_periods": return method == "GET"
        if table == "circuit_reports": return method in {"GET", "POST", "DELETE"}
        if table in {"action_points", "meetings"}: return method in {"GET", "POST", "DELETE"}
        if table == "diocesan_reviews": return method == "GET"
        return (table in MISSION_TABLES or table in MEMBERSHIP_TABLES) and method in {"GET", "POST", "PUT", "DELETE"}
    if role == "Local Church Evangelism Officer":
        if table == "church_plants": return False
        if table in {"action_points", "meetings"}: return method in {"GET", "POST", "DELETE"}
        return (table in MISSION_TABLES or table in MEMBERSHIP_TABLES) and method in {"GET", "POST", "PUT", "DELETE"}
    return False


def scoped_rows(table, u):
    role = u["role"]
    circuit = u["circuit"]
    church = u["church_name"]
    circuit_tables = {"churches", "members", "outreach", "mission_calendar", "mission_teams", "mission_contacts", "testimonies", "appreciations", "circuit_reports", "action_points", "church_plants"}
    church_tables = {"churches", "members", "outreach", "mission_calendar", "mission_teams", "mission_contacts", "testimonies", "appreciations"}
    if role == "Circuit Coordinator" and circuit and table in circuit_tables:
        return rows(f"SELECT * FROM {table} WHERE circuit=? ORDER BY id DESC", (circuit,))
    if role == "Local Church Evangelism Officer" and circuit and table in church_tables:
        return rows(f"SELECT * FROM {table} WHERE circuit=? AND church_name=? ORDER BY id DESC", (circuit, church))
    if role == "Local Church Evangelism Officer" and circuit and table == "action_points":
        return rows("SELECT * FROM action_points WHERE circuit=? ORDER BY id DESC", (circuit,))
    return rows(f"SELECT * FROM {table} ORDER BY id DESC")



@app.get("/api/me")
@login_required
def api_me():
    u = current_user()
    return jsonify(dict(u))


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return request.host.split(":")[0]
    finally:
        s.close()


def get_connection_url():
    port = int(os.environ.get("PORT", "8080"))
    return f"http://{get_local_ip()}:{port}"


@app.get("/api/connection")
@login_required
def api_connection():
    return jsonify({
        "url": get_connection_url(),
        "ip": get_local_ip(),
        "port": int(os.environ.get("PORT", "8080"))
    })


@app.get("/api/qr")
@login_required
def api_qr():
    img = qrcode.make(get_connection_url(), image_factory=SvgPathImage)
    svg = io.BytesIO()
    img.save(svg)
    svg.seek(0)
    return send_file(svg, mimetype="image/svg+xml", max_age=0)



@app.get("/api/dashboard")
@login_required
def dashboard():
    u = current_user()
    conn = db()

    def count(table, where="", args=()):
        sql = f"SELECT COUNT(*) FROM {table}"
        if where:
            sql += " WHERE " + where
        return conn.execute(sql, args).fetchone()[0]

    def total(table, where="", args=()):
        sql = f"SELECT COALESCE(SUM(amount),0) FROM {table}"
        if where:
            sql += " WHERE " + where
        return conn.execute(sql, args).fetchone()[0] or 0

    def recent(table, columns, limit=5, order="id DESC"):
        return rows(
            f"SELECT {columns} FROM {table} ORDER BY {order} LIMIT {limit}"
        )

    finance_roles = {
        "Admin",
        "Finance Officer",
        "Auditor",
        "Evangelism Minister",
        "Bishop / Diocesan Executive"
    }
    finance_visible = u["role"] in finance_roles

    churches = count("churches")
    members = count("members")
    plants = count("church_plants")
    active_plants = count(
        "church_plants",
        "LOWER(COALESCE(status,'')) NOT IN ('completed','closed','cancelled')"
    )
    outreach_count = count("outreach")
    calendar_count = count("mission_calendar")
    testimonies_count = count("testimonies")
    appreciations_count = count("appreciations")

    income_total = total("income") if finance_visible else 0
    expense_total = total("expenses") if finance_visible else 0
    balance = income_total - expense_total

    trust_income = 0
    trust_expense = 0
    trust_balance = 0

    if finance_visible:
        trust_income = total(
            "trust_fund",
            "LOWER(COALESCE(transaction_type,'')) IN ('income','receipt','received','credit')"
        )
        trust_expense = total(
            "trust_fund",
            "LOWER(COALESCE(transaction_type,'')) IN ('expense','payment','paid','debit')"
        )
        trust_balance = trust_income - trust_expense

    pledges = total(
        "commitments",
        "LOWER(COALESCE(status,'')) NOT IN ('cancelled','completed')"
    ) if finance_visible else 0

    procurement_value = 0
    pending_procurement = 0
    planned_budget = (conn.execute("SELECT COALESCE(SUM(planned_amount),0) FROM mission_budgets").fetchone()[0] or 0) if finance_visible else 0
    spent_budget = expense_total

    if finance_visible:
        procurement_value = conn.execute(
            """
            SELECT COALESCE(SUM(
                COALESCE(quantity,1) * COALESCE(estimated_unit_cost,0)
            ),0)
            FROM procurement_requests
            """
        ).fetchone()[0] or 0

        pending_procurement = count(
            "procurement_requests",
            "LOWER(COALESCE(approval_status,'')) NOT IN ('approved','rejected','completed','cancelled')"
        )

    upcoming_missions = rows(
        """
        SELECT id,event_date,event_time,event_type,circuit,location,
               activity,mission_phase,responsible_person,status
        FROM mission_calendar
        WHERE COALESCE(status,'') NOT IN ('Completed','Cancelled')
        ORDER BY event_date ASC, event_time ASC, id ASC
        LIMIT 10
        """
    )

    overdue_followups = rows(
        """
        SELECT id,contact_name,phone,circuit,church_name,
               next_followup_date,status,followup_status,assigned_to
        FROM mission_contacts
        WHERE next_followup_date IS NOT NULL
          AND TRIM(next_followup_date) <> ''
          AND date(next_followup_date) < date('now')
          AND LOWER(COALESCE(followup_status,'')) NOT IN
              ('completed','closed','done')
        ORDER BY date(next_followup_date) ASC
        LIMIT 20
        """
    )

    contact_followups = count(
        "mission_contacts",
        "next_followup_date IS NOT NULL AND TRIM(next_followup_date) <> ''"
    )

    recent_contacts = recent(
        "mission_contacts",
        "id,contact_name,phone,circuit,church_name,mission_date,status,followup_status,next_followup_date",
        5
    )

    recent_income = (
        recent("income",
               "id,date,donor_name,source,fund,amount,method,reference",
               5)
        if finance_visible else []
    )

    recent_expenses = (
        recent("expenses",
               "id,date,category,description,circuit,amount,approved_by,paid_by",
               5)
        if finance_visible else []
    )

    recent_trust = (
        recent("trust_fund",
               "id,date,transaction_type,source_or_payee,purpose,amount,method,reference",
               5)
        if finance_visible else []
    )

    recent_testimonies = recent(
        "testimonies",
        "id,date,member_name,circuit,church_name,title,testimony,recorded_by",
        5
    )

    recent_appreciations = recent(
        "appreciations",
        "id,date,recipient,role_position,circuit,church_name,reason,message,recorded_by",
        5
    )

    plant_plan = rows(
        """
        SELECT year,
               COUNT(*) AS churches_planned,
               COALESCE(SUM(CASE
                   WHEN LOWER(COALESCE(status,'')) IN
                       ('completed','launched','active')
                   THEN 1 ELSE 0 END),0) AS churches_progress
        FROM church_plants
        GROUP BY year
        ORDER BY year ASC
        """
    )

    return jsonify({
        "churches": churches,
        "members": members,
        "plants": plants,
        "active_plants": active_plants,
        "outreach": outreach_count,
        "calendar": calendar_count,
        "testimonies": testimonies_count,
        "appreciations": appreciations_count,
        "income": income_total,
        "expenses": expense_total,
        "balance": balance,
        "trust_balance": trust_balance,
        "trust_income": trust_income,
        "trust_expense": trust_expense,
        "pledges": pledges,
        "recent_income": recent_income,
        "recent_expenses": recent_expenses,
        "recent_trust": recent_trust,
        "pending_procurement": pending_procurement,
        "procurement_value": procurement_value,
        "planned_budget": planned_budget,
        "spent_budget": spent_budget,
        "recent_testimonies": recent_testimonies,
        "recent_appreciations": recent_appreciations,
        "plant_plan": plant_plan,
        "upcoming_missions": upcoming_missions,
        "overdue_followups": overdue_followups,
        "contact_followups": contact_followups,
        "recent_contacts": recent_contacts,
        "finance_visible": finance_visible
    })


@app.get("/api/<table>")
@login_required
def get_table(table):
    u = current_user()
    if table not in TABLES or not role_allows_table(u, table, "GET"):
        return jsonify({"error":"You do not have permission to view this section."}),403
    return jsonify(scoped_rows(table, u))


def generate_member_id(data):
    position = (data.get("role_position") or "Other").strip()
    codes = {
        "Bishop": "BP", "Lay President": "LP", "Evangelism Minister": "EM",
        "Circuit Presbyter": "CP", "Circuit Steward": "CS",
        "Local Church Minister": "LCM", "Local Church Steward": "LCS", "Other": "OTH"
    }
    code = codes.get(position, "OTH")
    circuit = (data.get("circuit") or "").replace(" Circuit", "")
    circuit_code = {"Effurun":"EFF", "Warri":"WAR", "Sapele":"SAP", "Steel Town":"ST"}.get(circuit, "DS")
    prefix = f"DSD-{code}" if position in {"Bishop", "Lay President", "Evangelism Minister", "Other"} else f"DSD-{code}-{circuit_code}"
    existing = db().execute("SELECT member_id FROM members WHERE member_id LIKE ?", (prefix + "-%",)).fetchall()
    numbers = []
    for row in existing:
        try: numbers.append(int(str(row[0]).rsplit("-", 1)[1]))
        except (ValueError, IndexError): pass
    n = (max(numbers) + 1) if numbers else 1
    return f"{prefix}-{n:04d}"


@app.post("/api/<table>")
@login_required
def create_row(table):
    u = current_user()
    if table not in TABLES or not role_allows_table(u, table, "POST"):
        return jsonify({"error":"You do not have permission to add records here."}),403
    data = request.get_json(force=True) or {}
    cols = [c for c in TABLES[table] if c in data]
    required = {"members":["circuit","church_name","full_name"],"churches":["circuit","church_name"],"commitments":["donor_name"],"income":["date","amount"],
      "expenses":["date","category","description","amount"],"equipment":["item"],"trust_fund":["date","transaction_type","amount"],"mission_budgets":["year","budget_name"],"procurement_requests":["request_date","item"],"church_plants":["year","location"],"planting_prospects":["prospect_id","location"],
      "outreach":["date","location"],"mission_calendar":["event_date","location"],"sponsors":["name"],
      "testimonies":["date","testimony"],
      "appreciations":["date","recipient","message"],
      "report_periods":["period_name","start_date","end_date"],
      "circuit_reports":["circuit"],
      "action_points":["action_item"],
      "meetings":["meeting_date"],
      "diocesan_reviews":["review_date","executive_summary"],
      "mission_teams":["team_name"],
      "mission_contacts":["contact_name"]}[table]
    missing = [c for c in required if not data.get(c) and data.get(c) != 0]
    if missing: return jsonify({"error":"Required: "+", ".join(missing)}),400
    if u["role"] in {"Circuit Coordinator", "Local Church Evangelism Officer"} and data.get("circuit") and u["circuit"] and data["circuit"] != u["circuit"]:
        return jsonify({"error":"You can only create records for your assigned circuit."}),403
    if table == "members":
        if u["role"] == "Local Church Evangelism Officer" and data.get("church_name") != u["church_name"]:
            return jsonify({"error":"You can only create members for your assigned church."}),403
        # The ID is always generated by the server; users never type it.
        data["member_id"] = generate_member_id(data)
        data["created_at"] = datetime.now().isoformat(timespec="seconds")

        circuit = (data.get("circuit") or "").strip()
        church_name = (data.get("church_name") or "").strip()
        # Diocesan officers are attached to the virtual Diocesan Office.
        # It is intentionally not stored in the 17 local-church registry.
        if circuit == "Diocesan":
            if church_name not in {"", "Diocesan Office"}:
                return jsonify({"error":"For a Diocesan officer, Local Church must be Diocesan Office."}),400
            data["church_name"] = "Diocesan Office"
        elif circuit and church_name:
            church = db().execute("SELECT id FROM churches WHERE circuit=? AND church_name=?", (circuit,church_name)).fetchone()
            if not church:
                return jsonify({"error":"The selected Local Church does not belong to the selected Circuit."}),400
    if table == "report_periods":
        data["created_at"] = datetime.now().isoformat(timespec="seconds")
    if table == "circuit_reports":
        data["submitted_by"] = u["username"]
        data["submitted_at"] = datetime.now().isoformat(timespec="seconds")
        data["status"] = "Submitted"
    if table == "action_points":
        data["created_by"] = u["username"]
        data["created_at"] = datetime.now().isoformat(timespec="seconds")
    if table == "meetings":
        data["created_by"] = u["username"]
        data["created_at"] = datetime.now().isoformat(timespec="seconds")
    if table == "diocesan_reviews":
        data["prepared_by"] = u["username"]
    if table in {"testimonies", "appreciations"}:
        data["recorded_by"] = u["username"]
        data["created_at"] = datetime.now().isoformat(timespec="seconds")
    if table in {"mission_calendar", "mission_teams", "mission_contacts"}:
        data["created_at"] = datetime.now().isoformat(timespec="seconds")
        if table in {"mission_teams", "mission_contacts"} and data.get("circuit") == "Diocesan":
            data["church_name"] = "Diocesan Office"
        if data.get("church_plant_id"):
            try: data["church_plant_id"] = int(data["church_plant_id"])
            except (TypeError, ValueError): data["church_plant_id"] = None
    cols = [c for c in TABLES[table] if c in data]
    if not cols: return jsonify({"error":"No recognized fields"}),400
    sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join(['?']*len(cols))})"
    try:
        cur = db().execute(sql, [data.get(c) for c in cols])
        db().commit()
    except sqlite3.IntegrityError as e:
        db().rollback()
        return jsonify({"error":"Could not save record: " + str(e)}),400
    except sqlite3.Error as e:
        db().rollback()
        return jsonify({"error":"Database error while saving: " + str(e)}),500
    # A logging failure must never turn a successful registration into a
    # misleading "Request failed" response.
    try:
        audit("CREATE",table,cur.lastrowid,json.dumps({k:data.get(k) for k in cols},ensure_ascii=False))
    except Exception:
        pass
    return jsonify({"id":cur.lastrowid,"member_id":data.get("member_id",""),"ok":True}),201



@app.post("/api/planting_prospects/<int:rid>/convert-to-church-plant")
@login_required
def convert_planting_prospect(rid):
    u = current_user()

    # Conversion creates a church-plant record, so the user must have
    # permission to create both prospect and church-plant records.
    if not role_allows_table(u, "planting_prospects", "GET") or not role_allows_table(u, "church_plants", "POST"):
        return jsonify({"error": "You do not have permission to convert planting prospects into church plants."}), 403

    conn = db()

    prospect = conn.execute(
        "SELECT * FROM planting_prospects WHERE id=?",
        (rid,)
    ).fetchone()

    if not prospect:
        return jsonify({"error": "Planting prospect not found."}), 404

    # Respect circuit assignment.
    if (
        u["role"] in {"Circuit Coordinator", "Local Church Evangelism Officer"}
        and prospect["circuit"]
        and u["circuit"]
        and prospect["circuit"] != u["circuit"]
    ):
        return jsonify({"error": "You can only convert prospects in your assigned circuit."}), 403

    if prospect["status"] == "Converted to Church Plant":
        return jsonify({"error": "This prospect has already been converted to a church plant."}), 400

    if prospect["status"] == "Closed":
        return jsonify({"error": "A closed prospect cannot be converted. Reopen it first."}), 400

    data = request.get_json(silent=True) or {}

    planting_year = data.get("year") or prospect["proposed_planting_year"] or prospect["year"]
    try:
        planting_year = int(planting_year)
    except (TypeError, ValueError):
        planting_year = datetime.now().year

    location = (prospect["location"] or "").strip()
    proposed_name = (prospect["proposed_church_name"] or "").strip()
    leader = (prospect["responsible_officer"] or "").strip()
    circuit = (prospect["circuit"] or "").strip()
    notes = (prospect["notes"] or "").strip()

    if not location:
        return jsonify({"error": "The prospect must have a proposed location before conversion."}), 400

    axis = proposed_name or location

    # Optional values supplied by the conversion dialog.
    phase = (data.get("phase") or "Surveying").strip()
    status = (data.get("status") or "Planned").strip()
    budget = data.get("budget", 0) or 0
    start_date = (data.get("start_date") or "").strip()
    launch_date = (data.get("launch_date") or "").strip()
    next_followup_date = (data.get("next_followup_date") or "").strip()
    followup_end_date = (data.get("followup_end_date") or "").strip()

    try:
        budget = float(budget)
    except (TypeError, ValueError):
        return jsonify({"error": "Budget must be a valid number."}), 400

    try:
        cur = conn.execute(
            """
            INSERT INTO church_plants
            (year, circuit, axis, location, phase, status, budget, leader,
             start_date, launch_date, next_followup_date, followup_end_date,
             members, notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                planting_year,
                circuit,
                axis,
                location,
                phase,
                status,
                budget,
                leader,
                start_date,
                launch_date,
                next_followup_date,
                followup_end_date,
                0,
                notes
            )
        )

        plant_id = cur.lastrowid

        conn.execute(
            """
            UPDATE planting_prospects
            SET status='Converted to Church Plant',
                evangelism_status='Follow-up',
                outreach_status='Follow-up'
            WHERE id=?
            """,
            (rid,)
        )

        conn.commit()

        try:
            audit(
                "CONVERT_PROSPECT_TO_CHURCH_PLANT",
                "planting_prospects",
                rid,
                json.dumps({
                    "prospect_id": prospect["prospect_id"],
                    "church_plant_id": plant_id,
                    "location": location,
                    "circuit": circuit,
                    "planting_year": planting_year
                }, ensure_ascii=False)
            )
        except Exception:
            pass

        return jsonify({
            "ok": True,
            "prospect_id": rid,
            "church_plant_id": plant_id,
            "location": location,
            "planting_year": planting_year
        }), 201

    except sqlite3.IntegrityError as e:
        conn.rollback()
        return jsonify({"error": "Could not convert prospect: " + str(e)}), 400
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({"error": "Database error during conversion: " + str(e)}), 500

@app.post("/api/churches/<int:rid>/upgrade-to-circuit")
@login_required
def upgrade_church_to_circuit(rid):
    u = current_user()
    if u["role"] != "Admin":
        return jsonify({"error": "Administrator access required."}), 403
    church = db().execute("SELECT * FROM churches WHERE id=?", (rid,)).fetchone()
    if not church:
        return jsonify({"error": "Church not found."}), 404
    if church["church_status"] == "Circuit Headquarters" or church["is_circuit_headquarters"]:
        return jsonify({"error": "This church is already a circuit headquarters."}), 400
    data = request.get_json(silent=True) or {}
    circuit_name = (data.get("circuit_name") or "").strip()
    if len(circuit_name) < 3:
        return jsonify({"error": "Enter the new circuit name."}), 400
    if not circuit_name.lower().endswith("circuit"):
        circuit_name += " Circuit"
    existing = db().execute("SELECT id FROM circuits WHERE lower(name)=lower(?)", (circuit_name,)).fetchone()
    if existing:
        return jsonify({"error": "That circuit already exists. Choose a different circuit name."}), 400
    now = datetime.now().isoformat(timespec="seconds")
    try:
        conn = db()
        conn.execute("INSERT INTO circuits(name,headquarters_church_id,status,created_at,notes) VALUES(?,?,?,?,?)",
                     (circuit_name, rid, "Active", now, "Created by upgrading an existing local church to circuit headquarters"))
        conn.execute("UPDATE churches SET circuit=?, church_status='Circuit Headquarters', is_circuit_headquarters=1, upgraded_at=? WHERE id=?",
                     (circuit_name, now, rid))
        conn.commit()
        audit("UPGRADE_TO_CIRCUIT", "churches", rid, json.dumps({"church_name": church["church_name"], "new_circuit": circuit_name}, ensure_ascii=False))
        return jsonify({"ok": True, "circuit_name": circuit_name, "church_id": rid})
    except sqlite3.IntegrityError as e:
        conn.rollback()
        return jsonify({"error": "Could not create the new circuit: " + str(e)}), 400


@app.get("/api/circuits")
@login_required
def get_circuits():
    return jsonify(rows("SELECT id,name,headquarters_church_id,status,created_at,notes FROM circuits ORDER BY name"))

@app.get("/api/membership/churches")
@login_required
def membership_churches():
    u = current_user()
    if u["role"] == "Circuit Coordinator" and u["circuit"]:
        return jsonify(rows("SELECT circuit,church_name FROM churches WHERE circuit=? ORDER BY church_name", (u["circuit"],)))
    if u["role"] == "Local Church Evangelism Officer" and u["church_name"]:
        return jsonify(rows("SELECT circuit,church_name FROM churches WHERE church_name=? ORDER BY church_name", (u["church_name"],)))
    return jsonify(rows("SELECT circuit,church_name FROM churches ORDER BY circuit,church_name"))


@app.delete("/api/churches/<int:rid>/circuit-status")
@login_required
def remove_circuit_status(rid):
    u = current_user()
    if u["role"] != "Admin":
        return jsonify({"error": "Administrator access required."}), 403
    church = db().execute("SELECT * FROM churches WHERE id=?", (rid,)).fetchone()
    if not church or not church["is_circuit_headquarters"]:
        return jsonify({"error": "This church is not a circuit headquarters."}), 400
    circuit = db().execute("SELECT * FROM circuits WHERE headquarters_church_id=?", (rid,)).fetchone()
    conn = db()
    conn.execute("UPDATE churches SET church_status='Local Church', is_circuit_headquarters=0, upgraded_at='' WHERE id=?", (rid,))
    if circuit:
        conn.execute("UPDATE circuits SET status='Inactive', headquarters_church_id=NULL WHERE id=?", (circuit["id"],))
    conn.commit()
    audit("REMOVE_CIRCUIT_STATUS", "churches", rid, json.dumps({"circuit": circuit["name"] if circuit else church["circuit"]}, ensure_ascii=False))
    return jsonify({"ok": True})


@app.get("/api/<table>/<int:rid>")
@login_required
def get_row(table, rid):
    u = current_user()
    if table not in TABLES or not role_allows_table(u, table, "GET"):
        return jsonify({"error":"You do not have permission to view this section."}),403
    existing = db().execute(f"SELECT * FROM {table} WHERE id=?", (rid,)).fetchone()
    if not existing:
        return jsonify({"error":"Record not found"}),404
    if u["role"] == "Circuit Coordinator" and "circuit" in existing.keys() and u["circuit"] and existing["circuit"] != u["circuit"]:
        return jsonify({"error":"You can only view records for your assigned circuit."}),403
    if u["role"] == "Local Church Evangelism Officer" and table == "churches" and u["church_name"] and existing["church_name"] != u["church_name"]:
        return jsonify({"error":"You can only view your assigned church record."}),403
    return jsonify(dict(existing))

@app.put("/api/<table>/<int:rid>")
@login_required
def update_row(table, rid):
    u = current_user()
    if table not in TABLES or not role_allows_table(u, table, "PUT"):
        return jsonify({"error":"You do not have permission to edit records here."}),403
    existing = db().execute(f"SELECT * FROM {table} WHERE id=?", (rid,)).fetchone()
    if not existing:
        return jsonify({"error":"Record not found"}),404
    if u["role"] == "Circuit Coordinator" and "circuit" in existing.keys() and u["circuit"] and existing["circuit"] != u["circuit"]:
        return jsonify({"error":"You can only edit records for your assigned circuit."}),403
    if u["role"] == "Local Church Evangelism Officer" and table == "churches" and u["church_name"] and existing["church_name"] != u["church_name"]:
        return jsonify({"error":"You can only edit your assigned church record."}),403
    data = request.get_json(force=True) or {}
    cols = [c for c in TABLES[table] if c != "id" and c in data]
    if not cols:
        return jsonify({"error":"No recognized fields"}),400
    if "circuit" in data and data.get("circuit") and u["role"] in {"Circuit Coordinator", "Local Church Evangelism Officer"} and u["circuit"] and data["circuit"] != u["circuit"]:
        return jsonify({"error":"You can only edit records for your assigned circuit."}),403
    if table == "members" and u["role"] == "Local Church Evangelism Officer" and data.get("church_name") and data.get("church_name") != u["church_name"]:
        return jsonify({"error":"You can only edit members for your assigned church."}),403
    sets = ",".join(f"{c}=?" for c in cols)
    try:
        db().execute(f"UPDATE {table} SET {sets} WHERE id=?", [data.get(c) for c in cols] + [rid])
        db().commit()
        try:
            audit("UPDATE", table, rid, json.dumps({k:data.get(k) for k in cols}, ensure_ascii=False))
        except Exception:
            pass
    except sqlite3.IntegrityError as e:
        db().rollback()
        return jsonify({"error":"Could not update record: " + str(e)}),400
    except sqlite3.Error as e:
        db().rollback()
        return jsonify({"error":"Database error while updating: " + str(e)}),500
    updated = db().execute(f"SELECT * FROM {table} WHERE id=?", (rid,)).fetchone()
    return jsonify(dict(updated))

@app.delete("/api/<table>/<int:rid>")
@login_required
def delete_row(table,rid):
    u = current_user()
    if table not in TABLES or not role_allows_table(u, table, "DELETE"):
        return jsonify({"error":"You do not have permission to delete records here."}),403
    existing = db().execute(f"SELECT * FROM {table} WHERE id=?", (rid,)).fetchone()
    if not existing: return jsonify({"error":"Record not found"}),404
    if u["role"] == "Circuit Coordinator" and "circuit" in existing.keys() and u["circuit"] and existing["circuit"] != u["circuit"]:
        return jsonify({"error":"You can only delete records for your assigned circuit."}),403
    if u["role"] == "Local Church Evangelism Officer" and table == "churches" and u["church_name"] and existing["church_name"] != u["church_name"]:
        return jsonify({"error":"You can only delete your assigned church record."}),403
    db().execute(f"DELETE FROM {table} WHERE id=?",(rid,)); db().commit(); audit("DELETE",table,rid,"")
    return jsonify({"ok":True})


@app.get("/api/users")
@login_required
def get_users():
    u = current_user()
    if u["role"] != "Admin": return jsonify({"error":"Administrator access required."}),403
    return jsonify(rows("SELECT id,username,role,circuit,church_name,active,must_change_password,created_at FROM users ORDER BY username"))


@app.post("/api/users")
@login_required
def create_user():
    u = current_user()
    if u["role"] != "Admin": return jsonify({"error":"Administrator access required."}),403
    data = request.get_json(force=True) or {}
    username = (data.get("username") or "").strip(); password = data.get("password") or ""; role = data.get("role") or "Auditor"
    circuit = (data.get("circuit") or "").strip(); church_name = (data.get("church_name") or "").strip()
    if len(username) < 3 or len(password) < 8: return jsonify({"error":"Username must be at least 3 characters and password at least 8 characters."}),400
    if role not in ROLES: return jsonify({"error":"Invalid role."}),400
    assignment_error = validate_user_assignment(role, circuit, church_name)
    if assignment_error: return jsonify({"error":assignment_error}),400
    try:
        cur = db().execute("INSERT INTO users(username,password,role,circuit,church_name,active,must_change_password,created_at) VALUES(?,?,?,?,?,?,?,?)",
                           (username,generate_password_hash(password),role,circuit,church_name,1,1,datetime.now().isoformat(timespec="seconds")))
        db().commit(); audit("CREATE", "users", cur.lastrowid, json.dumps({"username":username,"role":role}))
        return jsonify({"id":cur.lastrowid,"ok":True}),201
    except sqlite3.IntegrityError:
        return jsonify({"error":"That username already exists."}),400


@app.put("/api/users/<int:uid>")
@login_required
def update_user(uid):
    u = current_user()
    if u["role"] != "Admin": return jsonify({"error":"Administrator access required."}),403
    target = db().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if not target: return jsonify({"error":"User not found."}),404
    data = request.get_json(force=True) or {}
    role = data.get("role", target["role"]) or "Auditor"
    circuit = (data.get("circuit", target["circuit"]) or "").strip()
    church_name = (data.get("church_name", target["church_name"]) or "").strip()
    if role not in ROLES: return jsonify({"error":"Invalid role."}),400
    assignment_error = validate_user_assignment(role, circuit, church_name)
    if assignment_error: return jsonify({"error":assignment_error}),400
    db().execute("UPDATE users SET role=?,circuit=?,church_name=? WHERE id=?", (role,circuit,church_name,uid))
    db().commit(); audit("USER_ASSIGNMENT_UPDATED","users",uid,json.dumps({"role":role,"circuit":circuit,"church_name":church_name}))
    return jsonify({"ok":True})


@app.delete("/api/users/<int:uid>")
@login_required
def delete_user(uid):
    u = current_user()
    if u["role"] != "Admin": return jsonify({"error":"Administrator access required."}),403
    if uid == u["id"]: return jsonify({"error":"You cannot delete your own account."}),400
    target = db().execute("SELECT id,username FROM users WHERE id=?",(uid,)).fetchone()
    if not target: return jsonify({"error":"User not found"}),404
    db().execute("DELETE FROM users WHERE id=?",(uid,)); db().commit(); audit("DELETE","users",uid,"User removed")
    return jsonify({"ok":True})


@app.get("/api/audit")
@login_required
def audit_list():
    u = current_user()
    if u["role"] not in {"Admin", "Auditor"}: return jsonify({"error":"Administrator or Auditor access required."}),403
    return jsonify(rows("SELECT id,happened_at,action,table_name,record_id,details,username FROM audit_log ORDER BY id DESC LIMIT 500"))


@app.get("/api/reports")
@login_required
def reports():
    u = current_user(); conn = db()
    try: year = int(request.args.get("year", datetime.now().year))
    except: year = datetime.now().year
    circuit = (request.args.get("circuit") or "All").strip()
    scope = "" if circuit in ("", "All", "Diocesan") else circuit
    def count(table, where="", args=()):
        q=f"SELECT COUNT(*) FROM {table}" + (" WHERE "+where if where else "")
        return conn.execute(q,args).fetchone()[0]
    def sumv(table, col, where="", args=()):
        q=f"SELECT COALESCE(SUM({col}),0) FROM {table}" + (" WHERE "+where if where else "")
        return conn.execute(q,args).fetchone()[0]
    if scope:
        member_where="circuit=? AND death!='Yes'"; mw=(scope,)
        church_where="circuit=?"; cw=(scope,)
        plant_where="year=? AND circuit=?"; pw=(year,scope)
        outreach_where="strftime('%Y',date)=? AND circuit=?"; ow=(str(year),scope)
        contact_where="circuit=?"; ct=(scope,)
        calendar_where="strftime('%Y',event_date)=? AND circuit=?"; cal=(str(year),scope)
    else:
        member_where="death!='Yes'"; mw=()
        church_where="1=1"; cw=()
        plant_where="year=?"; pw=(year,)
        outreach_where="strftime('%Y',date)=?"; ow=(str(year),)
        contact_where="1=1"; ct=()
        calendar_where="strftime('%Y',event_date)=?"; cal=(str(year),)
    members=count("members",member_where,mw); churches=count("churches",church_where,cw)
    plants=count("church_plants",plant_where,pw); launched=count("church_plants",plant_where+" AND status IN ('Launched','Growing','Active')",pw)
    outreach=count("outreach",outreach_where,ow); attendance=sumv("outreach","attendance",outreach_where,ow); decisions=sumv("outreach","decisions",outreach_where,ow); followups=sumv("outreach","followups",outreach_where,ow); outreach_cost=sumv("outreach","cost",outreach_where,ow)
    contacts=count("mission_contacts",contact_where,ct); due=count("mission_contacts",contact_where+" AND next_followup_date<>'' AND next_followup_date<=? AND followup_status NOT IN ('Completed','Closed')",ct+(datetime.now().date().isoformat(),)); joined=count("mission_contacts",contact_where+" AND status='Joined Local Church'",ct); converts=count("mission_contacts",contact_where+" AND status IN ('New Convert','Under Discipleship','Ready for Church','Joined Local Church')",ct)
    calendar=count("mission_calendar",calendar_where,cal); completed=count("mission_calendar",calendar_where+" AND status='Completed'",cal)
    finance_visible=u["role"] in {"Admin","Finance Officer","Auditor"}
    finance={}
    if finance_visible:
        if scope:
            income=sumv("income","amount","date LIKE ? AND EXISTS (SELECT 1 FROM churches c WHERE c.circuit=? AND c.church_name=income.donor_name)",(f"{year}%",scope))
            expenses=sumv("expenses","amount","date LIKE ? AND circuit=?",(f"{year}%",scope))
        else:
            income=sumv("income","amount","date LIKE ?",(f"{year}%",)); expenses=sumv("expenses","amount","date LIKE ?",(f"{year}%",))
        trust_income=sumv("trust_fund","amount","date LIKE ? AND transaction_type='Income'",(f"{year}%",)); trust_expense=sumv("trust_fund","amount","date LIKE ? AND transaction_type='Expense'",(f"{year}%",))
        budget=sumv("mission_budgets","planned_amount","year=?"+(" AND circuit=?" if scope else ""), (year,scope) if scope else (year,)); spent=sumv("mission_budgets","spent_amount","year=?"+(" AND circuit=?" if scope else ""), (year,scope) if scope else (year,))
        procurement=sumv("procurement_requests","quantity*estimated_unit_cost","needed_by LIKE ? AND approval_status IN ('Pending','Approved')",(f"{year}%",))
        finance={"income":income,"expenses":expenses,"balance":income-expenses,"trust_income":trust_income,"trust_expense":trust_expense,"trust_balance":trust_income-trust_expense,"planned_budget":budget,"spent_budget":spent,"procurement_pipeline":procurement}
    circuit_rows=[]
    circuits=[scope] if scope else ["Effurun Circuit","Warri Circuit","Sapele Circuit","Steel Town Circuit"]
    for c in circuits:
        m=count("members","circuit=? AND death!='Yes'",(c,)); p=count("church_plants","year=? AND circuit=?",(year,c)); l=count("church_plants","year=? AND circuit=? AND status IN ('Launched','Growing','Active')",(year,c)); o=count("outreach","strftime('%Y',date)=? AND circuit=?",(str(year),c)); d=sumv("outreach","decisions","strftime('%Y',date)=? AND circuit=?",(str(year),c)); cc=count("mission_contacts","circuit=? AND status='Joined Local Church'",(c,)); circuit_rows.append({"circuit":c,"members":m,"plants":p,"launched":l,"outreach":o,"decisions":d,"joined":cc})
    fellow_rows=[]
    for r in rows("SELECT fellowship,COUNT(*) count FROM members WHERE death!='Yes'"+((" AND circuit=?") if scope else "")+" GROUP BY fellowship ORDER BY count DESC", (scope,) if scope else ()):
        fellow_rows.append(r)
    years=[]
    for yr in range(year,year+5):
        planned=count("church_plants","year=?"+((" AND circuit=?") if scope else ""),(yr,scope) if scope else (yr,)); launched_y=count("church_plants","year=? AND status IN ('Launched','Growing','Active')"+((" AND circuit=?") if scope else ""),(yr,scope) if scope else (yr,)); years.append({"year":yr,"target":5,"planned":planned,"launched":launched_y,"remaining":max(0,5-planned)})
    return jsonify({"year":year,"circuit":circuit or "All","finance_visible":finance_visible,"summary":{"members":members,"churches":churches,"plants":plants,"launched_plants":launched,"outreach":outreach,"attendance":attendance,"decisions":decisions,"followups":followups,"outreach_cost":outreach_cost,"contacts":contacts,"converts":converts,"joined":joined,"followups_due":due,"calendar":calendar,"calendar_completed":completed},"finance":finance,"circuits":circuit_rows,"fellowships":fellow_rows,"five_year":years})

@app.post("/api/circuit_reports/<int:report_id>/review")
@login_required
def review_circuit_report(report_id):
    u=current_user()
    if u["role"] != "Admin":
        return jsonify({"error":"Only an Administrator can approve or return a circuit report."}),403
    data=request.get_json(force=True) or {}
    status=(data.get("status") or "Approved").strip()
    if status not in {"Approved","Returned","Submitted"}:
        return jsonify({"error":"Status must be Approved, Returned or Submitted."}),400
    note=data.get("review_note") or ""
    cur=db().execute("UPDATE circuit_reports SET status=?,reviewed_by=?,reviewed_at=?,review_note=? WHERE id=?",(status,u["username"],datetime.now().isoformat(timespec="seconds"),note,report_id))
    if not cur.rowcount:
        return jsonify({"error":"Circuit report not found."}),404
    db().commit(); audit("REVIEW", "circuit_reports", report_id, f"Report {status}: {note}")
    return jsonify({"ok":True,"status":status})

@app.get("/api/admin/reporting-summary")
@login_required
def reporting_summary():
    u=current_user()
    if u["role"] not in {"Admin","Auditor","Circuit Coordinator","Evangelism Minister","Diocesan Secretary","Bishop / Diocesan Executive"}: return jsonify({"error":"Reporting access required."}),403
    periods=rows("SELECT * FROM report_periods ORDER BY start_date DESC,id DESC LIMIT 12")
    reports=rows("SELECT status,COUNT(*) count FROM circuit_reports GROUP BY status")
    actions=rows("SELECT status,COUNT(*) count FROM action_points GROUP BY status")
    meetings=db().execute("SELECT COUNT(*) FROM meetings").fetchone()[0]
    return jsonify({"periods":periods,"report_status":reports,"action_status":actions,"meetings":meetings})

@app.get("/api/reports/export")
@login_required
def export_report():
    u=current_user()
    if u["role"] not in {"Admin","Finance Officer","Auditor","Evangelism Minister","Bishop / Diocesan Executive"}: return jsonify({"error":"Report export access required."}),403
    data=reports().get_json(); out=Workbook(); ws=out.active; ws.title="Executive Summary"; ws.append(["MCN Delta South Diocese Evangelism Report"]); ws.append(["Year",data["year"]]); ws.append(["Circuit",data["circuit"]]); ws.append([]); ws.append(["Metric","Value"])
    for k,v in data["summary"].items(): ws.append([k,v])
    if data["finance_visible"]:
        ws=out.create_sheet("Finance"); ws.append(["Metric","Value"])
        for k,v in data["finance"].items(): ws.append([k,v])
    ws=out.create_sheet("Circuit Performance"); ws.append(list(data["circuits"][0].keys()) if data["circuits"] else ["circuit"])
    for r in data["circuits"]: ws.append(list(r.values()))
    ws=out.create_sheet("Fellowships"); ws.append(["fellowship","count"])
    for r in data["fellowships"]: ws.append([r.get("fellowship"),r.get("count")])
    ws=out.create_sheet("5 Year Roadmap"); ws.append(["year","target","planned","launched","remaining"])
    for r in data["five_year"]: ws.append(list(r.values()))
    for sheet in out.worksheets: sheet.freeze_panes="A2"; sheet.column_dimensions['A'].width=28
    buf=io.BytesIO(); out.save(buf); buf.seek(0)
    return send_file(buf,as_attachment=True,download_name=f"MCN_Delta_South_Evangelism_Report_{data['year']}.xlsx",mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.get("/api/export")
@login_required
def export_xlsx():
    u = current_user()
    if u["role"] not in {"Admin", "Finance Officer", "Auditor"}: return jsonify({"error":"Finance reporting access required."}),403
    out = Workbook(); out.remove(out.active)
    for table, cols in TABLES.items():
        ws = out.create_sheet(table[:31]); allcols = ["id"] + cols; ws.append(allcols)
        for r in rows(f"SELECT {','.join(allcols)} FROM {table} ORDER BY id"): ws.append([r.get(c) for c in allcols])
        ws.freeze_panes = "A2"; ws.auto_filter.ref = ws.dimensions
    ws = out.create_sheet("Summary"); d = dashboard().get_json(); ws.append(["Metric","Value"])
    for k in ["churches","income","expenses","balance","pledges","plants","active_plants"]: ws.append([k,d[k]])
    buf=io.BytesIO(); out.save(buf); buf.seek(0)
    return send_file(buf,as_attachment=True,download_name="MCN_Delta_South_Evangelism_Export.xlsx",mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


BACKUP_DIR = os.path.join(ROOT, "data", "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)

def security_allowed(roles={"Admin"}):
    u=current_user()
    return u and u["role"] in roles

def make_backup(kind="Manual"):
    u=current_user()
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    filename=f"mcn-delta-south-evangelism-{stamp}.sqlite"
    path=os.path.join(BACKUP_DIR, filename)
    src=sqlite3.connect(DB_PATH)
    try:
        src.execute("PRAGMA wal_checkpoint(FULL)")
    except Exception:
        pass
    dest=sqlite3.connect(path)
    try:
        src.backup(dest)
    finally:
        dest.close(); src.close()
    data=open(path,"rb").read(); digest=hashlib.sha256(data).hexdigest()
    conn=db(); conn.execute("INSERT INTO backup_history(created_at,created_by,filename,size_bytes,sha256,backup_type,status) VALUES(?,?,?,?,?,?,?)",
        (datetime.now().isoformat(timespec="seconds"),u["username"] if u else "system",filename,len(data),digest,kind,"Ready")); conn.commit()
    audit("BACKUP_CREATED","backup_history",None,f"{filename} · {len(data)} bytes · {digest[:12]}")
    return path,filename,digest

@app.get("/api/backup")
@login_required
def backup():
    u = current_user()
    if u["role"] not in {"Admin", "Auditor"}: return jsonify({"error":"Administrator or Auditor access required."}),403
    path,filename,_=make_backup("Manual Download")
    return send_file(path,as_attachment=True,download_name=filename,mimetype="application/octet-stream")

@app.post("/api/security/backup")
@login_required
def create_security_backup():
    if not security_allowed(): return jsonify({"error":"Administrator access required."}),403
    path,filename,digest=make_backup("Manual")
    return jsonify({"success":True,"filename":filename,"sha256":digest,"size_bytes":os.path.getsize(path)})

@app.get("/api/security/backups")
@login_required
def backup_history():
    if not security_allowed({"Admin","Auditor"}): return jsonify({"error":"Administrator or Auditor access required."}),403
    return jsonify(rows("SELECT id,created_at,created_by,filename,size_bytes,sha256,backup_type,status FROM backup_history ORDER BY id DESC LIMIT 100"))

@app.get("/api/security/status")
@login_required
def security_status():
    u=current_user()
    if u["role"] not in {"Admin","Auditor"}: return jsonify({"error":"Administrator or Auditor access required."}),403
    integrity=db().execute("PRAGMA integrity_check").fetchone()[0]
    users=db().execute("SELECT COUNT(*) FROM users").fetchone()[0]
    inactive=db().execute("SELECT COUNT(*) FROM users WHERE active=0").fetchone()[0]
    forced=db().execute("SELECT COUNT(*) FROM users WHERE must_change_password=1").fetchone()[0]
    audit_count=db().execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
    backups=db().execute("SELECT COUNT(*) FROM backup_history").fetchone()[0]
    latest=db().execute("SELECT created_at,created_by,filename,sha256 FROM backup_history ORDER BY id DESC LIMIT 1").fetchone()
    return jsonify({"integrity":integrity,"users":users,"inactive_users":inactive,"password_change_required":forced,"audit_entries":audit_count,"backups":backups,"latest_backup":dict(latest) if latest else None})

@app.post("/api/security/users/<int:uid>/toggle")
@login_required
def toggle_user(uid):
    if not security_allowed(): return jsonify({"error":"Administrator access required."}),403
    u=current_user()
    if uid==u["id"]: return jsonify({"error":"You cannot deactivate your own account."}),400
    target=db().execute("SELECT id,username,active FROM users WHERE id=?",(uid,)).fetchone()
    if not target: return jsonify({"error":"User not found."}),404
    new=0 if target["active"] else 1
    db().execute("UPDATE users SET active=? WHERE id=?",(new,uid)); db().commit()
    audit("USER_ACTIVATED" if new else "USER_DEACTIVATED","users",uid,target["username"])
    return jsonify({"success":True,"active":bool(new)})

@app.post("/api/security/restore/<int:bid>")
@login_required
def restore_backup(bid):
    if not security_allowed(): return jsonify({"error":"Administrator access required."}),403
    rec=db().execute("SELECT * FROM backup_history WHERE id=?",(bid,)).fetchone()
    if not rec: return jsonify({"error":"Backup not found."}),404
    path=os.path.join(BACKUP_DIR,rec["filename"])
    if not os.path.exists(path): return jsonify({"error":"Backup file is missing from the server."}),404
    try:
        check=sqlite3.connect(path); result=check.execute("PRAGMA integrity_check").fetchone()[0]; check.close()
    except Exception as exc:
        return jsonify({"error":f"Backup validation failed: {exc}"}),400
    if result!="ok": return jsonify({"error":"Backup failed SQLite integrity check."}),400
    # Preserve the current database before restoration.
    make_backup("Pre-Restore Safety Backup")
    temp=DB_PATH+".restore_tmp"
    src=sqlite3.connect(path); dest=sqlite3.connect(temp)
    try:
        src.backup(dest)
    finally:
        dest.close(); src.close()
    os.replace(temp,DB_PATH)
    audit("DATABASE_RESTORED","backup_history",bid,rec["filename"])
    return jsonify({"success":True,"message":"Database restored. Please sign in again."})


@app.get("/api/system/health")
@login_required
def system_health():
    """Final integration self-check. Reports real database/schema readiness without mutating records."""
    u = current_user()
    if u["role"] not in {"Admin", "Auditor"}:
        return jsonify({"error":"Administrator or Auditor access required."}),403
    conn = db()
    required_tables = sorted(ALL_TABLES | {"circuits", "users", "audit_log", "backup_history"})
    existing = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    table_checks = [{"table": t, "ok": t in existing} for t in required_tables]
    missing_tables = [x["table"] for x in table_checks if not x["ok"]]
    schema_issues=[]
    expected = {
        "members": ["member_id","full_name","circuit","church_name"],
        "church_plants": ["year","location","status"],
        "outreach": ["date","circuit","location","decisions"],
        "mission_contacts": ["contact_name","phone","next_followup_date","followup_status"],
        "report_periods": ["period_name","start_date","end_date","submission_due","status"],
        "circuit_reports": ["period_id","circuit","status","reviewed_by"],
        "action_points": ["action_item","responsible_person","due_date","status"],
        "meetings": ["meeting_date","meeting_type","minutes","decisions"],
        "diocesan_reviews": ["review_date","executive_summary","status"],
        "notifications": ["title","message","status","created_at"],
        "users": ["username","password","role","active","must_change_password"],
        "audit_log": ["happened_at","action","table_name","details","username"],
        "backup_history": ["created_at","filename","sha256","status"]
    }
    for table, cols in expected.items():
        if table not in existing:
            continue
        have={r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        for col in cols:
            if col not in have:
                schema_issues.append(f"{table}.{col}")
    try:
        integrity=conn.execute("PRAGMA integrity_check").fetchone()[0]
    except Exception as exc:
        integrity=f"error: {exc}"
    counts={}
    for table in ["members","churches","circuits","church_plants","outreach","mission_contacts","report_periods","circuit_reports","action_points","meetings","diocesan_reviews","notifications","audit_log","backup_history"]:
        if table in existing:
            try: counts[table]=conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            except Exception: counts[table]=None
    checks={
        "database_integrity": integrity == "ok",
        "required_tables": not missing_tables,
        "required_columns": not schema_issues,
        "backup_directory": os.path.isdir(BACKUP_DIR),
        "app_version": APP_VERSION
    }
    return jsonify({
        "ok": all(v is True for k,v in checks.items() if k != "app_version"),
        "version": APP_VERSION,
        "stage": APP_STAGE,
        "checks": checks,
        "integrity": integrity,
        "missing_tables": missing_tables,
        "schema_issues": schema_issues,
        "counts": counts,
        "user": {"username":u["username"],"role":u["role"]},
        "generated_at": datetime.now().isoformat(timespec="seconds")
    })

@app.get("/api/system/data-quality")
@login_required
def system_data_quality():
    u=current_user()
    if u["role"] not in {"Admin","Auditor"}:
        return jsonify({"error":"Administrator or Auditor access required."}),403
    conn=db(); issues=[]; checks=[]
    def count(sql,args=()):
        return conn.execute(sql,args).fetchone()[0]
    checks.append({"name":"Duplicate member IDs","count":count("SELECT COUNT(*) FROM (SELECT member_id FROM members WHERE member_id<>'' GROUP BY member_id HAVING COUNT(*)>1)"),"severity":"high"})
    checks.append({"name":"Members without name","count":count("SELECT COUNT(*) FROM members WHERE TRIM(COALESCE(full_name,''))=''"),"severity":"high"})
    checks.append({"name":"Members without circuit","count":count("SELECT COUNT(*) FROM members WHERE TRIM(COALESCE(circuit,''))=''"),"severity":"medium"})
    checks.append({"name":"Churches without circuit","count":count("SELECT COUNT(*) FROM churches WHERE TRIM(COALESCE(circuit,''))=''"),"severity":"high"})
    checks.append({"name":"Church plants without location","count":count("SELECT COUNT(*) FROM church_plants WHERE TRIM(COALESCE(location,''))=''"),"severity":"medium"})
    checks.append({"name":"People reached without follow-up date","count":count("SELECT COUNT(*) FROM mission_contacts WHERE TRIM(COALESCE(next_followup_date,''))='' AND status NOT IN ('Inactive','Transferred')"),"severity":"medium"})
    checks.append({"name":"Open action points without due date","count":count("SELECT COUNT(*) FROM action_points WHERE status IN ('Open','In Progress') AND TRIM(COALESCE(due_date,''))=''"),"severity":"medium"})
    checks.append({"name":"Circuit reports without review status","count":count("SELECT COUNT(*) FROM circuit_reports WHERE TRIM(COALESCE(status,''))=''"),"severity":"low"})
    for c in checks:
        if c["count"]:
            issues.append(c)
    return jsonify({"ok":not issues,"checks":checks,"issues":issues,"generated_at":datetime.now().isoformat(timespec="seconds")})

@app.get("/api/system/data-quality/details")
@login_required
def system_data_quality_details():
    u=current_user()
    if u["role"] not in {"Admin","Auditor"}:
        return jsonify({"error":"Administrator or Auditor access required."}),403
    conn=db(); details=[]
    def rows(sql,args=()):
        return [dict(r) for r in conn.execute(sql,args).fetchall()]
    details.append({"issue":"Members without name","records":rows("SELECT id,member_id,circuit,church_name,full_name FROM members WHERE TRIM(COALESCE(full_name,''))='' LIMIT 50")})
    details.append({"issue":"Members without circuit","records":rows("SELECT id,member_id,full_name,church_name,circuit FROM members WHERE TRIM(COALESCE(circuit,''))='' LIMIT 50")})
    details.append({"issue":"Churches without circuit","records":rows("SELECT id,church_name,circuit FROM churches WHERE TRIM(COALESCE(circuit,''))='' LIMIT 50")})
    details.append({"issue":"Church plants without location","records":rows("SELECT id,year,circuit,axis,location,status FROM church_plants WHERE TRIM(COALESCE(location,''))='' LIMIT 50")})
    details.append({"issue":"People reached without follow-up date","records":rows("SELECT id,contact_name,phone,circuit,church_name,status,next_followup_date FROM mission_contacts WHERE TRIM(COALESCE(next_followup_date,''))='' AND status NOT IN ('Inactive','Transferred') LIMIT 50")})
    details.append({"issue":"Open action points without due date","records":rows("SELECT id,action_item,responsible_person,status,due_date FROM action_points WHERE status IN ('Open','In Progress') AND TRIM(COALESCE(due_date,''))='' LIMIT 50")})
    return jsonify({"details":details,"generated_at":datetime.now().isoformat(timespec="seconds")})

@app.post("/api/system/data-quality/safe-cleanup")
@login_required
def system_data_quality_safe_cleanup():
    u=current_user()
    if u["role"]!="Admin":
        return jsonify({"error":"Administrator access required for safe cleanup."}),403
    conn=db(); changes=[]
    # Only whitespace normalization and unambiguous circuit inheritance are automated.
    text_fields={
        "members":["full_name","address","phone","birthday","fellowship","church_name","work_address","profession_business_trade","notes"],
        "churches":["circuit","church_name","contact_person","phone","notes"],
        "church_plants":["axis","location","phase","status","leader","notes"],
        "mission_contacts":["contact_name","phone","address","circuit","church_name","source_mission","status","assigned_to","followup_status","outcome","notes"],
        "action_points":["action_item","responsible_person","priority","status","completion_notes"],
    }
    for table, cols in text_fields.items():
        existing={r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        for col in cols:
            if col in existing:
                cur=conn.execute(f"UPDATE {table} SET {col}=TRIM({col}) WHERE {col} IS NOT NULL AND {col}<>TRIM({col})")
                if cur.rowcount: changes.append({"table":table,"field":col,"updated":cur.rowcount,"reason":"trimmed whitespace"})
    # Fill a missing member circuit only when the church name maps to exactly one active church/circuit.
    members=conn.execute("SELECT id,church_name FROM members WHERE TRIM(COALESCE(circuit,''))='' AND TRIM(COALESCE(church_name,''))<>''").fetchall()
    filled=0
    for m in members:
        matches=conn.execute("SELECT DISTINCT circuit FROM churches WHERE TRIM(church_name)=TRIM(?) AND TRIM(COALESCE(circuit,''))<>''",(m["church_name"],)).fetchall()
        circuits={x[0] for x in matches}
        if len(circuits)==1:
            conn.execute("UPDATE members SET circuit=? WHERE id=?",(next(iter(circuits)),m["id"])); filled+=1
    if filled: changes.append({"table":"members","field":"circuit","updated":filled,"reason":"filled from an unambiguous church-to-circuit match"})
    conn.commit()
    audit("DATA_QUALITY_SAFE_CLEANUP","system",None,json.dumps({"changes":changes},ensure_ascii=False))
    return jsonify({"success":True,"changes":changes,"total_updated":sum(x["updated"] for x in changes),"message":"Safe cleanup completed. No ambiguous records were changed."})

@app.get("/api/system/workflow-check")
@login_required
def system_workflow_check():
    u=current_user()
    if u["role"] not in {"Admin","Auditor"}:
        return jsonify({"error":"Administrator or Auditor access required."}),403
    conn=db(); results=[]
    required=[
        ("Membership registration","members","SELECT COUNT(*) FROM members"),
        ("Mission planning","mission_calendar","SELECT COUNT(*) FROM mission_calendar"),
        ("People reached / follow-up","mission_contacts","SELECT COUNT(*) FROM mission_contacts"),
        ("Church planting","church_plants","SELECT COUNT(*) FROM church_plants"),
        ("Finance / trust fund","trust_fund","SELECT COUNT(*) FROM trust_fund"),
        ("Reporting / accountability","circuit_reports","SELECT COUNT(*) FROM circuit_reports"),
        ("Security audit trail","audit_log","SELECT COUNT(*) FROM audit_log"),
        ("Backup history","backup_history","SELECT COUNT(*) FROM backup_history")]
    existing={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    for label,table,sql in required:
        if table not in existing:
            results.append({"workflow":label,"status":"Missing","detail":f"Table {table} is missing"})
        else:
            try: results.append({"workflow":label,"status":"Ready","records":conn.execute(sql).fetchone()[0]})
            except Exception as exc: results.append({"workflow":label,"status":"Error","detail":str(exc)})
    return jsonify({"ok":all(x["status"]=="Ready" for x in results),"results":results,"generated_at":datetime.now().isoformat(timespec="seconds")})

@app.get("/api/system/info")
@login_required
def system_info():
    u=current_user()
    if u["role"] not in {"Admin","Auditor"}:
        return jsonify({"error":"Administrator or Auditor access required."}),403
    return jsonify({
        "application":"Methodist Church Nigeria, Delta South Diocese: Department of Evangelism Mission System",
        "version":APP_VERSION,
        "stage":APP_STAGE,
        "database":"SQLite",
        "python":"Flask application",
        "circuits":["Effurun Circuit","Warri Circuit","Sapele Circuit","Steel Town Circuit"],
        "local_church_target":17,
        "church_plant_target_per_year":5,
        "current_year":datetime.now().year
    })


@app.get("/api/system/deployment-check")
@login_required
def deployment_check():
    u=current_user()
    if u["role"] not in {"Admin","Auditor"}:
        return jsonify({"error":"Administrator or Auditor access required."}),403
    conn=db(); checks=[]
    def add(name, ok, detail): checks.append({"name":name,"ok":bool(ok),"detail":detail})
    add("Database file", os.path.isfile(DB_PATH), DB_PATH)
    add("Database writable", os.access(DB_PATH, os.W_OK), "Application can write to the active database." if os.path.isfile(DB_PATH) else "Database file not found yet.")
    add("Backup folder", os.path.isdir(BACKUP_DIR), BACKUP_DIR)
    latest=conn.execute("SELECT created_at,created_by,filename,size_bytes,sha256,status FROM backup_history ORDER BY id DESC LIMIT 1").fetchone()
    backup_ok=False
    backup_detail="No verified backup has been recorded."
    if latest:
        path=os.path.join(BACKUP_DIR,latest["filename"])
        if os.path.isfile(path):
            try:
                digest=hashlib.sha256(open(path,"rb").read()).hexdigest()
                backup_ok=(digest==latest["sha256"] and latest["status"]=="Ready")
                backup_detail=f"{latest['filename']} · {'verified' if backup_ok else 'hash/status mismatch'}"
            except Exception as exc:
                backup_detail=f"Backup verification error: {exc}"
        else:
            backup_detail="Latest backup record exists but the file is missing."
    add("Latest backup verified", backup_ok, backup_detail)
    role_count=conn.execute("SELECT COUNT(DISTINCT role) FROM users WHERE active=1").fetchone()[0]
    add("Active user access", role_count>0, f"{role_count} active role type(s) in use.")
    church_count=conn.execute("SELECT COUNT(*) FROM churches").fetchone()[0]
    circuit_count=conn.execute("SELECT COUNT(*) FROM circuits").fetchone()[0]
    add("Diocesan baseline", church_count==17 and circuit_count==4, f"{church_count} local-church records · {circuit_count} circuit records.")
    integrity=conn.execute("PRAGMA integrity_check").fetchone()[0]
    add("SQLite integrity", integrity=="ok", integrity)
    return jsonify({"ok":all(x["ok"] for x in checks),"checks":checks,"version":APP_VERSION,"stage":APP_STAGE,"generated_at":datetime.now().isoformat(timespec="seconds")})

@app.get("/manifest.json")
def manifest():
    return jsonify({"name":"Methodist Church Nigeria, Delta South Diocese: Department of Evangelism Mission System",
      "short_name":"MCN Delta South Evangelism","start_url":"/","display":"standalone","background_color":"#f5f7f6","theme_color":"#14532d","version":APP_VERSION,"icons":[]})


def build_table_map():
    """Build the table/column map after the database schema has been initialized."""
    conn = db()
    names = set(ALL_TABLES)
    names.update({"circuits", "users", "audit_log", "backup_history"})
    table_map = {}
    for name in sorted(names):
        try:
            cols = [row[1] for row in conn.execute(f"PRAGMA table_info({name})").fetchall()]
            if cols:
                table_map[name] = cols
        except sqlite3.Error:
            continue
    return table_map

init_db()
with app.app_context():
    TABLES = build_table_map()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8080")),
        debug=False
    )
else:
    init_db()
