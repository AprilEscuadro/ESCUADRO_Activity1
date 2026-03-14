import os
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, redirect, render_template, render_template_string, session, jsonify
from dbhelper import (
    init_db,
    get_student_by_id, register_student, login_student,
    login_admin, get_all_students,
    get_all_sessions, get_student_sessions, add_sitin, end_sitin,
    get_all_announcements, add_announcement,
    get_purpose_counts,
)

import sqlite3 as _sqlite3

CCS_COURSES = {'BSIT', 'BSCS'}

def get_sitin_count(course):
    """Return correct sit-in count based on course: 30 for CCS, 15 for others."""
    return 30 if course in CCS_COURSES else 15

def reset_all_sessions():
    """Reset each student's sit-in count based on their course (CCS=30, others=15)."""
    conn = _sqlite3.connect('database.db')
    students = conn.execute("SELECT idNumber, course FROM students").fetchall()
    for s in students:
        count = get_sitin_count(s[1] or '')
        conn.execute("UPDATE students SET sitin_count = ? WHERE idNumber = ?", (count, s[0]))
    conn.commit()
    conn.close()

app = Flask(__name__)
app.secret_key = 'ccs_sitin_secret_key'

# ══════════════════════════════════════════
# EMAIL CONFIG — no library needed!
# ══════════════════════════════════════════
GMAIL_ADDRESS  = 'aprilescuadro2004@gmail.com'
GMAIL_PASSWORD = 'hhbr mpwx dhxz qyhq'

def send_email(to_address, subject, body):
    """Send an email using Python's built-in smtplib — no Flask-Mail needed."""
    msg = MIMEMultipart()
    msg['From']    = GMAIL_ADDRESS
    msg['To']      = to_address
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(GMAIL_ADDRESS, GMAIL_PASSWORD)
        server.send_message(msg)

# In-memory token store { token: id_number }
reset_tokens = {}


# ══════════════════════════════════════════
# PAGE TEMPLATES
# ══════════════════════════════════════════
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

RESET_PASSWORD_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Reset Password - CCS Sit-in System</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <nav class="navbar">
        <div class="nav-content">
            <div class="logo-section">
                <img src="{{ url_for('static', filename='images/ucmainccslogo.jpg') }}"
                     alt="CCS Logo" class="navbar-logo">
                <span class="site-title">College of Computer Studies Sit-in Monitoring System</span>
            </div>
        </div>
    </nav>
    <main class="register-container">
        <div class="register-card">
            <div class="form-content">
                <h1>Reset Password</h1>
                <p class="form-subtitle">Enter your new password below.</p>

                {% if error %}
                <div class="error-message">⚠️ {{ error }}</div>
                {% endif %}

                <form action="/reset-password/{{ token }}" method="post">
                    <div class="form-field">
                        <label>New Password</label>
                        <input type="password" name="newPassword"
                               required minlength="6" placeholder="Minimum 6 characters">
                    </div>
                    <div class="form-field">
                        <label>Confirm New Password</label>
                        <input type="password" name="confirmPassword"
                               required minlength="6" placeholder="Repeat new password">
                    </div>
                    <button type="submit" class="btn btn-primary btn-full">
                        Reset Password
                    </button>
                </form>
            </div>
        </div>
    </main>
    <footer>
        <p>&copy; 2026 College of Computer Studies - University of Cebu</p>
    </footer>
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
        return redirect('/dashboard')
    if session.get('admin'):
        return redirect('/admin/dashboard')
    return render_template('login.html')

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
    session_id = add_sitin(id_number, purpose, lab)  # ✅ capture returned ID
    return jsonify({'success': True, 'message': 'Sit-in successfully.', 'sessionId': session_id})  # ✅ send it back

