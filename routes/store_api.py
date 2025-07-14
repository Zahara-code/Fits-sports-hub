# routes/store_api.py
from flask import request, jsonify
from flask_restx import Namespace, Resource, fields
from services.store_service import StoreService
from models.product import db, Product, Category, Price, Stock

# Create namespace for store operations
store_api = Namespace('store', description='Store operations')

# Swagger models
category_model = store_api.model('CategoryWithCount', {
    'id': fields.Integer(readonly=True),
    'name': fields.String(readonly=True),
    'description': fields.String(readonly=True),
    'product_count': fields.Integer(readonly=True, description='Number of products in category')
})

product_summary_model = store_api.model('ProductSummary', {
    'id': fields.Integer(readonly=True),
    'name': fields.String(readonly=True),
    'description': fields.String(readonly=True),
    'price': fields.Float(readonly=True),
    'currency': fields.String(readonly=True),
    'stock_quantity': fields.Integer(readonly=True),
    'category': fields.Nested(store_api.model('CategoryBasic', {
        'id': fields.Integer(readonly=True),
        'name': fields.String(readonly=True)
    })),
    'images': fields.List(fields.String, description='List of image URLs')
})

product_detail_model = store_api.model('ProductDetail', {
    'id': fields.Integer(readonly=True),
    'name': fields.String(readonly=True),
    'description': fields.String(readonly=True),
    'price': fields.Float(readonly=True),
    'currency': fields.String(readonly=True),
    'stock_quantity': fields.Integer(readonly=True),
    'in_stock': fields.Boolean(readonly=True),
    'category': fields.Nested(category_model),
    'images': fields.List(fields.Nested(store_api.model('ImageDetail', {
        'id': fields.Integer(readonly=True),
        'filename': fields.String(readonly=True),
        'filepath': fields.String(readonly=True),
        'url': fields.String(readonly=True)
    })))
})

pagination_model = store_api.model('PaginationInfo', {
    'page': fields.Integer(readonly=True),
    'per_page': fields.Integer(readonly=True),
    'total': fields.Integer(readonly=True),
    'pages': fields.Integer(readonly=True),
    'has_prev': fields.Boolean(readonly=True),
    'has_next': fields.Boolean(readonly=True)
})

product_list_response = store_api.model('ProductListResponse', {
    'items': fields.List(fields.Nested(product_summary_model)),
    'pagination': fields.Nested(pagination_model)
})

availability_response = store_api.model('AvailabilityResponse', {
    'available': fields.Boolean(readonly=True),
    'requested_quantity': fields.Integer(readonly=True),
    'available_quantity': fields.Integer(readonly=True)
})

cart_add_request = store_api.model('CartAddRequest', {
    'product_id': fields.Integer(required=True, description='Product ID to add to cart'),
    'quantity': fields.Integer(required=True, description='Quantity to add', min=1)
})

cart_add_response = store_api.model('CartAddResponse', {
    'message': fields.String(readonly=True),
    'product_id': fields.Integer(readonly=True),
    'quantity': fields.Integer(readonly=True)
})

service = StoreService(db.session)

# Query parameters parsers
pagination_parser = store_api.parser()
pagination_parser.add_argument('page', type=int, default=1, help='Page number')
pagination_parser.add_argument('per_page', type=int, default=12, help='Items per page')

search_parser = pagination_parser.copy()
search_parser.add_argument('search', type=str, default='', help='Search query')

@store_api.route('/categories')
class CategoryList(Resource):
    @store_api.marshal_list_with(category_model)
    @store_api.doc('list_categories')
    def get(self):
        """Get all categories with product count"""
        return service.get_all_categories()

@store_api.route('/products')
class ProductList(Resource):
    @store_api.expect(search_parser)
    @store_api.marshal_with(product_list_response)
    @store_api.doc('list_products')
    def get(self):
        """Get products with pagination and search"""
        args = search_parser.parse_args()
        result = service.get_all_products(
            page=args['page'], 
            per_page=args['per_page'], 
            search=args['search']
        )
        
        # Ensure pagination info is complete
        return {
            'items': result.get('items', []),
            'pagination': {
                'page': result.get('current_page', args['page']),
                'per_page': args['per_page'],
                'total': result.get('total', 0),
                'pages': result.get('pages', 0),
                'has_prev': result.get('current_page', 1) > 1,
                'has_next': result.get('current_page', 1) < result.get('pages', 0)
            }
        }

