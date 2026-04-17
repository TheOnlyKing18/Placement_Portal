# models.py - Database models
import flask_login
import flask_sqlalchemy
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, company, student
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    company = db.relationship('Company', back_populates='user', uselist=False)
    student = db.relationship('Student', back_populates='user', uselist=False)

class Company(db.Model):
    __tablename__ = 'companies'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False, unique=True)
    industry = db.Column(db.String(100))
    website = db.Column(db.String(200))
    description = db.Column(db.Text)
    contact_person = db.Column(db.String(100))
    contact_phone = db.Column(db.String(20))
    is_approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='company')
    drives = db.relationship('PlacementDrive', back_populates='company', cascade='all, delete-orphan')

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    roll_number = db.Column(db.String(50), unique=True)
    branch = db.Column(db.String(100))
    year_of_passing = db.Column(db.Integer)
    cgpa = db.Column(db.Float)
    phone = db.Column(db.String(20))
    skills = db.Column(db.Text)
    resume_filename = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='student')
    applications = db.relationship('Application', back_populates='student', cascade='all, delete-orphan')

class PlacementDrive(db.Model):
    __tablename__ = 'placement_drives'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    job_role = db.Column(db.String(100), nullable=False)
    package = db.Column(db.String(50))
    location = db.Column(db.String(100))
    description = db.Column(db.Text)
    requirements = db.Column(db.Text)
    min_cgpa = db.Column(db.Float, default=0.0)
    eligible_branch = db.Column(db.String(200))
    drive_date = db.Column(db.Date)
    last_date_apply = db.Column(db.Date)
    is_approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    company = db.relationship('Company', back_populates='drives')
    applications = db.relationship('Application', back_populates='drive', cascade='all, delete-orphan')

class Application(db.Model):
    __tablename__ = 'applications'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    drive_id = db.Column(db.Integer, db.ForeignKey('placement_drives.id'), nullable=False)
    status = db.Column(db.String(30), default='Applied')  # Applied, Shortlisted, Selected, Rejected
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('student_id', 'drive_id', name='unique_student_drive'),)

    student = db.relationship('Student', back_populates='applications')
    drive = db.relationship('PlacementDrive', back_populates='applications')