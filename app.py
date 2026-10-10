import time
import os, sqlite3, json, io, socket, secrets, shutil, hashlib
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, render_template, send_file, g, Response, session, redirect, url_for
from werkzeug.utils import secure_filename
from openpyxl import load_workbook, Workbook
import qrcode
from qrcode.image.svg import SvgPathImage
from werkzeug.security import generate_password_hash, check_password_hash

APP_VERSION = "19.2.1"
APP_STAGE = "Stage 19.2.1 - API /api/me and Table Map Stability"
ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
MEMBER_PHOTO_DIR = os.path.join(DATA_DIR, "member_photos")
os.makedirs(MEMBER_PHOTO_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "evangelism.db")
XLSX_PATH = os.path.join(DATA_DIR, "Delta_South_Diocese_Evangelism_Fundraising_System.xlsx")
SECRET_PATH = os.path.join(DATA_DIR, ".session_secret")
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 3 * 1024 * 1024
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
    "Member": "Self-service access to personal membership records",
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

    elif role in {"Member", "Local Church Evangelism Officer"}:
        if not circuit or circuit == "Diocesan":
            if role == "Member":
                return "A Member must be assigned to a circuit."
            return "A Local Church Evangelism Officer must be assigned to a circuit."

        if not church_name:
            if role == "Member":
                return "A Member must be assigned to a local church."
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

FINANCE_TABLES = {"commitments", "income", "expenses", "sponsors", "equipment", "trust_fund", "mission_budgets", "procurement_requests", "church_accounts"}
MISSION_TABLES = {"churches", "church_plants", "planting_prospects", "outreach", "mission_calendar", "mission_teams", "mission_contacts", "report_periods", "circuit_reports", "action_points", "meetings", "diocesan_reviews", "notifications"}
MEMBERSHIP_TABLES = {"members", "member_registrations", "testimonies", "appreciations", "mission_contacts"}
ALL_TABLES = {"churches", "commitments", "income", "expenses", "equipment", "trust_fund", "mission_budgets", "procurement_requests", "church_plants", "planting_prospects", "outreach", "mission_calendar", "mission_teams", "mission_contacts", "sponsors", "members", "member_registrations", "testimonies", "appreciations", "report_periods", "circuit_reports", "action_points", "meetings", "diocesan_reviews", "notifications", "church_accounts"}


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
    # Account registration requests: initialize before the Admin
    # account-requests API is used. Existing records are preserved.
    db().execute("""
        CREATE TABLE IF NOT EXISTS account_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            username TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT DEFAULT '',
            circuit TEXT NOT NULL,
            church_name TEXT NOT NULL,
            password TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            review_note TEXT DEFAULT '',
            reviewed_by INTEGER DEFAULT NULL,
            reviewed_at TEXT DEFAULT NULL,
            created_at TEXT NOT NULL
        )
    """)
    db().commit()


    # Customer Care and Conference communication tables
    db().execute("""
        CREATE TABLE IF NOT EXISTS customer_care_threads(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id TEXT UNIQUE NOT NULL,
            customer_name TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            subject TEXT DEFAULT '',
            status TEXT DEFAULT 'Open',
            assigned_to TEXT DEFAULT '',
            created_at TEXT DEFAULT '',
            updated_at TEXT DEFAULT ''
        )
    """)

    db().execute("""
        CREATE TABLE IF NOT EXISTS customer_care_messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id TEXT NOT NULL,
            sender_name TEXT DEFAULT '',
            sender_role TEXT DEFAULT '',
            message TEXT NOT NULL,
            created_at TEXT DEFAULT '',
            read_at TEXT DEFAULT ''
        )
    """)

    db().execute("""
        CREATE TABLE IF NOT EXISTS conference_rooms(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_code TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            meeting_date TEXT DEFAULT '',
            start_time TEXT DEFAULT '',
            end_time TEXT DEFAULT '',
            meeting_type TEXT DEFAULT 'General Conference',
            circuit TEXT DEFAULT 'Diocesan',
            organizer TEXT DEFAULT '',
            meeting_url TEXT DEFAULT '',
            agenda TEXT DEFAULT '',
            status TEXT DEFAULT 'Scheduled',
            created_at TEXT DEFAULT ''
        )
    """)

    db().execute("""
        CREATE TABLE IF NOT EXISTS conference_participants(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_code TEXT NOT NULL,
            participant_name TEXT DEFAULT '',
            participant_role TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            status TEXT DEFAULT 'Invited',
            joined_at TEXT DEFAULT '',
            left_at TEXT DEFAULT ''
        )
    """)

    db().execute("""
        CREATE TABLE IF NOT EXISTS conference_messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_code TEXT NOT NULL,
            sender_name TEXT DEFAULT '',
            sender_role TEXT DEFAULT '',
            message TEXT NOT NULL,
            created_at TEXT DEFAULT ''
        )
    """)

    db().execute("""
        CREATE TABLE IF NOT EXISTS conference_signals(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_code TEXT NOT NULL,
            sender_id TEXT NOT NULL,
            recipient_id TEXT DEFAULT '',
            signal_type TEXT NOT NULL,
            payload TEXT DEFAULT '',
            created_at TEXT DEFAULT ''
        )
    """)
    db().execute("CREATE INDEX IF NOT EXISTS idx_conference_signals_room_id ON conference_signals(room_code, id)")

    db().commit()

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
    CREATE TABLE IF NOT EXISTS church_accounts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_level TEXT NOT NULL DEFAULT 'Diocese',
        circuit TEXT,
        church_name TEXT,
        bank_name TEXT NOT NULL,
        account_name TEXT NOT NULL,
        account_number TEXT NOT NULL,
        account_type TEXT DEFAULT 'Current',
        branch TEXT,
        notes TEXT,
        active INTEGER DEFAULT 1,
        created_by TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_church_accounts_level
        ON church_accounts(account_level);

    CREATE INDEX IF NOT EXISTS idx_church_accounts_circuit
        ON church_accounts(circuit);

    CREATE INDEX IF NOT EXISTS idx_church_accounts_church
        ON church_accounts(church_name);

    CREATE TABLE IF NOT EXISTS payment_transactions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference TEXT UNIQUE NOT NULL,
        gateway TEXT NOT NULL DEFAULT 'Monnify',
        status TEXT NOT NULL DEFAULT 'Pending',
        amount REAL NOT NULL,
        currency TEXT DEFAULT 'NGN',
        purpose TEXT,
        account_level TEXT,
        circuit TEXT,
        church_name TEXT,
        church_account_id INTEGER,
        member_id INTEGER,
        donor_name TEXT,
        donor_email TEXT,
        donor_phone TEXT,
        payment_method TEXT,
        gateway_transaction_id TEXT,
        gateway_response TEXT,
        paid_at TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(church_account_id) REFERENCES church_accounts(id),
        FOREIGN KEY(member_id) REFERENCES members(id)
    );

    CREATE INDEX IF NOT EXISTS idx_payment_reference
        ON payment_transactions(reference);

    CREATE INDEX IF NOT EXISTS idx_payment_member
        ON payment_transactions(member_id);

    CREATE INDEX IF NOT EXISTS idx_payment_status
        ON payment_transactions(status);

    CREATE TABLE IF NOT EXISTS payment_settings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider TEXT NOT NULL DEFAULT 'Monnify',
        enabled INTEGER DEFAULT 0,
        public_key TEXT,
        secret_key TEXT,
        contract_code TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

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
    CREATE TABLE IF NOT EXISTS member_registrations(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      registration_id TEXT UNIQUE NOT NULL,
      circuit TEXT NOT NULL,
      church_name TEXT NOT NULL,
      full_name TEXT NOT NULL,
      gender TEXT DEFAULT '',
      address TEXT DEFAULT '',
      phone TEXT DEFAULT '',
      email TEXT DEFAULT '',
      birthday TEXT DEFAULT '',
      fellowship TEXT DEFAULT '',
      baptised TEXT DEFAULT 'No',
      baptism_date TEXT DEFAULT '',
      confirmed TEXT DEFAULT 'No',
      confirmation_date TEXT DEFAULT '',
      marriage TEXT DEFAULT 'No',
      marriage_date TEXT DEFAULT '',
      work_address TEXT DEFAULT '',
      profession_business_trade TEXT DEFAULT '',
      passport_photo TEXT DEFAULT '',
      status TEXT DEFAULT 'Pending',
      review_note TEXT DEFAULT '',
      reviewed_by TEXT DEFAULT '',
      reviewed_at TEXT DEFAULT '',
      approved_member_id TEXT DEFAULT '',
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
    CREATE TABLE IF NOT EXISTS password_reset_tokens(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      token_hash TEXT NOT NULL UNIQUE,
      expires_at TEXT NOT NULL,
      used INTEGER DEFAULT 0,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS member_appointments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            office TEXT NOT NULL,
            level TEXT DEFAULT 'Local Church',
            circuit TEXT DEFAULT '',
            church_name TEXT DEFAULT '',
            start_date TEXT DEFAULT '',
            end_date TEXT DEFAULT '',
            status TEXT DEFAULT 'Active',
            notes TEXT DEFAULT '',
            appointed_by TEXT DEFAULT '',
            created_at TEXT DEFAULT '',
            updated_at TEXT DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_member_appointments_member
        ON member_appointments(member_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_member_appointments_status
        ON member_appointments(status)
    """)

    member_migrations = {
        "member_id": "TEXT DEFAULT ''",
        "role_position": "TEXT DEFAULT 'Other'",
        "circuit": "TEXT DEFAULT ''",
        "church_name": "TEXT DEFAULT ''",
        "full_name": "TEXT DEFAULT ''",
        "address": "TEXT DEFAULT ''",
        "phone": "TEXT DEFAULT ''",
        "birthday": "TEXT DEFAULT ''", "gender": "TEXT DEFAULT ''", "conference_awardee": "TEXT DEFAULT 'No'", "conference_award": "TEXT DEFAULT ''", "conference_award_year": "TEXT DEFAULT ''", "diocesan_awardee": "TEXT DEFAULT 'No'", "diocesan_award": "TEXT DEFAULT ''", "diocesan_award_year": "TEXT DEFAULT ''",
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
    ensure_column(conn, "users", "member_id", "INTEGER DEFAULT NULL")
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




def ensure_member_passport_photo_schema():
    """Ensure members has the passport_photo field using a standalone DB connection."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cols = {
            r[1]
            for r in conn.execute(
                "PRAGMA table_info(members)"
            ).fetchall()
        }

        if "passport_photo" not in cols:
            conn.execute(
                "ALTER TABLE members ADD COLUMN passport_photo TEXT DEFAULT ''"
            )
            conn.commit()
            print("Added members.passport_photo")
    finally:
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
      'income': {
        'church_account_id': 'INTEGER DEFAULT NULL'
      },
      'expenses': {
        'church_name': "TEXT DEFAULT ''"
      },
      'member_registrations': {
        'username': "TEXT DEFAULT ''",
        'password': "TEXT DEFAULT ''",
        'account_status': "TEXT DEFAULT 'Pending'",
        'approved_user_id': "INTEGER DEFAULT NULL"
      },
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
      'notifications': {'title':"TEXT DEFAULT ''",'message':"TEXT DEFAULT ''",'notification_type':"TEXT DEFAULT 'Reminder'",'target_circuit':"TEXT DEFAULT 'Diocesan'",'target_phone':"TEXT DEFAULT ''",'source_table':"TEXT DEFAULT ''",'source_id':'INTEGER DEFAULT NULL','due_date':"TEXT DEFAULT ''",'status':"TEXT DEFAULT 'Unread'",'created_at':"TEXT DEFAULT ''",'read_at':"TEXT DEFAULT ''"},
      'customer_care_threads': {
        'user_id': 'INTEGER DEFAULT NULL',
        'member_id': "TEXT DEFAULT ''",
        'category': "TEXT DEFAULT 'General Assistance'",
        'priority': "TEXT DEFAULT 'Normal'",
        'resolution_note': "TEXT DEFAULT ''",
        'resolved_at': "TEXT DEFAULT ''"
      }
    }
    for table, cols in migrations.items():
        for col, definition in cols.items():
            ensure_column(conn, table, col, definition)
    conn.commit()

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None

    user = db().execute(
        "SELECT id,username,password,role,circuit,church_name,active,must_change_password,created_at,member_id "
        "FROM users WHERE id=?",
        (uid,)
    ).fetchone()

    if not user:
        return None

    # Normalize Member portal links. Older accounts may contain the
    # official member code (for example DSD-OTH-0005) instead of
    # the numeric members.id expected by the portal APIs.
    if user["member_id"]:
        member = db().execute(
            "SELECT id FROM members WHERE id=? OR member_id=? LIMIT 1",
            (user["member_id"], str(user["member_id"]))
        ).fetchone()

        if member and str(user["member_id"]) != str(member["id"]):
            db().execute(
                "UPDATE users SET member_id=? WHERE id=?",
                (member["id"], user["id"])
            )
            db().commit()

            user = db().execute(
                "SELECT id,username,password,role,circuit,church_name,active,"
                "must_change_password,created_at,member_id FROM users WHERE id=?",
                (uid,)
            ).fetchone()

    return user


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



@app.post("/api/member/change-password")
@login_required
def member_change_password():
    u = current_user()
    if u["role"] != "Member":
        return jsonify({"error": "Member access required."}), 403

    data = request.get_json(silent=True) or {}
    current = data.get("current_password", "")
    new = data.get("new_password", "")
    confirm = data.get("confirm_password", "")

    if not current or not new or not confirm:
        return jsonify({"error": "Current password, new password and confirmation are required."}), 400

    if not check_password_hash(u["password"], current):
        return jsonify({"error": "Current password is incorrect."}), 400

    if len(new) < 8:
        return jsonify({"error": "New password must be at least 8 characters."}), 400

    if new != confirm:
        return jsonify({"error": "New passwords do not match."}), 400

    conn = db()
    conn.execute(
        "UPDATE users SET password=?, must_change_password=0 WHERE id=?",
        (generate_password_hash(new), u["id"])
    )
    conn.commit()

    return jsonify({"success": True, "message": "Password changed successfully."})


@app.put("/api/member/profile")
@login_required
def member_update_profile():
    u=current_user()

    if not u["member_id"]:
        return jsonify({"error":"Member account is not linked."}),403

    allowed={
        "full_name","gender","phone","birthday","address",
        "work_address","profession_business_trade","fellowship"
    }

    data=request.get_json(silent=True) or {}
    updates={k:data[k] for k in allowed if k in data}

    if not updates:
        return jsonify({"error":"No editable profile fields supplied."}),400

    sets=", ".join(f"{k}=?" for k in updates)
    values=list(updates.values())
    values.append(u["member_id"])

    conn=db()
    conn.execute(
        f"UPDATE members SET {sets} WHERE id=?",
        values
    )
    conn.commit()

    return jsonify({
        "success":True,
        "message":"Profile updated successfully."
    })


@app.get("/api/member/id-card")
@login_required
def member_id_card():
    u=current_user()

    if not u["member_id"]:
        return jsonify({"error":"Member account is not linked."}),403

    member=db().execute(
        "SELECT * FROM members WHERE id=?",
        (u["member_id"],)
    ).fetchone()

    if not member:
        return jsonify({"error":"Member record not found."}),404

    return jsonify({
        "member_id": member["member_id"],
        "full_name": member["full_name"],
        "role_position": member["role_position"],
        "circuit": member["circuit"],
        "church_name": member["church_name"],
        "fellowship": member["fellowship"],
        "passport_photo": member["passport_photo"] if "passport_photo" in member.keys() else None
    })



@app.get("/api/communications")
@login_required
def api_communications():
    u = current_user()
    conn = db()

    alerts = []

    contacts = conn.execute("""
        SELECT id, contact_name, phone, circuit, next_followup_date,
               followup_status, outcome
        FROM mission_contacts
        WHERE next_followup_date IS NOT NULL
          AND next_followup_date != ''
          AND followup_status NOT IN ('Completed','Closed')
        ORDER BY next_followup_date ASC, id DESC
    """).fetchall()

    for r in contacts:
        alerts.append({
            "kind": "Follow-up",
            "title": r["contact_name"] or "Mission Contact",
            "date": r["next_followup_date"],
            "circuit": r["circuit"] or "Diocesan",
            "detail": r["outcome"] or "Follow-up pending",
            "phone": r["phone"] or ""
        })

    missions = conn.execute("""
        SELECT id, event_date, event_time, event_type, circuit,
               location, activity, responsible_person, status
        FROM mission_calendar
        WHERE event_date IS NOT NULL
          AND event_date != ''
          AND status NOT IN ('Completed','Cancelled')
        ORDER BY event_date ASC, id DESC
    """).fetchall()

    for r in missions:
        alerts.append({
            "kind": "Mission",
            "title": r["activity"] or r["event_type"] or "Mission Activity",
            "date": r["event_date"],
            "circuit": r["circuit"] or "Diocesan",
            "detail": "Location: " + (r["location"] or "Not specified"),
            "phone": ""
        })

    plants = conn.execute("""
        SELECT id, year, location, status, circuit, leader, start_date
        FROM church_plants
        WHERE status NOT IN ('Launched','Active')
        ORDER BY year ASC, id DESC
    """).fetchall()

    for r in plants:
        alerts.append({
            "kind": "Church Plant",
            "title": "Church Plant: " + (r["location"] or "Proposed location"),
            "date": r["start_date"] or str(r["year"] or ""),
            "circuit": r["circuit"] or "Diocesan",
            "detail": "Status: " + (r["status"] or "Planned"),
            "phone": ""
        })

    notifications = conn.execute("""
        SELECT id, title, message, notification_type,
               target_circuit, target_phone, due_date, status
        FROM notifications
        WHERE status != 'Read'
        ORDER BY id DESC
    """).fetchall()

    for r in notifications:
        alerts.append({
            "kind": r["notification_type"] or "Reminder",
            "title": r["title"] or "Reminder",
            "date": r["due_date"] or "",
            "circuit": r["target_circuit"] or "Diocesan",
            "detail": r["message"] or "",
            "phone": r["target_phone"] or ""
        })

    alerts.sort(key=lambda x: (x.get("date") or "9999", x.get("title") or ""))

    unread = conn.execute("""
        SELECT COUNT(*) AS n
        FROM notifications
        WHERE status != 'Read'
    """).fetchone()["n"]

    from datetime import date
    return jsonify({
        "today": date.today().isoformat(),
        "alerts": alerts,
        "unread": unread
    })


@app.post("/api/notifications/generate")
@login_required
def api_notifications_generate():
    u = current_user()

    conn = db()
    created = 0

    contacts = conn.execute("""
        SELECT id, contact_name, phone, circuit, next_followup_date,
               outcome
        FROM mission_contacts
        WHERE next_followup_date IS NOT NULL
          AND next_followup_date != ''
          AND followup_status NOT IN ('Completed','Closed')
    """).fetchall()

    for r in contacts:
        title = "Follow-up: " + (r["contact_name"] or "Mission Contact")
        exists = conn.execute("""
            SELECT id FROM notifications
            WHERE source_table='mission_contacts'
              AND source_id=?
              AND due_date=?
              AND status != 'Read'
            LIMIT 1
        """, (r["id"], r["next_followup_date"])).fetchone()

        if not exists:
            conn.execute("""
                INSERT INTO notifications
                (title,message,notification_type,target_circuit,target_phone,
                 source_table,source_id,due_date,status,created_at)
                VALUES (?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
            """, (
                title,
                r["outcome"] or "Mission follow-up is due.",
                "Follow-up",
                r["circuit"] or "Diocesan",
                r["phone"] or "",
                "mission_contacts",
                r["id"],
                r["next_followup_date"],
                "Unread"
            ))
            created += 1

    missions = conn.execute("""
        SELECT id, event_date, event_type, circuit, location, activity
        FROM mission_calendar
        WHERE event_date IS NOT NULL
          AND event_date != ''
          AND status NOT IN ('Completed','Cancelled')
    """).fetchall()

    for r in missions:
        title = "Mission: " + (r["activity"] or r["event_type"] or "Mission Activity")
        exists = conn.execute("""
            SELECT id FROM notifications
            WHERE source_table='mission_calendar'
              AND source_id=?
              AND due_date=?
              AND status != 'Read'
            LIMIT 1
        """, (r["id"], r["event_date"])).fetchone()

        if not exists:
            conn.execute("""
                INSERT INTO notifications
                (title,message,notification_type,target_circuit,
                 source_table,source_id,due_date,status,created_at)
                VALUES (?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
            """, (
                title,
                "Mission at " + (r["location"] or "location not specified"),
                "Mission",
                r["circuit"] or "Diocesan",
                "mission_calendar",
                r["id"],
                r["event_date"],
                "Unread"
            ))
            created += 1

    conn.commit()

    audit(
        "CREATE",
        "notifications",
        None,
        f"Generated {created} communication reminder(s)"
    )

    return jsonify({
        "ok": True,
        "created": created,
        "message": "Communication reminders generated."
    })


@app.get("/api/member/notifications")
@login_required
def member_notifications():
    u=current_user()

    if not u["member_id"]:
        return jsonify({"error":"Member account is not linked."}),403

    member=db().execute(
        "SELECT phone,circuit,church_name FROM members WHERE id=?",
        (u["member_id"],)
    ).fetchone()

    if not member:
        return jsonify({"error":"Member record not found."}),404

    return jsonify(rows(
        """SELECT id,title,message,notification_type,due_date,status,
                  created_at,read_at
           FROM notifications
           WHERE (target_circuit IS NULL OR target_circuit='' OR target_circuit=?)
             AND (target_phone IS NULL OR target_phone='' OR target_phone=?)
           ORDER BY id DESC""",
        (member["circuit"],member["phone"])
    ))


@app.post("/api/member/notifications/<int:nid>/read")
@login_required
def member_notification_read(nid):
    u=current_user()

    if not u["member_id"]:
        return jsonify({"error":"Member account is not linked."}),403

    member=db().execute(
        "SELECT phone,circuit FROM members WHERE id=?",
        (u["member_id"],)
    ).fetchone()

    if not member:
        return jsonify({"error":"Member record not found."}),404

    conn=db()
    row=conn.execute(
        """SELECT id FROM notifications
           WHERE id=?
             AND (target_circuit IS NULL OR target_circuit='' OR target_circuit=?)
             AND (target_phone IS NULL OR target_phone='' OR target_phone=?)""",
        (nid,member["circuit"],member["phone"])
    ).fetchone()

    if not row:
        return jsonify({"error":"Notification not found."}),404

    conn.execute(
        "UPDATE notifications SET status='Read',read_at=CURRENT_TIMESTAMP WHERE id=?",
        (nid,)
    )
    conn.commit()

    return jsonify({"success":True,"message":"Notification marked as read."})


@app.get("/api/member/giving-history")
@login_required
def member_giving_history():
    u=current_user()

    if not u["member_id"]:
        return jsonify({"error":"Member account is not linked."}),403

    member=db().execute(
        "SELECT id FROM members WHERE id=?",
        (u["member_id"],)
    ).fetchone()

    if not member:
        return jsonify({"error":"Member record not found."}),404

    return jsonify(rows(
        """SELECT id,date,source,fund,amount,method,reference,notes
           FROM income
           WHERE member_id=?
           ORDER BY id DESC""",
        (u["member_id"],)
    ))


@app.post("/api/member-attendance")
@login_required
def record_member_attendance():
    u=current_user()
    if u["role"] not in {"Admin","Evangelism Minister","Planting Officer","Circuit Coordinator","Local Church Evangelism Officer"}:
        return jsonify({"error":"Attendance recording access denied."}),403
    data=request.get_json(force=True) or {}
    member_id=data.get("member_id")
    attendance_date=(data.get("attendance_date") or "").strip()
    meeting_type=(data.get("meeting_type") or "").strip()
    status=(data.get("status") or "Present").strip().title()
    if not member_id or not attendance_date:
        return jsonify({"error":"member_id and attendance_date are required."}),400
    if status not in {"Present","Absent"}:
        return jsonify({"error":"Status must be Present or Absent."}),400
    member=db().execute("SELECT id,circuit,church_name FROM members WHERE id=?",(member_id,)).fetchone()
    if not member:
        return jsonify({"error":"Member record not found."}),404
    if u["role"]=="Circuit Coordinator" and u["circuit"] and member["circuit"]!=u["circuit"]:
        return jsonify({"error":"Member is outside your circuit."}),403
    if u["role"]=="Local Church Evangelism Officer" and (member["circuit"]!=u["circuit"] or member["church_name"]!=u["church_name"]):
        return jsonify({"error":"Member is outside your local church."}),403
    cur=db().execute("INSERT INTO member_attendance(member_id,attendance_date,meeting_type,status,circuit,church_name,recorded_by,notes) VALUES(?,?,?,?,?,?,?,?)",(member_id,attendance_date,meeting_type,status,member["circuit"],member["church_name"],u["username"],(data.get("notes") or "").strip()))
    db().commit()
    return jsonify({"ok":True,"id":cur.lastrowid}),201

@app.post("/api/member-attendance/bulk")
@login_required
def record_bulk_attendance():
    u=current_user()
    if u["role"] not in {"Admin","Evangelism Minister","Planting Officer","Circuit Coordinator","Local Church Evangelism Officer"}:
        return jsonify({"error":"Attendance recording access denied."}),403
    data=request.get_json(force=True) or {}
    attendance_date=(data.get("attendance_date") or "").strip()
    meeting_type=(data.get("meeting_type") or "").strip()
    records=data.get("records") or []
    if not attendance_date or not records:
        return jsonify({"error":"attendance_date and records are required."}),400
    count=0
    for item in records:
        member_id=item.get("member_id")
        status=(item.get("status") or "Present").strip().title()
        if not member_id or status not in {"Present","Absent"}: continue
        member=db().execute("SELECT id,circuit,church_name FROM members WHERE id=?",(member_id,)).fetchone()
        if not member: continue
        if u["role"]=="Circuit Coordinator" and u["circuit"] and member["circuit"]!=u["circuit"]: continue
        if u["role"]=="Local Church Evangelism Officer" and (member["circuit"]!=u["circuit"] or member["church_name"]!=u["church_name"]): continue
        db().execute("INSERT INTO member_attendance(member_id,attendance_date,meeting_type,status,circuit,church_name,recorded_by,notes) VALUES(?,?,?,?,?,?,?,?)",(member_id,attendance_date,meeting_type,status,member["circuit"],member["church_name"],u["username"],item.get("notes") or "")); count+=1
    db().commit()
    return jsonify({"ok":True,"saved":count}),201

@app.get("/api/member/attendance-summary")
@login_required
def member_attendance_summary():
    u=current_user()

    if not u["member_id"]:
        return jsonify({"error":"Member account is not linked."}),403

    conn=db()
    total=conn.execute(
        "SELECT COUNT(*) AS n FROM member_attendance WHERE member_id=?",
        (u["member_id"],)
    ).fetchone()["n"]

    present=conn.execute(
        """SELECT COUNT(*) AS n FROM member_attendance
           WHERE member_id=? AND LOWER(status)='present'""",
        (u["member_id"],)
    ).fetchone()["n"]

    absent=conn.execute(
        """SELECT COUNT(*) AS n FROM member_attendance
           WHERE member_id=? AND LOWER(status)='absent'""",
        (u["member_id"],)
    ).fetchone()["n"]

    percentage=round((present/total)*100,1) if total else 0

    return jsonify({
        "total":total,
        "present":present,
        "absent":absent,
        "attendance_percentage":percentage
    })


@app.get("/api/member/attendance")
@login_required
def member_attendance():
    u=current_user()

    if not u["member_id"]:
        return jsonify({"error":"Member account is not linked."}),403

    return jsonify(rows(
        """SELECT id,attendance_date,meeting_type,status,circuit,
                  church_name,notes,created_at
           FROM member_attendance
           WHERE member_id=?
           ORDER BY attendance_date DESC,id DESC""",
        (u["member_id"],)
    ))




@app.get("/member/certificate")
@login_required
def member_certificate():
    u=current_user()

    if not u["member_id"]:
        return jsonify({"error":"Member account is not linked."}),403

    m=db().execute("""SELECT member_id,full_name,circuit,church_name,
        role_position,fellowship,baptised,baptism_date,
        confirmed,confirmation_date,marriage,marriage_date
        FROM members WHERE id=?""",(u["member_id"],)).fetchone()

    if not m:
        return jsonify({"error":"Member record not found."}),404

    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER

    buf=BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=45,leftMargin=45,topMargin=50,bottomMargin=50)
    styles=getSampleStyleSheet()
    title=ParagraphStyle("CertTitle",parent=styles["Title"],alignment=TA_CENTER,fontSize=20,spaceAfter=12)
    center=ParagraphStyle("Center",parent=styles["Normal"],alignment=TA_CENTER,fontSize=11)

    story=[
        Paragraph("METHODIST CHURCH NIGERIA",title),
        Paragraph("DELTA SOUTH DIOCESE",title),
        Spacer(1,15),
        Paragraph("MEMBER RECORD CERTIFICATE",title),
        Spacer(1,12),
        Paragraph("This is to certify that the following membership record is officially registered in the Delta South Diocese church membership system.",center),
        Spacer(1,20)
    ]

    data=[
        ["Member ID",m["member_id"] or ""],
        ["Full Name",m["full_name"] or ""],
        ["Position",m["role_position"] or "Member"],
        ["Local Church",m["church_name"] or ""],
        ["Circuit",m["circuit"] or ""],
        ["Fellowship",m["fellowship"] or ""],
        ["Baptised",m["baptised"] or "No"],
        ["Baptism Date",m["baptism_date"] or ""],
        ["Confirmed",m["confirmed"] or "No"],
        ["Confirmation Date",m["confirmation_date"] or ""],
        ["Married",m["marriage"] or "No"],
        ["Marriage Date",m["marriage_date"] or ""]
    ]

    table=Table(data,colWidths=[140,340])
    table.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),0.6,colors.grey),
        ("BACKGROUND",(0,0),(0,-1),colors.whitesmoke),
        ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("PADDING",(0,0),(-1,-1),8)
    ]))
    story.extend([table,Spacer(1,30),Paragraph("Issued electronically by MCN Delta South Diocese.",center)])

    doc.build(story)
    buf.seek(0)

    return send_file(
        buf,
        as_attachment=True,
        download_name="MCN_Delta_South_Member_Certificate.pdf",
        mimetype="application/pdf"
    )

