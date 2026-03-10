from flask import Flask, request, redirect, render_template, render_template_string, session
from dbhelper import (
    init_db,
    get_student_by_id, register_student, login_student,
    login_admin, get_all_students,
    get_all_sessions, get_student_sessions, add_sitin, end_sitin,
    get_all_announcements, add_announcement,
    update_sitin_on_login   # ✅ ADDED
)

app = Flask(__name__)
app.secret_key = 'ccs_sitin_secret_key'

CCS_COURSES = ['BSIT', 'BSCS']


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
        <h2 style="color:#1e7e34; margin-bottom:1rem;">✓ {{ title }}</h2>
        <p style="color:#555; margin-bottom:2rem;">{{ message }}</p>
        <a href="{{ next_page }}" style="background:#0F3E7D; color:white;
           padding:0.8rem 2rem; border-radius:5px; text-decoration:none;
           font-weight:bold;">Continue →</a>
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
        <h2 style="color:#c0392b; margin-bottom:1rem;">✗ Error</h2>
        <p style="color:#555; margin-bottom:2rem;">{{ message }}</p>
        <a href="{{ back_page }}" style="background:#0F3E7D; color:white;
           padding:0.8rem 2rem; border-radius:5px; text-decoration:none;
           font-weight:bold;">← Go Back</a>
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
        return redirect('/dashboard')
    if session.get('admin'):
        return redirect('/admin/dashboard')
    return render_template('login.html')


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
        return render_template_string(ERROR_PAGE, message="ID Number is required!", back_page="/register.html")
    if len(password) < 6:
        return render_template_string(ERROR_PAGE, message="Password must be at least 6 characters!", back_page="/register.html")
    if password != confirm_pass:
        return render_template_string(ERROR_PAGE, message="Passwords do not match!", back_page="/register.html")
    if '@' not in email:
        return render_template_string(ERROR_PAGE, message="Invalid email format!", back_page="/register.html")
    if course_level not in ['1', '2', '3', '4']:
        return render_template_string(ERROR_PAGE, message="Please select a valid course level!", back_page="/register.html")
    if not course:
        return render_template_string(ERROR_PAGE, message="Please select a course!", back_page="/register.html")
    if get_student_by_id(id_number):
        return render_template_string(ERROR_PAGE, message="ID Number already registered!", back_page="/register.html")

    sitin_count = 30 if course in CCS_COURSES else 15
    register_student(id_number, first_name, last_name, middle_name,
                     course_level, password, email, course, address, sitin_count)

    return render_template_string(SUCCESS_PAGE,
        title="Registration Successful!",
        message=f"Welcome, {first_name}! You have {sitin_count} sit-in sessions this semester.",
        next_page="/login")


# ══════════════════════════════════════════
# ROUTE — LOGIN (handles both admin & student)
# ══════════════════════════════════════════
@app.route('/login', methods=['POST'])
def login():
    id_number = request.form.get('loginId', '').strip()
    password  = request.form.get('loginPassword', '').strip()

    # Check admin first
    admin = login_admin(id_number, password)
    if admin:
        session['admin']      = True
        session['admin_name'] = id_number
        return redirect('/admin/dashboard')

    # Then check student
    student = login_student(id_number, password)
    if student:
        update_sitin_on_login(student['idNumber'])  # ✅ ADDED
        session['student_id']   = student['idNumber']
        session['student_name'] = f"{student['firstName']} {student['lastName']}"
        return redirect('/dashboard')

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

    sessions = get_student_sessions(session['student_id'])
    return render_template('student_dashboard.html',
        student=student,
        sessions=sessions
    )


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

    students      = get_all_students()
    sessions      = get_all_sessions()
    announcements = get_all_announcements()

    return render_template('admin_dashboard.html',
        students=students,
        sessions=sessions,
        announcements=announcements
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