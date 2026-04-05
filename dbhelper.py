import sqlite3
import hashlib
import re

DATABASE = "database.db"
# ══════════════════════════════════════════
# PROFANITY FILTER
# ══════════════════════════════════════════
BAD_WORDS = [
    # ── BISAYA ──
    'piste', 'pisti', 'yawa', 'yewe', 'inatay', 'atay', 'atayang', 'ataya',
    'animal', 'boang', 'buang', 'bogo', 'bogo', 'ogag', 'gunggong',
    'tonto', 'tungo', 'ngongo', 'ungo', 'mananap', 'bastos',
    'pakyas', 'paksha', 'bilat', 'bilata', 'boto', 'buyot',
    'luod', 'luoy', 'yawaa', 'yawang', 'dautan', 'dautang',
    'pastilan', 'pastil', 'susma', 'susmaryosep', 'susmariosep',
    'letse', 'leche', 'letcheng', 'lecheng',
    'bwisit', 'bwesit', 'busit', 'bsit', 'buwisit',
    'pakshet', 'pakshot', 'puta', 'pota', 'pote',
    'putang', 'putangina', 'putanginamo',
    'giatay', 'giatayan', 'giata',
    'hudas', 'ulol', 'ulong',
    'burikat', 'burikata',
    'animal', 'animala', 'animalia',
    'unggoy', 'unggoyan', 'unggoya',
    'baboy', 'baboya', 'baboyang',
    'aso', 'asong', 'asoa',
    'ihalas', 'ihalasin',
    'uwak', 'uwakan',
    'bubuyog', 'bubuyogan',
    'ahas', 'ahasan', 'ahasin',
    'butiki', 'butikia',
    'ipis', 'ipisang',
    'daga', 'dagaan', 'dagaang',
    'ambugas', 'ambugasan',
    'nawng', 'nawng aso', 'nawngaso',
    'nawng baboy', 'nawngbaboy',
    'nawng unggoy', 'nawngunggoy',
    'mukha', 'mukhaaso', 'mukha kang aso',
    'mukhang aso', 'mukhangaso',
    'mukhang baboy', 'mukhangbaboy',
    'mukhang unggoy', 'mukhangbaboy',
    'hitsura', 'hitsurang aso',
    'dagway', 'dagway aso', 'dagwayaso',
    'dagway baboy', 'dagwaybaboy',
    'dagway unggoy', 'dagwayunggoy',
    'panget', 'pangetang', 'pangit',
    'pangitang', 'napangit',
    'kagwang', 'uwak', 'langgam',
    'kulisap', 'uod', 'uodan',
    'bulate', 'bulaten', 'bulateng',

    # ── TAGALOG ──
    'tanga', 'tangina', 'tanginamo', 'tanginamo',
    'gago', 'gaga', 'gagong', 'inutil', 'duwag',
    'pakyu', 'tarantado', 'tarantadong',
    'punyeta', 'punyemas', 'punyetang',
    'leche', 'letse', 'letcheng',
    'bwisit', 'buwisit', 'bwiset',
    'hayop', 'hayopang', 'hayupa',
    'bobo', 'bobong', 'b0b0', 'b080',
    'loko', 'lokong', 'siraulo', 'siraulong',
    'gunggong', 'gungong', 'gunggung',
    'salot', 'salota', 'salotang',
    'demonyo', 'demonyong', 'diyablo',
    'kupal', 'kupaling', 'kupala',
    'palpak', 'palpaking',
    'ampota', 'ampotek', 'ampoteng',
    'ulol', 'ulolang', 'uluul',
    'hinayupak', 'hinayupaking',
    'nakakainit', 'nakakainis',
    'walang kwenta', 'walangkwenta',
    'walang hiya', 'walaghiya', 'walanghiya',
    'putragis', 'putragys',
    'supot', 'supota',
    'lintik', 'lintikan', 'lintikang',
    'kingina', 'kinginamo', 'kingina',
    'buset', 'buseta', 'busetang',
    'peste', 'pesteng', 'pesting',
    'shunga', 'sungga', 'sunga',
    'taena', 'taenang', 'taena',
    'galitera', 'galitero',

    # ── ENGLISH ──
    'fuck', 'fucker', 'fucking', 'fucked', 'fck', 'f0ck', 'fvck',
    'shit', 'shitty', 'shitter', 'bullshit', 'bullcrap',
    'ass', 'asshole', 'asses', 'jackass', 'smartass',
    'bitch', 'bitchy', 'bitching', 'bitches',
    'bastard', 'bastards', 'bastardly',
    'damn', 'damned', 'dammit', 'goddamn',
    'idiot', 'idiotic', 'idiots',
    'stupid', 'stupidity', 'stuped', 'stoopid', 'st4pid', 'stpid', 'styupid',
    'dumb', 'dumbass', 'dumbest',
    'moron', 'moronic', 'morons',
    'retard', 'retarded',
    'crap', 'crappy', 'craps',
    'hell', 'hells', 'hellish',
    'jerk', 'jerkoff', 'jerks',
    'loser', 'losers', 'l0ser',
    'trash', 'trashy',
    'ugly', 'uglyass',
    'fat', 'fatass', 'fatso',
    'pig', 'pighead',
    'freak', 'freaking', 'freaks',
    'suck', 'sucks', 'sucker', 'suckup',
    'pathetic', 'pathetico',
    'useless', 'uselessness',
    'worthless', 'worthlessness',
    'lazy', 'lazyass',
    'liar', 'liars',
    'cheater', 'cheaters',
    'scum', 'scumbag', 'scums',
    'slut', 'slutty', 'slob',
    'whore', 'whorish',
    'cunt', 'cunts',
    'dick', 'dicks', 'dickhead',
    'prick', 'pricks',
    'douchebag', 'douche',
    'numbskull', 'numskull',
    'imbecile', 'imbeciles',
    'nitwit', 'dimwit', 'halfwit',
    'bonehead', 'blockhead', 'knucklehead',

    # ── LEET VARIANTS ──
    'p0ta', 'p0t4', 'g4go', 'g@go',
    't4nga', 'tng4', 'b0b0', 'b080',
    'p1ste', 'y4wa', 'l3che',
    'f4ck', 'sh1t', 'b1tch', 'a55',
]