@app.get("/api/member/records")
@login_required
def member_records():
    u=current_user()
    if not u["member_id"]: return jsonify({"error":"Member account is not linked."}),403
    m=db().execute("SELECT member_id,full_name,circuit,church_name,baptised,baptism_date,confirmed,confirmation_date,marriage,marriage_date,relocated,relocation_destination,relocation_date,transfer,transfer_from,transfer_to,transfer_date FROM members WHERE id=?",(u["member_id"],)).fetchone()
    if not m: return jsonify({"error":"Member record not found."}),404
    return jsonify(dict(m))

@app.get("/api/member/announcements")
@login_required
def member_announcements():
    u=current_user()

    if not u["member_id"]:
        return jsonify({"error":"Member account is not linked."}),403

    member=db().execute(
        "SELECT phone,circuit FROM members WHERE id=?",
        (u["member_id"],)
    ).fetchone()

    if not member:
        return jsonify({"error":"Member record not found."}),404

    return jsonify(rows(
        """SELECT id,title,message,notification_type,
                  target_circuit,target_phone,due_date,status,
                  created_at,read_at
           FROM notifications
           WHERE notification_type='Announcement'
             AND (target_circuit IS NULL OR target_circuit='' OR target_circuit=?)
             AND (target_phone IS NULL OR target_phone='' OR target_phone=?)
           ORDER BY id DESC""",
        (member["circuit"],member["phone"])
    ))

@app.get("/api/member/events")
@login_required
def member_events():
    u=current_user()

    if not u["member_id"]:
        return jsonify({"error":"Member account is not linked."}),403

    member=db().execute(
        "SELECT circuit,church_name FROM members WHERE id=?",
        (u["member_id"],)
    ).fetchone()

    if not member:
        return jsonify({"error":"Member record not found."}),404

    return jsonify(rows(
        """SELECT id,event_date,event_time,event_type,circuit,location,
                  activity,mission_phase,church_plant_id,responsible_person,
                  expected_outcome,followup_date,status,notes,created_at
           FROM mission_calendar
           WHERE circuit IN (?, 'Diocesan')
           ORDER BY event_date DESC,event_time DESC,id DESC""",
        (member["circuit"],)
    ))

@app.get("/api/member/testimonies")
@login_required
def member_testimonies():
    u=current_user()

    if not u["member_id"]:
        return jsonify({"error":"Member account is not linked."}),403

    member=db().execute(
        "SELECT full_name,circuit,church_name FROM members WHERE id=?",
        (u["member_id"],)
    ).fetchone()

    if not member:
        return jsonify({"error":"Member record not found."}),404

    return jsonify(rows(
        """SELECT id,date,title,testimony,recorded_by,created_at
           FROM testimonies
           WHERE member_name=? AND circuit=? AND church_name=?
           ORDER BY id DESC""",
        (member["full_name"],member["circuit"],member["church_name"])
    ))


@app.get("/api/member/appreciations")
@login_required
def member_appreciations():
    u=current_user()

    if not u["member_id"]:
        return jsonify({"error":"Member account is not linked."}),403

    member=db().execute(
        "SELECT full_name,circuit,church_name FROM members WHERE id=?",
        (u["member_id"],)
    ).fetchone()

    if not member:
        return jsonify({"error":"Member record not found."}),404

    return jsonify(rows(
        """SELECT id,date,role_position,reason,message,recorded_by,created_at
           FROM appreciations
           WHERE recipient=? AND circuit=? AND church_name=?
           ORDER BY id DESC""",
        (member["full_name"],member["circuit"],member["church_name"])
    ))



@app.get("/api/member/me")
@login_required
def member_me():
    u = current_user()

    if not u["member_id"]:
        return jsonify({"error": "This member account is not linked to a membership record."}), 403
    member = db().execute("SELECT * FROM members WHERE id=?", (u["member_id"],)).fetchone()
    if not member:
        return jsonify({"error": "Linked membership record was not found."}), 404
    return jsonify({
        "user": {
            "id": u["id"],
            "username": u["username"],
            "role": u["role"]
        },
        "member": dict(member)
    })



def page_login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        u = current_user()
        if not u or not u["active"]:
            return redirect(url_for("login"))
        if u["must_change_password"] and request.endpoint != "change_password":
            return redirect(url_for("change_password"))
        return fn(*args, **kwargs)
    return wrapper


@app.before_request
def protect_app():
    public = {"login", "setup", "logout", "static", "manifest", "public_member_registration_page", "account_registration", "forgot_password", "reset_password"}
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
    if u["must_change_password"] and request.endpoint != "change_password":
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
        cur = conn.execute("INSERT INTO users(username,password,role,circuit,church_name,active,must_change_password,created_at,member_id) VALUES(?,?,?,?,?,?,?,?,?)",
                           (username, generate_password_hash(password), "Admin", "", "", 1, 0, now, None))
        conn.commit()
        session.clear(); session["user_id"] = cur.lastrowid
        audit("LOGIN_SETUP", "users", cur.lastrowid, "Initial diocesan administrator created")
        return redirect(url_for("home"))
    return render_template("setup.html", error="")



@app.route("/account-registration", methods=["GET", "POST"])
def account_registration():
    error = ""
    success = ""

    conn = db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS account_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            username TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT DEFAULT '',
            circuit TEXT NOT NULL,
            church_name TEXT NOT NULL,
            password TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            review_note TEXT DEFAULT '',
            reviewed_by INTEGER DEFAULT NULL,
            reviewed_at TEXT DEFAULT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()

    if request.method == "POST":
        full_name = (request.form.get("full_name") or "").strip()
        username = (request.form.get("username") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        email = (request.form.get("email") or "").strip()
        circuit = (request.form.get("circuit") or "").strip()
        church_name = (request.form.get("church_name") or "").strip()
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""

        if len(full_name) < 3:
            error = "Please enter your full name."
        elif len(username) < 3:
            error = "Username must be at least 3 characters."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        elif password != confirm_password:
            error = "Passwords do not match."
        elif not phone:
            error = "Please enter your phone number."
        elif not circuit:
            error = "Please select your circuit."
        elif not church_name:
            error = "Please enter your Local Church."
        else:
            existing_user = conn.execute(
                "SELECT id FROM users WHERE username=?",
                (username,)
            ).fetchone()

            existing_request = conn.execute(
                """
                SELECT id FROM account_requests
                WHERE username=? AND status='Pending'
                """,
                (username,)
            ).fetchone()

            if existing_user:
                error = "That username is already in use. Please choose another username."
            elif existing_request:
                error = "A registration request for that username is already pending."
            else:
                now = datetime.now().isoformat(timespec="seconds")

                conn.execute(
                    """
                    INSERT INTO account_requests
                    (full_name, username, phone, email, circuit, church_name,
                     password, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending', ?)
                    """,
                    (
                        full_name,
                        username,
                        phone,
                        email,
                        circuit,
                        church_name,
                        generate_password_hash(password),
                        now
                    )
                )
                conn.commit()

                success = (
                    "Registration submitted successfully. "
                    "Your account request is now pending administrator approval."
                )

    return render_template(
        "account_registration.html",
        error=error,
        success=success
    )


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
            if u["role"] == "Member":
                return redirect(url_for("member_dashboard"))
            return redirect(url_for("home"))
        return render_template("login.html", error="Invalid username or password.")
    return render_template("login.html", error="")


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    error = ""
    reset_url = ""

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()

        if not username:
            error = "Please enter your username."
        else:
            u = db().execute(
                "SELECT id, username, active FROM users WHERE username=?",
                (username,)
            ).fetchone()

            if not u or not u["active"]:
                error = "No active account was found for that username."
            else:
                import hashlib
                import secrets

                raw_token = secrets.token_urlsafe(32)
                token_hash = hashlib.sha256(
                    raw_token.encode("utf-8")
                ).hexdigest()

                expires_at = (
                    datetime.now() + timedelta(minutes=30)
                ).isoformat(timespec="seconds")

                db().execute(
                    "UPDATE password_reset_tokens SET used=1 WHERE user_id=? AND used=0",
                    (u["id"],)
                )

                db().execute(
                    """
                    INSERT INTO password_reset_tokens
                    (user_id, token_hash, expires_at, used)
                    VALUES (?, ?, ?, 0)
                    """,
                    (u["id"], token_hash, expires_at)
                )
                db().commit()

                reset_url = url_for(
                    "reset_password",
                    token=raw_token,
                    _external=True
                )

    return render_template(
        "forgot_password.html",
        error=error,
        reset_url=reset_url
    )


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    import hashlib

    token_hash = hashlib.sha256(
        (token or "").encode("utf-8")
    ).hexdigest()

    row = db().execute(
        """
        SELECT prt.id, prt.user_id, prt.expires_at, prt.used
        FROM password_reset_tokens prt
        WHERE prt.token_hash=?
        """,
        (token_hash,)
    ).fetchone()

    if not row or row["used"]:
        return render_template(
            "reset_password.html",
            error="This password reset link is invalid or has already been used.",
            token=""
        )

    try:
        expires = datetime.fromisoformat(row["expires_at"])
    except (TypeError, ValueError):
        expires = datetime.min

    if datetime.now() > expires:
        db().execute(
            "UPDATE password_reset_tokens SET used=1 WHERE id=?",
            (row["id"],)
        )
        db().commit()

        return render_template(
            "reset_password.html",
            error="This password reset link has expired. Please request a new one.",
            token=""
        )

    if request.method == "POST":
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm") or ""

        if len(password) < 8:
            return render_template(
                "reset_password.html",
                error="Password must be at least 8 characters.",
                token=token
            )

        if password != confirm:
            return render_template(
                "reset_password.html",
                error="Passwords do not match.",
                token=token
            )

        db().execute(
            """
            UPDATE users
            SET password=?, must_change_password=0
            WHERE id=?
            """,
            (generate_password_hash(password), row["user_id"])
        )

        db().execute(
            "UPDATE password_reset_tokens SET used=1 WHERE id=?",
            (row["id"],)
        )

        db().commit()

        audit(
            "PASSWORD_RESET",
            "users",
            row["user_id"],
            "Password reset completed"
        )

        return redirect(
            url_for(
                "login",
                reset="success"
            )
        )

    return render_template(
        "reset_password.html",
        error="",
        token=token
    )


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


@app.get("/member-dashboard")
@page_login_required
def member_dashboard():
    u=current_user()
    return render_template("member_dashboard.html")

@app.route("/")
@page_login_required
def home():
    turn_config = {
        "host": os.environ.get(
            "TURN_HOST",
            "global.relay.metered.ca"
        ),
        "username": os.environ.get(
            "TURN_USERNAME",
            ""
        ),
        "credential": os.environ.get(
            "TURN_CREDENTIAL",
            ""
        )
    }

    return render_template(
        "index.html",
        turn_config=turn_config
    )


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
        church_scoped_tables = {"churches", "members", "mission_contacts", "testimonies", "appreciations"}
        if table in church_scoped_tables:
            return rows(f"SELECT * FROM {table} WHERE circuit=? AND church_name=? ORDER BY id DESC", (circuit, church))
        return rows(f"SELECT * FROM {table} WHERE circuit=? ORDER BY id DESC", (circuit,))
    if role == "Local Church Evangelism Officer" and circuit and table == "action_points":
        return rows("SELECT * FROM action_points WHERE circuit=? ORDER BY id DESC", (circuit,))
    return rows(f"SELECT * FROM {table} ORDER BY id DESC")





# Temporary in-memory typing status for Member Care.
# Typing status is intentionally not stored in the database.
MEMBER_CARE_TYPING = {}


def _member_care_schema_conn():
    """Return a standalone SQLite connection for startup schema migrations."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_member_care_case_assignment_schema():
    conn = _member_care_schema_conn()
    try:
        cols = {
            r["name"]
            for r in conn.execute(
                "PRAGMA table_info(customer_care_threads)"
            ).fetchall()
        }

        additions = {
            "assigned_user_id": "INTEGER DEFAULT NULL",
            "assigned_user_name": "TEXT DEFAULT ''",
            "assigned_at": "TEXT DEFAULT ''",
            "assigned_by_user_id": "INTEGER DEFAULT NULL",
            "assigned_by_name": "TEXT DEFAULT ''"
        }

        for name, definition in additions.items():
            if name not in cols:
                conn.execute(
                    f"ALTER TABLE customer_care_threads "
                    f"ADD COLUMN {name} {definition}"
                )

        conn.commit()
    finally:
        conn.close()


def ensure_member_care_timeline_schema():
    conn = _member_care_schema_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS customer_care_timeline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                action TEXT DEFAULT '',
                details TEXT DEFAULT '',
                actor_user_id INTEGER DEFAULT NULL,
                actor_name TEXT DEFAULT '',
                actor_role TEXT DEFAULT '',
                visibility TEXT DEFAULT 'Internal',
                created_at TEXT DEFAULT ''
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_customer_care_timeline_thread
            ON customer_care_timeline(thread_id)
        """)

        conn.commit()
    finally:
        conn.close()


