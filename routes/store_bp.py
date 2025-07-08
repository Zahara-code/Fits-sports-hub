# routes/store_bp.py
from flask import Blueprint, jsonify, request, render_template
from services.store_service import StoreService
from models.product import db

store_bp = Blueprint('store', __name__, url_prefix='/store')
service = StoreService(db.session)

# API endpoints for AJAX calls
@store_bp.route('/api/categories')
def api_categories():
    """Get all categories with product count"""
    categories = service.get_all_categories()
    return jsonify(categories)

@store_bp.route('/api/products')
def api_products():
    """Get products with pagination and search"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 12, type=int)
    search = request.args.get('search', '')
    
    result = service.get_all_products(page=page, per_page=per_page, search=search)
    return jsonify(result)

@store_bp.route('/api/category/<int:category_id>/products')
def api_category_products(category_id):
    """Get products for a specific category"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 12, type=int)
    
    result = service.get_products_by_category(category_id, page=page, per_page=per_page)
    return jsonify(result)

@store_bp.route('/api/product/<int:product_id>')
def api_product_details(product_id):
    """Get detailed product information"""
    product = service.get_product_details(product_id)
    return jsonify(product)

@store_bp.route('/api/featured')
def api_featured_products():
    """Get featured products for homepage"""
    limit = request.args.get('limit', 8, type=int)
    products = service.get_featured_products(limit=limit)
    return jsonify(products)

@store_bp.route('/api/product/<int:product_id>/availability')
def api_check_availability(product_id):
    """Check product availability"""
    quantity = request.args.get('quantity', 1, type=int)
    available = service.check_product_availability(product_id, quantity)
    return jsonify({'available': available, 'requested_quantity': quantity})

# Template routes for server-side rendering
@store_bp.route('/')
def store_home():
    """Store homepage with featured products"""
    featured = service.get_featured_products()
    categories = service.get_all_categories()
    return render_template('store/home.html', 
                         featured_products=featured, 
                         categories=categories)

@store_bp.route('/products')
def products_page():
    """Products listing page"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    result = service.get_all_products(page=page, search=search)
    return render_template('store/products.html', 
                         products=result['items'],
                         pagination=result,
                         search=search)

@store_bp.route('/category/<int:category_id>')
def category_page(category_id):
    """Category products page"""
    page = request.args.get('page', 1, type=int)
    
    # Get category info
    categories = service.get_all_categories()
    current_category = next((c for c in categories if c['id'] == category_id), None)
    
    if not current_category:
        return "Category not found", 404
    
    result = service.get_products_by_category(category_id, page=page)
    return render_template('store/category.html', 
                         category=current_category,
                         products=result['items'],
                         pagination=result)

@store_bp.route('/product/<int:product_id>')
def product_detail_page(product_id):
    """Product detail page"""
    product = service.get_product_details(product_id)
    
    # Get related products from same category
    related = service.get_products_by_category(
        product['category']['id'], 
        page=1, 
        per_page=4
    )
    
    return render_template('store/product_detail.html', 
                         product=product,
                         related_products=related['items'])

# Cart integration endpoints (to be implemented with cart service)
@store_bp.route('/api/cart/add', methods=['POST'])
def add_to_cart():
    """Add product to cart"""
    data = request.json
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    
    # Check availability first
    if not service.check_product_availability(product_id, quantity):
        return jsonify({'error': 'Product not available in requested quantity'}), 400
    
    # TODO: Implement cart service integration
    return jsonify({'message': 'Product added to cart', 'product_id': product_id, 'quantity': quantity})