# ══════════════════════════════════════════
# ROUTE — REGISTER
# ══════════════════════════════════════════
@app.route('/register', methods=['POST'])
def register():
    id_number    = request.form.get('idNumber', '').strip()
    first_name   = request.form.get('firstName', '').strip()
    last_name    = request.form.get('lastName', '').strip()
    middle_name  = request.form.get('middleName', '').strip()
    course_level = request.form.get('courseLevel', '').strip()
    password     = request.form.get('password', '').strip()
    confirm_pass = request.form.get('confirmPassword', '').strip()
    email        = request.form.get('email', '').strip()
    course       = request.form.get('course', '').strip()
    address      = request.form.get('address', '').strip()

    if not id_number:
        return render_template_string(ERROR_PAGE,
            message="ID Number is required!", back_page="/register.html")
    if len(password) < 6:
        return render_template_string(ERROR_PAGE,
            message="Password must be at least 6 characters!", back_page="/register.html")
    if password != confirm_pass:
        return render_template_string(ERROR_PAGE,
            message="Passwords do not match!", back_page="/register.html")
    if '@' not in email:
        return render_template_string(ERROR_PAGE,
            message="Invalid email format!", back_page="/register.html")
    if course_level not in ['1', '2', '3', '4']:
        return render_template_string(ERROR_PAGE,
            message="Please select a valid course level!", back_page="/register.html")
    if not course:
        return render_template_string(ERROR_PAGE,
            message="Please select a course!", back_page="/register.html")
    if get_student_by_id(id_number):
        return render_template_string(ERROR_PAGE,
            message="ID Number already registered!", back_page="/register.html")

    sitin_count = get_sitin_count(course)

    register_student(id_number, first_name, last_name, middle_name,
                     course_level, password, email, course, address, sitin_count)

    return render_template_string(SUCCESS_PAGE,
        title="Registration Successful!",
        message=f"Welcome, {first_name}! You have {sitin_count} sit-in sessions this semester.",
        next_page="/login")


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
        return redirect('/admin/dashboard')

    student = login_student(id_number, password)
    if student:
        session['student_id']   = student['idNumber']
        session['student_name'] = f"{student['firstName']} {student['lastName']}"
        return redirect('/dashboard')

    return render_template('login.html', error="Invalid ID Number or Password!")


# ══════════════════════════════════════════
# ROUTE — FORGOT PASSWORD (sends real Gmail)
# ══════════════════════════════════════════
@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    id_number = request.form.get('forgotId', '').strip()
    email     = request.form.get('forgotEmail', '').strip()

    student = get_student_by_id(id_number)
    if student:
        student = dict(student)

    if student and student.get('email', '').lower() == email.lower():
        # Generate a secure one-time token
        token = secrets.token_urlsafe(32)
        reset_tokens[token] = id_number

        reset_link = f"http://localhost:5000/reset-password/{token}"

        # Build the email body
        body = f"""Hello {student['firstName']},

We received a request to reset the password for your CCS Sit-in System account.

Click the link below to set a new password:

{reset_link}

This link is valid for one use only. If you did not request a password reset, you can safely ignore this email.

— CCS Sit-in Monitoring System
   College of Computer Studies, University of Cebu
"""

        try:
            send_email(
                to_address = email,
                subject    = 'CCS Sit-in System — Password Reset Request',
                body       = body
            )
            return jsonify({
                'success': True,
                'message': '✓ A password reset link has been sent to your email.'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Could not send email. Error: {str(e)}'
            })

    return jsonify({
        'success': False,
        'message': '✗ No account found with that ID and email combination.'
    })


# ══════════════════════════════════════════
# ROUTE — RESET PASSWORD PAGE
# ══════════════════════════════════════════
@app.route('/reset-password/<token>', methods=['GET'])
def reset_password_page(token):
    id_number = reset_tokens.get(token)
    if not id_number:
        return render_template_string(ERROR_PAGE,
            message="This reset link is invalid or has already been used.",
            back_page="/login")
    return render_template_string(RESET_PASSWORD_PAGE, token=token, error=None)