def add_customer_care_timeline(thread_id, action, details="", user=None,
                                visibility="Internal"):
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        actor_id = None
        actor_name = ""
        actor_role = ""

        if user:
            try:
                actor_id = user["id"]
                actor_name = user["username"]
                actor_role = user["role"]
            except Exception:
                pass

        db().execute("""
            INSERT INTO customer_care_timeline
            (
                thread_id,
                action,
                details,
                actor_user_id,
                actor_name,
                actor_role,
                visibility,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            thread_id,
            str(action or ""),
            str(details or ""),
            actor_id,
            actor_name,
            actor_role,
            visibility,
            now
        ))

        db().commit()

    except Exception:
        # Timeline must never break the main Member Care operation.
        pass


def customer_care_scope(u):
    """Return the Customer Care SQL scope allowed for the current user."""
    role = str(u["role"] or "").strip()

    if role == "Member":
        return "t.user_id=?", [u["id"]]

    if role == "Local Church Evangelism Officer":
        return "m.circuit=? AND m.church_name=?", [
            u["circuit"], u["church_name"]
        ]

    if role == "Circuit Coordinator":
        return "m.circuit=?", [u["circuit"]]

    # Full Member Care access for diocesan/admin/customer-care officers.
    if role in {
        "Admin",
        "Officer",
        "Bishop / Diocesan Executive",
        "Evangelism Minister",
        "Planting Officer",
        "Diocesan Secretary",
        "Finance Officer",
        "Auditor"
    }:
        return "1=1", []

    return "1=0", []



def ensure_member_care_attachment_schema():
    """Add attachment fields to the existing Member Care messages table."""
    conn = _member_care_schema_conn()
    try:
        cols = {
            r["name"]
            for r in conn.execute(
                "PRAGMA table_info(customer_care_messages)"
            ).fetchall()
        }

        additions = {
            "attachment_name": "TEXT DEFAULT ''",
            "attachment_url": "TEXT DEFAULT ''",
            "attachment_type": "TEXT DEFAULT ''",
            "attachment_size": "INTEGER DEFAULT 0"
        }

        for name, definition in additions.items():
            if name not in cols:
                conn.execute(
                    f"ALTER TABLE customer_care_messages "
                    f"ADD COLUMN {name} {definition}"
                )

        conn.commit()
    finally:
        conn.close()


@app.get("/api/customer-care")
@login_required
def api_customer_care():
    u = current_user()
    scope, params = customer_care_scope(u)

    sql = f"""
        SELECT t.*
        FROM customer_care_threads t
        LEFT JOIN users m ON t.user_id = m.id
        WHERE {scope}
        ORDER BY
            CASE WHEN t.status='Open' THEN 0 ELSE 1 END,
            t.updated_at DESC,
            t.id DESC
    """

    return jsonify(rows(sql, params))


@app.post("/api/customer-care")
@login_required
def api_customer_care_create():
    u = current_user()
    data = request.get_json(silent=True) or {}

    customer_name = str(
        data.get("customer_name") or
        u["username"] or ""
    ).strip()

    phone = str(data.get("phone") or "").strip()
    email = str(data.get("email") or "").strip()
    subject = str(data.get("subject") or "").strip()
    message = str(data.get("message") or "").strip()

    category = str(
        data.get("category") or "General Assistance"
    ).strip()

    priority = str(
        data.get("priority") or "Normal"
    ).strip()

    allowed_categories = {
        "General Assistance",
        "Registration",
        "Church Records",
        "Baptism",
        "Confirmation",
        "Marriage",
        "Transfer / Relocation",
        "Giving / Tithe",
        "Technical Support",
        "Other"
    }

    allowed_priorities = {"Normal", "High", "Urgent"}

    if category not in allowed_categories:
        return jsonify({"error": "Invalid Member Care category"}), 400

    if priority not in allowed_priorities:
        return jsonify({"error": "Invalid priority"}), 400

    if not message:
        return jsonify({"error": "Message is required"}), 400

    member_id = ""

    if u["role"] == "Member":
        member_id = str(u["member_id"] or "")

    now = datetime.now().isoformat(timespec="seconds")
    thread_id = "MC-" + datetime.now().strftime("%Y%m%d%H%M%S%f")

    cur = db().execute("""
        INSERT INTO customer_care_threads
        (
            thread_id,
            customer_name,
            phone,
            email,
            subject,
            status,
            assigned_to,
            created_at,
            updated_at,
            user_id,
            member_id,
            category,
            priority
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        thread_id,
        customer_name,
        phone,
        email,
        subject,
        "Open",
        "",
        now,
        now,
        u["id"],
        member_id,
        category,
        priority
    ))

    thread_db_id = cur.lastrowid

    db().execute("""
        INSERT INTO customer_care_messages
        (
            thread_id,
            sender_name,
            sender_role,
            message,
            created_at
        )
        VALUES(?,?,?,?,?)
    """, (
        thread_id,
        u["username"],
        u["role"],
        message,
        now
    ))

    db().commit()

    audit(
        "CREATE",
        "customer_care_threads",
        thread_db_id,
        thread_id
    )

    return jsonify({
        "ok": True,
        "id": thread_db_id,
        "thread_id": thread_id,
        "category": category,
        "priority": priority,
        "status": "Open"
    }), 201



@app.get("/api/customer-care/unread-count")
@login_required
def api_customer_care_unread_count():
    u = current_user()
    scope, params = customer_care_scope(u)

    rows = db().execute(f"""
        SELECT
            t.id,
            t.thread_id,
            COUNT(m.id) AS unread_count
        FROM customer_care_threads t
        LEFT JOIN users cu ON t.user_id = cu.id
        LEFT JOIN customer_care_messages m
          ON m.thread_id = t.thread_id
         AND COALESCE(m.read_at,'')=''
         AND m.sender_role<>?
        WHERE {scope}
        GROUP BY t.id, t.thread_id
        HAVING COUNT(m.id) > 0
        ORDER BY t.updated_at DESC
    """, [u["role"]] + params).fetchall()

    total = sum(int(r["unread_count"] or 0) for r in rows)

    return jsonify({
        "ok": True,
        "total": total,
        "conversations": [
            {
                "id": r["id"],
                "thread_id": r["thread_id"],
                "unread_count": int(r["unread_count"] or 0)
            }
            for r in rows
        ]
    })

@app.get("/api/customer-care/<int:rid>")
@login_required
def api_customer_care_detail(rid):
    u = current_user()
    scope, params = customer_care_scope(u)

    sql = f"""
        SELECT t.*
        FROM customer_care_threads t
        LEFT JOIN users m ON t.user_id = m.id
        WHERE t.id=? AND {scope}
    """

    thread = db().execute(
        sql,
        [rid] + params
    ).fetchone()

    if not thread:
        return jsonify({
            "error": "Customer care conversation not found"
        }), 404

    messages = rows("""
        SELECT *
        FROM customer_care_messages
        WHERE thread_id=?
        ORDER BY id ASC
    """, (thread["thread_id"],))

    return jsonify({
        "thread": dict(thread),
        "messages": messages
    })





@app.get("/api/customer-care/<int:rid>/typing")
@login_required
def api_customer_care_typing_status(rid):
    u = current_user()
    scope, params = customer_care_scope(u)

    thread = db().execute(f"""
        SELECT t.*
        FROM customer_care_threads t
        LEFT JOIN users m ON t.user_id = m.id
        WHERE t.id=? AND {scope}
    """, [rid] + params).fetchone()

    if not thread:
        return jsonify({
            "ok": False,
            "error": "Conversation not found"
        }), 404

    status = MEMBER_CARE_TYPING.get(thread["thread_id"])

    # Typing status expires after 4 seconds.
    if status:
        if time.time() - float(status.get("time", 0)) > 4:
            MEMBER_CARE_TYPING.pop(
                thread["thread_id"],
                None
            )
            status = None

    # Never report the current user's own typing status.
    if status and status.get("user_id") == u["id"]:
        status = None

    return jsonify({
        "ok": True,
        "typing": bool(status),
        "username": status.get("username") if status else "",
        "role": status.get("role") if status else ""
    })


@app.post("/api/customer-care/<int:rid>/typing")
@login_required
def api_customer_care_typing(rid):
    u = current_user()
    scope, params = customer_care_scope(u)

    thread = db().execute(f"""
        SELECT t.*
        FROM customer_care_threads t
        LEFT JOIN users m ON t.user_id = m.id
        WHERE t.id=? AND {scope}
    """, [rid] + params).fetchone()

    if not thread:
        return jsonify({
            "ok": False,
            "error": "Conversation not found"
        }), 404

    data = request.get_json(silent=True) or {}
    typing = bool(data.get("typing", False))

    key = thread["thread_id"]

    if typing:
        MEMBER_CARE_TYPING[key] = {
            "user_id": u["id"],
            "username": u["username"],
            "role": u["role"],
            "time": time.time()
        }
    else:
        current = MEMBER_CARE_TYPING.get(key)

        if current and current.get("user_id") == u["id"]:
            MEMBER_CARE_TYPING.pop(key, None)

    return jsonify({"ok": True})

@app.post("/api/customer-care/<int:rid>/read")
@login_required
def api_customer_care_read(rid):
    u = current_user()
    scope, params = customer_care_scope(u)

    thread = db().execute(f"""
        SELECT t.*
        FROM customer_care_threads t
        LEFT JOIN users m ON t.user_id = m.id
        WHERE t.id=? AND {scope}
    """, [rid] + params).fetchone()

    if not thread:
        return jsonify({"ok": False, "error": "Conversation not found"}), 404

    # Mark messages sent by the other side as read.
    db().execute("""
        UPDATE customer_care_messages
        SET read_at=?
        WHERE thread_id=?
          AND COALESCE(read_at,'')=''
          AND sender_role<>?
    """, (
        datetime.now().isoformat(timespec="seconds"),
        thread["thread_id"],
        u["role"]
    ))

    db().commit()

    return jsonify({"ok": True})

@app.post("/api/customer-care/<int:rid>/message")
@login_required
def api_customer_care_message(rid):
    u = current_user()
    scope, params = customer_care_scope(u)

    sql = f"""
        SELECT t.*
        FROM customer_care_threads t
        LEFT JOIN users m ON t.user_id = m.id
        WHERE t.id=? AND {scope}
    """

    thread = db().execute(
        sql,
        [rid] + params
    ).fetchone()

    if not thread:
        return jsonify({
            "error": "Customer care conversation not found"
        }), 404

    data = request.get_json(silent=True) or {}
    message = str(data.get("message") or "").strip()

    if not message:
        return jsonify({
            "error": "Message is required"
        }), 400

    now = datetime.now().isoformat(timespec="seconds")

    db().execute("""
        INSERT INTO customer_care_messages
        (
            thread_id,
            sender_name,
            sender_role,
            message,
            created_at
        )
        VALUES(?,?,?,?,?)
    """, (
        thread["thread_id"],
        u["username"],
        u["role"],
        message,
        now
    ))

    db().execute("""
        UPDATE customer_care_threads
        SET updated_at=?, status='Open'
        WHERE id=?
    """, (now, rid))

    db().commit()

    audit(
        "MESSAGE",
        "customer_care_threads",
        rid,
        "Member Care message sent"
    )

    return jsonify({"ok": True})



@app.post("/api/customer-care/<int:rid>/attachment")
@login_required
def api_customer_care_attachment(rid):
    ensure_member_care_attachment_schema()

    u = current_user()
    scope, params = customer_care_scope(u)

    sql = f"""
        SELECT t.*
        FROM customer_care_threads t
        LEFT JOIN users m ON t.user_id = m.id
        WHERE t.id=? AND {scope}
    """

    thread = db().execute(
        sql,
        [rid] + params
    ).fetchone()

    if not thread:
        return jsonify({
            "error": "Customer care conversation not found"
        }), 404

    uploaded = request.files.get("file")

    if not uploaded or not uploaded.filename:
        return jsonify({
            "error": "Please select a file."
        }), 400

    original_name = secure_filename(uploaded.filename)

    if not original_name:
        return jsonify({
            "error": "Invalid file name."
        }), 400

    allowed_extensions = {
        "jpg", "jpeg", "png", "gif", "webp",
        "pdf", "doc", "docx", "xls", "xlsx",
        "txt"
    }

    ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""

    if ext not in allowed_extensions:
        return jsonify({
            "error": "File type not allowed. Use an image, PDF, Word, Excel or text file."
        }), 400

    # Maximum 8 MB
    uploaded.stream.seek(0, 2)
    size = uploaded.stream.tell()
    uploaded.stream.seek(0)

    if size > 8 * 1024 * 1024:
        return jsonify({
            "error": "File is too large. Maximum size is 8 MB."
        }), 400

    import uuid
    import os

    upload_dir = os.path.join(
        app.root_path,
        "static",
        "uploads",
        "member_care"
    )

    os.makedirs(upload_dir, exist_ok=True)

    stored_name = (
        datetime.now().strftime("%Y%m%d%H%M%S")
        + "_"
        + uuid.uuid4().hex[:12]
        + "."
        + ext
    )

    file_path = os.path.join(upload_dir, stored_name)
    uploaded.save(file_path)

    attachment_url = "/static/uploads/member_care/" + stored_name

    message = str(
        request.form.get("message") or
        "Attachment sent"
    ).strip()

    if not message:
        message = "Attachment sent"

    now = datetime.now().isoformat(timespec="seconds")

    db().execute("""
        INSERT INTO customer_care_messages
        (
            thread_id,
            sender_name,
            sender_role,
            message,
            created_at,
            attachment_name,
            attachment_url,
            attachment_type,
            attachment_size
        )
        VALUES(?,?,?,?,?,?,?,?,?)
    """, (
        thread["thread_id"],
        u["username"],
        u["role"],
        message,
        now,
        original_name,
        attachment_url,
        uploaded.mimetype or "",
        size
    ))

    db().execute("""
        UPDATE customer_care_threads
        SET updated_at=?, status='Open'
        WHERE id=?
    """, (now, rid))

    db().commit()

    audit(
        "ATTACHMENT",
        "customer_care_threads",
        rid,
        "Member Care attachment sent"
    )

    return jsonify({
        "ok": True,
        "attachment": {
            "name": original_name,
            "url": attachment_url,
            "type": uploaded.mimetype or "",
            "size": size
        }
    })



@app.get("/api/customer-care/officers")
@login_required
def api_customer_care_officers():
    u = current_user()

    allowed_roles = {
        "Admin",
        "Bishop / Diocesan Executive",
        "Evangelism Minister",
        "Planting Officer",
        "Diocesan Secretary",
        "Circuit Coordinator",
        "Local Church Evangelism Officer",
        "Finance Officer",
        "Auditor"
    }

    if not u or u["role"] not in allowed_roles:
        return jsonify({
            "ok": False,
            "error": "Not authorized"
        }), 403

    try:
        rows = db().execute("""
            SELECT id, username, role
            FROM users
            WHERE COALESCE(active, 1)=1
              AND role != 'Member'
            ORDER BY username COLLATE NOCASE
        """).fetchall()

        officers = [
            {
                "id": r["id"],
                "username": r["username"],
                "role": r["role"]
            }
            for r in rows
        ]

        return jsonify({
            "ok": True,
            "officers": officers
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": "Unable to load officers",
            "detail": str(e)
        }), 500


@app.post("/api/customer-care/<int:rid>/assign")
@login_required
def api_customer_care_assign(rid):
    u = current_user()

    allowed_roles = {
        "Admin",
        "Bishop / Diocesan Executive",
        "Evangelism Minister",
        "Planting Officer",
        "Diocesan Secretary",
        "Circuit Coordinator",
        "Local Church Evangelism Officer"
    }

    if u["role"] not in allowed_roles:
        return jsonify({"error": "Not authorized to assign cases"}), 403

    scope, params = customer_care_scope(u)

    thread = db().execute(
        f"""
        SELECT t.*
        FROM customer_care_threads t
        LEFT JOIN users m ON t.user_id=m.id
        WHERE t.id=? AND {scope}
        """,
        [rid] + params
    ).fetchone()

    if not thread:
        return jsonify({"error": "Conversation not found"}), 404

    data = request.get_json() or {}

    try:
        officer_id = int(data.get("assigned_user_id"))
    except (TypeError, ValueError):
        officer_id = 0

    if officer_id <= 0:
        return jsonify({"error": "Select an officer"}), 400

    officer = db().execute(
        """
        SELECT id, username, role
        FROM users
        WHERE id=?
          AND COALESCE(active,1)=1
          AND role != 'Member'
        """,
        (officer_id,)
    ).fetchone()

    if not officer:
        return jsonify({"error": "Selected officer was not found"}), 404

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db().execute(
        """
        UPDATE customer_care_threads
        SET assigned_user_id=?,
            assigned_user_name=?,
            assigned_at=?,
            assigned_by_user_id=?,
            assigned_by_name=?,
            updated_at=?
        WHERE id=?
        """,
        (
            officer["id"],
            officer["username"],
            now,
            u["id"],
            u["username"],
            now,
            rid
        )
    )

    db().commit()

    try:
        db().execute(
            """
            INSERT INTO audit_log
            (action, table_name, record_id, username, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "Member Care Case Assigned",
                "customer_care_threads",
                rid,
                u["username"],
                f"Assigned to {officer['username']} ({officer['role']})",
                now
            )
        )
        db().commit()
    except Exception:
        pass

    return jsonify({
        "ok": True,
        "assigned_user_id": officer["id"],
        "assigned_user_name": officer["username"],
        "assigned_role": officer["role"],
        "assigned_at": now,
        "assigned_by_name": u["username"]
    })



@app.get("/api/customer-care/<int:rid>/timeline")
@login_required
def api_customer_care_timeline(rid):
    u = current_user()
    scope, params = customer_care_scope(u)

    thread = db().execute(
        f"""
        SELECT t.*
        FROM customer_care_threads t
        LEFT JOIN users m ON t.user_id=m.id
        WHERE t.id=? AND {scope}
        """,
        [rid] + params
    ).fetchone()

    if not thread:
        return jsonify({"error": "Conversation not found"}), 404

    rows = db().execute(
        """
        SELECT id, action, details, actor_user_id,
               actor_name, actor_role, visibility, created_at
        FROM customer_care_timeline
        WHERE thread_id=?
          AND (
              visibility='Public'
              OR ? != 'Member'
          )
        ORDER BY id ASC
        """,
        (thread["thread_id"], u["role"])
    ).fetchall()

    return jsonify({
        "ok": True,
        "timeline": [dict(r) for r in rows]
    })


@app.post("/api/customer-care/<int:rid>/internal-note")
@login_required
def api_customer_care_internal_note(rid):
    u = current_user()

    allowed_roles = {
        "Admin",
        "Bishop / Diocesan Executive",
        "Evangelism Minister",
        "Planting Officer",
        "Diocesan Secretary",
        "Circuit Coordinator",
        "Local Church Evangelism Officer",
        "Finance Officer",
        "Auditor"
    }

    if u["role"] not in allowed_roles:
        return jsonify({"error": "Not authorized"}), 403

    scope, params = customer_care_scope(u)

    thread = db().execute(
        f"""
        SELECT t.*
        FROM customer_care_threads t
        LEFT JOIN users m ON t.user_id=m.id
        WHERE t.id=? AND {scope}
        """,
        [rid] + params
    ).fetchone()

    if not thread:
        return jsonify({"error": "Conversation not found"}), 404

    data = request.get_json() or {}
    note = str(data.get("note") or "").strip()

    if not note:
        return jsonify({"error": "Enter an internal note"}), 400

    if len(note) > 5000:
        return jsonify({"error": "Internal note is too long"}), 400

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db().execute(
        """
        INSERT INTO customer_care_timeline
        (
            thread_id,
            action,
            details,
            actor_user_id,
            actor_name,
            actor_role,
            visibility,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            thread["thread_id"],
            "Internal Note",
            note,
            u["id"],
            u["username"],
            u["role"],
            "Internal",
            now
        )
    )

    db().execute(
        """
        UPDATE customer_care_threads
        SET updated_at=?
        WHERE id=?
        """,
        (now, rid)
    )

    db().commit()

    return jsonify({
        "ok": True,
        "message": "Internal note added",
        "created_at": now
    })


@app.post("/api/customer-care/<int:rid>/status")
@login_required
def api_customer_care_status(rid):
    u = current_user()
    scope, params = customer_care_scope(u)

    sql = f"""
        SELECT t.*
        FROM customer_care_threads t
        LEFT JOIN users m ON t.user_id = m.id
        WHERE t.id=? AND {scope}
    """

    thread = db().execute(
        sql,
        [rid] + params
    ).fetchone()

    if not thread:
        return jsonify({
            "error": "Customer care conversation not found"
        }), 404

    data = request.get_json(silent=True) or {}

    status = str(
        data.get("status") or ""
    ).strip()

    priority = str(
        data.get("priority") or ""
    ).strip()

    resolution_note = str(
        data.get("resolution_note") or ""
    ).strip()

    allowed_statuses = {
        "Open",
        "In Progress",
        "Pending",
        "Resolved"
    }

    allowed_priorities = {
        "Normal",
        "High",
        "Urgent"
    }

    if status and status not in allowed_statuses:
        return jsonify({
            "error": "Invalid Member Care status"
        }), 400

    if priority and priority not in allowed_priorities:
        return jsonify({
            "error": "Invalid priority"
        }), 400

    current_status = thread["status"] or "Open"
    current_priority = thread["priority"] or "Normal"

    status = status or current_status
    priority = priority or current_priority

    now = datetime.now().isoformat(timespec="seconds")

    resolved_at = (
        now
        if status == "Resolved"
        else ""
    )

    db().execute("""
        UPDATE customer_care_threads
        SET status=?,
            priority=?,
            resolution_note=?,
            resolved_at=?,
            updated_at=?
        WHERE id=?
    """, (
        status,
        priority,
        resolution_note,
        resolved_at,
        now,
        rid
    ))

    db().commit()

    audit(
        "STATUS",
        "customer_care_threads",
        rid,
        f"Member Care updated: status={status}, priority={priority}"
    )

    return jsonify({
        "ok": True,
        "status": status,
        "priority": priority,
        "resolution_note": resolution_note,
        "resolved_at": resolved_at
    })


@app.get("/conference/<room_code>")
@login_required
def conference_join(room_code):
    room = db().execute(
        "SELECT * FROM conference_rooms WHERE room_code=?",
        (room_code,)
    ).fetchone()

    if not room:
        return "Conference room not found.", 404

    return redirect("/?conference=" + room_code)


@app.get("/api/conference/<int:rid>/signals")
@login_required
def api_conference_signals(rid):
    room = db().execute(
        "SELECT room_code FROM conference_rooms WHERE id=?",
        (rid,)
    ).fetchone()

    if not room:
        return jsonify({"error": "Conference not found"}), 404

    room_code = room["room_code"]
    since_id = request.args.get("since_id", 0, type=int)

    rows = db().execute("""
        SELECT id, room_code, sender_id, recipient_id,
               signal_type, payload, created_at
        FROM conference_signals
        WHERE room_code=? AND id>?
        ORDER BY id ASC
        LIMIT 200
    """, (room_code, since_id)).fetchall()

    return jsonify([dict(r) for r in rows])


