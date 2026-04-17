# app.py - Main Flask Application
import os
import flask_login
from datetime import datetime, date
from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, User, Company, Student, PlacementDrive, Application

# App configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'resumes')
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

app = Flask(__name__)
app.config['SECRET_KEY'] = 'placement-portal-secret-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "placement.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Role decorators
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated

def company_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'company':
            abort(403)
        return f(*args, **kwargs)
    return decorated

def student_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'student':
            abort(403)
        return f(*args, **kwargs)
    return decorated

# ---------------------- AUTH ROUTES ----------------------
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for(f'{current_user.role}_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password, password):
            flash('Invalid email or password.', 'danger')
            return render_template('login.html')
        if not user.is_active:
            flash('Your account has been blacklisted. Contact admin.', 'danger')
            return render_template('login.html')
        # Company approval check
        if user.role == 'company' and (not user.company or not user.company.is_approved):
            flash('Your company account is awaiting admin approval.', 'warning')
            return render_template('login.html')
        login_user(user)
        flash(f'Welcome back, {user.email}!', 'success')
        next_page = request.args.get('next')
        return redirect(next_page or url_for(f'{user.role}_dashboard'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/register/student', methods=['GET', 'POST'])
def register_student():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        roll_number = request.form.get('roll_number', '').strip()
        branch = request.form.get('branch', '').strip()
        year = request.form.get('year_of_passing', '')
        cgpa = request.form.get('cgpa', '')
        phone = request.form.get('phone', '').strip()
        skills = request.form.get('skills', '').strip()

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('register_student.html')
        if Student.query.filter_by(roll_number=roll_number).first():
            flash('Roll number already registered.', 'danger')
            return render_template('register_student.html')

        # Validate CGPA
        if cgpa:
            try:
                cgpa_val = float(cgpa)
                if not (0 <= cgpa_val <= 10):
                    raise ValueError
            except ValueError:
                flash('CGPA must be between 0 and 10.', 'danger')
                return render_template('register_student.html')

        user = User(email=email, password=generate_password_hash(password), role='student')
        db.session.add(user)
        db.session.flush()
        student = Student(
            user_id=user.id, full_name=full_name, roll_number=roll_number, branch=branch,
            year_of_passing=int(year) if year else None,
            cgpa=float(cgpa) if cgpa else None, phone=phone, skills=skills
        )
        db.session.add(student)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register_student.html')

@app.route('/register/company', methods=['GET', 'POST'])
def register_company():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        name = request.form.get('name', '').strip()
        industry = request.form.get('industry', '').strip()
        website = request.form.get('website', '').strip()
        description = request.form.get('description', '').strip()
        contact_person = request.form.get('contact_person', '').strip()
        contact_phone = request.form.get('contact_phone', '').strip()

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('register_company.html')
        if Company.query.filter_by(name=name).first():
            flash('Company name already exists.', 'danger')
            return render_template('register_company.html')

        user = User(email=email, password=generate_password_hash(password), role='company')
        db.session.add(user)
        db.session.flush()
        company = Company(
            user_id=user.id, name=name, industry=industry, website=website,
            description=description, contact_person=contact_person, contact_phone=contact_phone
        )
        db.session.add(company)
        db.session.commit()
        flash('Company registered! Awaiting admin approval.', 'success')
        return redirect(url_for('login'))
    return render_template('register_company.html')

# ---------------------- ADMIN ROUTES ----------------------
@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    search_student = request.args.get('search_student', '').strip()
    search_company = request.args.get('search_company', '').strip()

    total_students = Student.query.count()
    total_companies = Company.query.count()
    total_drives = PlacementDrive.query.count()
    total_applications = Application.query.count()
    pending_companies = Company.query.filter_by(is_approved=False).count()
    pending_drives = PlacementDrive.query.filter_by(is_approved=False).count()

    students_q = Student.query.join(User)
    if search_student:
        students_q = students_q.filter(
            (Student.full_name.ilike(f'%{search_student}%')) |
            (Student.roll_number.ilike(f'%{search_student}%')) |
            (User.email.ilike(f'%{search_student}%'))
        )
    students = students_q.all()

    companies_q = Company.query.join(User)
    if search_company:
        companies_q = companies_q.filter(
            (Company.name.ilike(f'%{search_company}%')) |
            (User.email.ilike(f'%{search_company}%'))
        )
    companies = companies_q.all()

    pending_drives_list = PlacementDrive.query.filter_by(is_approved=False).all()

    return render_template('admin/dashboard.html',
        total_students=total_students, total_companies=total_companies,
        total_drives=total_drives, total_applications=total_applications,
        pending_companies=pending_companies, pending_drives=pending_drives,
        students=students, companies=companies, pending_drives_list=pending_drives_list,
        search_student=search_student, search_company=search_company)

@app.route('/admin/company/<int:company_id>/approve')
@login_required
@admin_required
def approve_company(company_id):
    company = Company.query.get_or_404(company_id)
    company.is_approved = True
    db.session.commit()
    flash(f'Company "{company.name}" approved.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/company/<int:company_id>/reject')
@login_required
@admin_required
def reject_company(company_id):
    company = Company.query.get_or_404(company_id)
    company.is_approved = False
    db.session.commit()
    flash(f'Company "{company.name}" approval revoked.', 'warning')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/drive/<int:drive_id>/approve')
@login_required
@admin_required
def approve_drive(drive_id):
    drive = PlacementDrive.query.get_or_404(drive_id)
    drive.is_approved = True
    db.session.commit()
    flash(f'Drive "{drive.title}" approved.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/drive/<int:drive_id>/reject')
@login_required
@admin_required
def reject_drive(drive_id):
    drive = PlacementDrive.query.get_or_404(drive_id)
    drive.is_approved = False
    db.session.commit()
    flash(f'Drive "{drive.title}" rejected.', 'warning')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/user/<int:user_id>/blacklist')
@login_required
@admin_required
def blacklist_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        flash('Cannot blacklist admin.', 'danger')
        return redirect(url_for('admin_dashboard'))
    user.is_active = not user.is_active
    status = 'blacklisted' if not user.is_active else 'reinstated'
    db.session.commit()
    flash(f'User {user.email} has been {status}.', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/drives')
@login_required
@admin_required
def admin_drives():
    drives = PlacementDrive.query.order_by(PlacementDrive.created_at.desc()).all()
    return render_template('admin/drives.html', drives=drives)

# ---------------------- COMPANY ROUTES ----------------------
@app.route('/company/dashboard')
@login_required
@company_required
def company_dashboard():
    company = current_user.company
    if not company:
        flash('Company profile not found.', 'danger')
        return redirect(url_for('logout'))
    drives = PlacementDrive.query.filter_by(company_id=company.id).order_by(PlacementDrive.created_at.desc()).all()
    drive_stats = {}
    for d in drives:
        drive_stats[d.id] = {
            'total': Application.query.filter_by(drive_id=d.id).count(),
            'shortlisted': Application.query.filter_by(drive_id=d.id, status='Shortlisted').count(),
            'selected': Application.query.filter_by(drive_id=d.id, status='Selected').count(),
        }
    return render_template('company/dashboard.html', company=company, drives=drives, drive_stats=drive_stats)

@app.route('/company/drive/create', methods=['GET', 'POST'])
@login_required
@company_required
def create_drive():
    company = current_user.company
    if not company.is_approved:
        flash('Your company is not approved yet.', 'warning')
        return redirect(url_for('company_dashboard'))
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        job_role = request.form.get('job_role', '').strip()
        package = request.form.get('package', '').strip()
        location = request.form.get('location', '').strip()
        description = request.form.get('description', '').strip()
        requirements = request.form.get('requirements', '').strip()
        min_cgpa = request.form.get('min_cgpa', '0')
        eligible_branch = request.form.get('eligible_branch', '').strip()
        drive_date = request.form.get('drive_date')
        last_date_apply = request.form.get('last_date_apply')
        drive = PlacementDrive(
            company_id=company.id, title=title, job_role=job_role, package=package,
            location=location, description=description, requirements=requirements,
            min_cgpa=float(min_cgpa) if min_cgpa else 0.0, eligible_branch=eligible_branch,
            drive_date=datetime.strptime(drive_date, '%Y-%m-%d').date() if drive_date else None,
            last_date_apply=datetime.strptime(last_date_apply, '%Y-%m-%d').date() if last_date_apply else None
        )
        db.session.add(drive)
        db.session.commit()
        flash('Drive created! Awaiting admin approval.', 'success')
        return redirect(url_for('company_dashboard'))
    return render_template('company/create_drive.html', company=company)

@app.route('/company/drive/<int:drive_id>/edit', methods=['GET', 'POST'])
@login_required
@company_required
def edit_drive(drive_id):
    drive = PlacementDrive.query.get_or_404(drive_id)
    if drive.company_id != current_user.company.id:
        abort(403)
    # Prevent edit after deadline
    if drive.last_date_apply and drive.last_date_apply < date.today():
        flash('Cannot edit drive after application deadline.', 'danger')
        return redirect(url_for('company_dashboard'))
    if request.method == 'POST':
        drive.title = request.form.get('title', '').strip()
        drive.job_role = request.form.get('job_role', '').strip()
        drive.package = request.form.get('package', '').strip()
        drive.location = request.form.get('location', '').strip()
        drive.description = request.form.get('description', '').strip()
        drive.requirements = request.form.get('requirements', '').strip()
        drive.min_cgpa = float(request.form.get('min_cgpa', '0') or 0)
        drive.eligible_branch = request.form.get('eligible_branch', '').strip()
        d_date = request.form.get('drive_date')
        l_date = request.form.get('last_date_apply')
        drive.drive_date = datetime.strptime(d_date, '%Y-%m-%d').date() if d_date else None
        drive.last_date_apply = datetime.strptime(l_date, '%Y-%m-%d').date() if l_date else None
        drive.is_approved = False  # needs re-approval
        db.session.commit()
        flash('Drive updated! It needs re-approval.', 'info')
        return redirect(url_for('company_dashboard'))
    return render_template('company/edit_drive.html', drive=drive)

@app.route('/company/drive/<int:drive_id>/delete', methods=['POST'])
@login_required
@company_required
def delete_drive(drive_id):
    drive = PlacementDrive.query.get_or_404(drive_id)
    if drive.company_id != current_user.company.id:
        abort(403)
    if drive.last_date_apply and drive.last_date_apply < date.today():
        flash('Cannot delete drive after deadline.', 'danger')
        return redirect(url_for('company_dashboard'))
    db.session.delete(drive)
    db.session.commit()
    flash('Drive deleted.', 'info')
    return redirect(url_for('company_dashboard'))

@app.route('/company/drive/<int:drive_id>/applicants')
@login_required
@company_required
def view_applicants(drive_id):
    drive = PlacementDrive.query.get_or_404(drive_id)
    if drive.company_id != current_user.company.id:
        abort(403)
    applications = Application.query.filter_by(drive_id=drive_id).join(Student).all()
    return render_template('company/applicants.html', drive=drive, applications=applications)

@app.route('/company/application/<int:app_id>/status', methods=['POST'])
@login_required
@company_required
def update_application_status(app_id):
    application = Application.query.get_or_404(app_id)
    if application.drive.company_id != current_user.company.id:
        abort(403)
    new_status = request.form.get('status')
    if new_status in ('Applied', 'Shortlisted', 'Selected', 'Rejected'):
        application.status = new_status
        application.updated_at = datetime.utcnow()
        db.session.commit()
        flash(f'Status updated to "{new_status}".', 'success')
    else:
        flash('Invalid status.', 'danger')
    return redirect(url_for('view_applicants', drive_id=application.drive_id))

# ---------------------- STUDENT ROUTES ----------------------
@app.route('/student/dashboard')
@login_required
@student_required
def student_dashboard():
    student = current_user.student
    if not student:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('logout'))
    today = date.today()
    available_drives = PlacementDrive.query.filter_by(is_approved=True)\
        .filter((PlacementDrive.last_date_apply == None) | (PlacementDrive.last_date_apply >= today))\
        .order_by(PlacementDrive.created_at.desc()).all()
    applied_drive_ids = {a.drive_id for a in student.applications}
    return render_template('student/dashboard.html', student=student, drives=available_drives, applied_drive_ids=applied_drive_ids)

@app.route('/student/drive/<int:drive_id>/apply', methods=['POST'])
@login_required
@student_required
def apply_drive(drive_id):
    student = current_user.student
    drive = PlacementDrive.query.get_or_404(drive_id)
    if not drive.is_approved:
        flash('This drive is not available.', 'danger')
        return redirect(url_for('student_dashboard'))
    if Application.query.filter_by(student_id=student.id, drive_id=drive.id).first():
        flash('You have already applied for this drive.', 'warning')
        return redirect(url_for('student_dashboard'))
    if drive.last_date_apply and drive.last_date_apply < date.today():
        flash('Application deadline has passed.', 'danger')
        return redirect(url_for('student_dashboard'))
    # Eligibility: CGPA check
    if drive.min_cgpa and student.cgpa and student.cgpa < drive.min_cgpa:
        flash('You do not meet the minimum CGPA requirement.', 'danger')
        return redirect(url_for('student_dashboard'))
    application = Application(student_id=student.id, drive_id=drive.id)
    db.session.add(application)
    db.session.commit()
    flash(f'Successfully applied for "{drive.title}"!', 'success')
    return redirect(url_for('student_dashboard'))

@app.route('/student/applications')
@login_required
@student_required
def student_applications():
    student = current_user.student
    applications = Application.query.filter_by(student_id=student.id).order_by(Application.applied_at.desc()).all()
    return render_template('student/applications.html', student=student, applications=applications)

@app.route('/student/profile', methods=['GET', 'POST'])
@login_required
@student_required
def student_profile():
    student = current_user.student
    if request.method == 'POST':
        student.full_name = request.form.get('full_name', '').strip()
        student.branch = request.form.get('branch', '').strip()
        student.phone = request.form.get('phone', '').strip()
        student.skills = request.form.get('skills', '').strip()
        cgpa = request.form.get('cgpa', '')
        if cgpa:
            try:
                cgpa_val = float(cgpa)
                if 0 <= cgpa_val <= 10:
                    student.cgpa = cgpa_val
                else:
                    flash('CGPA must be between 0 and 10.', 'danger')
                    return redirect(url_for('student_profile'))
            except ValueError:
                flash('Invalid CGPA.', 'danger')
                return redirect(url_for('student_profile'))
        year = request.form.get('year_of_passing', '')
        if year:
            student.year_of_passing = int(year)
        if 'resume' in request.files:
            file = request.files['resume']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"resume_{student.roll_number}_{int(datetime.utcnow().timestamp())}.{file.filename.rsplit('.',1)[1]}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                student.resume_filename = filename
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('student_profile'))
    return render_template('student/profile.html', student=student)

@app.route('/student/drive/<int:drive_id>')
@login_required
@student_required
def drive_detail(drive_id):
    drive = PlacementDrive.query.get_or_404(drive_id)
    if not drive.is_approved:
        abort(404)
    student = current_user.student
    applied = Application.query.filter_by(student_id=student.id, drive_id=drive.id).first()
    return render_template('student/drive_detail.html', drive=drive, applied=applied)

# ---------------------- ERROR HANDLERS ----------------------
@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403

@app.errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404

# ---------------------- DB INIT & SEED ----------------------
def create_tables_and_seed():
    db.create_all()
    admin_email = 'admin@placement.com'
    if not User.query.filter_by(email=admin_email).first():
        admin = User(email=admin_email, password=generate_password_hash('admin123'), role='admin')
        db.session.add(admin)
        db.session.commit()
        print(f'Admin created: {admin_email} / admin123')
    else:
        print('Admin already exists.')

if __name__ == '__main__':
    with app.app_context():
        create_tables_and_seed()
    app.run(debug=True)