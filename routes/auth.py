from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from models.user import db, User, Admin
from datetime import datetime
import os

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
admin_auth_bp = Blueprint('admin_auth', __name__, url_prefix='/admin/auth')

# User Authentication Routes
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            flash('Invalid email or password', 'error')
            return redirect(url_for('auth.login'))
        
        if not user.is_active:
            flash('Your account has been deactivated', 'error')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=remember)
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('index'))
    
    return render_template('login.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        
        # Validation
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('auth.signup'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return redirect(url_for('auth.signup'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('auth.signup'))
        
        # Create new user
        user = User(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('signup.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Admin Authentication Routes
@admin_auth_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        admin = Admin.query.filter_by(username=username).first()
        
        if not admin or not admin.check_password(password):
            return render_template('admin/adminlogin.html', error='Invalid credentials')
        
        if not admin.is_active:
            return render_template('admin/adminlogin.html', error='Account deactivated')
        
        # Update last login
        admin.last_login = datetime.utcnow()
        db.session.commit()
        
        login_user(admin, remember=remember)
        return redirect(url_for('admin.dashboard'))
    
    return render_template('admin/adminlogin.html')

@admin_auth_bp.route('/signup', methods=['GET', 'POST'])
def admin_signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')
        access_code = request.form.get('access_code')
        
        # Check access code
        ADMIN_ACCESS_CODE = os.environ.get('ADMIN_ACCESS_CODE', 'FITSPORTS2024')
        if access_code != ADMIN_ACCESS_CODE:
            flash('Invalid access code', 'error')
            return redirect(url_for('admin_auth.admin_signup'))
        
        # Validation
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('admin_auth.admin_signup'))
        
        if Admin.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return redirect(url_for('admin_auth.admin_signup'))
        
        if Admin.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('admin_auth.admin_signup'))
        
        # Create new admin
        admin = Admin(
            username=username,
            email=email,
            full_name=full_name
        )
        admin.set_password(password)
        
        db.session.add(admin)
        db.session.commit()
        
        flash('Admin account created successfully!', 'success')
        return redirect(url_for('admin_auth.admin_login'))
    
    return render_template('admin/adminsignup.html')

@admin_auth_bp.route('/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('admin_auth.admin_login'))