@app.route('/reset-password/<token>', methods=['POST'])
def reset_password_submit(token):
    id_number = reset_tokens.get(token)
    if not id_number:
        return render_template_string(ERROR_PAGE,
            message="This reset link is invalid or has already been used.",
            back_page="/login")

    new_password = request.form.get('newPassword', '').strip()
    confirm      = request.form.get('confirmPassword', '').strip()

    if len(new_password) < 6:
        return render_template_string(RESET_PASSWORD_PAGE,
            token=token, error="Password must be at least 6 characters.")
    if new_password != confirm:
        return render_template_string(RESET_PASSWORD_PAGE,
            token=token, error="Passwords do not match.")

    import hashlib
    hashed = hashlib.sha256(new_password.encode()).hexdigest()

    conn = _sqlite3.connect('database.db')
    conn.execute(
        "UPDATE students SET password = ? WHERE idNumber = ?",
        (hashed, id_number)
    )
    conn.commit()
    conn.close()

    # Invalidate token — one-time use
    del reset_tokens[token]

    return render_template_string(SUCCESS_PAGE,
        title="Password Reset Successful!",
        message="Your password has been updated. You can now log in with your new password.",
        next_page="/login")


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
    return render_template('student_dashboard.html',
        student=student,
        sessions=sessions,
        announcements=announcements
    )


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
        course_level = field('courseLevel', current.get('courseLevel') or '')
        new_password = request.form.get('newPassword', '').strip()

        submitted_middle = request.form.get('middleName', '').strip()
        middle_name = submitted_middle if submitted_middle else None

        if '@' not in email:
            return jsonify({'success': False, 'message': 'Invalid email format.'})
        if new_password and len(new_password) < 6:
            return jsonify({'success': False, 'message': 'Password must be at least 6 characters.'})

        # Recalculate sit-in count based on course
        new_sitin_count = get_sitin_count(course)

        # ── Photo upload ──────────────────────────────────────────────────
        photo_url  = current.get('photo_url') or None
        photo_file = request.files.get('photo')
        if photo_file and photo_file.filename:
            ext = os.path.splitext(photo_file.filename)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                return jsonify({'success': False,
                                'message': 'Invalid image type. Use JPG, PNG, GIF, or WEBP.'})
            upload_folder = os.path.join(app.root_path, 'static', 'uploads', 'profiles')
            os.makedirs(upload_folder, exist_ok=True)
            filename  = f"profile_{id_number}{ext}"
            save_path = os.path.join(upload_folder, filename)
            photo_file.save(save_path)
            photo_url = f"/static/uploads/profiles/{filename}"

        # ── Write to SQLite3 ──────────────────────────────────────────────
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
                    email=?, address=?, course=?, courseLevel=?,
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
                    email=?, address=?, course=?, courseLevel=?,
                    sitin_count=?,
                    photo_url=COALESCE(?, photo_url)
                WHERE idNumber=?
            ''', (first_name, last_name, middle_name,
                  email, address, course, course_level,
                  new_sitin_count, photo_url, id_number))

        conn.commit()
        conn.close()

        session['student_name'] = f"{first_name} {last_name}"

        if middle_name:
            full_name = f"{first_name} {middle_name} {last_name}"
        else:
            full_name = f"{first_name} {last_name}"

        return jsonify({
            'success':  True,
            'fullName': full_name,
            'photoUrl': photo_url
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

    return render_template('admin_dashboard.html',
        students=students,
        sessions=sessions,
        announcements=announcements,
        purpose_counts=purpose_counts
    )


# ══════════════════════════════════════════
# ROUTE — ADMIN ADD SIT-IN
# ══════════════════════════════════════════
@app.route('/admin/sitin/add', methods=['POST'])
def admin_add_sitin():
    if not session.get('admin'):
        return redirect('/login')

    id_number = request.form.get('idNumber', '').strip()
    purpose   = request.form.get('purpose', '').strip()
    lab       = request.form.get('lab', '').strip()

    student = get_student_by_id(id_number)
    if not student:
        return render_template_string(ERROR_PAGE,
            message=f"Student ID '{id_number}' not found!",
            back_page="/admin/dashboard")

    if student['sitin_count'] <= 0:
        return render_template_string(ERROR_PAGE,
            message=f"Student {id_number} has no remaining sit-in sessions!",
            back_page="/admin/dashboard")

    add_sitin(id_number, purpose, lab)
    return redirect('/admin/dashboard')


# ══════════════════════════════════════════
# ROUTE — ADMIN END SIT-IN
# ══════════════════════════════════════════
@app.route('/admin/sitin/end/<int:session_id>', methods=['POST'])
def admin_end_sitin(session_id):
    if not session.get('admin'):
        return redirect('/login')
    end_sitin(session_id)
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
            message="Title and content are required!",
            back_page="/admin/dashboard")

    add_announcement(title, content, session['admin_name'])
    return redirect('/admin/dashboard')


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
        return redirect('/login')

    id_number    = request.form.get('idNumber', '').strip()
    first_name   = request.form.get('firstName', '').strip()
    last_name    = request.form.get('lastName', '').strip()
    middle_name  = request.form.get('middleName', '').strip() or None
    email        = request.form.get('email', '').strip()
    course       = request.form.get('course', '').strip()
    course_level = request.form.get('courseLevel', '').strip()
    address      = request.form.get('address', '').strip() or None
    sitin_count  = request.form.get('sitin_count', '').strip()

    # If admin manually set a count use it, otherwise recalculate from course
    if sitin_count:
        sitin_count = int(sitin_count)
    else:
        sitin_count = get_sitin_count(course)

    conn = _sqlite3.connect('database.db')
    conn.execute(
        '''UPDATE students
           SET firstName=?, lastName=?, middleName=?,
               email=?, course=?, courseLevel=?, address=?, sitin_count=?
           WHERE idNumber=?''',
        (first_name, last_name, middle_name, email,
         course, course_level, address, sitin_count, id_number)
    )
    conn.commit()
    conn.close()
    return redirect('/admin/dashboard')


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


# ══════════════════════════════════════════
# ROUTE — ADMIN LOGOUT
# ══════════════════════════════════════════
@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect('/')


# ══════════════════════════════════════════
# RUN
# ══════════════════════════════════════════
if __name__ == '__main__':
    init_db()
    print("=================================")
    print("CCS Sit-in System Server Running!")
    print("Open: http://localhost:5000")
    print("=================================")
    app.run(debug=True)