LEET_MAP = {
    '0': 'o', '1': 'i', '3': 'e', '4': 'a',
    '5': 's', '7': 't', '8': 'b', '@': 'a',
    '$': 's', '+': 't', '!': 'i',
}

def normalize_text(text):
    text = text.lower()
    # Replace leet speak
    for char, replacement in LEET_MAP.items():
        text = text.replace(char, replacement)
    # Remove spaces, dots, dashes
    text = re.sub(r'[\s\.\-\_\*]+', '', text)
    # Collapse repeated characters: yawaaaaaa → yawa, boangggg → boang
    text = re.sub(r'(.)\1+', r'\1', text)
    return text

def contains_bad_words(text):
    normalized        = normalize_text(text)         # spaces removed + leet normalized
    original          = text.lower()
    no_spaces         = re.sub(r'\s+', '', original) # just remove spaces, no leet
    
    for word in BAD_WORDS:
        if word in normalized:
            return True, word
        if word in original:
            return True, word
        if word in no_spaces:                        # catches "atay ang" → "atayang"
            return True, word
    
    return False, None
# ══════════════════════════════════════════
# REST OF YOUR CODE BELOW...
# ══════════════════════════════════════════
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
        "ALTER TABLE feedback ADD COLUMN is_flagged INTEGER DEFAULT 0",
        "ALTER TABLE feedback ADD COLUMN pc_number INTEGER DEFAULT NULL",
        "ALTER TABLE sitin_sessions ADD COLUMN pc_number INTEGER DEFAULT NULL",
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
        conn.execute("INSERT INTO admin (username, password) VALUES (?, ?)", ('admin', hash_password('admin123')))
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
    hashed = hash_password(password)
    conn = get_db()
    admin = conn.execute(
        "SELECT * FROM admin WHERE username = ? AND password = ?",
        (username, hashed)
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
               s.pc_number,
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

def add_sitin(id_number, purpose, lab, pc_number=None):
    conn = get_db()
    # Check if PC is already occupied
    if pc_number:
        existing = conn.execute("""
            SELECT id FROM sitin_sessions
            WHERE lab=? AND pc_number=? AND status='active'
        """, (lab, pc_number)).fetchone()
        if existing:
            conn.close()
            return None, 'PC is already occupied by another student.'
    cursor = conn.execute("""
        INSERT INTO sitin_sessions (idNumber, purpose, lab, pc_number)
        VALUES (?, ?, ?, ?)
    """, (id_number, purpose, lab, pc_number))
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id, None

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

def get_lab_counts():
    conn = get_db()
    rows = conn.execute("""
        SELECT 
            CASE 
                WHEN lab LIKE '%524%' THEN '524'
                WHEN lab LIKE '%526%' THEN '526'
                WHEN lab LIKE '%528%' THEN '528'
                WHEN lab LIKE '%530%' THEN '530'
                WHEN lab LIKE '%542%' THEN '542'
                WHEN lab LIKE '%544%' THEN '544'
                ELSE lab
            END as lab_normalized,
            COUNT(*) as cnt
        FROM sitin_sessions
        GROUP BY lab_normalized
    """).fetchall()
    conn.close()
    return {row['lab_normalized']: row['cnt'] for row in rows}
# ══════════════════════════════════════════
# FEEDBACK QUERIES
# ══════════════════════════════════════════
def save_feedback(id_number, session_id, lab, message, rating=0, pc_number=None):
    is_flagged = 1 if contains_bad_words(message)[0] else 0
    conn = get_db()
    try:
        conn.execute("ALTER TABLE feedback ADD COLUMN pc_number INTEGER DEFAULT NULL")
        conn.commit()
    except:
        pass
    conn.execute("""
        INSERT INTO feedback (idNumber, session_id, lab, pc_number, rating, message, is_flagged)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (id_number, session_id, lab, pc_number, rating, message, is_flagged))

    conn.commit()
    conn.close()

def get_all_feedback():
    conn = get_db()
    rows = conn.execute("""
        SELECT f.id,
            f.idNumber,
            f.session_id,
            COALESCE(f.lab, s.lab, '—') AS lab,
            f.pc_number,
            COALESCE(f.rating, 0)        AS rating,
            f.message,
            f.is_flagged,
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

def init_reservations_table():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            idNumber    TEXT NOT NULL,
            purpose     TEXT NOT NULL,
            lab         TEXT NOT NULL,
            pc_number   INTEGER,
            time_in     TEXT NOT NULL,
            date        TEXT NOT NULL,
            status      TEXT DEFAULT 'pending',
            message     TEXT DEFAULT NULL,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (idNumber) REFERENCES students(idNumber)
        )
    """)
    try:
        conn.execute("ALTER TABLE reservations ADD COLUMN pc_number INTEGER")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE reservations ADD COLUMN message TEXT DEFAULT NULL")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE reservations ADD COLUMN session_id INTEGER DEFAULT NULL")
    except Exception:
        pass

    conn.execute("""
        CREATE TABLE IF NOT EXISTS blocked_pcs (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            lab       TEXT NOT NULL,
            pc_number INTEGER NOT NULL,
            UNIQUE(lab, pc_number)
        )
    """)
    conn.commit()
    conn.close()

def add_reservation(id_number, purpose, lab, pc_number, time_in, date):
    conn = get_db()
    
    # Check if student already has a pending or approved reservation
    existing = conn.execute("""
        SELECT id FROM reservations 
        WHERE idNumber = ? AND status IN ('pending', 'approved')
    """, (id_number,)).fetchone()
    if existing:
        conn.close()
        return None, 'You already have an active or pending reservation. Wait for it to be resolved first.'
    
    # Check if student already has a reservation on the same date
    same_day = conn.execute("""
        SELECT id FROM reservations
        WHERE idNumber = ? AND date = ? AND status NOT IN ('rejected', 'expired', 'done')
    """, (id_number, date)).fetchone()
    if same_day:
        conn.close()
        return None, 'You already have a reservation on this date.'
    
    cursor = conn.execute("""
        INSERT INTO reservations (idNumber, purpose, lab, pc_number, time_in, date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (id_number, purpose, lab, pc_number, time_in, date))
    res_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return res_id, None

def get_student_reservations(id_number):
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM reservations WHERE idNumber = ?
        ORDER BY created_at DESC
    """, (id_number,)).fetchall()
    conn.close()
    return rows

def get_all_reservations():
    conn = get_db()
    rows = conn.execute("""
        SELECT r.*, s.firstName, s.lastName, s.middleName
        FROM reservations r
        JOIN students s ON r.idNumber = s.idNumber
        WHERE r.status IN ('pending', 'approved', 'sitting_in')
        ORDER BY r.created_at DESC
    """).fetchall()
    conn.close()
    return rows

def update_reservation_status(res_id, status):
    conn = get_db()
    if status == 'done':
        conn.execute("""
            UPDATE reservations SET status=?, message=?
            WHERE id=?
        """, (status, '✅ Your sit-in session has been completed successfully. Thank you for using the CCS Laboratory! We hope your session was productive. Please take a moment to leave a feedback — your thoughts help us improve our services. We appreciate you! 😊', res_id))
    elif status == 'expired':
        conn.execute("""
            UPDATE reservations SET status=?, message=?
            WHERE id=?
        """, (status, '⏰ Your reservation has expired as your time slot has already passed. Please book a new reservation at a different time. We apologize for any inconvenience this may have caused.', res_id))
    else:
        conn.execute("UPDATE reservations SET status=? WHERE id=?", (status, res_id))
    conn.commit()
    conn.close()

# ══════════════════════════════════════════
# RESERVATION SETTINGS (admin on/off)
# ══════════════════════════════════════════
def init_reservation_settings():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reservation_settings (
            id       INTEGER PRIMARY KEY,
            enabled  INTEGER DEFAULT 1,
            message  TEXT DEFAULT 'Reservations are currently disabled.'
        )
    """)
    # Insert default row if not exists
    conn.execute("""
        INSERT OR IGNORE INTO reservation_settings (id, enabled, message)
        VALUES (1, 1, 'Reservations are currently closed during Major Exams Week. Sit-ins are not allowed.')
    """)
    conn.commit()
    conn.close()