@store_api.route('/category/<int:category_id>/products')
@store_api.param('category_id', 'The category identifier')
class CategoryProducts(Resource):
    @store_api.expect(pagination_parser)
    @store_api.marshal_with(product_list_response)
    @store_api.doc('get_category_products')
    def get(self, category_id):
        """Get products for a specific category"""
        args = pagination_parser.parse_args()
        return service.get_products_by_category(
            category_id, 
            page=args['page'], 
            per_page=args['per_page']
        )

@store_api.route('/product/<int:product_id>')
@store_api.param('product_id', 'The product identifier')
class ProductDetail(Resource):
    @store_api.marshal_with(product_detail_model)
    @store_api.doc('get_product_details')
    def get(self, product_id):
        """Get detailed product information"""
        return service.get_product_details(product_id)

@store_api.route('/featured')
class FeaturedProducts(Resource):
    @store_api.doc('get_featured_products')
    @store_api.param('limit', 'Maximum number of products to return', type=int, default=8)
    @store_api.marshal_list_with(product_summary_model)
    def get(self):
        """Get featured products for homepage"""
        limit = request.args.get('limit', 8, type=int)
        return service.get_featured_products(limit=limit)

@store_api.route('/product/<int:product_id>/availability')
@store_api.param('product_id', 'The product identifier')
class ProductAvailability(Resource):
    @store_api.doc('check_product_availability')
    @store_api.param('quantity', 'Requested quantity', type=int, default=1)
    @store_api.marshal_with(availability_response)
    def get(self, product_id):
        """Check product availability"""
        quantity = request.args.get('quantity', 1, type=int)
        available = service.check_product_availability(product_id, quantity)
        
        # Get actual available quantity
        product = service.get_product_details(product_id)
        available_quantity = product.get('stock_quantity', 0) if product else 0
        
        return {
            'available': available, 
            'requested_quantity': quantity,
            'available_quantity': available_quantity
        }

@store_api.route('/cart/add')
class CartAdd(Resource):
    @store_api.expect(cart_add_request, validate=True)
    @store_api.marshal_with(cart_add_response)
    @store_api.doc('add_to_cart')
    @store_api.response(400, 'Product not available in requested quantity')
    def post(self):
        """Add product to cart"""
        data = request.json
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)
        
        # Check availability first
        if not service.check_product_availability(product_id, quantity):
            store_api.abort(400, 'Product not available in requested quantity')
        
        # TODO: Implement cart service integration
        return {
            'message': 'Product added to cart', 
            'product_id': product_id, 
            'quantity': quantity
        }

# Define models for store API
product_model = store_api.model('StoreProduct', {
    'id': fields.Integer(readonly=True),
    'name': fields.String(required=True),
    'description': fields.String(),
    'category_id': fields.Integer(),
    'price': fields.Float(),
    'stock': fields.Integer()
})

@store_api.route('/products')
class StoreProductList(Resource):
    @store_api.marshal_list_with(product_model)
    def get(self):
        """Get all products for store display"""
        products = Product.query.all()
        result = []
        for product in products:
            item = {
                'id': product.id,
                'name': product.name,
                'description': product.description,
                'category_id': product.category_id,
                'price': float(product.price.amount) if product.price else 0,
                'stock': product.stock.quantity if product.stock else 0
            }
            result.append(item)
        return result

@store_api.route('/categories/options')
class CategoryOptions(Resource):
    def get(self):
        """Get categories for dropdown"""
        categories = Category.query.all()
        options_html = '<option value="">Select Category</option>'
        for cat in categories:
            options_html += f'<option value="{cat.id}">{cat.name}</option>'
        return options_html, 200, {'Content-Type': 'text/html'}

@store_api.route('/categories')
class CategoriesList(Resource):
    def get(self):
        """Get all categories"""
        categories = Category.query.all()
        return jsonify([{
            'id': cat.id,
            'name': cat.name,
            'description': cat.description
        } for cat in categories])

@store_api.route('/stats/products')
class ProductStats(Resource):
    def get(self):
        """Get total number of products"""
        try:
            count = Product.query.count()
            return str(count), 200, {'Content-Type': 'text/plain'}
        except:
            return "0", 200, {'Content-Type': 'text/plain'}

@store_api.route('/stats/categories')
class CategoryStats(Resource):
    def get(self):
        """Get total number of categories"""
        try:
            count = Category.query.count()
            return str(count), 200, {'Content-Type': 'text/plain'}
        except:
            return "0", 200, {'Content-Type': 'text/plain'}

@store_api.route('/stats/low-stock')
class LowStockStats(Resource):
    def get(self):
        """Get number of low stock items (less than 10)"""
        try:
            count = Stock.query.filter(Stock.quantity < 10).count()
            return str(count), 200, {'Content-Type': 'text/plain'}
        except:
            return "0", 200, {'Content-Type': 'text/plain'}
