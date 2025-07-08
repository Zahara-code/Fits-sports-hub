from flask import Blueprint, render_template

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
def dashboard():
    return render_template('admin/admin_dashboard.html')

@admin_bp.route('/products')
def products():
    return render_template('admin/admin_product.html')

@admin_bp.route('/payments')
def payments():
    return render_template('admin/admin_payments.html')