def get_reservation_settings():
    conn = get_db()
    row = conn.execute("SELECT * FROM reservation_settings WHERE id=1").fetchone()
    conn.close()
    return row

def set_reservation_enabled(enabled: int, message: str = None):
    conn = get_db()
    if message:
        conn.execute("UPDATE reservation_settings SET enabled=?, message=? WHERE id=1", (enabled, message))
    else:
        conn.execute("UPDATE reservation_settings SET enabled=? WHERE id=1", (enabled,))
    conn.commit()
    conn.close()

def get_reservation_log():
    conn = get_db()
    rows = conn.execute("""
        SELECT r.id, r.idNumber, r.purpose, r.lab, r.pc_number,
               r.time_in, r.date, r.status,
               s.firstName, s.lastName, s.middleName
        FROM reservations r
        JOIN students s ON r.idNumber = s.idNumber
        WHERE r.status IN ('rejected', 'expired', 'done')
        ORDER BY r.created_at DESC
    """).fetchall()
    conn.close()
    return rows

def get_blocked_pcs(lab):
    conn = get_db()
    rows = conn.execute(
        "SELECT pc_number FROM blocked_pcs WHERE lab = ?", (lab,)
    ).fetchall()
    conn.close()
    return [r['pc_number'] for r in rows]

def set_pc_blocked(lab, pc_number, blocked):
    conn = get_db()
    if blocked:
        conn.execute(
            "INSERT OR IGNORE INTO blocked_pcs (lab, pc_number) VALUES (?, ?)",
            (lab, pc_number)
        )
    else:
        conn.execute(
            "DELETE FROM blocked_pcs WHERE lab = ? AND pc_number = ?",
            (lab, pc_number)
        )
    conn.commit()
    conn.close()

