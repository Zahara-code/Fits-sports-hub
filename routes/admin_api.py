from flask_restx import Namespace, Resource, fields
from services.admin_service import AdminService
from models.product import db

admin_api = Namespace('admin', description='Admin dashboard and management')
service = AdminService(db.session)

dashboard_stats = admin_api.model('DashboardStats', {
    'total_products': fields.Integer,
    'categories': fields.Integer,
    'low_stock': fields.Integer,
    'total_orders': fields.Integer,
})

activity_item = admin_api.model('ActivityItem', {
    'type': fields.String,
    'name': fields.String,
})

payments_stats = admin_api.model('PaymentsStats', {
    'revenue': fields.Float,
    'pending': fields.Integer,
    'processing': fields.Integer,
    'completed': fields.Integer,
})

@admin_api.route('/dashboard/stats')
class DashboardStats(Resource):
    @admin_api.marshal_with(dashboard_stats)
    def get(self):
        """Get dashboard statistics"""
        return service.get_dashboard_stats()

@admin_api.route('/dashboard/activity')
class DashboardActivity(Resource):
    @admin_api.marshal_list_with(activity_item)
    def get(self):
        """Get recent admin activity"""
        return service.get_recent_activity()

@admin_api.route('/payments/stats')
class PaymentsStats(Resource):
    @admin_api.marshal_with(payments_stats)
    def get(self):
        """Get payments and orders statistics"""
        return service.get_payments_stats()
