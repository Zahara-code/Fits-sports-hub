from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from werkzeug.utils import secure_filename
import os
import time
from models.product import db, Category, Product
from services.product_service import ProductService

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('admin/admin_dashboard.html')

@admin_bp.route('/products')
@login_required
def products():
    # Use eager loading to get related data
    products = Product.query.options(
        db.joinedload(Product.category),
        db.joinedload(Product.price),
        db.joinedload(Product.stock),
        db.joinedload(Product.images)
    ).all()
    categories = Category.query.all()
    return render_template('admin/admin_product.html', products=products, categories=categories)

@admin_bp.route('/products/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'GET':
        categories = Category.query.all()
        return render_template('admin/add_product.html', categories=categories)
    
    if request.method == 'POST':
        service = ProductService(db.session)
        
        # Create product
        product = service.create_product(
            name=request.form['name'],
            category_id=request.form['category_id'],
            description=request.form.get('description')
        )
        
        # Set price
        if request.form.get('price'):
            service.set_price(product.id, float(request.form['price']))
        
        # Set stock
        if request.form.get('stock'):
            service.set_stock(product.id, int(request.form['stock']))
        
        # Handle image uploads
        if 'images' in request.files:
            from flask import current_app
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'products')
            os.makedirs(upload_folder, exist_ok=True)
            
            for file in request.files.getlist('images'):
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    # Use time.time() to get current timestamp
                    timestamp = int(time.time())
                    unique_filename = f"{product.id}_{timestamp}_{filename}"
                    filepath = os.path.join(upload_folder, unique_filename)
                    file.save(filepath)
                    
                    # Save to database
                    relative_path = f"uploads/products/{unique_filename}"
                    service.add_product_image(product.id, filename, relative_path)
        
        flash('Product created successfully!', 'success')
        return redirect(url_for('admin.products'))

@admin_bp.route('/payments')
@login_required
def payments():
    return render_template('admin/admin_payments.html')