@app.post("/api/conference/<int:rid>/signals")
@login_required
def api_conference_signal(rid):
    room = db().execute(
        "SELECT room_code FROM conference_rooms WHERE id=?",
        (rid,)
    ).fetchone()

    if not room:
        return jsonify({"error": "Conference not found"}), 404

    data = request.get_json(silent=True) or {}

    sender_id = str(data.get("sender_id") or "").strip()
    recipient_id = str(data.get("recipient_id") or "").strip()
    signal_type = str(data.get("signal_type") or "").strip()
    payload = data.get("payload")

    allowed = {"offer", "answer", "ice", "leave"}

    if not sender_id:
        return jsonify({"error": "sender_id is required"}), 400

    if signal_type not in allowed:
        return jsonify({"error": "Invalid signal type"}), 400

    if payload is None:
        payload = ""

    import json
    if not isinstance(payload, str):
        payload = json.dumps(payload, separators=(",", ":"))

    if len(payload) > 100000:
        return jsonify({"error": "Signal payload is too large"}), 400

    now = datetime.now().isoformat(timespec="seconds")

    cur = db().execute("""
        INSERT INTO conference_signals
        (room_code, sender_id, recipient_id, signal_type, payload, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        room["room_code"],
        sender_id,
        recipient_id,
        signal_type,
        payload,
        now
    ))

    db().commit()

    return jsonify({
        "ok": True,
        "id": cur.lastrowid
    })


@app.delete("/api/conference/<int:rid>/signals")
@login_required
def api_conference_clear_signals(rid):
    room = db().execute(
        "SELECT room_code FROM conference_rooms WHERE id=?",
        (rid,)
    ).fetchone()

    if not room:
        return jsonify({"error": "Conference not found"}), 404

    db().execute(
        "DELETE FROM conference_signals WHERE room_code=?",
        (room["room_code"],)
    )
    db().commit()

    return jsonify({"ok": True})



# =========================================================
# CONFERENCE LIVE PARTICIPANT PRESENCE
# =========================================================

@app.post("/api/conference/<int:rid>/presence")
@login_required
def api_conference_presence(rid):
    room = db().execute(
        "SELECT room_code FROM conference_rooms WHERE id=?",
        (rid,)
    ).fetchone()

    if not room:
        return jsonify({"error": "Conference not found"}), 404

    data = request.get_json(silent=True) or {}

    participant_id = str(data.get("participant_id") or "").strip()
    participant_name = str(data.get("participant_name") or "").strip()
    audio_only = 1 if data.get("audio_only") else 0

    if not participant_id:
        return jsonify({"error": "participant_id is required"}), 400

    now = datetime.now().isoformat(timespec="seconds")

    db().execute("""
        CREATE TABLE IF NOT EXISTS conference_presence(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_code TEXT NOT NULL,
            participant_id TEXT NOT NULL,
            participant_name TEXT DEFAULT '',
            audio_only INTEGER DEFAULT 0,
            last_seen TEXT DEFAULT '',
            UNIQUE(room_code, participant_id)
        )
    """)

    db().execute("""
        INSERT INTO conference_presence
        (room_code, participant_id, participant_name, audio_only, last_seen)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(room_code, participant_id)
        DO UPDATE SET
            participant_name=excluded.participant_name,
            audio_only=excluded.audio_only,
            last_seen=excluded.last_seen
    """, (
        room["room_code"],
        participant_id,
        participant_name,
        audio_only,
        now
    ))

    db().commit()

    return jsonify({
        "ok": True,
        "participant_id": participant_id,
        "last_seen": now
    })


@app.get("/api/conference/<int:rid>/presence")
@login_required
def api_conference_presence_list(rid):
    room = db().execute(
        "SELECT room_code FROM conference_rooms WHERE id=?",
        (rid,)
    ).fetchone()

    if not room:
        return jsonify({"error": "Conference not found"}), 404

    db().execute("""
        CREATE TABLE IF NOT EXISTS conference_presence(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_code TEXT NOT NULL,
            participant_id TEXT NOT NULL,
            participant_name TEXT DEFAULT '',
            audio_only INTEGER DEFAULT 0,
            last_seen TEXT DEFAULT '',
            UNIQUE(room_code, participant_id)
        )
    """)

    cutoff = (
        datetime.now() -
        timedelta(seconds=12)
    ).isoformat(timespec="seconds")

    # Remove stale participants first.
    db().execute("""
        DELETE FROM conference_presence
        WHERE room_code=? AND last_seen < ?
    """, (room["room_code"], cutoff))

    db().commit()

    rows = db().execute("""
        SELECT
            participant_id,
            participant_name,
            audio_only,
            last_seen
        FROM conference_presence
        WHERE room_code=?
        ORDER BY id ASC
    """, (room["room_code"],)).fetchall()

    return jsonify([dict(r) for r in rows])


@app.delete("/api/conference/<int:rid>/presence")
@login_required
def api_conference_presence_leave(rid):
    room = db().execute(
        "SELECT room_code FROM conference_rooms WHERE id=?",
        (rid,)
    ).fetchone()

    if not room:
        return jsonify({"error": "Conference not found"}), 404

    participant_id = str(
        request.args.get("participant_id") or ""
    ).strip()

    if participant_id:
        db().execute("""
            DELETE FROM conference_presence
            WHERE room_code=? AND participant_id=?
        """, (
            room["room_code"],
            participant_id
        ))
        db().commit()

    return jsonify({"ok": True})

@app.get("/api/church-accounts")
@login_required
def api_church_accounts():
    u=current_user(); role=u["role"]
    q="SELECT * FROM church_accounts WHERE active=1"; args=()
    if role=="Circuit Coordinator": q+=" AND account_level=? AND circuit=?"; args=("Circuit",u["circuit"])
    elif role=="Local Church Evangelism Officer": q+=" AND account_level=? AND circuit=? AND church_name=?"; args=("Local Church",u["circuit"],u["church_name"])
    elif role not in {"Admin","Finance Officer","Evangelism Minister","Auditor","Bishop / Diocesan Executive","Diocesan Secretary","Member"}: return jsonify({"error":"Not authorized"}),403
    q+=" ORDER BY account_level,circuit,church_name,id DESC"
    return jsonify([dict(r) for r in db().execute(q,args).fetchall()])
@app.get("/api/conference")
@login_required
def api_conference_rooms():
    rooms = rows("""
        SELECT *
        FROM conference_rooms
        ORDER BY
            CASE WHEN status='Live' THEN 0
                 WHEN status='Scheduled' THEN 1
                 ELSE 2 END,
            meeting_date ASC,
            start_time ASC,
            id DESC
    """)
    return jsonify(rooms)


@app.post("/api/conference")
@login_required
def api_conference_create():
    data = request.get_json(silent=True) or {}

    title = str(data.get("title") or "").strip()
    meeting_date = str(data.get("meeting_date") or "").strip()
    start_time = str(data.get("start_time") or "").strip()
    end_time = str(data.get("end_time") or "").strip()
    meeting_type = str(data.get("meeting_type") or "General Conference").strip()
    circuit = str(data.get("circuit") or "Diocesan").strip()
    organizer = str(data.get("organizer") or current_user()["username"]).strip()
    agenda = str(data.get("agenda") or "").strip()

    if not title:
        return jsonify({"error": "Conference title is required"}), 400

    now = datetime.now().isoformat(timespec="seconds")
    room_code = "CONF-" + datetime.now().strftime("%Y%m%d%H%M%S%f")
    meeting_url = "/conference/" + room_code

    cur = db().execute("""
        INSERT INTO conference_rooms
        (room_code,title,meeting_date,start_time,end_time,meeting_type,
         circuit,organizer,meeting_url,agenda,status,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        room_code, title, meeting_date, start_time, end_time,
        meeting_type, circuit, organizer, meeting_url, agenda,
        "Scheduled", now
    ))

    db().commit()
    audit("CREATE", "conference_rooms", cur.lastrowid, room_code)

    return jsonify({
        "ok": True,
        "id": cur.lastrowid,
        "room_code": room_code
    }), 201


@app.get("/api/conference/<int:rid>")
@login_required
def api_conference_detail(rid):
    room = db().execute(
        "SELECT * FROM conference_rooms WHERE id=?",
        (rid,)
    ).fetchone()

    if not room:
        return jsonify({"error": "Conference not found"}), 404

    participants = rows("""
        SELECT *
        FROM conference_participants
        WHERE room_code=?
        ORDER BY id ASC
    """, (room["room_code"],))

    messages = rows("""
        SELECT *
        FROM conference_messages
        WHERE room_code=?
        ORDER BY id ASC
    """, (room["room_code"],))

    return jsonify({
        "room": dict(room),
        "participants": participants,
        "messages": messages
    })


@app.post("/api/conference/<int:rid>/participant")
@login_required
def api_conference_participant(rid):
    room = db().execute(
        "SELECT * FROM conference_rooms WHERE id=?",
        (rid,)
    ).fetchone()

    if not room:
        return jsonify({"error": "Conference not found"}), 404

    data = request.get_json(silent=True) or {}

    name = str(data.get("participant_name") or "").strip()
    role = str(data.get("participant_role") or "").strip()
    phone = str(data.get("phone") or "").strip()

    if not name:
        return jsonify({"error": "Participant name is required"}), 400

    db().execute("""
        INSERT INTO conference_participants
        (room_code,participant_name,participant_role,phone,status)
        VALUES(?,?,?,?,?)
    """, (
        room["room_code"], name, role, phone, "Invited"
    ))

    db().commit()

    audit(
        "CREATE",
        "conference_participants",
        None,
        f"Participant added to {room['room_code']}"
    )

    return jsonify({"ok": True}), 201


@app.post("/api/conference/<int:rid>/message")
@login_required
def api_conference_message(rid):
    room = db().execute(
        "SELECT * FROM conference_rooms WHERE id=?",
        (rid,)
    ).fetchone()

    if not room:
        return jsonify({"error": "Conference not found"}), 404

    data = request.get_json(silent=True) or {}
    message = str(data.get("message") or "").strip()

    if not message:
        return jsonify({"error": "Message is required"}), 400

    u = current_user()
    now = datetime.now().isoformat(timespec="seconds")

    db().execute("""
        INSERT INTO conference_messages
        (room_code,sender_name,sender_role,message,created_at)
        VALUES(?,?,?,?,?)
    """, (
        room["room_code"],
        u["username"],
        u["role"],
        message,
        now
    ))

    db().commit()

    audit(
        "MESSAGE",
        "conference_rooms",
        rid,
        "Conference message sent"
    )

    return jsonify({"ok": True})


@app.put("/api/conference/<int:rid>")
@login_required
def api_conference_update(rid):
    u = current_user()
    if u["role"] != "Admin":
        return jsonify({"error": "Only Admin can edit conferences."}), 403
    room = db().execute("SELECT * FROM conference_rooms WHERE id=?", (rid,)).fetchone()
    if not room:
        return jsonify({"error": "Conference not found"}), 404
    data = request.get_json(silent=True) or {}
    allowed = ["title","meeting_date","start_time","end_time","meeting_type","circuit","organizer","agenda","status"]
    vals = {k: str(data.get(k) or "").strip() for k in allowed if k in data}
    if "title" in vals and not vals["title"]:
        return jsonify({"error":"Conference title is required"}), 400
    if not vals:
        return jsonify({"error":"No conference fields supplied"}), 400
    sets = ",".join(f"{k}=?" for k in vals)
    db().execute(f"UPDATE conference_rooms SET {sets} WHERE id=?", list(vals.values())+[rid])
    db().commit()
    audit("UPDATE", "conference_rooms", rid, "Conference updated")
    return jsonify({"ok":True})

@app.delete("/api/conference/<int:rid>")
@login_required
def api_conference_delete(rid):
    u = current_user()
    if u["role"] != "Admin":
        return jsonify({"error": "Only Admin can delete conferences."}), 403
    room = db().execute("SELECT room_code FROM conference_rooms WHERE id=?", (rid,)).fetchone()
    if not room:
        return jsonify({"error":"Conference not found"}), 404
    db().execute("DELETE FROM conference_participants WHERE room_code=?", (room["room_code"],))
    db().execute("DELETE FROM conference_messages WHERE room_code=?", (room["room_code"],))
    db().execute("DELETE FROM conference_rooms WHERE id=?", (rid,))
    db().commit()
    audit("DELETE", "conference_rooms", rid, "Conference deleted")
    return jsonify({"ok":True})

@app.post("/api/conference/<int:rid>/status")
@login_required
def api_conference_status(rid):
    room = db().execute(
        "SELECT id FROM conference_rooms WHERE id=?",
        (rid,)
    ).fetchone()

    if not room:
        return jsonify({"error": "Conference not found"}), 404

    data = request.get_json(silent=True) or {}
    status = str(data.get("status") or "").strip()

    allowed = {"Scheduled", "Live", "Completed", "Cancelled"}

    if status not in allowed:
        return jsonify({
            "error": "Invalid conference status"
        }), 400

    db().execute(
        "UPDATE conference_rooms SET status=? WHERE id=?",
        (status, rid)
    )

    db().commit()

    audit(
        "STATUS",
        "conference_rooms",
        rid,
        f"Conference status changed to {status}"
    )

    return jsonify({
        "ok": True,
        "status": status
    })

@app.get("/api/me")
@login_required
def api_me():
    u = current_user()
    return jsonify(dict(u))


def get_connection_url():
    host = request.host
    proto = request.headers.get("X-Forwarded-Proto", request.scheme).split(",")[0].strip()

    # Public/cloud deployment
    if host.endswith(".rumptycloud.app"):
        return f"https://{host}".rstrip("/")

    hostname = host.split(":")[0]
    port = None

    # Preserve an explicitly supplied port.
    if ":" in host:
        try:
            port = int(host.rsplit(":", 1)[1])
        except ValueError:
            pass

    # Local Android/Termux deployment
    if hostname in ("localhost", "127.0.0.1", "::1"):
        import socket

        network_ip = None
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            s.connect(("8.8.8.8", 80))
            network_ip = s.getsockname()[0]
        except Exception:
            pass
        finally:
            s.close()

        if network_ip and not network_ip.startswith("127."):
            hostname = network_ip

        # Flask's normal development port.
        if port is None:
            port = 5000

    if port:
        host = f"{hostname}:{port}"
    else:
        host = hostname

    return f"{proto}://{host}".rstrip("/")


@app.get("/api/connection")
@login_required
def api_connection():
    return jsonify({
        "url": get_connection_url()
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



@app.get("/api/command-centre")
@login_required
def command_centre():
    u = current_user()
    conn = db()

    finance_roles = {
        "Admin",
        "Finance Officer",
        "Auditor",
        "Evangelism Minister",
        "Bishop / Diocesan Executive"
    }
    finance_visible = u["role"] in finance_roles

    # Keep diocesan data available to diocesan roles, while respecting
    # circuit scope for circuit/local-church officers.
    scoped_circuit = ""
    if u["role"] in {"Circuit Coordinator", "Local Church Evangelism Officer"}:
        scoped_circuit = (u.get("circuit") or "").strip()

    def scoped_count(table, where="", args=()):
        sql = f"SELECT COUNT(*) FROM {table}"
        conditions = []
        params = list(args)

        if where:
            conditions.append(where)

        if scoped_circuit and table in {
            "members", "outreach", "church_plants", "mission_contacts",
            "mission_calendar", "action_points", "circuit_reports"
        }:
            conditions.append("circuit = ?")
            params.append(scoped_circuit)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        return conn.execute(sql, params).fetchone()[0] or 0

    def scoped_sum(table, column, where="", args=()):
        sql = f"SELECT COALESCE(SUM({column}),0) FROM {table}"
        conditions = []
        params = list(args)

        if where:
            conditions.append(where)

        if scoped_circuit and table in {
            "outreach", "church_plants", "mission_contacts",
            "mission_calendar", "action_points", "circuit_reports"
        }:
            conditions.append("circuit = ?")
            params.append(scoped_circuit)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        return conn.execute(sql, params).fetchone()[0] or 0

    members = scoped_count("members")
    churches = (
        scoped_count("churches")
        if scoped_circuit
        else conn.execute("SELECT COUNT(*) FROM churches").fetchone()[0] or 0
    )

    plants = scoped_count("church_plants")
    launched = scoped_count(
        "church_plants",
        "LOWER(COALESCE(status,'')) IN ('completed','launched','active')"
    )

    outreach = scoped_count("outreach")
    contacts = scoped_sum("outreach", "attendance")
    decisions = scoped_sum("outreach", "decisions")

    followups_due = scoped_count(
        "mission_contacts",
        """
        next_followup_date IS NOT NULL
        AND TRIM(next_followup_date) <> ''
        AND date(next_followup_date) <= date('now')
        AND LOWER(COALESCE(followup_status,'')) NOT IN
            ('completed','closed','done')
        """
    )

    followups_overdue = scoped_count(
        "mission_contacts",
        """
        next_followup_date IS NOT NULL
        AND TRIM(next_followup_date) <> ''
        AND date(next_followup_date) < date('now')
        AND LOWER(COALESCE(followup_status,'')) NOT IN
            ('completed','closed','done')
        """
    )

    action_open = scoped_count(
        "action_points",
        "LOWER(COALESCE(status,'')) NOT IN ('completed','closed','done')"
    )

    action_overdue = scoped_count(
        "action_points",
        """
        due_date IS NOT NULL
        AND TRIM(due_date) <> ''
        AND date(due_date) < date('now')
        AND LOWER(COALESCE(status,'')) NOT IN
            ('completed','closed','done')
        """
    )

    reports_pending = scoped_count(
        "circuit_reports",
        "LOWER(COALESCE(status,'')) NOT IN ('reviewed','approved','completed')"
    )

    upcoming_sql = """
        SELECT id,event_date,event_time,event_type,circuit,location,
               activity,mission_phase,responsible_person,status
        FROM mission_calendar
        WHERE COALESCE(status,'') NOT IN ('Completed','Cancelled')
          AND date(event_date) >= date('now')
    """
    upcoming_args = []

    if scoped_circuit:
        upcoming_sql += " AND circuit = ?"
        upcoming_args.append(scoped_circuit)

    upcoming_sql += """
        ORDER BY date(event_date) ASC, event_time ASC, id ASC
        LIMIT 10
    """
    upcoming_missions = rows(upcoming_sql, upcoming_args)

    followup_sql = """
        SELECT id,contact_name,phone,circuit,church_name,
               next_followup_date,status,followup_status,assigned_to
        FROM mission_contacts
        WHERE next_followup_date IS NOT NULL
          AND TRIM(next_followup_date) <> ''
          AND date(next_followup_date) <= date('now')
          AND LOWER(COALESCE(followup_status,'')) NOT IN
              ('completed','closed','done')
    """
    followup_args = []

    if scoped_circuit:
        followup_sql += " AND circuit = ?"
        followup_args.append(scoped_circuit)

    followup_sql += """
        ORDER BY date(next_followup_date) ASC, id ASC
        LIMIT 10
    """
    followups = rows(followup_sql, followup_args)

    action_sql = """
        SELECT id,action_item,circuit,responsible_person,
               due_date,priority,status
        FROM action_points
        WHERE LOWER(COALESCE(status,'')) NOT IN
              ('completed','closed','done')
    """
    action_args = []

    if scoped_circuit:
        action_sql += " AND circuit = ?"
        action_args.append(scoped_circuit)

    action_sql += """
        ORDER BY
          CASE WHEN due_date IS NULL OR TRIM(due_date) = '' THEN 1 ELSE 0 END,
          date(due_date) ASC, id ASC
        LIMIT 10
    """
    actions = rows(action_sql, action_args)

    circuit_rows = []
    circuit_source = (
        [scoped_circuit]
        if scoped_circuit
        else [
            r["name"]
            for r in conn.execute(
                "SELECT name FROM circuits ORDER BY name"
            ).fetchall()
        ]
    )

    for circuit_name in circuit_source:
        cmembers = conn.execute(
            "SELECT COUNT(*) FROM members WHERE circuit=?",
            (circuit_name,)
        ).fetchone()[0] or 0

        coutreach = conn.execute(
            "SELECT COUNT(*) FROM outreach WHERE circuit=?",
            (circuit_name,)
        ).fetchone()[0] or 0

        cdecisions = conn.execute(
            "SELECT COALESCE(SUM(decisions),0) FROM outreach WHERE circuit=?",
            (circuit_name,)
        ).fetchone()[0] or 0

        cplants = conn.execute(
            "SELECT COUNT(*) FROM church_plants WHERE circuit=?"
            if False else
            "SELECT COUNT(*) FROM church_plants WHERE axis=?",
            (circuit_name,)
        ).fetchone()[0] or 0

        claunched = conn.execute(
            """
            SELECT COUNT(*) FROM church_plants
            WHERE axis=?
              AND LOWER(COALESCE(status,'')) IN
                  ('completed','launched','active')
            """,
            (circuit_name,)
        ).fetchone()[0] or 0

        cjoined = conn.execute(
            "SELECT COALESCE(SUM(members),0) FROM church_plants WHERE axis=?",
            (circuit_name,)
        ).fetchone()[0] or 0

        circuit_rows.append({
            "circuit": circuit_name,
            "members": cmembers,
            "outreach": coutreach,
            "decisions": cdecisions,
            "plants": cplants,
            "launched": claunched,
            "joined": cjoined,
            "plant_gap": max(0, 5 - cplants)
        })

    finance = {
        "income": 0,
        "expenses": 0,
        "balance": 0,
        "trust_balance": 0,
        "procurement_pipeline": 0
    }

    if finance_visible:
        income = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM income"
        ).fetchone()[0] or 0

        expenses = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM expenses"
        ).fetchone()[0] or 0

        trust_income = conn.execute(
            """
            SELECT COALESCE(SUM(amount),0)
            FROM trust_fund
            WHERE LOWER(COALESCE(transaction_type,'')) IN
                  ('income','receipt','received','credit')
            """
        ).fetchone()[0] or 0

        trust_expense = conn.execute(
            """
            SELECT COALESCE(SUM(amount),0)
            FROM trust_fund
            WHERE LOWER(COALESCE(transaction_type,'')) IN
                  ('expense','payment','paid','debit')
            """
        ).fetchone()[0] or 0

        procurement_pipeline = conn.execute(
            """
            SELECT COALESCE(SUM(
                COALESCE(quantity,1) * COALESCE(estimated_unit_cost,0)
            ),0)
            FROM procurement_requests
            WHERE LOWER(COALESCE(approval_status,'')) NOT IN
                  ('approved','rejected','completed','cancelled')
            """
        ).fetchone()[0] or 0

        finance = {
            "income": income,
            "expenses": expenses,
            "balance": income - expenses,
            "trust_balance": trust_income - trust_expense,
            "procurement_pipeline": procurement_pipeline
        }

    return jsonify({
        "year": datetime.now().year,
        "scope": scoped_circuit or "Delta South Diocese",
        "summary": {
            "members": members,
            "churches": churches,
            "plants": plants,
            "launched": launched,
            "outreach": outreach,
            "contacts": contacts,
            "decisions": decisions,
            "followups_due": followups_due,
            "followups_overdue": followups_overdue,
            "action_open": action_open,
            "action_overdue": action_overdue,
            "reports_pending": reports_pending
        },
        "circuits": circuit_rows,
        "followups": followups,
        "upcoming_missions": upcoming_missions,
        "actions": actions,
        "finance_visible": finance_visible,
        "finance": finance
    })