def update_reservation_message(res_id, message):
    conn = get_db()
    conn.execute(
        "UPDATE reservations SET message = ? WHERE id = ?",
        (message, res_id)
    )
    conn.commit()
    conn.close()

def get_reserved_pcs(lab, date):
    conn = get_db()
    rows = conn.execute("""
        SELECT pc_number FROM reservations
        WHERE lab=? AND date=? AND status NOT IN ('rejected', 'expired', 'done')
    """, (lab, date)).fetchall()
    blocked = conn.execute(
        "SELECT pc_number FROM blocked_pcs WHERE lab = ?", (lab,)
    ).fetchall()
    occupied = conn.execute("""
        SELECT pc_number FROM sitin_sessions
        WHERE lab=? AND status='active' AND pc_number IS NOT NULL
    """, (lab,)).fetchall()
    conn.close()
    reserved = [r['pc_number'] for r in rows if r['pc_number']]
    blocked_list = [r['pc_number'] for r in blocked]
    occupied_list = [r['pc_number'] for r in occupied]
    return list(set(reserved + blocked_list + occupied_list))
    
def get_occupied_pcs(lab):
    """Return list of PC numbers currently occupied (active sit-in sessions)."""
    conn = get_db()
    rows = conn.execute("""
        SELECT pc_number FROM sitin_sessions
        WHERE lab = ? AND status = 'active' AND pc_number IS NOT NULL
    """, (lab,)).fetchall()
    conn.close()
    return [r['pc_number'] for r in rows]

def get_reserved_pcs_today(lab):
    from datetime import date
    today = date.today().isoformat()
    conn = get_db()
    rows = conn.execute("""
        SELECT pc_number FROM reservations
        WHERE lab=? AND date=? AND status IN ('pending', 'approved')
    """, (lab, today)).fetchall()
    conn.close()
    return [r['pc_number'] for r in rows if r['pc_number']]