# routes/product_bp.py
from flask import Blueprint, request, jsonify, current_app
from flask_restx import Namespace, Resource, fields, Api
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
import os
from models.product import db, Category, Product, ProductImage, Stock, Price
from routes.admin_api import admin_api
from routes.checkout_api import checkout_api
from services.product_service import ProductService
# Import store API namespace
from routes.store_api import store_api

bp = Blueprint('products', __name__, url_prefix='/products')
api = Namespace('products', description='Product operations')

# Swagger models
def_category = api.model('Category', {
    'id': fields.Integer(readonly=True),
    'name': fields.String(required=True, description='Category name'),
    'description': fields.String(description='Optional description'),
})
def_product = api.model('Product', {
    'id': fields.Integer(readonly=True),
    'name': fields.String(required=True, description='Product name'),
    'description': fields.String(description='Optional description'),
    'category_id': fields.Integer(required=True, description='Category ID'),
})

# Update the image model for file uploads
upload_parser = api.parser()
upload_parser.add_argument('file', location='files', type=FileStorage, required=True, help='Product image file')

def_image_response = api.model('ProductImageResponse', {
    'id': fields.Integer(readonly=True),
    'product_id': fields.Integer(readonly=True),
    'filename': fields.String(readonly=True),
    'filepath': fields.String(readonly=True),
    'uploaded_at': fields.DateTime(readonly=True)
})

def_stock = api.model('Stock', {
    'id': fields.Integer(readonly=True),
    'product_id': fields.Integer(required=True),
    'quantity': fields.Integer(required=True),
})

def_price = api.model('Price', {
    'id': fields.Integer(readonly=True),
    'product_id': fields.Integer(required=True),
    'amount': fields.Fixed(required=True),
    'currency': fields.String(required=True),
})

service = ProductService(db.session)

@api.route('/categories')
class CategoryList(Resource):
    @api.expect(def_category, validate=True)
    @api.marshal_with(def_category, code=201)
    def post(self):
        """Create a new category"""
        data = request.json
        cat = service.create_category(data['name'], data.get('description'))
        return cat, 201

@api.route('')
class ProductList(Resource):
    @api.expect(def_product, validate=True)
    @api.marshal_with(def_product, code=201)
    def post(self):
        """Create a new product"""
        data = request.json
        prod = service.create_product(data['name'], data['category_id'], data.get('description'))
        return prod, 201

@api.route('/<int:product_id>/images')
class ProductImages(Resource):
    @api.expect(upload_parser)
    @api.marshal_with(def_image_response, code=201)
    def post(self, product_id):
        """Upload image for product"""
        args = upload_parser.parse_args()
        uploaded_file = args['file']
        
        if uploaded_file:
            # Secure the filename
            filename = secure_filename(uploaded_file.filename)
            
            # Create unique filename to avoid conflicts
            unique_filename = f"{product_id}_{int(db.func.current_timestamp())}_{filename}"
            
            # Define upload path
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'products')
            os.makedirs(upload_folder, exist_ok=True)
            
            filepath = os.path.join(upload_folder, unique_filename)
            uploaded_file.save(filepath)
            
            # Save to database using relative path
            relative_path = f"uploads/products/{unique_filename}"
            img = service.add_product_image(product_id, filename, relative_path)
            return img, 201
        
        return {'message': 'No file uploaded'}, 400

# Add GET endpoint to retrieve product images
@api.route('/<int:product_id>/images')
class ProductImagesList(Resource):
    @api.marshal_list_with(def_image_response)
    def get(self, product_id):
        """Get all images for a product"""
        product = Product.query.get_or_404(product_id)
        return product.images

@api.route('/<int:product_id>/stock')
class ProductStock(Resource):
    @api.expect(def_stock, validate=True)
    @api.marshal_with(def_stock)
    def put(self, product_id):
        """Set product stock"""
        data = request.json
        stk = service.set_stock(product_id, data['quantity'])
        return stk

@api.route('/<int:product_id>/price')
class ProductPrice(Resource):
    @api.expect(def_price, validate=True)
    @api.marshal_with(def_price)
    def put(self, product_id):
        """Set product price"""
        data = request.json
        pr = service.set_price(product_id, data['amount'], data.get('currency', 'USD'))
        return pr

# Attach Namespace to blueprint
api_bp = Blueprint('api', __name__)
restx_api = Api(api_bp, 
    title='Fit Sports Hub API', 
    version='1.0', 
    description='Admin product management and store operations',
    doc='/docs'  # This sets the Swagger UI path
)
restx_api.add_namespace(api, path='/products')  # Add path prefix for the namespace
restx_api.add_namespace(store_api, path='/store')
restx_api.add_namespace(checkout_api, path='/checkout')
restx_api.add_namespace(admin_api, path='/admin')  # Add store namespace