@app.get("/api/public/churches")
def public_churches():
    return jsonify(rows(
        "SELECT circuit, church_name FROM churches "
        "ORDER BY circuit, church_name"
    ))


@app.get("/api/<table>")
@login_required
def get_table(table):
    u = current_user()
    if table == "member_registrations":
        return jsonify({"error":"Member registrations must use the registration review workflow."}),403
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


@app.post("/api/public/member-registration/<int:rid>/photo")
def upload_member_registration_photo(rid):
    conn = db()

    registration = conn.execute(
        "SELECT registration_id, status FROM member_registrations WHERE id=?",
        (rid,)
    ).fetchone()

    if not registration:
        return jsonify({"error": "Registration not found."}), 404

    if registration["status"] != "Pending":
        return jsonify({
            "error": "Photo can only be uploaded for a pending registration."
        }), 400

    photo = request.files.get("photo")

    if not photo or not photo.filename:
        return jsonify({"error": "Please select a photo."}), 400

    allowed_types = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp"
    }

    extension = allowed_types.get((photo.mimetype or "").lower())

    if not extension:
        return jsonify({
            "error": "Only JPEG, PNG and WebP images are allowed."
        }), 400

    stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    safe_name = f"registration_{rid}_{stamp}{extension}"
    destination = os.path.join(MEMBER_PHOTO_DIR, safe_name)

    try:
        photo.save(destination)

        old = conn.execute(
            "SELECT passport_photo FROM member_registrations WHERE id=?",
            (rid,)
        ).fetchone()

        if old and old["passport_photo"]:
            old_path = os.path.join(
                MEMBER_PHOTO_DIR,
                os.path.basename(old["passport_photo"])
            )
            if os.path.isfile(old_path):
                os.remove(old_path)

        conn.execute(
            "UPDATE member_registrations SET passport_photo=? WHERE id=?",
            (safe_name, rid)
        )
        conn.commit()

    except (OSError, sqlite3.Error):
        conn.rollback()
        if os.path.isfile(destination):
            os.remove(destination)
        return jsonify({"error": "Unable to save the registration photo."}), 500

    return jsonify({
        "ok": True,
        "registration_id": registration["registration_id"],
        "photo_uploaded": True
    }), 201



@app.get("/api/member-registration-photo/<path:filename>")
@login_required
def view_member_registration_photo(filename):
    u = current_user()

    safe_name = os.path.basename(filename)
    if safe_name != filename or not safe_name:
        return jsonify({"error": "Invalid photo filename."}), 400

    allowed_roles = {
        "Admin",
        "Bishop / Diocesan Executive",
        "Evangelism Minister",
        "Planting Officer",
        "Diocesan Secretary",
        "Circuit Coordinator",
        "Local Church Evangelism Officer",
        "Auditor"
    }

    if u["role"] == "Member":
        if not u["member_id"]:
            return jsonify({
                "error": "Member account is not linked to a membership record."
            }), 403

        member = db().execute(
            "SELECT passport_photo FROM members WHERE id=?",
            (u["member_id"],)
        ).fetchone()

        if not member:
            return jsonify({"error": "Member record not found."}), 404

        own_photo = os.path.basename(member["passport_photo"] or "")
        if not own_photo or own_photo != safe_name:
            return jsonify({
                "error": "You are not authorized to view this photo."
            }), 403

    elif u["role"] not in allowed_roles:
        return jsonify({
            "error": "You are not authorized to view member photos."
        }), 403

    photo_path = os.path.join(MEMBER_PHOTO_DIR, safe_name)

    if not os.path.isfile(photo_path):
        return jsonify({"error": "Photo not found."}), 404

    return send_file(
        photo_path,
        conditional=True,
        max_age=0
    )


@app.get("/api/membership-statistics")
@login_required
def membership_statistics():
    u = current_user()

    if u["role"] not in {
        "Admin",
        "Bishop / Diocesan Executive",
        "Evangelism Minister",
        "Planting Officer",
        "Diocesan Secretary",
        "Circuit Coordinator",
        "Local Church Evangelism Officer",
        "Auditor"
    }:
        return jsonify({
            "error": "You do not have permission to view membership statistics."
        }), 403

    conn = db()

    total = conn.execute(
        "SELECT COUNT(*) FROM members"
    ).fetchone()[0]

    male = conn.execute(
        "SELECT COUNT(*) FROM members WHERE LOWER(TRIM(gender))='male'"
    ).fetchone()[0]

    female = conn.execute(
        "SELECT COUNT(*) FROM members WHERE LOWER(TRIM(gender))='female'"
    ).fetchone()[0]

    baptised = conn.execute(
        "SELECT COUNT(*) FROM members WHERE LOWER(TRIM(baptised))='yes'"
    ).fetchone()[0]

    confirmed = conn.execute(
        "SELECT COUNT(*) FROM members WHERE LOWER(TRIM(confirmed))='yes'"
    ).fetchone()[0]

    married = conn.execute(
        "SELECT COUNT(*) FROM members WHERE LOWER(TRIM(marriage))='yes'"
    ).fetchone()[0]

    transferred = conn.execute(
        "SELECT COUNT(*) FROM members WHERE LOWER(TRIM(transfer))='yes'"
    ).fetchone()[0]

    relocated = conn.execute(
        "SELECT COUNT(*) FROM members WHERE LOWER(TRIM(relocated))='yes'"
    ).fetchone()[0]

    new_members = conn.execute("""
        SELECT COUNT(*)
        FROM members
        WHERE date(created_at) >= date('now', '-30 days')
    """).fetchone()[0]

    fellowships = {}
    for row in conn.execute("""
        SELECT fellowship, COUNT(*) AS total
        FROM members
        WHERE TRIM(fellowship) <> ''
        GROUP BY fellowship
        ORDER BY total DESC, fellowship
    """).fetchall():
        fellowships[row["fellowship"]] = row["total"]

    circuits = {}
    for row in conn.execute("""
        SELECT circuit, COUNT(*) AS total
        FROM members
        WHERE TRIM(circuit) <> ''
        GROUP BY circuit
        ORDER BY circuit
    """).fetchall():
        circuits[row["circuit"]] = row["total"]

    churches = {}
    for row in conn.execute("""
        SELECT circuit, church_name, COUNT(*) AS total
        FROM members
        GROUP BY circuit, church_name
        ORDER BY circuit, church_name
    """).fetchall():
        churches.setdefault(row["circuit"], {})[row["church_name"]] = row["total"]


    from datetime import date, datetime

    children_count = 0
    youth_count = 0
    today = date.today()

    for row in conn.execute("SELECT birthday FROM members").fetchall():
        value = (row["birthday"] or "").strip()
        if not value:
            continue
        try:
            birth = datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            continue

        age = today.year - birth.year - (
            (today.month, today.day) < (birth.month, birth.day)
        )

        if 1 <= age <= 12:
            children_count += 1
        elif age >= 13:
            youth_count += 1

    return jsonify({
        "total_members": total,
        "male": male,
        "female": female,
        "youth": youth_count,
        "children": children_count,
        "baptised": baptised,
        "confirmed": confirmed,
        "married": married,
        "new_members": new_members,
        "transferred": transferred,
        "relocated": relocated,
        "conference_awardees": conn.execute(
            "SELECT COUNT(*) FROM members WHERE LOWER(TRIM(conference_awardee))='yes'"
        ).fetchone()[0],
        "diocesan_awardees": conn.execute(
            "SELECT COUNT(*) FROM members WHERE LOWER(TRIM(diocesan_awardee))='yes'"
        ).fetchone()[0],
        "fellowships": fellowships,
        "circuits": circuits,
        "churches": churches
    })


@app.get("/api/member-registrations")
@login_required
def list_member_registrations():
    u = current_user()
    if u["role"] not in {"Admin", "Evangelism Minister"}:
        return jsonify({"error": "You do not have permission to review member registrations."}), 403

    rows = db().execute("""
        SELECT *
        FROM member_registrations
        ORDER BY id DESC
    """).fetchall()

    return jsonify([dict(row) for row in rows])


@app.post("/api/member-registrations/<int:rid>/review")
@login_required
def review_member_registration(rid):
    u = current_user()

    if u["role"] not in {"Admin", "Evangelism Minister"}:
        return jsonify({
            "error": "You do not have permission to approve member registrations."
        }), 403

    data = request.get_json(force=True) or {}
    status = (data.get("status") or "").strip()
    review_note = (data.get("review_note") or "").strip()
    role = (data.get("role") or "").strip()
    circuit = (data.get("circuit") or "").strip()
    church_name = (data.get("church_name") or "").strip()

    if status not in {"Approved", "Rejected", "Under Review"}:
        return jsonify({
            "error": "Status must be Approved, Rejected or Under Review."
        }), 400

    allowed_roles = {
        "Member",
        "Admin",
        "Bishop / Diocesan Executive",
        "Evangelism Minister",
        "Planting Officer",
        "Diocesan Secretary",
        "Circuit Coordinator",
        "Local Church Evangelism Officer",
        "Finance Officer",
        "Auditor"
    }

    if status == "Approved" and role not in allowed_roles:
        return jsonify({"error": "A valid system role is required for approval."}), 400

    conn = db()

    row = conn.execute(
        "SELECT * FROM member_registrations WHERE id=?",
        (rid,)
    ).fetchone()

    if not row:
        return jsonify({"error": "Registration not found."}), 404

    registration = dict(row)

    if registration["status"] == "Approved":
        return jsonify({
            "error": "This registration has already been approved.",
            "member_id": registration.get("approved_member_id", ""),
            "user_id": registration.get("approved_user_id", "")
        }), 400

    if status == "Approved":
        diocesan_roles = {
            "Admin",
            "Bishop / Diocesan Executive",
            "Evangelism Minister",
            "Planting Officer",
            "Diocesan Secretary",
            "Finance Officer",
            "Auditor"
        }

        if role in diocesan_roles:
            circuit = ""
            church_name = ""
        elif role == "Circuit Coordinator":
            if not circuit:
                circuit = registration.get("circuit") or ""
            church_name = ""
        elif role == "Local Church Evangelism Officer":
            if not circuit:
                circuit = registration.get("circuit") or ""
            if not church_name:
                church_name = registration.get("church_name") or ""
        else:
            if not circuit:
                circuit = registration.get("circuit") or ""
            if not church_name:
                church_name = registration.get("church_name") or ""

        assignment_error = validate_user_assignment(
            role,
            circuit,
            church_name
        )

        if assignment_error:
            return jsonify({"error": assignment_error}), 400

        if not registration.get("username"):
            return jsonify({
                "error": "This registration has no username and cannot create a login account."
            }), 400

        if not registration.get("password"):
            return jsonify({
                "error": "This registration has no password and cannot create a login account."
            }), 400

        existing_user = conn.execute(
            "SELECT id FROM users WHERE username=?",
            (registration["username"],)
        ).fetchone()

        if existing_user:
            return jsonify({
                "error": "That username is already in use by another account."
            }), 400

    now = datetime.now().isoformat(timespec="seconds")

    try:
        conn.execute("BEGIN")

        approved_member_id = ""
        approved_user_id = None

        if status == "Approved":
            member_data = {
                "role_position": "Other",
                "circuit": registration.get("circuit") or "",
                "church_name": registration.get("church_name") or ""
            }

            approved_member_id = generate_member_id(member_data)

            member_columns = [
                "member_id",
                "role_position",
                "circuit",
                "church_name",
                "full_name",
                "address",
                "phone",
                "birthday",
                "fellowship",
                "gender",
                "baptised",
                "baptism_date",
                "confirmed",
                "confirmation_date",
                "marriage",
                "marriage_date",
                "work_address",
                "profession_business_trade",
                "passport_photo",
                "notes",
                "created_at"
            ]

            conn.execute("""
                INSERT INTO members(
                    member_id,
                    role_position,
                    circuit,
                    church_name,
                    full_name,
                    address,
                    phone,
                    birthday,
                    fellowship,
                    gender,
                    baptised,
                    baptism_date,
                    confirmed,
                    confirmation_date,
                    marriage,
                    marriage_date,
                    work_address,
                    profession_business_trade,
                    passport_photo,
                    notes,
                    created_at
                )
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                approved_member_id,
                "Other",
                registration.get("circuit") or "",
                registration.get("church_name") or "",
                registration.get("full_name") or "",
                registration.get("address") or "",
                registration.get("phone") or "",
                registration.get("birthday") or "",
                registration.get("fellowship") or "",
                registration.get("gender") or "",
                registration.get("baptised") or "",
                registration.get("baptism_date") or "",
                registration.get("confirmed") or "",
                registration.get("confirmation_date") or "",
                registration.get("marriage") or "",
                registration.get("marriage_date") or "",
                registration.get("work_address") or "",
                registration.get("profession_business_trade") or "",
                registration.get("passport_photo") or "",
                "Approved from merged public member registration.",
                now
            ))

            cur = conn.execute("""
                INSERT INTO users(
                    username,
                    password,
                    role,
                    circuit,
                    church_name,
                    active,
                    must_change_password,
                    created_at,
                    member_id
                )
                VALUES (?, ?, ?, ?, ?, 1, 1, ?, ?)
            """, (
                registration["username"],
                registration["password"],
                role,
                circuit,
                church_name,
                now,
                approved_member_id
            ))

            approved_user_id = cur.lastrowid

            conn.execute("""
                UPDATE member_registrations
                SET status=?,
                    account_status='Approved',
                    review_note=?,
                    reviewed_by=?,
                    reviewed_at=?,
                    approved_member_id=?,
                    approved_user_id=?
                WHERE id=?
            """, (
                status,
                review_note,
                u["username"],
                now,
                approved_member_id,
                approved_user_id,
                rid
            ))

        else:
            conn.execute("""
                UPDATE member_registrations
                SET status=?,
                    account_status=?,
                    review_note=?,
                    reviewed_by=?,
                    reviewed_at=?
                WHERE id=?
            """, (
                status,
                status,
                review_note,
                u["username"],
                now,
                rid
            ))

        conn.commit()

        audit(
            "MEMBER_REGISTRATION_REVIEWED",
            "member_registrations",
            rid,
            json.dumps({
                "status": status,
                "username": registration.get("username", ""),
                "member_id": approved_member_id,
                "user_id": approved_user_id,
                "role": role,
                "circuit": circuit,
                "church_name": church_name
            })
        )

    except sqlite3.IntegrityError as e:
        conn.rollback()
        return jsonify({
            "error": "Could not complete registration approval: " + str(e)
        }), 400

    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({
            "error": "Database error while reviewing registration: " + str(e)
        }), 500

    return jsonify({
        "ok": True,
        "status": status,
        "registration_id": registration["registration_id"],
        "approved_member_id": approved_member_id,
        "approved_user_id": approved_user_id,
        "message": (
            "Registration approved. Official member record and login account created."
            if status == "Approved"
            else f"Registration marked {status}."
        )
    })
    
@app.get("/member-registration")
def public_member_registration_page():
    return render_template("member_registration.html")


@app.post("/api/public/member-registration")
def public_member_registration():
    data = request.get_json(force=True) or {}

    circuit = (data.get("circuit") or "").strip()
    church_name = (data.get("church_name") or "").strip()
    full_name = (data.get("full_name") or "").strip()
    phone = (data.get("phone") or "").strip()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    confirm_password = data.get("confirm_password") or ""

    if not circuit or not church_name or not full_name:
        return jsonify({
            "error": "Circuit, Local Church and Full Name are required."
        }), 400

    if len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters."}), 400

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters."}), 400

    if password != confirm_password:
        return jsonify({"error": "Passwords do not match."}), 400

    existing_username = db().execute(
        "SELECT id FROM users WHERE username=?",
        (username,)
    ).fetchone()

    if existing_username:
        return jsonify({
            "error": "That username is already in use. Please choose another username."
        }), 400

    pending_username = db().execute(
        """SELECT id FROM member_registrations
           WHERE username=? AND status IN ('Pending','Under Review')""",
        (username,)
    ).fetchone()

    if pending_username:
        return jsonify({
            "error": "A registration using that username is already pending."
        }), 400

    if circuit not in {"Effurun Circuit", "Warri Circuit", "Sapele Circuit", "Steel Town Circuit"}:
        return jsonify({"error": "Invalid circuit selected."}), 400

    church = db().execute(
        "SELECT id FROM churches WHERE circuit=? AND church_name=?",
        (circuit, church_name)
    ).fetchone()

    if not church:
        return jsonify({
            "error": "The selected Local Church does not belong to the selected Circuit."
        }), 400

    # Prevent duplicate registrations by phone number.
    if phone:
        duplicate = db().execute(
            """SELECT id FROM member_registrations
               WHERE phone=? AND status IN ('Pending','Under Review','Approved')
               ORDER BY id DESC LIMIT 1""",
            (phone,)
        ).fetchone()
        if duplicate:
            return jsonify({
                "error": "This phone number has already been used for a membership registration."
            }), 400

    # Prevent the same person from registering again under a different phone
    # number or with different capitalization/extra spaces.
    import re
    normalized_name = re.sub(r"\s+", " ", full_name).strip().lower()

    registration_rows = db().execute(
        """SELECT id, full_name, status
           FROM member_registrations
           WHERE status IN ('Pending','Under Review','Approved')"""
    ).fetchall()

    for existing in registration_rows:
        existing_name = re.sub(r"\s+", " ", (existing["full_name"] or "")).strip().lower()
        if existing_name == normalized_name:
            return jsonify({
                "error": "This person has already submitted a membership registration. Please contact the church office if this is an error."
            }), 400

    member_rows = db().execute(
        "SELECT id, full_name FROM members"
    ).fetchall()

    for existing in member_rows:
        existing_name = re.sub(r"\s+", " ", (existing["full_name"] or "")).strip().lower()
        if existing_name == normalized_name:
            return jsonify({
                "error": "This person is already registered as a church member. A second registration is not allowed."
            }), 400

    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    registration_id = f"DSD-REG-{stamp}"

    try:
        cur = db().execute(
            """INSERT INTO member_registrations(
                registration_id,circuit,church_name,full_name,gender,address,phone,
                email,birthday,fellowship,baptised,baptism_date,confirmed,
                confirmation_date,marriage,marriage_date,work_address,
                profession_business_trade,passport_photo,status,created_at,
                username,password,account_status
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                registration_id,
                circuit,
                church_name,
                full_name,
                (data.get("gender") or "").strip(),
                (data.get("address") or "").strip(),
                phone,
                (data.get("email") or "").strip(),
                (data.get("birthday") or "").strip(),
                (data.get("fellowship") or "").strip(),
                (data.get("baptised") or "No").strip(),
                (data.get("baptism_date") or "").strip(),
                (data.get("confirmed") or "No").strip(),
                (data.get("confirmation_date") or "").strip(),
                (data.get("marriage") or "No").strip(),
                (data.get("marriage_date") or "").strip(),
                (data.get("work_address") or "").strip(),
                (data.get("profession_business_trade") or "").strip(),
                (data.get("passport_photo") or "").strip(),
                "Pending",
                datetime.now().isoformat(timespec="seconds"),
                username,
                generate_password_hash(password),
                "Pending"
            )
        )
        db().commit()
    except sqlite3.IntegrityError:
        db().rollback()
        return jsonify({
            "error": "Could not create the registration. Please try again."
        }), 400
    except sqlite3.Error:
        db().rollback()
        return jsonify({
            "error": "Database error while submitting registration."
        }), 500

    return jsonify({
        "ok": True,
        "id": cur.lastrowid,
        "registration_id": registration_id,
        "status": "Pending",
        "message": "Registration submitted successfully. It will be reviewed by an authorized church officer."
    }), 201


