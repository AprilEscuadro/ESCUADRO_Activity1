import os
from flask import Flask, request, redirect, render_template, render_template_string, session, jsonify
from dbhelper import (
    contains_bad_words,
    init_db,
    get_student_by_id, register_student, login_student,
    login_admin, get_all_students,
    get_all_sessions, get_student_sessions, add_sitin, end_sitin,
    get_all_announcements, add_announcement,
    edit_announcement, delete_announcement, toggle_pin_announcement,
    get_purpose_counts, get_lab_counts,
    save_feedback, get_all_feedback, has_feedback,
    init_reservations_table, add_reservation,
    get_student_reservations, get_all_reservations,
    update_reservation_status,
    get_reservation_settings, set_reservation_enabled,
    init_reservation_settings, get_reserved_pcs,
    get_reservation_log, get_blocked_pcs,
    set_pc_blocked,
    update_reservation_message, get_occupied_pcs,
    get_reserved_pcs_today,
)

import sqlite3 as _sqlite3

CCS_COURSES = {'BSIT', 'BSCS', 'BSCoE', 'CISCO'}

def get_sitin_count(course):
    return 30 if course in CCS_COURSES else 15

def reset_all_sessions():
    conn = _sqlite3.connect('database.db')
    students = conn.execute("SELECT idNumber, course FROM students").fetchall()
    for s in students:
        count = get_sitin_count(s[1] or '')
        conn.execute("UPDATE students SET sitin_count = ? WHERE idNumber = ?", (count, s[0]))
    conn.commit()
    conn.close()

app = Flask(__name__)
app.secret_key = 'ccs_sitin_secret_key'


SUCCESS_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <nav class="navbar">
        <div class="nav-content">
            <div class="logo-section">
                <img src="{{ url_for('static', filename='images/ucmainccslogo.jpg') }}" alt="CCS Logo" class="navbar-logo">
                <span class="site-title">College of Computer Studies Sit-in Monitoring System</span>
            </div>
        </div>
    </nav>
    <div style="max-width:500px; margin:4rem auto; text-align:center;
                background:white; padding:2rem; border-radius:10px;
                box-shadow:0 2px 10px rgba(0,0,0,0.1);">
        <h2 style="color:#1e7e34; margin-bottom:1rem;">&#10003; {{ title }}</h2>
        <p style="color:#555; margin-bottom:2rem;">{{ message }}</p>
        <a href="{{ next_page }}" style="background:#0F3E7D; color:white;
           padding:0.8rem 2rem; border-radius:5px; text-decoration:none;
           font-weight:bold;">Continue &rarr;</a>
    </div>
</body>
</html>
"""

ERROR_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Error</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <nav class="navbar">
        <div class="nav-content">
            <div class="logo-section">
                <img src="{{ url_for('static', filename='images/ucmainccslogo.jpg') }}" alt="CCS Logo" class="navbar-logo">
                <span class="site-title">College of Computer Studies Sit-in Monitoring System</span>
            </div>
        </div>
    </nav>
    <div style="max-width:500px; margin:4rem auto; text-align:center;
                background:white; padding:2rem; border-radius:10px;
                box-shadow:0 2px 10px rgba(0,0,0,0.1);">
        <h2 style="color:#c0392b; margin-bottom:1rem;">&#10007; Error</h2>
        <p style="color:#555; margin-bottom:2rem;">{{ message }}</p>
        <a href="{{ back_page }}" style="background:#0F3E7D; color:white;
           padding:0.8rem 2rem; border-radius:5px; text-decoration:none;
           font-weight:bold;">&larr; Go Back</a>
    </div>
</body>
</html>
"""


# ══════════════════════════════════════════
# ROUTES — PAGES
# ══════════════════════════════════════════
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register.html')
def register_page():
    return render_template('register.html')

@app.route('/login', methods=['GET'])
def login_page():
    if session.get('student_id'):
        return redirect('/dashboard?loggedin=1')
    if session.get('admin'):
        return redirect('/admin/dashboard')
    return render_template('login.html')

