from models.product import db, Product, Category, Stock, Price

class AdminService:
    def __init__(self, db_session):
        self.db = db_session

    def get_dashboard_stats(self):
        return {
            'total_products': Product.query.count(),
            'categories': Category.query.count(),
            'low_stock': Stock.query.filter(Stock.quantity < 5).count(),
            'total_orders': 0  # Placeholder, implement order model if needed
        }

    def get_recent_activity(self):
        # Placeholder: return latest products/categories
        products = Product.query.order_by(Product.id.desc()).limit(5).all()
        return [{'type': 'product', 'name': p.name} for p in products]

    def get_payments_stats(self):
        # Placeholder: implement with real payment/order models
        return {
            'revenue': 0.0,
            'pending': 0,
            'processing': 0,
            'completed': 0
        }