@app.post("/api/<table>")
@login_required
def create_row(table):
    u = current_user()
    if table == "member_registrations":
        return jsonify({"error":"Member registrations must use the registration review workflow."}),403
    if table not in TABLES or not role_allows_table(u, table, "POST"):
        return jsonify({"error":"You do not have permission to add records here."}),403
    data = request.get_json(force=True) or {}
    if table == "income" and data.get("member_id"):
        linked_member=db().execute("SELECT full_name,circuit,church_name FROM members WHERE id=?",(data.get("member_id"),)).fetchone()
        if not linked_member:
            return jsonify({"error":"The selected member record was not found."}),404
        data["donor_name"]=linked_member["full_name"]
        data["circuit"]=linked_member["circuit"]
        data["church_name"]=linked_member["church_name"]

    cols = [c for c in TABLES[table] if c in data]
    required = {"members":["circuit","church_name","full_name"],"churches":["circuit","church_name"],"commitments":["donor_name"],"income":["date","amount"],
      "expenses":["date","category","description","circuit","church_name","amount"],"equipment":["item"],"trust_fund":["date","transaction_type","amount"],"mission_budgets":["year","budget_name"],"procurement_requests":["request_date","item"],"church_plants":["year","location"],"planting_prospects":["prospect_id","location"],
      "outreach":["date","location"],"mission_calendar":["event_date","location"],"sponsors":["name"],
      "testimonies":["date","testimony"],
      "appreciations":["date","recipient","message"],
      "report_periods":["period_name","start_date","end_date"],
      "circuit_reports":["circuit"],
      "action_points":["action_item"],
      "meetings":["meeting_date"],
      "diocesan_reviews":["review_date","executive_summary"],
      "mission_teams":["team_name"],
      "mission_contacts":["contact_name"],"church_accounts":["bank_name","account_name","account_number"]}[table]
    missing = [c for c in required if not data.get(c) and data.get(c) != 0]
    if missing: return jsonify({"error":"Required: "+", ".join(missing)}),400
    if u["role"] in {"Circuit Coordinator", "Local Church Evangelism Officer"} and data.get("circuit") and u["circuit"] and data["circuit"] != u["circuit"]:
        return jsonify({"error":"You can only create records for your assigned circuit."}),403

    if u["role"] == "Local Church Evangelism Officer" and "church_name" in TABLES[table]:
        if not u["church_name"]:
            return jsonify({"error":"Your account has no assigned church."}),403
        if not data.get("church_name"):
            data["church_name"] = u["church_name"]
        elif data["church_name"] != u["church_name"]:
            return jsonify({"error":"You can only create records for your assigned church."}),403

    if table == "members":
        if u["role"] == "Local Church Evangelism Officer" and data.get("church_name") != u["church_name"]:
            return jsonify({"error":"You can only create members for your assigned church."}),403
        # Prevent duplicate official member records.
        import re
        normalized_name = re.sub(r"\s+", " ", str(data.get("full_name") or "")).strip().lower()

        existing_members = db().execute(
            "SELECT id, full_name, member_id FROM members"
        ).fetchall()

        for existing in existing_members:
            existing_name = re.sub(
                r"\s+", " ", str(existing["full_name"] or "")
            ).strip().lower()

            if existing_name == normalized_name:
                return jsonify({
                    "error": f'This person is already registered as a church member ({existing["member_id"]}). A duplicate member record cannot be created.'
                }), 400

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
    if u["role"] == "Local Church Evangelism Officer" and "church_name" in existing.keys() and u["church_name"] and existing["church_name"] != u["church_name"]:
        return jsonify({"error":"You can only view records for your assigned church."}),403
    return jsonify(dict(existing))

@app.put("/api/<table>/<int:rid>")
@login_required
def update_row(table, rid):
    u = current_user()
    if table == "member_registrations":
        return jsonify({"error":"Member registrations must use the registration review workflow."}),403
    if table not in TABLES or not role_allows_table(u, table, "PUT"):
        return jsonify({"error":"You do not have permission to edit records here."}),403
    existing = db().execute(f"SELECT * FROM {table} WHERE id=?", (rid,)).fetchone()
    if not existing:
        return jsonify({"error":"Record not found"}),404
    if u["role"] == "Circuit Coordinator" and "circuit" in existing.keys() and u["circuit"] and existing["circuit"] != u["circuit"]:
        return jsonify({"error":"You can only edit records for your assigned circuit."}),403
    if u["role"] == "Local Church Evangelism Officer" and "church_name" in existing.keys() and u["church_name"] and existing["church_name"] != u["church_name"]:
        return jsonify({"error":"You can only edit records for your assigned church."}),403
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
    if table == "member_registrations":
        return jsonify({"error":"Member registrations must use the registration review workflow."}),403
    if table not in TABLES or not role_allows_table(u, table, "DELETE"):
        return jsonify({"error":"You do not have permission to delete records here."}),403
    existing = db().execute(f"SELECT * FROM {table} WHERE id=?", (rid,)).fetchone()
    if not existing: return jsonify({"error":"Record not found"}),404
    if u["role"] == "Circuit Coordinator" and "circuit" in existing.keys() and u["circuit"] and existing["circuit"] != u["circuit"]:
        return jsonify({"error":"You can only delete records for your assigned circuit."}),403
    if u["role"] == "Local Church Evangelism Officer" and "church_name" in existing.keys() and u["church_name"] and existing["church_name"] != u["church_name"]:
        return jsonify({"error":"You can only delete records for your assigned church."}),403
    db().execute(f"DELETE FROM {table} WHERE id=?",(rid,)); db().commit(); audit("DELETE",table,rid,"")
    return jsonify({"ok":True})



@app.get("/api/account-requests")
@login_required
def list_account_requests():
    u = current_user()

    if u["role"] != "Admin":
        return jsonify({"error": "Administrator access required."}), 403

    requests = db().execute(
        """
        SELECT id, full_name, username, phone, email,
               circuit, church_name, status, review_note,
               reviewed_at, created_at
        FROM account_requests
        ORDER BY
            CASE WHEN status='Pending' THEN 0 ELSE 1 END,
            created_at DESC
        """
    ).fetchall()

    return jsonify([dict(r) for r in requests])


@app.post("/api/account-requests/<int:rid>/approve")
@login_required
def approve_account_request(rid):
    u = current_user()

    if u["role"] != "Admin":
        return jsonify({"error": "Administrator access required."}), 403

    data = request.get_json(force=True) or {}

    role = (data.get("role") or "").strip()
    circuit = (data.get("circuit") or "").strip()
    church_name = (data.get("church_name") or "").strip()

    allowed_roles = [
        "Admin",
        "Bishop / Diocesan Executive",
        "Evangelism Minister",
        "Planting Officer",
        "Diocesan Secretary",
        "Circuit Coordinator",
        "Local Church Evangelism Officer",
        "Finance Officer",
        "Auditor"
    ]

    if role not in allowed_roles:
        return jsonify({"error": "Invalid role selected."}), 400

    req = db().execute(
        """
        SELECT *
        FROM account_requests
        WHERE id=? AND status='Pending'
        """,
        (rid,)
    ).fetchone()

    if not req:
        return jsonify({
            "error": "Pending registration request not found."
        }), 404

    diocesan_roles = {
        "Admin",
        "Bishop / Diocesan Executive",
        "Evangelism Minister",
        "Planting Officer",
        "Diocesan Secretary",
        "Finance Officer",
        "Auditor"
    }

    if role in diocesan_roles:
        circuit = ""
        church_name = ""
    else:
        if not circuit:
            circuit = req["circuit"] or ""

        if not church_name:
            church_name = req["church_name"] or ""

    assignment_error = validate_user_assignment(
        role,
        circuit,
        church_name
    )

    if assignment_error:
        return jsonify({"error": assignment_error}), 400

    existing = db().execute(
        "SELECT id FROM users WHERE username=?",
        (req["username"],)
    ).fetchone()

    if existing:
        return jsonify({
            "error": "That username is already in use."
        }), 400

    now = datetime.now().isoformat(timespec="seconds")

    try:
        cur = db().execute(
            """
            INSERT INTO users
            (username, password, role, circuit, church_name,
             active, must_change_password, created_at, member_id)
            VALUES (?, ?, ?, ?, ?, 1, 1, ?, NULL)
            """,
            (
                req["username"],
                req["password"],
                role,
                circuit,
                church_name,
                now
            )
        )

        db().execute(
            """
            UPDATE account_requests
            SET status='Approved',
                review_note=?,
                reviewed_by=?,
                reviewed_at=?
            WHERE id=?
            """,
            (
                "Account approved by administrator.",
                u["id"],
                now,
                rid
            )
        )

        db().commit()

        audit(
            "ACCOUNT_REGISTRATION_APPROVED",
            "account_requests",
            rid,
            json.dumps({
                "username": req["username"],
                "user_id": cur.lastrowid,
                "role": role,
                "circuit": circuit,
                "church_name": church_name
            })
        )

        return jsonify({
            "ok": True,
            "user_id": cur.lastrowid,
            "message": "Account approved successfully."
        }), 201

    except sqlite3.IntegrityError:
        db().rollback()
        return jsonify({
            "error": "Unable to create the account because the username already exists."
        }), 400


@app.post("/api/account-requests/<int:rid>/reject")
@login_required
def reject_account_request(rid):
    u = current_user()

    if u["role"] != "Admin":
        return jsonify({"error": "Administrator access required."}), 403

    data = request.get_json(force=True) or {}
    note = (data.get("review_note") or "").strip()

    req = db().execute(
        """
        SELECT id
        FROM account_requests
        WHERE id=? AND status='Pending'
        """,
        (rid,)
    ).fetchone()

    if not req:
        return jsonify({
            "error": "Pending registration request not found."
        }), 404

    now = datetime.now().isoformat(timespec="seconds")

    db().execute(
        """
        UPDATE account_requests
        SET status='Rejected',
            review_note=?,
            reviewed_by=?,
            reviewed_at=?
        WHERE id=?
        """,
        (
            note or "Registration request rejected by administrator.",
            u["id"],
            now,
            rid
        )
    )

    db().commit()

    audit(
        "ACCOUNT_REGISTRATION_REJECTED",
        "account_requests",
        rid,
        note
    )

    return jsonify({
        "ok": True,
        "message": "Registration request rejected."
    })


@app.get("/api/user-linkable-members")
@login_required
def user_linkable_members():
    u = current_user()
    if u["role"] != "Admin":
        return jsonify({"error": "Administrator access required."}), 403

    return jsonify(rows("""
        SELECT m.id, m.member_id, m.full_name, m.circuit, m.church_name,
               u.id AS linked_user_id, u.username AS linked_username
        FROM members m
        LEFT JOIN users u ON u.member_id = m.id
        ORDER BY m.full_name
    """))


@app.get("/api/users")
@login_required
def get_users():
    u = current_user()
    if u["role"] != "Admin": return jsonify({"error":"Administrator access required."}),403
    return jsonify(rows("""
        SELECT u.id, u.username, u.role, u.circuit, u.church_name,
               u.active, u.must_change_password, u.created_at,
               u.member_id, m.full_name AS member_name,
               m.member_id AS official_member_code
        FROM users u
        LEFT JOIN members m ON m.id = u.member_id
        ORDER BY u.username
    """))