@app.route('/admin/feedback/delete', methods=['POST'])
def admin_delete_feedback():
    if not session.get('admin'):
        return jsonify({'success': False}), 401
    feedback_id = request.form.get('id', '').strip()
    conn = _sqlite3.connect('database.db')
    conn.execute("DELETE FROM feedback WHERE id = ?", (feedback_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/admin/add-student', methods=['POST'])
def admin_add_student():
    if not session.get('admin'):
        return jsonify({'success': False, 'message': 'Not logged in.'}), 401

    id_number   = request.form.get('idNumber', '').strip()
    first_name  = request.form.get('firstName', '').strip().upper()
    last_name   = request.form.get('lastName', '').strip().upper()
    middle_name = request.form.get('middleName', '').strip().upper() or None
    course      = request.form.get('course', '').strip()
    year_level  = request.form.get('yearLevel', '').strip()
    email       = request.form.get('email', '').strip()
    address     = request.form.get('address', '').strip() or None
    password    = request.form.get('password', '').strip()

    if not id_number.isdigit() or len(id_number) != 8:
        return jsonify({'success': False, 'message': 'ID Number must be exactly 8 digits.'})
    if get_student_by_id(id_number):
        return jsonify({'success': False, 'message': 'ID Number is already registered.'})
    if len(password) < 6:
        return jsonify({'success': False, 'message': 'Password must be at least 6 characters.'})
    if '@' not in email:
        return jsonify({'success': False, 'message': 'Invalid email format.'})

    sitin_count = get_sitin_count(course)
    register_student(id_number, first_name, last_name, middle_name,
                     year_level, password, email, course, address, sitin_count)

    return jsonify({
        'success': True,
        'idNumber': id_number,
        'firstName': first_name.upper(),
        'lastName': last_name.upper(),
        'middleName': middle_name.upper() if middle_name else '',
        'course': course.upper(),
        'yearLevel': year_level,
        'email': email,
        'address': address or '',
        'sitin_count': sitin_count
    })
# ══════════════════════════════════════════
# ROUTE — REGISTER
# ══════════════════════════════════════════
@app.route('/register', methods=['POST'])
def register():
    id_number    = request.form.get('idNumber', '').strip()
    first_name   = request.form.get('firstName', '').strip()
    last_name    = request.form.get('lastName', '').strip()
    middle_name  = request.form.get('middleName', '').strip()
    course_level = request.form.get('yearLevel', '').strip()
    password     = request.form.get('password', '').strip()
    confirm_pass = request.form.get('confirmPassword', '').strip()
    email        = request.form.get('email', '').strip()
    course       = request.form.get('course', '').strip()
    address      = request.form.get('address', '').strip()

    form_data = {
        'idNumber':   id_number,
        'firstName':  first_name,
        'lastName':   last_name,
        'middleName': middle_name,
        'yearLevel':  course_level,
        'email':      email,
        'course':     course,
        'address':    address,
    }

    def render_error(msg):
        return render_template('register.html', error=msg, form_data=form_data)

    if not id_number.isdigit():
        return render_error("ID Number must contain numbers only.")
    if len(id_number) != 8:
        return render_error("ID Number must be exactly 8 digits.")
    if len(password) < 6:
        return render_error("Password must be at least 6 characters.")
    if password != confirm_pass:
        return render_error("Passwords do not match.")
    if '@' not in email:
        return render_error("Invalid email format.")
    if course_level not in ['1', '2', '3', '4']:
        return render_error("Please select a valid year level.")
    if not course:
        return render_error("Please select a course.")
    if get_student_by_id(id_number):
        return render_error("ID Number already registered! Please use a different ID or login instead.")

    sitin_count = get_sitin_count(course)
    register_student(id_number, first_name, last_name, middle_name,
                     course_level, password, email, course, address, sitin_count)

    return redirect('/login?registered=1')


# ══════════════════════════════════════════
# ROUTE — LOGIN
# ══════════════════════════════════════════
@app.route('/login', methods=['POST'])
def login():
    id_number = request.form.get('loginId', '').strip()
    password  = request.form.get('loginPassword', '').strip()

    admin = login_admin(id_number, password)
    if admin:
        session['admin']      = True
        session['admin_name'] = id_number
        return redirect('/admin/dashboard?loggedin=1')

    student = login_student(id_number, password)
    if student:
        session['student_id']   = student['idNumber']
        session['student_name'] = f"{student['firstName']} {student['lastName']}"
        return redirect('/dashboard?loggedin=1')

    return render_template('login.html', error="Invalid ID Number or Password!")


# ══════════════════════════════════════════
# ROUTE — STUDENT DASHBOARD
# ══════════════════════════════════════════
@app.route('/dashboard')
def dashboard():
    if not session.get('student_id'):
        return redirect('/login')

    student = get_student_by_id(session['student_id'])
    if not student:
        session.clear()
        return redirect('/login')

    sessions      = get_student_sessions(session['student_id'])
    announcements = get_all_announcements()

    # Build set of session IDs that already have feedback
    submitted_ids = set()
    for s in sessions:
        if has_feedback(s['id']):
            submitted_ids.add(s['id'])

    reservations = get_student_reservations(session['student_id'])
    res_settings = get_reservation_settings()
    return render_template('student_dashboard.html',
        student=student,
        sessions=sessions,
        announcements=announcements,
        submitted_feedback_ids=submitted_ids,
        reservations=reservations,
        res_settings=res_settings
    )


# ══════════════════════════════════════════
# ROUTE — STUDENT SUBMIT FEEDBACK (AJAX)
# ══════════════════════════════════════════
@app.route('/student/submit-feedback', methods=['POST'])
def student_submit_feedback():
    if not session.get('student_id'):
        return jsonify({'success': False, 'message': 'Not logged in.'}), 401

    id_number  = session['student_id']
    session_id = request.form.get('session_id', '').strip()
    message    = request.form.get('message', '').strip()
    rating_raw = request.form.get('rating', '0').strip()

    try:
        rating = int(rating_raw)
        if rating < 0 or rating > 5:
            rating = 0
    except (ValueError, TypeError):
        rating = 0

    if not session_id or not message:
        return jsonify({'success': False, 'message': 'Feedback message is required.'})

    flagged, word = contains_bad_words(message)
    if flagged:
        return jsonify({'success': False, 'message': 'Please keep feedback respectful.'})

    # Prevent duplicate feedback
    if has_feedback(int(session_id)):
        return jsonify({'success': False, 'message': 'You already submitted feedback for this session.'})

    # Get the lab from the session
    import sqlite3 as _sq
    conn = _sq.connect('database.db')
    conn.row_factory = _sq.Row
    row = conn.execute(
        "SELECT lab, pc_number FROM sitin_sessions WHERE id = ? AND idNumber = ?",
        (session_id, id_number)
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({'success': False, 'message': 'Session not found.'})

    lab = row['lab']
    pc_number = row['pc_number'] if row['pc_number'] else None
    conn.close()
    save_feedback(id_number, int(session_id), lab, message, rating, pc_number)

    return jsonify({'success': True, 'message': 'Feedback submitted successfully!'})


# ══════════════════════════════════════════
# ROUTE — STUDENT UPDATE PROFILE (AJAX)
# ══════════════════════════════════════════
@app.route('/student/update-profile', methods=['POST'])
def student_update_profile():
    import sqlite3 as _sq3, hashlib as _hl

    if not session.get('student_id'):
        return jsonify({'success': False, 'message': 'Not logged in.'}), 401

    id_number = session['student_id']

    try:
        current = get_student_by_id(id_number)
        if not current:
            return jsonify({'success': False, 'message': 'Student not found.'}), 404

        if not isinstance(current, dict):
            current = dict(current)

        def field(name, fallback):
            val = request.form.get(name, '').strip()
            return val if val else fallback

        first_name   = field('firstName',   current.get('firstName', ''))
        last_name    = field('lastName',    current.get('lastName', ''))
        email        = field('email',       current.get('email', ''))
        address      = request.form.get('address', '').strip() or None
        course       = field('course',      current.get('course') or '')
        course_level = field('yearLevel', current.get('yearLevel') or '')
        new_password = request.form.get('newPassword', '').strip()

        submitted_middle = request.form.get('middleName', '').strip()
        middle_name = submitted_middle if submitted_middle else None

        new_id = request.form.get('idNumber', '').strip()
        if not new_id.isdigit():
            return jsonify({'success': False, 'message': 'ID Number must contain numbers only.'})
        if len(new_id) != 8:
            return jsonify({'success': False, 'message': 'ID Number must be exactly 8 digits.'})

        if new_id != id_number:
            existing = get_student_by_id(new_id)
            if existing:
                return jsonify({'success': False, 'message': 'That ID Number is already taken by another student!'})

        if '@' not in email:
            return jsonify({'success': False, 'message': 'Invalid email format.'})
        if new_password and len(new_password) < 6:
            return jsonify({'success': False, 'message': 'Password must be at least 6 characters.'})

        old_course = current.get('course', '')
        old_is_ccs = old_course in CCS_COURSES
        new_is_ccs = course in CCS_COURSES

        if old_is_ccs != new_is_ccs:
            new_sitin_count = get_sitin_count(course)
        else:
            new_sitin_count = current.get('sitin_count', get_sitin_count(course))

        photo_url  = current.get('photo_url') or None
        photo_file = request.files.get('photo')
        if photo_file and photo_file.filename:
            ext = os.path.splitext(photo_file.filename)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                return jsonify({'success': False, 'message': 'Invalid image type.'})
            upload_folder = os.path.join(app.root_path, 'static', 'uploads', 'profiles')
            os.makedirs(upload_folder, exist_ok=True)
            filename  = f"profile_{id_number}{ext}"
            save_path = os.path.join(upload_folder, filename)
            photo_file.save(save_path)
            photo_url = f"/static/uploads/profiles/{filename}"

        conn = _sq3.connect('database.db')
        conn.row_factory = _sq3.Row

        try:
            conn.execute("ALTER TABLE students ADD COLUMN photo_url TEXT DEFAULT NULL")
            conn.commit()
        except _sq3.OperationalError:
            pass

        if new_password:
            hashed = _hl.sha256(new_password.encode()).hexdigest()
            conn.execute('''
                UPDATE students
                SET firstName=?, lastName=?, middleName=?,
                    email=?, address=?, course=?, yearLevel=?,
                    password=?, sitin_count=?,
                    photo_url=COALESCE(?, photo_url)
                WHERE idNumber=?
            ''', (first_name, last_name, middle_name,
                  email, address, course, course_level,
                  hashed, new_sitin_count, photo_url, id_number))
        else:
            conn.execute('''
                UPDATE students
                SET firstName=?, lastName=?, middleName=?,
                    email=?, address=?, course=?, yearLevel=?,
                    sitin_count=?,
                    photo_url=COALESCE(?, photo_url)
                WHERE idNumber=?
            ''', (first_name, last_name, middle_name,
                  email, address, course, course_level,
                  new_sitin_count, photo_url, id_number))

        conn.commit()
        conn.close()

        session['student_name'] = f"{first_name} {last_name}"
        full_name = f"{first_name} {middle_name} {last_name}" if middle_name else f"{first_name} {last_name}"

        return jsonify({
            'success':    True,
            'fullName':   full_name,
            'photoUrl':   photo_url,
            'course':     course,
            'yearLevel':  course_level,
            'email':      email,
            'address':    address or '',
            'sitinCount': new_sitin_count
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ══════════════════════════════════════════
# ROUTE — LOGOUT
# ══════════════════════════════════════════
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# ══════════════════════════════════════════
# ROUTE — ADMIN DASHBOARD
# ══════════════════════════════════════════
@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect('/login')

    students       = get_all_students()
    sessions       = get_all_sessions()
    announcements  = get_all_announcements()
    purpose_counts = get_purpose_counts()
    lab_counts = get_lab_counts()
    feedback_list  = get_all_feedback()

    all_reservations = get_all_reservations()
    res_settings = get_reservation_settings()
    reservation_log = get_reservation_log()
    return render_template('admin_dashboard.html',
        students=students,
        sessions=sessions,
        announcements=announcements,
        purpose_counts=purpose_counts,
        lab_counts=lab_counts,
        feedback_list=feedback_list,
        all_reservations=all_reservations,
        res_settings=res_settings,
        reservation_log=reservation_log
    )


# ══════════════════════════════════════════
# ROUTE — ADMIN ADD SIT-IN (AJAX)
# ══════════════════════════════════════════
@app.route('/admin/sitin/add-ajax', methods=['POST'])
def admin_add_sitin_ajax():
    if not session.get('admin'):
        return jsonify({'success': False, 'message': 'Not logged in.'}), 401
    id_number = request.form.get('idNumber', '').strip()
    purpose   = request.form.get('purpose', '').strip()
    lab       = request.form.get('lab', '').strip()
    if not id_number or not purpose or not lab:
        return jsonify({'success': False, 'message': 'All fields are required.'})
    student = get_student_by_id(id_number)
    if not student:
        return jsonify({'success': False, 'message': f"Student ID '{id_number}' not found."})
    if student['sitin_count'] <= 0:
        return jsonify({'success': False, 'message': 'Student has no remaining sit-in sessions.'})

    from datetime import date as _date
    today = _date.today().isoformat()
    conn_check = _sqlite3.connect('database.db')

    # Check pending reservation
    existing_res = conn_check.execute("""
        SELECT id, lab, pc_number, time_in, status FROM reservations
        WHERE idNumber = ? AND date = ? AND status = 'pending'
    """, (id_number, today)).fetchone()

    # Check active sit-in session
    active_session = conn_check.execute("""
        SELECT id FROM sitin_sessions
        WHERE idNumber = ? AND status = 'active'
    """, (id_number,)).fetchone()

    conn_check.close()

    if existing_res:
        return jsonify({
            'success': False,
            'message': f"⚠️ This student has a PENDING reservation today for Lab {existing_res[1]}, PC {existing_res[2]} at {existing_res[3]}. Please go to the Reservation tab to process it, or reject it first before doing a walk-in."
        })

    if active_session:
        return jsonify({
            'success': False,
            'message': f"⚠️ This student already has an ACTIVE sit-in session! Please logout their current session first before starting a new one."
        })

    pc_number = request.form.get('pc_number', '').strip()
    pc_number = int(pc_number) if pc_number.isdigit() else None
    session_id, error = add_sitin(id_number, purpose, lab, pc_number)
    if error:
        return jsonify({'success': False, 'message': error})
    reservation_id = request.form.get('reservation_id', '').strip()
    if reservation_id:
        update_reservation_status(int(reservation_id), 'sitting_in')
        # Link the session to the reservation
        conn2 = _sqlite3.connect('database.db')
        conn2.execute("UPDATE reservations SET session_id=? WHERE id=?", (session_id, int(reservation_id)))
        conn2.commit()
        conn2.close()
    return jsonify({'success': True, 'message': 'Sit-in successful.', 'sessionId': session_id, 'pc_number': pc_number})

@app.route('/admin/get-active-session', methods=['GET'])
def admin_get_active_session():
    if not session.get('admin'):
        return jsonify({'success': False}), 401
    id_number = request.args.get('idNumber', '').strip()
    conn = _sqlite3.connect('database.db')
    row = conn.execute(
        "SELECT id FROM sitin_sessions WHERE idNumber=? AND status='active' ORDER BY id DESC LIMIT 1",
        (id_number,)
    ).fetchone()
    conn.close()
    if row:
        return jsonify({'sessionId': row[0]})
    return jsonify({'sessionId': None})
# ══════════════════════════════════════════
# ROUTE — ADMIN END SIT-IN
# ══════════════════════════════════════════
@app.route('/admin/sitin/end/<int:session_id>', methods=['POST'])
def admin_end_sitin(session_id):
    if not session.get('admin'):
        return redirect('/login')
    end_sitin(session_id)
    conn = _sqlite3.connect('database.db')
    res = conn.execute(
        "SELECT id FROM reservations WHERE session_id=? AND status='sitting_in'",
        (session_id,)
    ).fetchone()
    conn.close()
    if res:
        update_reservation_status(res[0], 'done')
    return redirect('/admin/dashboard')


# ══════════════════════════════════════════
# ROUTE — ADMIN RESET ALL SESSIONS
# ══════════════════════════════════════════
@app.route('/admin/sessions/reset-all', methods=['POST'])
def admin_reset_all_sessions():
    if not session.get('admin'):
        return redirect('/login')
    reset_all_sessions()
    return redirect('/admin/dashboard')


# ══════════════════════════════════════════
# ROUTE — ADMIN ADD ANNOUNCEMENT
# ══════════════════════════════════════════
@app.route('/admin/announcement/add', methods=['POST'])
def admin_add_announcement():
    if not session.get('admin'):
        return redirect('/login')
    title   = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    if not title or not content:
        return render_template_string(ERROR_PAGE,
            message="Title and content are required!", back_page="/admin/dashboard")
    add_announcement(title, content, session['admin_name'])
    return redirect('/admin/dashboard')


# ══════════════════════════════════════════
# ROUTE — ADMIN EDIT ANNOUNCEMENT (AJAX)
# ══════════════════════════════════════════
@app.route('/admin/announcement/edit', methods=['POST'])
def admin_edit_announcement():
    if not session.get('admin'):
        return jsonify({'success': False, 'message': 'Not logged in.'}), 401
    ann_id  = request.form.get('id', '').strip()
    title   = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    if not ann_id or not title or not content:
        return jsonify({'success': False, 'message': 'All fields are required.'})
    edit_announcement(int(ann_id), title, content)
    return jsonify({'success': True, 'id': int(ann_id), 'title': title, 'content': content})


# ══════════════════════════════════════════
# ROUTE — ADMIN DELETE ANNOUNCEMENT (AJAX)
# ══════════════════════════════════════════
@app.route('/admin/announcement/delete', methods=['POST'])
def admin_delete_announcement():
    if not session.get('admin'):
        return jsonify({'success': False, 'message': 'Not logged in.'}), 401
    ann_id = request.form.get('id', '').strip()
    if not ann_id:
        return jsonify({'success': False, 'message': 'ID required.'})
    delete_announcement(int(ann_id))
    return jsonify({'success': True, 'id': int(ann_id)})

# ══════════════════════════════════════════
# ROUTE — SIT IN (AJAX)
# ══════════════════════════════════════════
@app.route('/admin/sitin/end-from-res/<int:session_id>/<int:res_id>', methods=['POST'])
def admin_end_sitin_from_res(session_id, res_id):
    if not session.get('admin'):
        return jsonify({'success': False}), 401
    end_sitin(session_id)
    update_reservation_status(res_id, 'done')
    return jsonify({'success': True})
# ══════════════════════════════════════════
# ROUTE — ADMIN TOGGLE PIN ANNOUNCEMENT (AJAX)
# ══════════════════════════════════════════
@app.route('/admin/announcement/pin', methods=['POST'])
def admin_pin_announcement():
    if not session.get('admin'):
        return jsonify({'success': False, 'message': 'Not logged in.'}), 401
    ann_id = request.form.get('id', '').strip()
    if not ann_id:
        return jsonify({'success': False, 'message': 'ID required.'})
    new_val = toggle_pin_announcement(int(ann_id))
    if new_val is None:
        return jsonify({'success': False, 'message': 'Announcement not found.'})
    return jsonify({'success': True, 'id': int(ann_id), 'is_pinned': new_val})


# ══════════════════════════════════════════
# ROUTE — ADMIN SEARCH STUDENT (AJAX)
# ══════════════════════════════════════════
@app.route('/admin/search-student', methods=['GET'])
def admin_search_student():
    if not session.get('admin'):
        return jsonify({'success': False, 'message': 'Not logged in.'}), 401
    id_number = request.args.get('idNumber', '').strip()
    if not id_number:
        return jsonify({'success': False, 'message': 'Please enter a Student ID.'})
    student = get_student_by_id(id_number)
    if not student:
        return jsonify({'success': False, 'message': 'NO RECORDS AVAILABLE'})
    if not isinstance(student, dict):
        student = dict(student)
    return jsonify({
        'success':    True,
        'idNumber':   student.get('idNumber', ''),
        'firstName':  student.get('firstName', ''),
        'lastName':   student.get('lastName', ''),
        'middleName': student.get('middleName', '') or '',
        'remaining':  student.get('sitin_count', 0)
    })


# ══════════════════════════════════════════
# ROUTE — ADMIN EDIT STUDENT
# ══════════════════════════════════════════
@app.route('/admin/edit-student', methods=['POST'])
def admin_edit_student():
    if not session.get('admin'):
        return jsonify({'success': False, 'message': 'Not logged in.'}), 401

    id_number     = request.form.get('idNumber', '').strip()
    new_id_number = request.form.get('newIdNumber', '').strip() or id_number
    first_name   = request.form.get('firstName', '').strip().upper()
    last_name    = request.form.get('lastName', '').strip().upper()
    middle_name  = request.form.get('middleName', '').strip().upper() or None
    email        = request.form.get('email', '').strip()
    course       = request.form.get('course', '').strip()
    course_level = request.form.get('yearLevel', '').strip()
    address      = request.form.get('address', '').strip() or None
    sitin_count_raw = request.form.get('sitin_count', '').strip()
    sitin_count     = int(sitin_count_raw) if sitin_count_raw else get_sitin_count(course)

    # Get old course to check if CCS status changed
    old_student = get_student_by_id(id_number)
    if old_student:
        old_course  = old_student['course'] or ''
        old_is_ccs  = old_course in CCS_COURSES
        new_is_ccs  = course in CCS_COURSES
        if old_is_ccs != new_is_ccs:
            sitin_count = get_sitin_count(course)

    conn = _sqlite3.connect('database.db')
    conn.execute(
        '''UPDATE students
        SET idNumber=?, firstName=?, lastName=?, middleName=?,
            email=?, course=?, yearLevel=?, address=?, sitin_count=?
        WHERE idNumber=?''',
        (new_id_number, first_name, last_name, middle_name, email,
        course, course_level, address, sitin_count, id_number)
    )
    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'idNumber': new_id_number,
        'firstName': first_name,
        'lastName': last_name,
        'middleName': middle_name or '',
        'course': course,
        'yearLevel': course_level,
        'sitin_count': sitin_count
    })

# ══════════════════════════════════════════
# RESERVATION AUTO-EXPIRE
# ══════════════════════════════════════════
@app.route('/admin/reservations/auto-expire', methods=['POST'])
def admin_auto_expire():
    conn = _sqlite3.connect('database.db')
    rows = conn.execute("""
        SELECT id FROM reservations
        WHERE status IN ('pending', 'approved')
        AND datetime(date || ' ' || time_in) < datetime('now', 'localtime', '-30 minutes')
    """).fetchall()
    expired_ids = [r[0] for r in rows]
    conn.execute("""
        UPDATE reservations 
        SET status='expired',
            message='⏰ Your reservation has expired as your time slot has already passed. Please book a new reservation at a different time. We apologize for any inconvenience this may have caused.'
        WHERE status IN ('pending', 'approved')
        AND datetime(date || ' ' || time_in) < datetime('now', 'localtime', '-30 minutes')
    """)
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'expired_ids': expired_ids})

# ══════════════════════════════════════════
# Get blocked PCs for a lab
# ══════════════════════════════════════════
@app.route('/admin/get-blocked-pcs', methods=['GET'])
def admin_get_blocked_pcs():
    if not session.get('admin'):
        return jsonify({'success': False}), 401
    lab = request.args.get('lab', '').strip()
    if not lab:
        return jsonify({'blocked': [], 'occupied': []})
    blocked  = get_blocked_pcs(lab)
    occupied = get_occupied_pcs(lab)
    reserved = get_reserved_pcs_today(lab)
    return jsonify({'blocked': blocked, 'occupied': occupied, 'reserved': reserved})

# ══════════════════════════════════════════
#  Toggle a PC blocked/unblocked
# ══════════════════════════════════════════
@app.route('/admin/toggle-pc-block', methods=['POST'])
def admin_toggle_pc_block():
    if not session.get('admin'):
        return jsonify({'success': False}), 401
    lab       = request.form.get('lab', '').strip()
    pc_number = request.form.get('pc_number', '').strip()
    blocked   = request.form.get('blocked', '0').strip()
    if not lab or not pc_number:
        return jsonify({'success': False, 'message': 'Missing fields.'})
    set_pc_blocked(lab, int(pc_number), blocked == '1')
    return jsonify({'success': True, 'blocked': blocked == '1'})

# ══════════════════════════════════════════
# RESERVATION DELETE
# ══════════════════════════════════════════
@app.route('/admin/reservations/delete', methods=['POST'])
def admin_delete_reservation():
    if not session.get('admin'):
        return jsonify({'success': False}), 401
    res_id = request.form.get('id', '').strip()
    conn = _sqlite3.connect('database.db')
    conn.execute("DELETE FROM reservations WHERE id = ?", (res_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})
# ══════════════════════════════════════════
# ROUTE — ADMIN DELETE STUDENT
# ══════════════════════════════════════════
@app.route('/admin/delete-student', methods=['POST'])
def admin_delete_student():
    if not session.get('admin'):
        return redirect('/login')
    id_number = request.form.get('idNumber', '').strip()
    conn = _sqlite3.connect('database.db')
    conn.execute("DELETE FROM students WHERE idNumber = ?", (id_number,))
    conn.commit()
    conn.close()
    return redirect('/admin/dashboard')

@app.route('/student/reserve', methods=['POST'])
def student_reserve():
    if not session.get('student_id'):
        return jsonify({'success': False, 'message': 'Not logged in.'}), 401

    settings = get_reservation_settings()
    if settings and not settings['enabled']:
        return jsonify({'success': False, 'message': settings['message']})

    id_number = session['student_id']
    purpose   = request.form.get('purpose', '').strip()
    lab       = request.form.get('lab', '').strip()
    pc_number = request.form.get('pc_number', '').strip()
    time_in   = request.form.get('time_in', '').strip()
    date      = request.form.get('date', '').strip()

    if not purpose or not lab or not time_in or not date or not pc_number:
        return jsonify({'success': False, 'message': 'All fields are required.'})

    from datetime import datetime as _dt2
    now = _dt2.now()
    today_str = now.date().isoformat()

    # Block past dates
    if date < today_str:
        return jsonify({'success': False, 'message': 'You cannot book a reservation in the past.'})

    # Block Sundays (weekday 6 = Sunday)
    from datetime import date as _d
    booking_date = _d.fromisoformat(date)
    if booking_date.weekday() == 6:
        return jsonify({'success': False, 'message': 'Reservations are not allowed on Sundays.'})

    # Block past time if booking for today
    if date == today_str:
        if time_in <= now.strftime('%H:%M'):
            return jsonify({'success': False, 'message': 'That time has already passed. Please choose a future time.'})

    if time_in < '08:00' or time_in > '20:00':
        return jsonify({'success': False, 'message': 'Reservation time must be between 8:00 AM and 8:00 PM only.'})

    student = get_student_by_id(id_number)
    if not student or student['sitin_count'] <= 0:
        return jsonify({'success': False, 'message': 'No remaining sessions.'})

    res_id, error = add_reservation(id_number, purpose, lab, int(pc_number), time_in, date)
    if error:
        return jsonify({'success': False, 'message': error})
    return jsonify({'success': True, 'reservationId': res_id})

# ══════════════════════════════════════════
# ROUTE — STUDENT RESERVATION
# ══════════════════════════════════════════
@app.route('/admin/reservations/update', methods=['POST'])
def admin_update_reservation():
    if not session.get('admin'):
        return jsonify({'success': False}), 401
    res_id  = request.form.get('id', '').strip()
    status  = request.form.get('status', '').strip()
    message = request.form.get('message', '').strip() or None
    update_reservation_status(int(res_id), status)
    if message:
        update_reservation_message(int(res_id), message)
    return jsonify({'success': True})

@app.route('/admin/reservation-settings', methods=['POST'])
def admin_reservation_settings():
    if not session.get('admin'):
        return jsonify({'success': False}), 401
    enabled = int(request.form.get('enabled', 1))
    message = request.form.get('message', '').strip()
    set_reservation_enabled(enabled, message if message else None)
    return jsonify({'success': True, 'enabled': enabled})

@app.route('/admin/get-reserved-pcs', methods=['GET'])
def admin_get_reserved_pcs():
    lab  = request.args.get('lab', '').strip()
    date = request.args.get('date', '').strip()
    if not lab or not date:
        return jsonify({'reserved': []})
    
    import sqlite3 as _sq
    conn = _sq.connect('database.db')
    
    # Only actual reservations for that date
    rows = conn.execute("""
        SELECT pc_number FROM reservations
        WHERE lab=? AND date=? AND status NOT IN ('rejected', 'expired', 'done')
    """, (lab, date)).fetchall()
    
    # Blocked PCs
    blocked = conn.execute(
        "SELECT pc_number FROM blocked_pcs WHERE lab=?", (lab,)
    ).fetchall()
    
    # Currently occupied (active sit-in)
    occupied = conn.execute("""
        SELECT pc_number FROM sitin_sessions
        WHERE lab=? AND status='active' AND pc_number IS NOT NULL
    """, (lab,)).fetchall()
    
    conn.close()
    
    reserved_list = [r[0] for r in rows if r[0]]
    blocked_list  = [r[0] for r in blocked]
    occupied_list = [r[0] for r in occupied]
    
    return jsonify({
        'reserved': reserved_list,
        'blocked':  blocked_list,
        'occupied': occupied_list
    })

@app.route('/admin/get-available-pcs', methods=['GET'])
def admin_get_available_pcs():
    if not session.get('admin'):
        return jsonify({'success': False}), 401
    lab = request.args.get('lab', '').strip()
    date = request.args.get('date', '').strip()
    if not date:
        from datetime import date as _date
        date = _date.today().isoformat()
    if not lab:
        return jsonify({'available': []})
    
    from datetime import date as _dt
    today = _dt.today().isoformat()
    
    total_pcs = 50
    blocked  = get_blocked_pcs(lab)
    occupied = get_occupied_pcs(lab)
    
    # Also exclude PCs reserved for today
    conn = _sqlite3.connect('database.db')
    reserved_today = conn.execute("""
        SELECT pc_number FROM reservations
        WHERE lab=? AND date=? AND status IN ('pending', 'approved', 'sitting_in')
    """, (lab, today)).fetchall()
    conn.close()
    reserved_today = [r[0] for r in reserved_today]
    
    unavailable = set(blocked + occupied + reserved_today)
    available = [i for i in range(1, total_pcs + 1) if i not in unavailable]
    return jsonify({'available': available})

@app.route('/admin/reservations/update-pc', methods=['POST'])
def admin_update_reservation_pc():
    if not session.get('admin'):
        return jsonify({'success': False}), 401
    res_id    = request.form.get('id', '').strip()
    pc_number = request.form.get('pc_number', '').strip()
    if not res_id or not pc_number:
        return jsonify({'success': False, 'message': 'Missing fields.'})
    conn = _sqlite3.connect('database.db')

    # Update reservations table
    conn.execute("UPDATE reservations SET pc_number=? WHERE id=?", (int(pc_number), int(res_id)))

    # Only update sitin_sessions if it was created FROM this reservation
    # Update sitin_sessions linked to this reservation
    res = conn.execute("SELECT idNumber, session_id FROM reservations WHERE id=?", (int(res_id),)).fetchone()
    if res and res[1]:
        conn.execute("""
            UPDATE sitin_sessions SET pc_number=?
            WHERE id=? AND status='active'
        """, (int(pc_number), res[1]))

    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/admin/reservations/edit-details', methods=['POST'])
def admin_edit_reservation_details():
    if not session.get('admin'):
        return jsonify({'success': False}), 401
    res_id = request.form.get('id', '').strip()
    date   = request.form.get('date', '').strip()
    lab    = request.form.get('lab', '').strip()
    pc     = request.form.get('pc_number', '').strip()
    if not res_id or not date or not lab or not pc:
        return jsonify({'success': False, 'message': 'All fields are required.'})
    conn = _sqlite3.connect('database.db')
    conn.execute("""
        UPDATE reservations SET date=?, lab=?, pc_number=? WHERE id=?
    """, (date, lab, int(pc), int(res_id)))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

def format_time(time_str):
    if not time_str:
        return '—'
    try:
        from datetime import datetime
        t = datetime.strptime(time_str.strip(), '%H:%M:%S')
        return t.strftime('%I:%M %p')
    except:
        try:
            from datetime import datetime
            t = datetime.strptime(time_str.strip(), '%H:%M')
            return t.strftime('%I:%M %p')
        except:
            return time_str

app.jinja_env.filters['timeformat'] = format_time
# ══════════════════════════════════════════
# ROUTE — ADMIN LOGOUT
# ══════════════════════════════════════════
@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect('/')

# ══════════════════════════════════════════
# ROUTE —  FORGOT PSSWORD
# ══════════════════════════════════════════
@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    return jsonify({'success': True, 'message': '✓ If your ID and email match, a reset link has been sent.'})
# ══════════════════════════════════════════
# RUN
# ══════════════════════════════════════════
if __name__ == '__main__':
    init_db()
    init_reservations_table()
    init_reservation_settings()
    print("=================================")
    print("CCS Sit-in System Server Running!")
    print("Open: http://localhost:5000")
    print("=================================")
    app.run(debug=True)