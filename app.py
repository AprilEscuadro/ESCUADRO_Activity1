import os
from flask import Flask, request, redirect, render_template, render_template_string, session, jsonify
from dbhelper import (
    get_student_notifications,
    mark_notification_read,
    get_read_notification_ids,
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
    get_reserved_pcs_today, mark_announcement_read,
    get_read_announcement_ids,
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
    notifications = get_student_notifications(session['student_id'])
    read_notif_ids = get_read_notification_ids(session['student_id'])
    read_ann_ids = get_read_announcement_ids(session['student_id'])
    unread_notif_count = sum(1 for n in notifications if n['res_id'] not in read_notif_ids)
    unread_ann_count = sum(1 for a in announcements if a['id'] not in read_ann_ids)
    return render_template('student_dashboard.html',
        student=student,
        sessions=sessions,
        announcements=announcements,
        submitted_feedback_ids=submitted_ids,
        reservations=reservations,
        res_settings=res_settings,
        notifications=notifications,
        read_notif_ids=read_notif_ids,
        read_ann_ids=read_ann_ids,
        unread_notif_count=unread_notif_count,
        unread_ann_count=unread_ann_count,
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
    from datetime import datetime as _dt_now, timezone as _tz, timedelta as _td
    PH_TZ = _tz(_td(hours=8))
    now_str = _dt_now.now(PH_TZ).strftime('%H:%M')
    # Pass only time_start — add_sitin will auto-calculate end based on next reservation
    # If sit-in is from a reservation, use the reservation's actual time_end
    res_time_end = None
    reservation_id = request.form.get('reservation_id', '').strip()
    if reservation_id:
        conn3 = _sqlite3.connect('database.db')
        res_row = conn3.execute(
            "SELECT time_end FROM reservations WHERE id=?", (reservation_id,)
        ).fetchone()
        conn3.close()
        if res_row and res_row[0]:
            res_time_end = res_row[0]

    session_id, error, time_end = add_sitin(id_number, purpose, lab, pc_number, now_str, time_end=res_time_end)
    if error:
        return jsonify({'success': False, 'message': error})
    if reservation_id:
        update_reservation_status(int(reservation_id), 'sitting_in')
        conn2 = _sqlite3.connect('database.db')
        conn2.execute("UPDATE reservations SET session_id=? WHERE id=?", (session_id, int(reservation_id)))
        conn2.commit()
        conn2.close()
    return jsonify({'success': True, 'message': 'Sit-in successful.', 'sessionId': session_id, 'pc_number': pc_number, 'time_end': time_end})

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
    
    from datetime import datetime, timezone, timedelta
    PH_TZ = timezone(timedelta(hours=8))
    now_str = datetime.now(PH_TZ).strftime('%H:%M')
    
    end_sitin(session_id)
    
    conn = _sqlite3.connect('database.db')
    res = conn.execute(
        "SELECT id FROM reservations WHERE session_id=? AND status='sitting_in'",
        (session_id,)
    ).fetchone()
    if res:
        conn.execute("UPDATE reservations SET time_out=? WHERE id=?", (now_str, res[0]))
        conn.commit()
        update_reservation_status(res[0], 'done')
    conn.close()
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
    
    from datetime import datetime, timezone, timedelta
    PH_TZ = timezone(timedelta(hours=8))
    now_str = datetime.now(PH_TZ).strftime('%H:%M')
    
    end_sitin(session_id)
    update_reservation_status(res_id, 'done')
    
    # Save actual logout time to reservation
    conn = _sqlite3.connect('database.db')
    conn.execute("UPDATE reservations SET time_out=? WHERE id=?", (now_str, res_id))
    conn.commit()
    conn.close()
    
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
    if not session.get('admin') and not session.get('student_id'):
        return jsonify({'success': False}), 401
    lab        = request.args.get('lab', '').strip()
    date       = request.args.get('date', '').strip()
    time_start = request.args.get('time_start', '').strip()
    time_end   = request.args.get('time_end', '').strip()
    if not lab:
        return jsonify({'blocked': [], 'occupied': [], 'reserved': []})
    
    blocked  = get_blocked_pcs(lab)
    from datetime import date as _date
    _today = _date.today().isoformat()
    if date == _today:
        occupied = get_occupied_pcs(lab, slot_start=time_start, slot_end=time_end)
    else:
        occupied = []
    
    conn = _sqlite3.connect('database.db')
    if date and time_start and time_end:
        rows = conn.execute("""
            SELECT pc_number FROM reservations
            WHERE lab=? AND date=?
            AND status NOT IN ('rejected', 'expired', 'done', 'cancelled')
            AND time_in < ? AND COALESCE(time_end, time_in) > ?
        """, (lab, date, time_end, time_start)).fetchall()
    elif date:
        rows = conn.execute("""
            SELECT pc_number FROM reservations
            WHERE lab=? AND date=?
            AND status NOT IN ('rejected', 'expired', 'done', 'cancelled')
        """, (lab, date)).fetchall()
    else:
        rows = conn.execute("""
            SELECT pc_number FROM reservations
            WHERE lab=? AND date=date('now','localtime')
            AND status NOT IN ('rejected', 'expired', 'done', 'cancelled')
        """, (lab,)).fetchall()
    conn.close()
    
    return jsonify({
        'blocked':  blocked,
        'occupied': occupied,
        'reserved': [r[0] for r in rows if r[0]]
    })

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
    time_end  = request.form.get('time_end', '').strip()
    date      = request.form.get('date', '').strip()
    if not time_end:
        # default +2 hours
        from datetime import datetime, timedelta
        try:
            t = datetime.strptime(time_in, '%H:%M')
            time_end = (t + timedelta(hours=2)).strftime('%H:%M')
        except:
            time_end = time_in

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

    res_id, error = add_reservation(id_number, purpose, lab, int(pc_number), time_in, date, time_end)
    if error:
        return jsonify({'success': False, 'message': error})
    return jsonify({'success': True, 'reservationId': res_id})

@app.route('/student/mark-notification-read', methods=['POST'])
def student_mark_notification_read():
    if not session.get('student_id'):
        return jsonify({'success': False}), 401
    res_id = request.form.get('res_id', '').strip()
    if res_id:
        mark_notification_read(session['student_id'], int(res_id))
    return jsonify({'success': True})

@app.route('/student/cancel-reservation', methods=['POST'])
def student_cancel_reservation():
    if not session.get('student_id'):
        return jsonify({'success': False, 'message': 'Not logged in.'}), 401
    res_id = request.form.get('id', '').strip()
    id_number = session['student_id']
    conn = _sqlite3.connect('database.db')
    row = conn.execute(
        "SELECT status FROM reservations WHERE id=? AND idNumber=?",
        (res_id, id_number)
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({'success': False, 'message': 'Reservation not found.'})
    if row[0] not in ('pending', 'approved'):
        conn.close()
        return jsonify({'success': False, 'message': 'Only pending or approved reservations can be cancelled.'})
    conn.execute(
        "UPDATE reservations SET status='cancelled', message='Cancelled by student.' WHERE id=?",
        (res_id,)
    )
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/admin/reservations/update-pc-time', methods=['POST'])
def admin_update_reservation_pc_time():
    if not session.get('admin'):
        return jsonify({'success': False}), 401
    res_id    = request.form.get('id', '').strip()
    pc_number = request.form.get('pc_number', '').strip()
    time_in   = request.form.get('time_in', '').strip()
    time_end  = request.form.get('time_end', '').strip()

    if not res_id:
        return jsonify({'success': False, 'message': 'Missing reservation ID.'})

    conn = _sqlite3.connect('database.db')
    updates = []
    params  = []
    if pc_number:
        updates.append('pc_number=?')
        params.append(int(pc_number))
    if time_in:
        updates.append('time_in=?')
        params.append(time_in)
    if time_end:
        updates.append('time_end=?')
        params.append(time_end)
    date = request.form.get('date', '').strip()
    if date:
        updates.append('date=?')
        params.append(date)
    if not updates:
        conn.close()
        return jsonify({'success': False, 'message': 'Nothing to update.'})

    params.append(int(res_id))
    conn.execute(f"UPDATE reservations SET {', '.join(updates)} WHERE id=?", params)

    # Only update pc_number on linked session if changed
    res = conn.execute("SELECT session_id FROM reservations WHERE id=?", (int(res_id),)).fetchone()
    if res and res[0] and pc_number:
        conn.execute("UPDATE sitin_sessions SET pc_number=? WHERE id=? AND status='active'",
                     (int(pc_number), res[0]))
    conn.commit()
    conn.close()
    return jsonify({'success': True})
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

    # ── NEW: if approved, shorten current sitter's time_end on that PC ──
    if status == 'approved':
        conn = _sqlite3.connect('database.db')
        res = conn.execute(
            "SELECT lab, pc_number, time_in, date FROM reservations WHERE id=?",
            (int(res_id),)
        ).fetchone()
        if res:
            lab, pc_number, approved_time_in, res_date = res
            from datetime import date as _date
            today = _date.today().isoformat()
            if res_date == today and pc_number:
                active = conn.execute("""
                    SELECT id FROM sitin_sessions
                    WHERE lab=? AND pc_number=? AND status='active'
                """, (lab, pc_number)).fetchone()
                if active:
                    conn.execute("""
                        UPDATE sitin_sessions SET time_end=?
                        WHERE id=?
                    """, (approved_time_in, active[0]))
                    conn.commit()
        conn.close()

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
    lab        = request.args.get('lab', '').strip()
    date       = request.args.get('date', '').strip()
    time_start = request.args.get('time_start', '').strip()
    time_end   = request.args.get('time_end', '').strip()
    if not lab or not date:
        return jsonify({'reserved': [], 'blocked': [], 'occupied': []})

    import sqlite3 as _sq
    conn = _sq.connect('database.db')

    # If time slot provided, only get PCs that OVERLAP with this slot
    if time_start and time_end:
        rows = conn.execute("""
            SELECT pc_number FROM reservations
            WHERE lab=? AND date=?
            AND status NOT IN ('rejected', 'expired', 'done', 'cancelled')
            AND time_in < ? AND COALESCE(time_end, time_in) > ?
        """, (lab, date, time_end, time_start)).fetchall()
    else:
        # No time slot = show all reserved for that date
        rows = conn.execute("""
            SELECT pc_number FROM reservations
            WHERE lab=? AND date=?
            AND status NOT IN ('rejected', 'expired', 'done', 'cancelled')
        """, (lab, date)).fetchall()

    blocked = conn.execute(
        "SELECT pc_number FROM blocked_pcs WHERE lab=?", (lab,)
    ).fetchall()

    conn.close()

    # Occupied = active sit-ins, filtered by time slot overlap if provided
    from datetime import date as _date
    today = _date.today().isoformat()

    if date == today:
        occupied = get_occupied_pcs(lab, slot_start=time_start or None, slot_end=time_end or None)
    else:
        occupied = []

    return jsonify({
        'reserved': [r[0] for r in rows if r[0]],
        'blocked':  [r[0] for r in blocked if r[0]],
        'occupied': occupied
    })

@app.route('/admin/get-available-pcs', methods=['GET'])
def admin_get_available_pcs():
    if not session.get('admin'):
        return jsonify({'success': False}), 401
    lab  = request.args.get('lab', '').strip()
    if not lab:
        return jsonify({'available': []})

    from datetime import datetime, timezone, timedelta
    PH_TZ = timezone(timedelta(hours=8))
    now_str = datetime.now(PH_TZ).strftime('%H:%M')
    today = datetime.now(PH_TZ).strftime('%Y-%m-%d')

    blocked  = get_blocked_pcs(lab)
    occupied = get_occupied_pcs(lab)

    conn = _sqlite3.connect('database.db')
    # Only block PCs where reservation starts within 30 minutes or already started
    reserved_rows = conn.execute("""
        SELECT pc_number FROM reservations
        WHERE lab=? AND date=? 
        AND status IN ('pending', 'approved', 'sitting_in')
        AND time_in <= ?
    """, (lab, today, 
          (datetime.now(PH_TZ) + timedelta(minutes=30)).strftime('%H:%M')
    )).fetchall()
    conn.close()

    reserved_soon = [r[0] for r in reserved_rows]
    unavailable = set(blocked + occupied + reserved_soon)
    available = [i for i in range(1, 51) if i not in unavailable]
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
    from datetime import datetime, timedelta
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
        try:
            t = datetime.strptime(time_str.strip(), fmt)
            # If hour is between 0-15, likely UTC — add 8 hours
            if t.hour <= 15:
                t = t + timedelta(hours=8)
            return t.strftime('%I:%M %p')
        except:
            continue
    for fmt in ('%H:%M:%S', '%H:%M'):
        try:
            t = datetime.strptime(time_str.strip(), fmt)
            return t.strftime('%I:%M %p')
        except:
            continue
    return time_str

app.jinja_env.filters['timeformat'] = format_time

@app.route('/student/mark-announcement-read', methods=['POST'])
def student_mark_announcement_read():
    if not session.get('student_id'):
        return jsonify({'success': False}), 401
    ann_id = request.form.get('ann_id', '').strip()
    if ann_id:
        mark_announcement_read(session['student_id'], int(ann_id))
    return jsonify({'success': True})

@app.route('/admin/sitin/check-overdue', methods=['POST'])
def admin_check_overdue():
    if not session.get('admin'):
        return jsonify({'success': False}), 401
    from datetime import datetime
    now = datetime.now().strftime('%H:%M')
    conn = _sqlite3.connect('database.db')
    # Mark sessions as overdue where time_end has passed but still active
    overdue = conn.execute("""
        SELECT id FROM sitin_sessions
        WHERE status='active' AND session_status != 'overdue'
        AND time_end IS NOT NULL AND time_end <= ?
    """, (now,)).fetchall()
    overdue_ids = [r[0] for r in overdue]
    if overdue_ids:
        conn.execute("""
            UPDATE sitin_sessions SET session_status='overdue'
            WHERE status='active' AND session_status != 'overdue'
            AND time_end IS NOT NULL AND time_end <= ?
        """, (now,))
        conn.commit()
    conn.close()
    return jsonify({'success': True, 'overdue_ids': overdue_ids})

@app.route('/admin/sitin/extend/<int:session_id>', methods=['POST'])
def admin_extend_sitin(session_id):
    if not session.get('admin'):
        return jsonify({'success': False}), 401
    
    from datetime import datetime, timezone, timedelta
    PH_TZ = timezone(timedelta(hours=8))

    TIME_SLOTS = [
        ('08:00','10:00'),('10:00','12:00'),('12:00','14:00'),
        ('14:00','16:00'),('16:00','18:00'),('18:00','20:00'),
    ]

    conn = _sqlite3.connect('database.db')
    row = conn.execute(
        "SELECT lab, pc_number, time_end FROM sitin_sessions WHERE id=?",
        (session_id,)
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({'success': False, 'message': 'Session not found.'})

    lab = row[0]
    pc_number = row[1]
    current_end = row[2]

    if current_end >= '20:00':
        conn.close()
        return jsonify({'success': False, 'message': 'Cannot extend. Already at maximum time (8:00 PM).'})

    # Calculate new_end FIRST
    new_end = '20:00'
    for i, (s, e) in enumerate(TIME_SLOTS):
        if s <= current_end < e or current_end == e:
            if i + 1 < len(TIME_SLOTS):
                new_end = TIME_SLOTS[i + 1][1]
            break

    # Check next reservation on this PC
    today = datetime.now(PH_TZ).strftime('%Y-%m-%d')
    next_res = conn.execute("""
        SELECT time_in FROM reservations
        WHERE lab=? AND pc_number=? AND date=?
        AND status IN ('pending','approved')
        AND time_in >= ?
        ORDER BY time_in ASC LIMIT 1
    """, (lab, pc_number, today, current_end)).fetchone()

    # Only block if reservation conflicts with the new extended slot
    if next_res and next_res[0] < new_end:
        t = next_res[0]
        try:
            dt = datetime.strptime(t, '%H:%M')
            hr = dt.hour
            hr12 = hr % 12 or 12
            ampm = 'PM' if hr >= 12 else 'AM'
            hr2 = hr + 2
            hr2_12 = hr2 % 12 or 12
            ampm2 = 'PM' if hr2 >= 12 else 'AM'
            slot_label = f'{hr12}:00 {ampm} – {hr2_12}:00 {ampm2}'
        except:
            slot_label = t
        conn.close()
        return jsonify({
            'success': False,
            'message': f'Cannot extend. A student has reserved this PC at {slot_label}.'
        })

    conn.execute("""
        UPDATE sitin_sessions
        SET time_end=?, session_status='extended'
        WHERE id=?
    """, (new_end, session_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'new_end': new_end})

# ══════════════════════════════════════════
# ROUTE — AUTO LOGOUT IF OVERDUE FOR 15 MINUTES
# ══════════════════════════════════════════
@app.route('/admin/sitin/auto-logout-overdue', methods=['POST'])
def admin_auto_logout_overdue():
    if not session.get('admin') and not session.get('student_id'):
        return jsonify({'success': False}), 401

    from datetime import datetime, timezone, timedelta
    PH_TZ = timezone(timedelta(hours=8))
    now = datetime.now(PH_TZ)
    now_str = now.strftime('%H:%M')

    conn = _sqlite3.connect('database.db')
    # Find sessions overdue by 15+ minutes
    overdue_rows = conn.execute("""
        SELECT id, idNumber, lab, pc_number FROM sitin_sessions
        WHERE status = 'active'
        AND time_end IS NOT NULL
        AND time_end <= ?
    """, ((now - timedelta(minutes=15)).strftime('%H:%M'),)).fetchall()

    auto_logged = []
    for row in overdue_rows:
        session_id = row[0]
        id_number  = row[1]

        # End the session
        now_ph = now.strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("""
            UPDATE sitin_sessions
            SET time_out=?, status='done'
            WHERE id=?
        """, (now_ph, session_id))
        conn.execute("""
            UPDATE students SET sitin_count = sitin_count - 1
            WHERE idNumber = ? AND sitin_count > 0
        """, (id_number,))

        # Update reservation if linked
        res = conn.execute("""
            SELECT id FROM reservations
            WHERE session_id=? AND status='sitting_in'
        """, (session_id,)).fetchone()
        if res:
            conn.execute("""
                UPDATE reservations SET status='done', time_out=?
                WHERE id=?
            """, (now_str, res[0]))

        auto_logged.append(session_id)

    conn.commit()
    conn.close()
    return jsonify({'success': True, 'auto_logged': auto_logged})


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