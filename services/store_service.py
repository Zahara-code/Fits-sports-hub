# services/store_service.py
from sqlalchemy import func
from models.product import db, Category, Product, ProductImage, Stock, Price


class StoreService:
    def __init__(self, db_session):
        self.db = db_session

    def get_all_categories(self):
        """Get all active categories with product count"""
        categories = self.db.query(
            Category,
            func.count(Product.id).label('product_count')
        ).outerjoin(Product).group_by(Category.id).all()
        
        return [{
            'id': cat.id,
            'name': cat.name,
            'description': cat.description,
            'product_count': count
        } for cat, count in categories]

    def get_products_by_category(self, category_id, page=1, per_page=12):
        """Get paginated products for a category"""
        products = Product.query.filter_by(category_id=category_id)\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        items = []
        for product in products.items:
            item = self._format_product_summary(product)
            items.append(item)
        
        return {
            'items': items,
            'total': products.total,
            'pages': products.pages,
            'current_page': page
        }

    def get_all_products(self, page=1, per_page=12, search=None):
        """Get all products with optional search"""
        query = Product.query
        
        if search:
            query = query.filter(
                Product.name.ilike(f'%{search}%') | 
                Product.description.ilike(f'%{search}%')
            )
        
        products = query.paginate(page=page, per_page=per_page, error_out=False)
        
        items = []
        for product in products.items:
            item = self._format_product_summary(product)
            items.append(item)
        
        return {
            'items': items,
            'total': products.total,
            'pages': products.pages,
            'current_page': page
        }

    def get_product_details(self, product_id):
        """Get detailed product information"""
        product = Product.query.get_or_404(product_id)
        
        # Get price
        price = Price.query.filter_by(product_id=product_id).first()
        
        # Get stock
        stock = Stock.query.filter_by(product_id=product_id).first()
        
        # Get images
        images = ProductImage.query.filter_by(product_id=product_id).all()
        
        return {
            'id': product.id,
            'name': product.name,
            'description': product.description,
            'category': {
                'id': product.category.id,
                'name': product.category.name
            },
            'price': {
                'amount': float(price.amount) if price else 0,
                'currency': price.currency if price else 'USD'
            },
            'stock': {
                'available': stock.quantity > 0 if stock else False,
                'quantity': stock.quantity if stock else 0
            },
            'images': [{
                'id': img.id,
                'url': f'/static/{img.filepath}',
                'filename': img.filename
            } for img in images]
        }

    def get_featured_products(self, limit=8):
        """Get featured products (latest products with images)"""
        products = Product.query.join(ProductImage)\
            .order_by(Product.id.desc())\
            .limit(limit).all()
        
        items = []
        for product in products:
            item = self._format_product_summary(product)
            items.append(item)
        
        return items

    def _format_product_summary(self, product):
        """Format product for listing views"""
        price = Price.query.filter_by(product_id=product.id).first()
        stock = Stock.query.filter_by(product_id=product.id).first()
        first_image = ProductImage.query.filter_by(product_id=product.id).first()
        
        return {
            'id': product.id,
            'name': product.name,
            'description': product.description[:100] + '...' if product.description and len(product.description) > 100 else product.description,
            'category_name': product.category.name,
            'price': float(price.amount) if price else 0,
            'currency': price.currency if price else 'USD',
            'in_stock': stock.quantity > 0 if stock else False,
            'image_url': f'/static/{first_image.filepath}' if first_image else '/static/img/placeholder.jpg'
        }

    def check_product_availability(self, product_id, quantity=1):
        """Check if product is available in requested quantity"""
        stock = Stock.query.filter_by(product_id=product_id).first()
        if not stock:
            return False
        return stock.quantity >= quantity

    def get_product_by_slug(self, slug):
        """Get product by URL-friendly slug (future enhancement)"""
        # This could be implemented later for SEO-friendly URLs
        pass
