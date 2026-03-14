import sqlite3
import hashlib

DATABASE = "database.db"

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

CCS_COURSES = {'BSIT', 'BSCS'}

def get_sitin_count(course):
    """Return correct sit-in count: 30 for CCS, 15 for all others."""
    return 30 if course in CCS_COURSES else 15


def ensure_photo_url_column():
    """Safely add photo_url column to students table if it doesn't exist yet."""
    conn = get_db()
    try:
        conn.execute("ALTER TABLE students ADD COLUMN photo_url TEXT")
        conn.commit()
        print("✓ photo_url column added to students table.")
    except Exception:
        pass  # Column already exists — that's fine
    conn.close()


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            idNumber    TEXT UNIQUE NOT NULL,
            firstName   TEXT NOT NULL,
            lastName    TEXT NOT NULL,
            middleName  TEXT,
            courseLevel TEXT,
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
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            idNumber    TEXT NOT NULL,
            session_id  INTEGER,
            message     TEXT NOT NULL,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (idNumber) REFERENCES students(idNumber),
            FOREIGN KEY (session_id) REFERENCES sitin_sessions(id)
        )
    """)

    # Safely migrate existing DB: add photo_url if missing
    try:
        conn.execute("ALTER TABLE students ADD COLUMN photo_url TEXT")
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
                     courseLevel, password, email, course, address, sitin_count):
    """Register student — password is hashed before saving."""
    hashed = hash_password(password)
    conn = get_db()
    conn.execute("""
        INSERT INTO students
        (idNumber, firstName, lastName, middleName, courseLevel,
         password, email, course, address, sitin_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (idNumber, firstName, lastName, middleName, courseLevel,
          hashed, email, course, address, sitin_count))
    conn.commit()
    conn.close()

def login_student(id_number, password):
    """Login — hash the input password before comparing."""
    hashed = hash_password(password)
    conn = get_db()
    student = conn.execute(
        "SELECT * FROM students WHERE idNumber = ? AND password = ?",
        (id_number, hashed)
    ).fetchone()
    conn.close()
    return student


def update_student_profile(id_number, first_name, last_name, middle_name,
                            email, address, course, course_level,
                            new_password=None, photo_url=None):
    conn = get_db()

    # Always recalculate sit-in count based on course
    sitin_count = get_sitin_count(course)

    if new_password and photo_url:
        conn.execute("""
            UPDATE students
            SET firstName=?, lastName=?, middleName=?,
                email=?, address=?, course=?, courseLevel=?,
                password=?, photo_url=?, sitin_count=?
            WHERE idNumber=?
        """, (first_name, last_name, middle_name,
              email, address, course, course_level,
              hash_password(new_password), photo_url, sitin_count, id_number))

    elif new_password:
        conn.execute("""
            UPDATE students
            SET firstName=?, lastName=?, middleName=?,
                email=?, address=?, course=?, courseLevel=?,
                password=?, sitin_count=?
            WHERE idNumber=?
        """, (first_name, last_name, middle_name,
              email, address, course, course_level,
              hash_password(new_password), sitin_count, id_number))

    elif photo_url:
        conn.execute("""
            UPDATE students
            SET firstName=?, lastName=?, middleName=?,
                email=?, address=?, course=?, courseLevel=?,
                photo_url=?, sitin_count=?
            WHERE idNumber=?
        """, (first_name, last_name, middle_name,
              email, address, course, course_level,
              photo_url, sitin_count, id_number))

    else:
        conn.execute("""
            UPDATE students
            SET firstName=?, lastName=?, middleName=?,
                email=?, address=?, course=?, courseLevel=?,
                sitin_count=?
            WHERE idNumber=?
        """, (first_name, last_name, middle_name,
              email, address, course, course_level,
              sitin_count, id_number))

    conn.commit()
    conn.close()


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
    session_id = cursor.lastrowid  # ✅ get the new ID
    conn.commit()
    conn.close()
    return session_id  # ✅ return it

def end_sitin(session_id):
    """Mark sit-in as done AND deduct one session from the student."""
    conn = get_db()
    # Get the student ID from this session
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
        "SELECT * FROM announcements ORDER BY created_at DESC"
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


# ══════════════════════════════════════════
# PURPOSE COUNTS (for pie chart)
# ══════════════════════════════════════════
def get_purpose_counts():
    """Returns a dict like {'C Programming': 5, 'Java Programming': 3, ...}"""
    conn = get_db()
    rows = conn.execute("""
        SELECT purpose, COUNT(*) as cnt
        FROM sitin_sessions
        GROUP BY purpose
    """).fetchall()
    conn.close()
    return {row['purpose']: row['cnt'] for row in rows}