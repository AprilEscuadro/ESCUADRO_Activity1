import sqlite3
import hashlib

DATABASE = "database.db"

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

CCS_COURSES = {'BSIT', 'BSCS', 'BSCoE', 'CISCO'}

def get_sitin_count(course):
    return 30 if course in CCS_COURSES else 15


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            idNumber    TEXT UNIQUE NOT NULL,
            firstName   TEXT NOT NULL,
            lastName    TEXT NOT NULL,
            middleName  TEXT,
            yearLevel   TEXT,
            password    TEXT NOT NULL,
            email       TEXT NOT NULL,
            course      TEXT,
            address     TEXT,
            sitin_count INTEGER DEFAULT 30,
            photo_url   TEXT,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS admin (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT UNIQUE NOT NULL,
            password    TEXT NOT NULL,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sitin_sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            idNumber    TEXT NOT NULL,
            purpose     TEXT NOT NULL,
            lab         TEXT NOT NULL,
            time_in     DATETIME DEFAULT CURRENT_TIMESTAMP,
            time_out    DATETIME,
            status      TEXT DEFAULT 'active',
            FOREIGN KEY (idNumber) REFERENCES students(idNumber)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            content     TEXT NOT NULL,
            posted_by   TEXT NOT NULL,
            is_pinned   INTEGER DEFAULT 0,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            idNumber    TEXT NOT NULL,
            session_id  INTEGER,
            lab         TEXT,
            rating      INTEGER DEFAULT 0,
            message     TEXT NOT NULL,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (idNumber) REFERENCES students(idNumber),
            FOREIGN KEY (session_id) REFERENCES sitin_sessions(id)
        )
    """)

    # Migrations: safely add columns if missing
    for migration in [
        "ALTER TABLE students ADD COLUMN photo_url TEXT",
        "ALTER TABLE announcements ADD COLUMN is_pinned INTEGER DEFAULT 0",
        "ALTER TABLE feedback ADD COLUMN lab TEXT",
        "ALTER TABLE feedback ADD COLUMN rating INTEGER DEFAULT 0",
    ]:
        try:
            conn.execute(migration)
        except Exception:
            pass

    # Rename courseLevel to yearLevel if it still exists
    try:
        conn.execute("ALTER TABLE students RENAME COLUMN courseLevel TO yearLevel")
        conn.commit()
    except Exception:
        pass

    existing_admin = conn.execute("SELECT * FROM admin WHERE username = 'admin'").fetchone()
    if not existing_admin:
        conn.execute("INSERT INTO admin (username, password) VALUES (?, ?)", ('admin', 'admin123'))
        print("✓ Default admin created → username: admin | password: admin123")

    conn.commit()
    conn.close()


# ══════════════════════════════════════════
# STUDENT QUERIES
# ══════════════════════════════════════════
def get_all_students():
    conn = get_db()
    students = conn.execute("SELECT * FROM students").fetchall()
    conn.close()
    return students

def get_student_by_id(id_number):
    conn = get_db()
    student = conn.execute(
        "SELECT * FROM students WHERE idNumber = ?", (id_number,)
    ).fetchone()
    conn.close()
    return student

def register_student(idNumber, firstName, lastName, middleName,
                     yearLevel, password, email, course, address, sitin_count):
    hashed = hash_password(password)
    conn = get_db()
    conn.execute("""
        INSERT INTO students
        (idNumber, firstName, lastName, middleName, yearLevel,
         password, email, course, address, sitin_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (idNumber, firstName, lastName, middleName, yearLevel,
          hashed, email, course, address, sitin_count))
    conn.commit()
    conn.close()

def login_student(id_number, password):
    hashed = hash_password(password)
    conn = get_db()
    student = conn.execute(
        "SELECT * FROM students WHERE idNumber = ? AND password = ?",
        (id_number, hashed)
    ).fetchone()
    conn.close()
    return student


# ══════════════════════════════════════════
# ADMIN QUERIES
# ══════════════════════════════════════════
def login_admin(username, password):
    conn = get_db()
    admin = conn.execute(
        "SELECT * FROM admin WHERE username = ? AND password = ?",
        (username, password)
    ).fetchone()
    conn.close()
    return admin


