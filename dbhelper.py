import sqlite3

DATABASE = "database.db"

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


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
    student = conn.execute("SELECT * FROM students WHERE idNumber = ?", (id_number,)).fetchone()
    conn.close()
    return student

def register_student(idNumber, firstName, lastName, middleName,
                     courseLevel, password, email, course, address, sitin_count):
    conn = get_db()
    conn.execute("""
        INSERT INTO students
        (idNumber, firstName, lastName, middleName, courseLevel,
         password, email, course, address, sitin_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (idNumber, firstName, lastName, middleName, courseLevel,
          password, email, course, address, sitin_count))
    conn.commit()
    conn.close()

def login_student(id_number, password):
    conn = get_db()
    student = conn.execute(
        "SELECT * FROM students WHERE idNumber = ? AND password = ?", (id_number, password)
    ).fetchone()
    conn.close()
    return student

def update_sitin_on_login(id_number):
    conn = get_db()
    conn.execute("""
        UPDATE students
        SET number_of_sitins = number_of_sitins + 1,
            sitin_count = sitin_count - 1
        WHERE idNumber = ?
    """, (id_number,))
    conn.commit()
    conn.close()
    
# ══════════════════════════════════════════
# ADMIN QUERIES
# ══════════════════════════════════════════
def login_admin(username, password):
    conn = get_db()
    admin = conn.execute(
        "SELECT * FROM admin WHERE username = ? AND password = ?", (username, password)
    ).fetchone()
    conn.close()
    return admin


# ══════════════════════════════════════════
# SIT-IN QUERIES
# ══════════════════════════════════════════
def get_all_sessions():
    conn = get_db()
    sessions = conn.execute("""
        SELECT s.*, st.firstName, st.lastName
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
    conn.execute("""
        INSERT INTO sitin_sessions (idNumber, purpose, lab)
        VALUES (?, ?, ?)
    """, (id_number, purpose, lab))
    conn.execute("""
        UPDATE students SET sitin_count = sitin_count - 1 WHERE idNumber = ?
    """, (id_number,))
    conn.commit()
    conn.close()

def end_sitin(session_id):
    conn = get_db()
    conn.execute("""
        UPDATE sitin_sessions
        SET time_out = CURRENT_TIMESTAMP, status = 'done'
        WHERE id = ?
    """, (session_id,))
    conn.commit()
    conn.close()


# ══════════════════════════════════════════
# ANNOUNCEMENT QUERIES
# ══════════════════════════════════════════
def get_all_announcements():
    conn = get_db()
    announcements = conn.execute("SELECT * FROM announcements ORDER BY created_at DESC").fetchall()
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