@app.post("/api/users")
@login_required
def create_user():
    u = current_user()
    if u["role"] != "Admin":
        return jsonify({"error": "Administrator access required."}), 403

    data = request.get_json(force=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    role = data.get("role") or "Member"

    if len(username) < 3 or len(password) < 8:
        return jsonify({
            "error": "Username must be at least 3 characters and password at least 8 characters."
        }), 400

    if role not in ROLES:
        return jsonify({"error": "Invalid role."}), 400

    try:
        member_id = int(data.get("member_id") or 0)
    except (ValueError, TypeError):
        return jsonify({"error": "Select a valid official member record."}), 400

    if member_id <= 0:
        return jsonify({"error": "Select an official member record for this account."}), 400

    conn = db()
    linked = conn.execute(
        "SELECT id, circuit, church_name FROM members WHERE id=?",
        (member_id,)
    ).fetchone()

    if not linked:
        return jsonify({"error": "The selected member record was not found."}), 400

    existing = conn.execute(
        "SELECT id, username FROM users WHERE member_id=?",
        (member_id,)
    ).fetchone()

    if existing:
        return jsonify({
            "error": f"This member is already linked to account: {existing['username']}."
        }), 400

    circuit = (data.get("circuit") or "").strip()
    church_name = (data.get("church_name") or "").strip()

    # Preserve the established role-assignment rules.
    if role in DIOSAN_ROLES:
        circuit = ""
        church_name = ""
    elif role == "Circuit Coordinator":
        circuit = linked["circuit"] or circuit
        church_name = ""
    elif role in {"Member", "Local Church Evangelism Officer"}:
        circuit = linked["circuit"] or circuit
        church_name = linked["church_name"] or church_name

    assignment_error = validate_user_assignment(role, circuit, church_name)
    if assignment_error:
        return jsonify({"error": assignment_error}), 400

    try:
        cur = conn.execute("""
            INSERT INTO users(
                username, password, role, circuit, church_name,
                active, must_change_password, created_at, member_id
            ) VALUES (?, ?, ?, ?, ?, 1, 1, ?, ?)
        """, (
            username,
            generate_password_hash(password),
            role,
            circuit,
            church_name,
            datetime.now().isoformat(timespec="seconds"),
            member_id
        ))
        conn.commit()
        audit("CREATE", "users", cur.lastrowid, json.dumps({
            "username": username,
            "role": role,
            "member_id": member_id
        }))
        return jsonify({"id": cur.lastrowid, "ok": True}), 201

    except sqlite3.IntegrityError:
        conn.rollback()
        return jsonify({"error": "That username or membership link already exists."}), 400


@app.put("/api/users/<int:uid>")
@login_required
def update_user(uid):
    u = current_user()
    if u["role"] != "Admin":
        return jsonify({"error": "Administrator access required."}), 403

    conn = db()
    target = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if not target:
        return jsonify({"error": "User not found."}), 404

    data = request.get_json(force=True) or {}
    role = data.get("role", target["role"]) or "Member"
    circuit = (data.get("circuit", target["circuit"]) or "").strip()
    church_name = (data.get("church_name", target["church_name"]) or "").strip()

    if role not in ROLES:
        return jsonify({"error": "Invalid role."}), 400

    member_id = target["member_id"]
    if "member_id" in data:
        try:
            member_id = int(data.get("member_id") or 0)
        except (ValueError, TypeError):
            return jsonify({"error": "Select a valid official member record."}), 400

        if member_id <= 0:
            return jsonify({"error": "An account must remain linked to an official member record."}), 400

    linked = conn.execute(
        "SELECT id, circuit, church_name FROM members WHERE id=?",
        (member_id,)
    ).fetchone()

    if not linked:
        return jsonify({"error": "The selected member record was not found."}), 400

    existing = conn.execute(
        "SELECT id, username FROM users WHERE member_id=? AND id<>?",
        (member_id, uid)
    ).fetchone()

    if existing:
        return jsonify({
            "error": f"This member is already linked to account: {existing['username']}."
        }), 400

    if role in DIOSAN_ROLES:
        circuit = ""
        church_name = ""
    elif role == "Circuit Coordinator":
        circuit = linked["circuit"] or circuit
        church_name = ""
    elif role in {"Member", "Local Church Evangelism Officer"}:
        circuit = linked["circuit"] or circuit
        church_name = linked["church_name"] or church_name

    assignment_error = validate_user_assignment(role, circuit, church_name)
    if assignment_error:
        return jsonify({"error": assignment_error}), 400

    conn.execute("""
        UPDATE users
        SET role=?, circuit=?, church_name=?, member_id=?
        WHERE id=?
    """, (role, circuit, church_name, member_id, uid))
    conn.commit()

    audit("USER_ASSIGNMENT_UPDATED", "users", uid, json.dumps({
        "role": role,
        "circuit": circuit,
        "church_name": church_name,
        "member_id": member_id
    }))
    return jsonify({"ok": True})


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
        planned=count("church_plants","year=?"+((" AND circuit=?") if scope else ""),(yr,scope) if scope else (yr,)); launched_y=count("church_plants","year=? AND status IN ('Launched','Growing','Active')"+((" AND circuit=?") if scope else ""),(yr,scope) if scope else (yr,)); years.append({"year":yr,"target":5,"planned":planned,"launched":launched_y,"remaining":max(0,5-launched_y)})
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
    """Build and refresh the table/column map after the database schema is initialized."""
    global TABLES

    conn = db()
    names = set(ALL_TABLES)
    names.update({"circuits", "users", "audit_log", "backup_history"})

    table_map = {}

    for name in sorted(names):
        try:
            cols = [
                row[1]
                for row in conn.execute(
                    f"PRAGMA table_info({name})"
                ).fetchall()
            ]

            if cols:
                table_map[name] = cols

        except sqlite3.Error:
            continue

    TABLES = table_map
    return TABLES

with app.app_context():
    init_db()
    ensure_runtime_schema()
    ensure_member_passport_photo_schema()
    ensure_member_care_attachment_schema()
    ensure_member_care_case_assignment_schema()
    ensure_member_care_timeline_schema()
    TABLES = build_table_map()
@app.post("/api/payment/settings")
@login_required
def api_payment_settings_save():
    if current_user()["role"]!="Admin": return jsonify({"error":"Only Admin can change payment settings"}),403
    d=request.get_json() or {}
    provider=d.get("provider","Monnify")
    enabled=1 if d.get("enabled") else 0
    db().execute("DELETE FROM payment_settings")
    db().execute("INSERT INTO payment_settings(provider,enabled,public_key,contract_code) VALUES(?,?,?,?)",(provider,enabled,d.get("public_key",""),d.get("contract_code","")))
    db().commit()
    return jsonify({"ok":True,"message":"Payment settings saved."})

@app.get("/api/payment/settings")
@login_required
def api_payment_settings():
    if current_user()["role"]!="Admin": return jsonify({"error":"Only Admin can view payment settings"}),403
    r=db().execute("SELECT provider,enabled,public_key,contract_code FROM payment_settings ORDER BY id DESC LIMIT 1").fetchone()
    return jsonify(dict(r) if r else {"provider":"Monnify","enabled":0,"public_key":"","contract_code":""})





@app.get("/api/payment-history/<reference>")
@login_required
def api_payment_details(reference):
    u = current_user()
    allowed = {
        "Admin",
        "Finance Officer",
        "Auditor",
        "Evangelism Minister",
        "Bishop / Diocesan Executive",
        "Diocesan Secretary",
    }

    if u["role"] not in allowed:
        return jsonify({"error":"Not authorized"}),403

    row = db().execute(
        """
        SELECT
            p.id,
            p.reference,
            p.gateway,
            p.status,
            p.amount,
            p.currency,
            p.purpose,
            p.account_level,
            p.circuit,
            p.church_name,
            p.church_account_id,
            p.member_id,
            p.donor_name,
            p.donor_email,
            p.donor_phone,
            p.payment_method,
            p.gateway_transaction_id,
            p.paid_at,
            p.created_at,
            ca.bank_name,
            ca.account_name,
            ca.account_number,
            ca.account_type,
            ca.branch
        FROM payment_transactions p
        LEFT JOIN church_accounts ca
            ON ca.id=p.church_account_id
        WHERE p.reference=?
        LIMIT 1
        """,
        (reference,)
    ).fetchone()

    if not row:
        return jsonify({"error":"Payment transaction not found."}),404

    return jsonify(dict(row))




@app.post("/api/payment-reconciliation/<reference>/reconcile")
@login_required
def api_payment_reconciliation_reconcile(reference):
    u=current_user()

    allowed={
        "Admin",
        "Finance Officer",
        "Evangelism Minister",
    }

    if u["role"] not in allowed:
        return jsonify({"error":"Only authorized finance officers can reconcile payments."}),403

    reference=str(reference or "").strip()

    if not reference:
        return jsonify({"error":"Payment reference is required."}),400

    payment=db().execute(
        "SELECT * FROM payment_transactions WHERE reference=? LIMIT 1",
        (reference,)
    ).fetchone()

    if not payment:
        return jsonify({"error":"Payment transaction not found."}),404

    if str(payment["status"] or "").lower()!="paid":
        return jsonify({
            "error":"Only successful paid transactions can be reconciled.",
            "status":payment["status"]
        }),409

    existing=db().execute(
        "SELECT * FROM income WHERE reference=? LIMIT 1",
        (reference,)
    ).fetchone()

    if existing:
        return jsonify({
            "ok":True,
            "already_reconciled":True,
            "message":"This payment is already linked to an income record.",
            "income_id":existing["id"],
            "reference":reference
        }),200

    amount=float(payment["amount"] or 0)

    if amount<=0:
        return jsonify({"error":"Payment amount is invalid."}),409

    donor_name=payment["donor_name"] or "Online Donor"
    purpose=payment["purpose"] or "General Evangelism"

    db().execute(
        """
        INSERT INTO income
        (
            date,
            donor_name,
            source,
            fund,
            amount,
            method,
            reference,
            received_by,
            notes,
            member_id,
            church_account_id
        )
        VALUES(
            date('now'),
            ?,?,?,?,?,?,?,?,?,?
        )
        """,
        (
            donor_name,
            "Online Payment",
            purpose,
            amount,
            payment["payment_method"] or "Paystack",
            reference,
            u["username"] if "username" in u.keys() else u["role"],
            "Manually reconciled online payment",
            payment["member_id"],
            payment["church_account_id"]
        )
    )

    db().commit()

    new_income=db().execute(
        "SELECT id FROM income WHERE reference=? LIMIT 1",
        (reference,)
    ).fetchone()

    audit_details = {
        "payment_reference": reference,
        "income_id": new_income["id"] if new_income else None,
        "amount": amount,
        "action": "Manual payment reconciliation"
    }

    db().execute(
        """
        INSERT INTO audit_log
        (happened_at, action, table_name, record_id, details, user_id, username)
        VALUES(datetime('now'),?,?,?,?,?,?)
        """,
        (
            "MANUAL_RECONCILIATION",
            "income",
            new_income["id"] if new_income else None,
            str(audit_details),
            u.get("id"),
            u.get("username") or u.get("role")
        )
    )
    db().commit()

    return jsonify({
        "ok":True,
        "already_reconciled":False,
        "message":"Payment successfully reconciled into income.",
        "income_id":new_income["id"] if new_income else None,
        "reference":reference,
        "amount":amount
    }),201

@app.get("/api/payment-reconciliation/<reference>")
@login_required
def api_payment_reconciliation_details(reference):
    u=current_user()

    allowed={
        "Admin",
        "Finance Officer",
        "Auditor",
        "Evangelism Minister",
        "Bishop / Diocesan Executive",
        "Diocesan Secretary",
    }

    if u["role"] not in allowed:
        return jsonify({"error":"Not authorized"}),403

    row=db().execute(
        """
        SELECT
            p.id,
            p.reference,
            p.status AS payment_status,
            p.amount AS payment_amount,
            p.currency,
            p.purpose,
            p.account_level,
            p.circuit,
            p.church_name,
            p.church_account_id,
            p.member_id,
            p.donor_name,
            p.donor_email,
            p.donor_phone,
            p.payment_method,
            p.gateway,
            p.gateway_transaction_id,
            p.paid_at,
            p.created_at AS payment_created_at,

            i.id AS income_id,
            i.reference AS income_reference,
            i.amount AS income_amount,
            i.date AS income_date,
            i.donor_name AS income_donor_name,
            i.source AS income_source,
            i.fund AS income_fund,
            i.method AS income_method,
            i.received_by,
            i.notes AS income_notes,
            i.member_id AS income_member_id,

            ca.bank_name,
            ca.account_name,
            ca.account_number,
            ca.account_type,
            ca.branch
        FROM payment_transactions p
        LEFT JOIN income i
            ON i.reference=p.reference
        LEFT JOIN church_accounts ca
            ON ca.id=p.church_account_id
        WHERE p.reference=?
        LIMIT 1
        """,
        (reference,)
    ).fetchone()

    if not row:
        return jsonify({"error":"Payment transaction not found."}),404

    result=dict(row)

    payment_amount=float(result.get("payment_amount") or 0)
    income_amount=result.get("income_amount")

    if result.get("income_id"):
        result["reconciliation_status"]="Matched"
        result["amount_difference"]=round(
            payment_amount-float(income_amount or 0),2
        )
    elif str(result.get("payment_status") or "").lower()=="paid":
        result["reconciliation_status"]="Unmatched"
        result["amount_difference"]=payment_amount
    else:
        result["reconciliation_status"]="Pending"
        result["amount_difference"]=0

    return jsonify(result),200



@app.get("/api/financial-accountability-report")
@login_required
def api_financial_accountability_report():
    u=current_user()
    allowed={"Admin","Finance Officer","Auditor","Evangelism Minister","Bishop / Diocesan Executive","Diocesan Secretary"}
    if u["role"] not in allowed:
        return jsonify({"error":"Forbidden"}),403

    year=request.args.get("year","").strip()
    circuit=request.args.get("circuit","").strip()

    if year and (not year.isdigit() or not 2000 <= int(year) <= 2100):
        return jsonify({"error":"Invalid year"}),400

    conn=db()
    iw=["1=1"]
    ip=[]
    ew=["1=1"]
    ep=[]

    if year:
        iw.append("substr(i.date,1,4)=?")
        ip.append(year)
        ew.append("substr(e.date,1,4)=?")
        ep.append(year)

    if circuit:
        iw.append("COALESCE(ca.circuit,'Diocesan')=?")
        ip.append(circuit)
        ew.append("COALESCE(e.circuit,'Diocesan')=?")
        ep.append(circuit)

    income=conn.execute(f"""
        SELECT COALESCE(SUM(i.amount),0) total,
               COUNT(i.id) count
        FROM income i
        LEFT JOIN church_accounts ca ON ca.id=i.church_account_id
        WHERE {' AND '.join(iw)}
    """,ip).fetchone()

    expenses=conn.execute(f"""
        SELECT COALESCE(SUM(e.amount),0) total,
               COUNT(e.id) count
        FROM expenses e
        WHERE {' AND '.join(ew)}
    """,ep).fetchone()

    funds=conn.execute(f"""
        SELECT COALESCE(i.fund,'Unspecified') fund,
               COALESCE(SUM(i.amount),0) total
        FROM income i
        LEFT JOIN church_accounts ca ON ca.id=i.church_account_id
        WHERE {' AND '.join(iw)}
        GROUP BY COALESCE(i.fund,'Unspecified')
        ORDER BY total DESC
    """,ip).fetchall()

    categories=conn.execute(f"""
        SELECT COALESCE(e.category,'Uncategorized') category,
               COALESCE(SUM(e.amount),0) total
        FROM expenses e
        WHERE {' AND '.join(ew)}
        GROUP BY COALESCE(e.category,'Uncategorized')
        ORDER BY total DESC
    """,ep).fetchall()

    church_accountability = []
    church_rows = conn.execute("""
        SELECT id, COALESCE(circuit,'Diocesan') circuit,
               COALESCE(church_name,'Local Church') church_name
        FROM churches
        ORDER BY circuit, church_name
    """).fetchall()

    for ch in church_rows:
        ccircuit = ch["circuit"] or "Diocesan"

        if circuit and ccircuit != circuit:
            continue

        iw2 = ["ca.church_name=?"]
        ip2 = [ch["church_name"]]

        if year:
            iw2.append("substr(i.date,1,4)=?")
            ip2.append(year)

        ci = conn.execute(f"""
            SELECT COALESCE(SUM(i.amount),0) total, COUNT(i.id) count
            FROM income i
            LEFT JOIN church_accounts ca ON ca.id=i.church_account_id
            WHERE {' AND '.join(iw2)}
        """, ip2).fetchone()

        ew2 = ["e.circuit=?", "COALESCE(e.church_name,'')=?"]
        ep2 = [ccircuit, ch["church_name"]]

        if year:
            ew2.append("substr(e.date,1,4)=?")
            ep2.append(year)

        ce = conn.execute(f"""
            SELECT COALESCE(SUM(e.amount),0) total, COUNT(e.id) count
            FROM expenses e
            WHERE {' AND '.join(ew2)}
        """, ep2).fetchone()

        cin = float(ci["total"] or 0)
        cex = float(ce["total"] or 0)

        church_accountability.append({
            "church_id": ch["id"],
            "circuit": ccircuit,
            "church_name": ch["church_name"],
            "income_total": cin,
            "expense_total": cex,
            "net_balance": cin - cex,
            "income_count": int(ci["count"] or 0),
            "expense_count": int(ce["count"] or 0)
        })

    income_total=float(income["total"] or 0)
    expense_total=float(expenses["total"] or 0)

    return jsonify({
        "generated_at":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "year":year,
        "circuit":circuit,
        "summary":{
            "income_total":income_total,
            "expense_total":expense_total,
            "net_balance":income_total-expense_total,
            "income_count":int(income["count"] or 0),
            "expense_count":int(expenses["count"] or 0)
        },
        "income_by_fund":[dict(x) for x in funds],
        "expenses_by_category":[dict(x) for x in categories],
        "church_accountability":church_accountability
    })


@app.get("/api/finance-drilldown")
@login_required
def api_finance_drilldown():
    u=current_user()
    allowed={"Admin","Finance Officer","Auditor","Evangelism Minister","Bishop / Diocesan Executive","Diocesan Secretary"}
    if u["role"] not in allowed:
        return jsonify({"error":"Forbidden"}),403

    year=request.args.get("year","").strip()
    circuit=request.args.get("circuit","").strip()

    if year and (not year.isdigit() or not 2000 <= int(year) <= 2100):
        return jsonify({"error":"Invalid year"}),400

    conn=db()

    income_where=["1=1"]
    income_params=[]
    expense_where=["1=1"]
    expense_params=[]

    if year:
        income_where.append("substr(i.date,1,4)=?")
        income_params.append(year)
        expense_where.append("substr(e.date,1,4)=?")
        expense_params.append(year)

    if circuit:
        income_where.append("COALESCE(ca.circuit,'Diocesan')=?")
        income_params.append(circuit)
        expense_where.append("COALESCE(e.circuit,'Diocesan')=?")
        expense_params.append(circuit)

    income_rows=conn.execute(f"""
        SELECT
            COALESCE(ca.circuit,'Diocesan') AS circuit,
            COALESCE(ca.church_name,'Diocesan') AS church_name,
            COALESCE(SUM(i.amount),0) AS income_total,
            COUNT(i.id) AS income_count
        FROM income i
        LEFT JOIN church_accounts ca ON ca.id=i.church_account_id
        WHERE {' AND '.join(income_where)}
        GROUP BY circuit, church_name
        ORDER BY circuit, income_total DESC
    """,income_params).fetchall()

    expense_rows=conn.execute(f"""
        SELECT
            COALESCE(e.circuit,'Diocesan') AS circuit,
            COALESCE(SUM(e.amount),0) AS expense_total,
            COUNT(e.id) AS expense_count
        FROM expenses e
        WHERE {' AND '.join(expense_where)}
        GROUP BY circuit
        ORDER BY circuit
    """,expense_params).fetchall()

    expenses_by_circuit={
        r["circuit"]:{
            "expense_total":float(r["expense_total"] or 0),
            "expense_count":int(r["expense_count"] or 0)
        }
        for r in expense_rows
    }

    grouped={}

    account_rows=conn.execute("""
        SELECT
            COALESCE(circuit,'Diocesan') AS circuit,
            COALESCE(church_name,'Diocesan') AS church_name
        FROM church_accounts
        WHERE active=1
        ORDER BY circuit, church_name
    """).fetchall()

    church_rows=conn.execute("""
        SELECT
            COALESCE(circuit,'Diocesan') AS circuit,
            COALESCE(church_name,'Local Church') AS church_name
        FROM churches
        ORDER BY circuit, church_name
    """).fetchall()

    for r in account_rows:
        c=r["circuit"] or "Diocesan"
        church=r["church_name"] or "Diocesan"
        grouped.setdefault(c,[]).append({
            "church_name":church,
            "income_total":0,
            "income_count":0
        })

    for r in church_rows:
        c=r["circuit"] or "Diocesan"
        church=r["church_name"] or "Local Church"
        existing=next(
            (x for x in grouped.setdefault(c,[]) if x["church_name"]==church),
            None
        )
        if not existing:
            grouped[c].append({
                "church_name":church,
                "income_total":0,
                "income_count":0
            })

    for r in income_rows:
        c=r["circuit"] or "Diocesan"
        church=r["church_name"] or "Diocesan"
        existing=next((x for x in grouped.setdefault(c,[]) if x["church_name"]==church),None)
        if existing:
            existing["income_total"]=float(r["income_total"] or 0)
            existing["income_count"]=int(r["income_count"] or 0)
        else:
            grouped[c].append({
                "church_name":church,
                "income_total":float(r["income_total"] or 0),
                "income_count":int(r["income_count"] or 0)
            })

    circuits=[]
    names=sorted(set(grouped)|set(expenses_by_circuit))
    for c in names:
        churches=grouped.get(c,[])
        income_total=sum(x["income_total"] for x in churches)
        expense_total=expenses_by_circuit.get(c,{}).get("expense_total",0)
        circuits.append({
            "circuit":c,
            "total_income":income_total,
            "total_expenses":expense_total,
            "net_balance":income_total-expense_total,
            "church_count":len(churches),
            "churches":churches
        })

    return jsonify({
        "year":year,
        "circuit_filter":circuit,
        "circuits":circuits
    })

@app.get("/api/finance-summary")
@login_required
def api_finance_summary():
    u=current_user()

    allowed={
        "Admin",
        "Finance Officer",
        "Auditor",
        "Evangelism Minister",
        "Bishop / Diocesan Executive",
        "Diocesan Secretary",
    }

    if u["role"] not in allowed:
        return jsonify({"error":"Not authorized"}),403

    year=request.args.get("year","").strip()

    if year:
        try:
            year_int=int(year)
            if year_int<2000 or year_int>2100:
                raise ValueError
        except ValueError:
            return jsonify({"error":"Invalid year."}),400
    else:
        year_int=None

    date_filter=""
    args=[]

    if year_int:
        date_filter=" AND substr(date,1,4)=?"
        args.append(str(year_int))

    income_total=float(
        db().execute(
            "SELECT COALESCE(SUM(amount),0) FROM income WHERE 1=1"+date_filter,
            args
        ).fetchone()[0] or 0
    )

    expense_args=[]
    expense_filter=""

    if year_int:
        expense_filter=" AND substr(date,1,4)=?"
        expense_args.append(str(year_int))

    expense_total=float(
        db().execute(
            "SELECT COALESCE(SUM(amount),0) FROM expenses WHERE 1=1"+expense_filter,
            expense_args
        ).fetchone()[0] or 0
    )

    paid_total=float(
        db().execute(
            """
            SELECT COALESCE(SUM(amount),0)
            FROM payment_transactions
            WHERE LOWER(status)='paid'
            """ + (" AND substr(paid_at,1,4)=?" if year_int else ""),
            [str(year_int)] if year_int else []
        ).fetchone()[0] or 0
    )

    matched_total=float(
        db().execute(
            """
            SELECT COALESCE(SUM(i.amount),0)
            FROM income i
            INNER JOIN payment_transactions p
                ON p.reference=i.reference
            WHERE LOWER(p.status)='paid'
            """ + (" AND substr(i.date,1,4)=?" if year_int else ""),
            [str(year_int)] if year_int else []
        ).fetchone()[0] or 0
    )

    unmatched_paid=round(paid_total-matched_total,2)

    fund_rows=db().execute(
        """
        SELECT COALESCE(fund,'Unspecified') AS fund,
               COALESCE(SUM(amount),0) AS total
        FROM income
        WHERE 1=1
        """ + date_filter + """
        GROUP BY COALESCE(fund,'Unspecified')
        ORDER BY total DESC
        """,
        args
    ).fetchall()

    category_rows=db().execute(
        """
        SELECT COALESCE(category,'Uncategorized') AS category,
               COALESCE(SUM(amount),0) AS total
        FROM expenses
        WHERE 1=1
        """ + expense_filter + """
        GROUP BY COALESCE(category,'Uncategorized')
        ORDER BY total DESC
        """,
        expense_args
    ).fetchall()

    circuit_rows=db().execute(
        """
        SELECT
            COALESCE(ca.circuit,'Diocesan') AS circuit,
            COALESCE(SUM(i.amount),0) AS total
        FROM income i
        LEFT JOIN church_accounts ca
            ON ca.id=i.church_account_id
        WHERE 1=1
        """ + date_filter.replace("date","i.date") + """
        GROUP BY COALESCE(ca.circuit,'Diocesan')
        ORDER BY total DESC
        """,
        args
    ).fetchall()

    monthly_rows=db().execute(
        """
        SELECT
            substr(date,1,7) AS month,
            COALESCE(SUM(amount),0) AS total
        FROM income
        WHERE date IS NOT NULL
        """ + date_filter + """
        GROUP BY substr(date,1,7)
        ORDER BY month
        """,
        args
    ).fetchall()

    return jsonify({
        "year":year_int,
        "summary":{
            "income_total":income_total,
            "expense_total":expense_total,
            "net_balance":round(income_total-expense_total,2),
            "paid_online_total":paid_total,
            "matched_online_total":matched_total,
            "unmatched_online_total":unmatched_paid
        },
        "income_by_fund":[dict(r) for r in fund_rows],
        "expenses_by_category":[dict(r) for r in category_rows],
        "income_by_circuit":[dict(r) for r in circuit_rows],
        "monthly_income":[dict(r) for r in monthly_rows]
    }),200

@app.get("/api/payment-reconciliation")
@login_required
def api_payment_reconciliation():
    u = current_user()
    allowed = {
        "Admin",
        "Finance Officer",
        "Auditor",
        "Evangelism Minister",
        "Bishop / Diocesan Executive",
        "Diocesan Secretary",
    }

    if u["role"] not in allowed:
        return jsonify({"error":"Not authorized"}),403

    q = """
        SELECT
            p.id,
            p.reference,
            p.status AS payment_status,
            p.amount AS payment_amount,
            p.currency,
            p.purpose,
            p.account_level,
            p.circuit,
            p.church_name,
            p.church_account_id,
            p.donor_name,
            p.donor_email,
            p.paid_at,
            p.created_at AS payment_created_at,
            i.id AS income_id,
            i.reference AS income_reference,
            i.amount AS income_amount,
            i.date AS income_date,
            i.source AS income_source,
            i.fund AS income_fund,
            i.method AS income_method,
            i.received_by,
            i.notes AS income_notes,
            ca.bank_name,
            ca.account_name,
            ca.account_number
        FROM payment_transactions p
        LEFT JOIN income i
            ON i.reference = p.reference
        LEFT JOIN church_accounts ca
            ON ca.id = p.church_account_id
        WHERE 1=1
    """

    args = []

    status = request.args.get("status","").strip()
    circuit = request.args.get("circuit","").strip()
    search = request.args.get("search","").strip()

    if status:
        q += " AND p.status=?"
        args.append(status)

    if circuit:
        q += " AND p.circuit=?"
        args.append(circuit)

    if search:
        q += """
            AND (
                p.reference LIKE ?
                OR p.donor_name LIKE ?
                OR p.donor_email LIKE ?
            )
        """
        like=f"%{search}%"
        args.extend([like,like,like])

    q += " ORDER BY p.id DESC"

    rows = db().execute(q,args).fetchall()

    records=[]
    matched=0
    unmatched=0
    paid_total=0.0
    matched_total=0.0

    for row in rows:
        r=dict(row)

        payment_amount=float(r.get("payment_amount") or 0)
        income_amount=r.get("income_amount")

        if str(r.get("payment_status") or "").lower()=="paid":
            paid_total += payment_amount

        if r.get("income_id"):
            matched += 1
            matched_total += float(income_amount or 0)
            r["reconciliation_status"]="Matched"
        elif str(r.get("payment_status") or "").lower()=="paid":
            unmatched += 1
            r["reconciliation_status"]="Unmatched"
        else:
            r["reconciliation_status"]="Pending"

        records.append(r)

    return jsonify({
        "payments":records,
        "summary":{
            "transaction_count":len(records),
            "paid_total":paid_total,
            "matched_count":matched,
            "unmatched_count":unmatched,
            "matched_income_total":matched_total
        }
    }),200

@app.get("/api/payment-history/export")
@login_required
def api_payment_history_export():
    u = current_user()
    role = u["role"]

    allowed = {
        "Admin",
        "Finance Officer",
        "Auditor",
        "Evangelism Minister",
        "Bishop / Diocesan Executive",
        "Diocesan Secretary",
    }

    if role not in allowed:
        return jsonify({"error": "Not authorized"}), 403

    q = """
        SELECT
            p.id,
            p.reference,
            p.gateway,
            p.status,
            p.amount,
            p.currency,
            p.purpose,
            p.account_level,
            p.circuit,
            p.church_name,
            p.church_account_id,
            p.donor_name,
            p.donor_email,
            p.donor_phone,
            p.payment_method,
            p.gateway_transaction_id,
            p.paid_at,
            p.created_at,
            ca.bank_name,
            ca.account_name,
            ca.account_number,
            ca.account_type
        FROM payment_transactions p
        LEFT JOIN church_accounts ca
            ON ca.id = p.church_account_id
        WHERE 1=1
    """
    args=[]

    status=(request.args.get("status") or "").strip()
    purpose=(request.args.get("purpose") or "").strip()
    circuit=(request.args.get("circuit") or "").strip()
    church=(request.args.get("church_name") or "").strip()
    search=(request.args.get("search") or "").strip()
    date_from=(request.args.get("date_from") or "").strip()
    date_to=(request.args.get("date_to") or "").strip()

    if status:
        q+=" AND p.status=?"
        args.append(status)

    if purpose:
        q+=" AND p.purpose=?"
        args.append(purpose)

    if circuit:
        q+=" AND p.circuit=?"
        args.append(circuit)

    if church:
        q+=" AND p.church_name=?"
        args.append(church)

    if search:
        q+="""
            AND (
                p.reference LIKE ?
                OR p.donor_name LIKE ?
                OR p.donor_email LIKE ?
                OR p.gateway_transaction_id LIKE ?
            )
        """
        term="%"+search+"%"
        args.extend([term,term,term,term])

    if date_from:
        q+=" AND date(p.created_at)>=date(?)"
        args.append(date_from)

    if date_to:
        q+=" AND date(p.created_at)<=date(?)"
        args.append(date_to)

    if role=="Circuit Coordinator":
        q+=" AND p.circuit=?"
        args.append(u["circuit"])

    if role=="Local Church Evangelism Officer":
        q+=" AND p.circuit=? AND p.church_name=?"
        args.extend([u["circuit"],u["church_name"]])

    q+=" ORDER BY p.id DESC"

    rows_data=db().execute(q,args).fetchall()

    from openpyxl import Workbook

    wb=Workbook()
    ws=wb.active
    ws.title="Payment History"

    headers=[
        "ID","Reference","Gateway","Status","Amount","Currency","Purpose",
        "Account Level","Circuit","Local Church","Church Account ID",
        "Donor Name","Donor Email","Donor Phone","Payment Method",
        "Gateway Transaction ID","Paid At","Created At",
        "Bank Name","Account Name","Account Number","Account Type"
    ]
    ws.append(headers)

    for r in rows_data:
        ws.append([
            r["id"],
            r["reference"],
            r["gateway"],
            r["status"],
            r["amount"],
            r["currency"],
            r["purpose"],
            r["account_level"],
            r["circuit"],
            r["church_name"],
            r["church_account_id"],
            r["donor_name"],
            r["donor_email"],
            r["donor_phone"],
            r["payment_method"],
            r["gateway_transaction_id"],
            r["paid_at"],
            r["created_at"],
            r["bank_name"],
            r["account_name"],
            r["account_number"],
            r["account_type"],
        ])

    ws.freeze_panes="A2"
    ws.auto_filter.ref=ws.dimensions

    for column in ws.columns:
        width=max(len(str(cell.value or "")) for cell in column)+2
        ws.column_dimensions[column[0].column_letter].width=min(width,35)

    from io import BytesIO
    buf=BytesIO()
    wb.save(buf)
    buf.seek(0)

    return send_file(
        buf,
        as_attachment=True,
        download_name="MCN_Delta_South_Payment_History.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.get("/api/payment-history")
@login_required
def api_payment_history():
    u = current_user()
    role = u["role"]

    allowed = {
        "Admin",
        "Finance Officer",
        "Auditor",
        "Evangelism Minister",
        "Bishop / Diocesan Executive",
        "Diocesan Secretary",
    }

    if role not in allowed:
        return jsonify({"error": "Not authorized"}), 403

    q = """
        SELECT
            p.*,
            ca.bank_name,
            ca.account_name,
            ca.account_number,
            ca.account_type
        FROM payment_transactions p
        LEFT JOIN church_accounts ca
            ON ca.id = p.church_account_id
        WHERE 1=1
    """
    args = []

    status = (request.args.get("status") or "").strip()
    purpose = (request.args.get("purpose") or "").strip()
    circuit = (request.args.get("circuit") or "").strip()
    church = (request.args.get("church_name") or "").strip()
    search = (request.args.get("search") or "").strip()
    date_from = (request.args.get("date_from") or "").strip()
    date_to = (request.args.get("date_to") or "").strip()

    if status:
        q += " AND p.status=?"
        args.append(status)

    if purpose:
        q += " AND p.purpose=?"
        args.append(purpose)

    if circuit:
        q += " AND p.circuit=?"
        args.append(circuit)

    if church:
        q += " AND p.church_name=?"
        args.append(church)

    if search:
        q += """
            AND (
                p.reference LIKE ?
                OR p.donor_name LIKE ?
                OR p.donor_email LIKE ?
                OR p.gateway_transaction_id LIKE ?
            )
        """
        term = "%" + search + "%"
        args.extend([term, term, term, term])

    if date_from:
        q += " AND date(p.created_at) >= date(?)"
        args.append(date_from)

    if date_to:
        q += " AND date(p.created_at) <= date(?)"
        args.append(date_to)

    # Circuit Coordinator sees only their circuit.
    if role == "Circuit Coordinator":
        q += " AND p.circuit=?"
        args.append(u["circuit"])

    # Local Church Evangelism Officer sees only their church.
    if role == "Local Church Evangelism Officer":
        q += " AND p.circuit=? AND p.church_name=?"
        args.extend([u["circuit"], u["church_name"]])

    q += " ORDER BY p.id DESC"

    rows = db().execute(q, args).fetchall()

    records = [dict(r) for r in rows]
    for r in records:
        r.pop("gateway_response", None)

    total = sum(
        float(r.get("amount") or 0)
        for r in records
        if str(r.get("status") or "").lower() == "paid"
    )

    paid_count = sum(
        1 for r in records
        if str(r.get("status") or "").lower() == "paid"
    )

    pending_count = sum(
        1 for r in records
        if str(r.get("status") or "").lower() == "pending"
    )

    abandoned_count = sum(
        1 for r in records
        if str(r.get("status") or "").lower() == "abandoned"
    )

    return jsonify({
        "payments": records,
        "summary": {
            "total_paid": total,
            "paid_count": paid_count,
            "pending_count": pending_count,
            "abandoned_count": abandoned_count,
            "transaction_count": len(records)
        }
    })

@app.get("/api/payment/verify/<reference>")
def api_payment_verify(reference):
    import os, requests
    reference = str(reference or "").strip()
    if not reference:
        return jsonify({"error":"Payment reference is required."}),400

    row = db().execute(
        "SELECT * FROM payment_transactions WHERE reference=?",
        (reference,)
    ).fetchone()

    if not row:
        return jsonify({"error":"Payment transaction not found."}),404

    secret = os.environ.get("PAYSTACK_SECRET_KEY","").strip()
    if not secret:
        return jsonify({"error":"Paystack secret key is not configured on the server."}),503

    try:
        r = requests.get(
            "https://api.paystack.co/transaction/verify/" + reference,
            headers={
                "Authorization":"Bearer " + secret,
                "Content-Type":"application/json"
            },
            timeout=30
        )
        result = r.json()
    except Exception as e:
        return jsonify({"error":"Paystack verification failed.","detail":str(e)}),502

    if not result.get("status"):
        return jsonify({
            "error": result.get("message","Paystack verification failed."),
            "reference": reference
        }),502

    data = result.get("data") or {}
    gateway_status = str(data.get("status") or "").lower()
    amount = float(data.get("amount") or 0) / 100
    expected_amount = float(row["amount"] or 0)

    if gateway_status == "success" and abs(amount - expected_amount) > 0.01:
        return jsonify({
            "error":"Payment amount mismatch.",
            "reference":reference,
            "expected_amount":expected_amount,
            "paid_amount":amount
        }),409

    if gateway_status != "success":
        db().execute(
            "UPDATE payment_transactions SET status=?,gateway_response=? WHERE reference=?",
            (gateway_status.title() or "Pending", str(result), reference)
        )
        db().commit()
        return jsonify({
            "ok":True,
            "paid":False,
            "reference":reference,
            "status":gateway_status or "pending"
        })

    existing = db().execute(
        "SELECT id FROM income WHERE reference=? LIMIT 1",
        (reference,)
    ).fetchone()

    if not existing:
        db().execute(
            """INSERT INTO income
            (date,donor_name,source,fund,amount,method,reference,received_by,notes,church_account_id)
            VALUES(date('now'),?,?,?,?,?,?,?,?,?)""",
            (
                row["donor_name"] or "",
                "Online Payment",
                row["purpose"] or "General Evangelism",
                amount,
                "Paystack",
                reference,
                "Paystack",
                "Verified Paystack payment",
                row["church_account_id"]
            )
        )

    db().execute(
        """UPDATE payment_transactions
           SET status='Paid',
               gateway_transaction_id=?,
               gateway_response=?,
               paid_at=CURRENT_TIMESTAMP
           WHERE reference=?""",
        (
            str(data.get("id") or ""),
            str(result),
            reference
        )
    )
    db().commit()

    return jsonify({
        "ok":True,
        "paid":True,
        "reference":reference,
        "status":"Paid",
        "amount":amount
    }),200

@app.post("/api/payment/initiate")
def api_payment_initiate():
    import os,uuid,requests

    d=request.get_json() or {}
    email=(d.get("donor_email") or "").strip()
    amount=float(d.get("amount",0))
    account_id=d.get("church_account_id")

    if amount<=0 or not email:
        return jsonify({"error":"Valid amount and email are required."}),400

    if not account_id:
        return jsonify({"error":"A church account must be selected."}),400

    account=db().execute(
        "SELECT * FROM church_accounts WHERE id=? AND active=1",
        (account_id,)
    ).fetchone()

    if not account:
        return jsonify({"error":"Selected church account was not found or is inactive."}),404

    ref="DSD-"+uuid.uuid4().hex[:12].upper()

    callback_url = request.url_root.rstrip("/") + "/?payment=return"

    payload={
        "email":email,
        "amount":str(round(amount*100)),
        "currency":"NGN",
        "reference":ref,
        "callback_url":callback_url,
        "metadata":{
            "purpose":d.get("purpose"),
            "account_level":account["account_level"],
            "circuit":account["circuit"],
            "church_name":account["church_name"],
            "church_account_id":account["id"],
            "account_name":account["account_name"],
            "bank_name":account["bank_name"],
            "account_number":account["account_number"],
            "donor_name":d.get("donor_name"),
            "donor_phone":d.get("donor_phone")
        }
    }

    secret=os.environ.get("PAYSTACK_SECRET_KEY","").strip()
    if not secret:
        return jsonify({"error":"Paystack secret key is not configured on the server."}),503

    try:
        r=requests.post(
            "https://api.paystack.co/transaction/initialize",
            json=payload,
            headers={
                "Authorization":"Bearer "+secret,
                "Content-Type":"application/json"
            },
            timeout=30
        )
        result=r.json()
    except Exception as e:
        return jsonify({"error":"Paystack connection failed.","detail":str(e)}),502

    if not result.get("status"):
        return jsonify({
            "error":result.get("message","Paystack initialization failed.")
        }),502

    data=result["data"]

    db().execute(
        """INSERT INTO payment_transactions(
            reference,gateway,status,amount,currency,purpose,
            account_level,circuit,church_name,church_account_id,
            donor_name,donor_email,donor_phone,payment_method,
            gateway_transaction_id,gateway_response
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            ref,
            "Paystack",
            "Pending",
            amount,
            "NGN",
            d.get("purpose"),
            account["account_level"],
            account["circuit"],
            account["church_name"],
            account["id"],
            d.get("donor_name"),
            email,
            d.get("donor_phone"),
            d.get("payment_method") or "Paystack",
            str(data.get("access_code","")),
            str(result)
        )
    )
    db().commit()

    return jsonify({
        "reference":ref,
        "status":"Pending",
        "authorization_url":data.get("authorization_url"),
        "access_code":data.get("access_code")
    }),201


@login_required
@app.delete("/api/church-accounts/<int:aid>")
@login_required
def api_church_accounts_delete(aid):
    u=current_user(); r=db().execute("SELECT * FROM church_accounts WHERE id=?",(aid,)).fetchone()
    if not r: return jsonify({"error":"Account not found"}),404
    if u["role"]=="Circuit Coordinator" and (r["account_level"]!="Circuit" or r["circuit"]!=u["circuit"]): return jsonify({"error":"Not authorized"}),403
    if u["role"]=="Local Church Evangelism Officer" and (r["account_level"]!="Local Church" or r["circuit"]!=u["circuit"] or r["church_name"]!=u["church_name"]): return jsonify({"error":"Not authorized"}),403
    if u["role"] not in {"Admin","Finance Officer","Evangelism Minister","Circuit Coordinator","Local Church Evangelism Officer"}: return jsonify({"error":"Not authorized"}),403
    db().execute("DELETE FROM church_accounts WHERE id=?",(aid,)); db().commit()
    return jsonify({"ok":True})

@app.put("/api/church-accounts/<int:aid>")
@login_required
def api_church_accounts_update(aid):
    u=current_user(); d=request.get_json() or {}
    r=db().execute("SELECT * FROM church_accounts WHERE id=?",(aid,)).fetchone()
    if not r: return jsonify({"error":"Account not found"}),404
    if u["role"]=="Circuit Coordinator" and (r["account_level"]!="Circuit" or r["circuit"]!=u["circuit"]): return jsonify({"error":"Not authorized"}),403
    if u["role"]=="Local Church Evangelism Officer" and (r["account_level"]!="Local Church" or r["circuit"]!=u["circuit"] or r["church_name"]!=u["church_name"]): return jsonify({"error":"Not authorized"}),403
    if u["role"] not in {"Admin","Finance Officer","Evangelism Minister","Circuit Coordinator","Local Church Evangelism Officer"}: return jsonify({"error":"Not authorized"}),403
    db().execute("UPDATE church_accounts SET bank_name=?,account_name=?,account_number=?,account_type=?,branch=?,notes=? WHERE id=?",(d.get("bank_name",r["bank_name"]),d.get("account_name",r["account_name"]),d.get("account_number",r["account_number"]),d.get("account_type",r["account_type"]),d.get("branch",r["branch"]),d.get("notes",r["notes"]),aid)); db().commit()
    return jsonify({"ok":True})

@app.post("/api/church-accounts")
def api_church_accounts_create():
    u=current_user(); d=request.get_json() or {}
    if u["role"] not in {"Admin","Finance Officer","Evangelism Minister","Circuit Coordinator","Local Church Evangelism Officer"}: return jsonify({"error":"Not authorized"}),403
    level=d.get("account_level","Diocese"); circuit=d.get("circuit"); church=d.get("church_name")
    if u["role"]=="Circuit Coordinator": level="Circuit"; circuit=u["circuit"]; church=None
    if u["role"]=="Local Church Evangelism Officer": level="Local Church"; circuit=u["circuit"]; church=u["church_name"]
    if not d.get("bank_name") or not d.get("account_name") or not d.get("account_number"): return jsonify({"error":"Bank, account name and account number are required"}),400
    c=db(); r=c.execute("INSERT INTO church_accounts(account_level,circuit,church_name,bank_name,account_name,account_number,account_type,branch,notes,created_by) VALUES(?,?,?,?,?,?,?,?,?,?)",(level,circuit,church,d["bank_name"],d["account_name"],d["account_number"],d.get("account_type","Current"),d.get("branch"),d.get("notes"),u["username"])); c.commit()
    return jsonify(dict(c.execute("SELECT * FROM church_accounts WHERE id=?",(r.lastrowid,)).fetchone())),201


# =========================================================
# MEMBER CHURCH OFFICE / APPOINTMENT MANAGEMENT
# =========================================================

MEMBER_CHURCH_OFFICES = [
    "Bishop / Diocesan Executive",
    "Lay President",
    "Evangelism Minister",
    "Presbyters",
    "Ministers",
    "Lay Preachers",
    "Planting Officer",
    "Diocesan Secretary",
    "Circuit Coordinator",
    "Local Church Evangelism Officer",
    "Sunday School Teachers",
    "Finance Officer",
    "Conference Awardees",
    "Diocesan Awardees",
    "Friends of the Diocese",
    "Auditor",
    "Men Fellowship President",
    "Women Fellowship President",
    "Youth Fellowship President",
    "Others",
]

MEMBER_APPOINTMENT_LEVELS = [
    "Diocesan",
    "Circuit",
    "Local Church",
]

MEMBER_APPOINTMENT_STATUSES = [
    "Active",
    "Terminated",
]


def member_appointment_admin_required():
    u = current_user()
    if u["role"] != "Admin":
        return jsonify({"error": "Administrator access required."}), 403
    return None


@app.get("/api/members/<int:member_id>/appointments")
@login_required
def get_member_appointments(member_id):
    denied = member_appointment_admin_required()
    if denied:
        return denied

    member = db().execute(
        "SELECT id, member_id, full_name, circuit, church_name "
        "FROM members WHERE id=?",
        (member_id,)
    ).fetchone()

    if not member:
        return jsonify({"error": "Member not found."}), 404

    records = rows("""
        SELECT
            id,
            member_id,
            office,
            level,
            circuit,
            church_name,
            start_date,
            end_date,
            status,
            notes,
            appointed_by,
            created_at,
            updated_at
        FROM member_appointments
        WHERE member_id=?
        ORDER BY
            CASE WHEN status='Active' THEN 0 ELSE 1 END,
            start_date DESC,
            id DESC
    """, (member_id,))

    return jsonify({
        "member": dict(member),
        "appointments": records,
        "offices": MEMBER_CHURCH_OFFICES,
        "levels": MEMBER_APPOINTMENT_LEVELS,
        "statuses": MEMBER_APPOINTMENT_STATUSES
    })


@app.post("/api/members/<int:member_id>/appointments")
@login_required
def create_member_appointment(member_id):
    denied = member_appointment_admin_required()
    if denied:
        return denied

    member = db().execute(
        "SELECT id, full_name, circuit, church_name "
        "FROM members WHERE id=?",
        (member_id,)
    ).fetchone()

    if not member:
        return jsonify({"error": "Member not found."}), 404

    data = request.get_json(silent=True) or {}

    office = (data.get("office") or "").strip()
    level = (data.get("level") or "Local Church").strip()
    circuit = (data.get("circuit") or "").strip()
    church_name = (data.get("church_name") or "").strip()
    start_date = (data.get("start_date") or "").strip()
    end_date = (data.get("end_date") or "").strip()
    status = (data.get("status") or "Active").strip()
    notes = (data.get("notes") or "").strip()

    if office not in MEMBER_CHURCH_OFFICES:
        return jsonify({"error": "Select a valid church office."}), 400

    if level not in MEMBER_APPOINTMENT_LEVELS:
        return jsonify({"error": "Select a valid appointment level."}), 400

    if status not in MEMBER_APPOINTMENT_STATUSES:
        return jsonify({"error": "Select a valid appointment status."}), 400

    if not start_date:
        return jsonify({"error": "Appointment start date is required."}), 400

    if level == "Diocesan":
        circuit = ""
        church_name = ""

    elif level == "Circuit":
        if not circuit or circuit == "Diocesan":
            return jsonify({
                "error": "A circuit appointment must have a circuit."
            }), 400
        church_name = ""

    elif level == "Local Church":
        if not circuit or circuit == "Diocesan":
            return jsonify({
                "error": "A local church appointment must have a circuit."
            }), 400

        if not church_name:
            return jsonify({
                "error": "A local church appointment must have a local church."
            }), 400

        church = db().execute(
            "SELECT 1 FROM churches WHERE circuit=? AND church_name=?",
            (circuit, church_name)
        ).fetchone()

        if not church:
            return jsonify({
                "error": "The selected local church does not belong to the selected circuit."
            }), 400

    now = datetime.now().isoformat(timespec="seconds")
    u = current_user()
    appointed_by = u["username"] or "Administrator"

    conn = db()

    try:
        cur = conn.execute("""
            INSERT INTO member_appointments(
                member_id,
                office,
                level,
                circuit,
                church_name,
                start_date,
                end_date,
                status,
                notes,
                appointed_by,
                created_at,
                updated_at
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            member_id,
            office,
            level,
            circuit,
            church_name,
            start_date,
            end_date,
            status,
            notes,
            appointed_by,
            now,
            now
        ))

        conn.commit()

        try:
            audit(
                "CREATE_MEMBER_APPOINTMENT",
                "member_appointments",
                cur.lastrowid,
                json.dumps({
                    "member_id": member_id,
                    "member_name": member["full_name"],
                    "office": office,
                    "level": level,
                    "circuit": circuit,
                    "church_name": church_name,
                    "status": status
                }, ensure_ascii=False)
            )
        except Exception:
            pass

        return jsonify({
            "ok": True,
            "id": cur.lastrowid,
            "message": "Church office appointment added successfully."
        }), 201

    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({
            "error": "Could not create appointment: " + str(e)
        }), 500


@app.put("/api/member-appointments/<int:appointment_id>")
@login_required
def update_member_appointment(appointment_id):
    denied = member_appointment_admin_required()
    if denied:
        return denied

    appointment = db().execute(
        "SELECT * FROM member_appointments WHERE id=?",
        (appointment_id,)
    ).fetchone()

    if not appointment:
        return jsonify({"error": "Appointment not found."}), 404

    data = request.get_json(silent=True) or {}

    office = (data.get("office") or appointment["office"] or "").strip()
    level = (data.get("level") or appointment["level"] or "Local Church").strip()
    circuit = (data.get("circuit") or "").strip()
    church_name = (data.get("church_name") or "").strip()
    start_date = (data.get("start_date") or "").strip()
    end_date = (data.get("end_date") or "").strip()
    status = (data.get("status") or "Active").strip()
    notes = (data.get("notes") or "").strip()

    if office not in MEMBER_CHURCH_OFFICES:
        return jsonify({"error": "Select a valid church office."}), 400

    if level not in MEMBER_APPOINTMENT_LEVELS:
        return jsonify({"error": "Select a valid appointment level."}), 400

    if status not in MEMBER_APPOINTMENT_STATUSES:
        return jsonify({"error": "Select a valid appointment status."}), 400

    if not start_date:
        return jsonify({"error": "Appointment start date is required."}), 400

    if level == "Diocesan":
        circuit = ""
        church_name = ""

    elif level == "Circuit":
        if not circuit or circuit == "Diocesan":
            return jsonify({
                "error": "A circuit appointment must have a circuit."
            }), 400
        church_name = ""

    else:
        if not circuit or circuit == "Diocesan":
            return jsonify({
                "error": "A local church appointment must have a circuit."
            }), 400

        if not church_name:
            return jsonify({
                "error": "A local church appointment must have a local church."
            }), 400

        church = db().execute(
            "SELECT 1 FROM churches WHERE circuit=? AND church_name=?",
            (circuit, church_name)
        ).fetchone()

        if not church:
            return jsonify({
                "error": "The selected local church does not belong to the selected circuit."
            }), 400

    now = datetime.now().isoformat(timespec="seconds")

    conn = db()

    try:
        conn.execute("""
            UPDATE member_appointments
            SET office=?,
                level=?,
                circuit=?,
                church_name=?,
                start_date=?,
                end_date=?,
                status=?,
                notes=?,
                updated_at=?
            WHERE id=?
        """, (
            office,
            level,
            circuit,
            church_name,
            start_date,
            end_date,
            status,
            notes,
            now,
            appointment_id
        ))

        conn.commit()

        try:
            audit(
                "UPDATE_MEMBER_APPOINTMENT",
                "member_appointments",
                appointment_id,
                json.dumps({
                    "office": office,
                    "level": level,
                    "status": status,
                    "end_date": end_date
                }, ensure_ascii=False)
            )
        except Exception:
            pass

        return jsonify({
            "ok": True,
            "message": "Church office appointment updated successfully."
        })

    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({
            "error": "Could not update appointment: " + str(e)
        }), 500


@app.post("/api/member-appointments/<int:appointment_id>/terminate")
@login_required
def terminate_member_appointment(appointment_id):
    denied = member_appointment_admin_required()
    if denied:
        return denied

    appointment = db().execute(
        "SELECT * FROM member_appointments WHERE id=?",
        (appointment_id,)
    ).fetchone()

    if not appointment:
        return jsonify({"error": "Appointment not found."}), 404

    if appointment["status"] == "Terminated":
        return jsonify({"error": "This appointment is already terminated."}), 400

    data = request.get_json(silent=True) or {}
    end_date = (data.get("end_date") or "").strip()
    notes = (data.get("notes") or "").strip()

    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")

    now = datetime.now().isoformat(timespec="seconds")

    conn = db()

    try:
        old_notes = appointment["notes"] or ""
        final_notes = notes or old_notes

        conn.execute("""
            UPDATE member_appointments
            SET status='Terminated',
                end_date=?,
                notes=?,
                updated_at=?
            WHERE id=?
        """, (
            end_date,
            final_notes,
            now,
            appointment_id
        ))

        conn.commit()

        try:
            audit(
                "TERMINATE_MEMBER_APPOINTMENT",
                "member_appointments",
                appointment_id,
                json.dumps({
                    "office": appointment["office"],
                    "member_id": appointment["member_id"],
                    "end_date": end_date
                }, ensure_ascii=False)
            )
        except Exception:
            pass

        return jsonify({
            "ok": True,
            "message": "Church office appointment terminated. Membership remains active."
        })

    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({
            "error": "Could not terminate appointment: " + str(e)
        }), 500


@app.get("/api/member-appointment-options")
@login_required
def member_appointment_options():
    if current_user()["role"] != "Admin":
        return jsonify({"error": "Administrator access required."}), 403

    return jsonify({
        "offices": MEMBER_CHURCH_OFFICES,
        "levels": MEMBER_APPOINTMENT_LEVELS,
        "statuses": MEMBER_APPOINTMENT_STATUSES
    })



if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8080")),
        debug=False
    )