# ══════════════════════════════════════════
# SIT-IN QUERIES
# ══════════════════════════════════════════
def get_all_sessions():
    conn = get_db()
    sessions = conn.execute("""
        SELECT s.id,
               s.idNumber,
               s.purpose,
               s.lab,
               s.time_in,
               s.time_out,
               s.status,
               st.firstName,
               st.lastName,
               st.middleName,
               st.sitin_count
        FROM sitin_sessions s
        JOIN students st ON s.idNumber = st.idNumber
        ORDER BY s.time_in DESC
    """).fetchall()
    conn.close()
    return sessions

def get_student_sessions(id_number):
    conn = get_db()
    sessions = conn.execute("""
        SELECT * FROM sitin_sessions
        WHERE idNumber = ?
        ORDER BY time_in DESC
    """, (id_number,)).fetchall()
    conn.close()
    return sessions

def add_sitin(id_number, purpose, lab):
    conn = get_db()
    cursor = conn.execute("""
        INSERT INTO sitin_sessions (idNumber, purpose, lab)
        VALUES (?, ?, ?)
    """, (id_number, purpose, lab))
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id

def end_sitin(session_id):
    conn = get_db()
    row = conn.execute(
        "SELECT idNumber FROM sitin_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    conn.execute("""
        UPDATE sitin_sessions
        SET time_out = CURRENT_TIMESTAMP, status = 'done'
        WHERE id = ?
    """, (session_id,))
    if row:
        conn.execute("""
            UPDATE students SET sitin_count = sitin_count - 1
            WHERE idNumber = ? AND sitin_count > 0
        """, (row['idNumber'],))
    conn.commit()
    conn.close()


# ══════════════════════════════════════════
# ANNOUNCEMENT QUERIES
# ══════════════════════════════════════════
def get_all_announcements():
    conn = get_db()
    announcements = conn.execute(
        "SELECT * FROM announcements ORDER BY is_pinned DESC, created_at DESC"
    ).fetchall()
    conn.close()
    return announcements

def add_announcement(title, content, posted_by):
    conn = get_db()
    conn.execute("""
        INSERT INTO announcements (title, content, posted_by)
        VALUES (?, ?, ?)
    """, (title, content, posted_by))
    conn.commit()
    conn.close()

def edit_announcement(ann_id, title, content):
    conn = get_db()
    conn.execute(
        "UPDATE announcements SET title=?, content=? WHERE id=?",
        (title, content, ann_id)
    )
    conn.commit()
    conn.close()

def delete_announcement(ann_id):
    conn = get_db()
    conn.execute("DELETE FROM announcements WHERE id=?", (ann_id,))
    conn.commit()
    conn.close()

def toggle_pin_announcement(ann_id):
    conn = get_db()
    row = conn.execute("SELECT is_pinned FROM announcements WHERE id=?", (ann_id,)).fetchone()
    if row:
        new_val = 0 if row['is_pinned'] else 1
        conn.execute("UPDATE announcements SET is_pinned=? WHERE id=?", (new_val, ann_id))
        conn.commit()
        conn.close()
        return new_val
    conn.close()
    return None


# ══════════════════════════════════════════
# PURPOSE COUNTS (for pie chart)
# ══════════════════════════════════════════
def get_purpose_counts():
    conn = get_db()
    rows = conn.execute("""
        SELECT purpose, COUNT(*) as cnt
        FROM sitin_sessions
        GROUP BY purpose
    """).fetchall()
    conn.close()
    return {row['purpose']: row['cnt'] for row in rows}


# ══════════════════════════════════════════
# FEEDBACK QUERIES
# ══════════════════════════════════════════
def save_feedback(id_number, session_id, lab, message, rating=0):
    conn = get_db()
    conn.execute("""
        INSERT INTO feedback (idNumber, session_id, lab, rating, message)
        VALUES (?, ?, ?, ?, ?)
    """, (id_number, session_id, lab, rating, message))
    conn.commit()
    conn.close()

def get_all_feedback():
    conn = get_db()
    rows = conn.execute("""
        SELECT f.id,
               f.idNumber,
               f.session_id,
               COALESCE(f.lab, s.lab, '—') AS lab,
               COALESCE(f.rating, 0)        AS rating,
               f.message,
               DATE(f.created_at)           AS date,
               f.created_at
        FROM feedback f
        LEFT JOIN sitin_sessions s ON f.session_id = s.id
        ORDER BY f.created_at DESC
    """).fetchall()
    conn.close()
    return rows

def has_feedback(session_id):
    """Check if feedback already submitted for a session."""
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM feedback WHERE session_id = ?", (session_id,)
    ).fetchone()
    conn.close()
    return row is not None