from flask import request, session
from flask_restx import Namespace, Resource, fields
from services import payment_service
from services.payment_service import PaymentService
from services.cart_service import CartService
from models.product import db
import uuid

# Create namespace for checkout operations
checkout_api = Namespace('checkout', description='Checkout and payment operations')

# Swagger models
checkout_request = checkout_api.model('CheckoutRequest', {
    'email': fields.String(required=True, description='Customer email'),
    'name': fields.String(required=True, description='Customer name'),
    'phone': fields.String(description='Customer phone number'),
    'shipping_address': fields.String(required=True, description='Shipping address'),
    'payment_provider': fields.String(required=True, enum=['stripe', 'africas_talking', 'paypal']),
    'payment_method_data': fields.Raw(description='Provider-specific payment data')
})

payment_intent_response = checkout_api.model('PaymentIntentResponse', {
    'success': fields.Boolean(),
    'order_id': fields.Integer(),
    'order_number': fields.String(),
    'client_secret': fields.String(description='Stripe client secret'),
    'checkout_token': fields.String(description='Africa\'s Talking checkout token'),
    'amount': fields.Float(),
    'currency': fields.String(),
    'error': fields.String()
})

cart_item_model = checkout_api.model('CartItem', {
    'product_id': fields.Integer(),
    'product_name': fields.String(),
    'quantity': fields.Integer(),
    'unit_price': fields.Float(),
    'total_price': fields.Float(),
    'stock_available': fields.Integer(),
    'image': fields.String()
})

cart_response = checkout_api.model('CartResponse', {
    'items': fields.List(fields.Nested(cart_item_model)),
    'total': fields.Float(),
    'item_count': fields.Integer()
})

add_to_cart_request = checkout_api.model('AddToCartRequest', {
    'product_id': fields.Integer(required=True),
    'quantity': fields.Integer(required=True, min=1)
})

update_cart_request = checkout_api.model('UpdateCartRequest', {
    'quantity': fields.Integer(required=True, min=0)
})

order_status_response = checkout_api.model('OrderStatusResponse', {
    'order_number': fields.String(),
    'status': fields.String(),
    'total_amount': fields.Float(),
    'currency': fields.String(),
    'created_at': fields.DateTime(),
    'items': fields.List(fields.Raw())
})

cart_service = CartService(db.session)

def get_session_id():
    """Get or create session ID for cart"""
    if 'cart_session_id' not in session:
        session['cart_session_id'] = str(uuid.uuid4())
    return session['cart_session_id']

@checkout_api.route('/cart')
class CartOperations(Resource):
    @checkout_api.marshal_with(cart_response)
    @checkout_api.doc('get_cart')
    def get(self):
        """Get current cart contents"""
        session_id = get_session_id()
        return cart_service.get_cart_items(session_id)
    
    @checkout_api.doc('clear_cart')
    def delete(self):
        """Clear cart"""
        session_id = get_session_id()
        return cart_service.clear_cart(session_id)

@checkout_api.route('/cart/add')
class AddToCart(Resource):
    @checkout_api.expect(add_to_cart_request, validate=True)
    @checkout_api.doc('add_to_cart')
    def post(self):
        """Add item to cart"""
        session_id = get_session_id()
        data = request.json
        result = cart_service.add_to_cart(
            session_id,
            data['product_id'],
            data['quantity']
        )
        if not result['success']:
            checkout_api.abort(400, result['error'])
        return {'success': True, 'message': 'Item added to cart'}

@checkout_api.route('/cart/item/<int:product_id>')
@checkout_api.param('product_id', 'Product ID')
class CartItem(Resource):
    @checkout_api.expect(update_cart_request, validate=True)
    @checkout_api.doc('update_cart_item')
    def put(self, product_id):
        """Update cart item quantity"""
        session_id = get_session_id()
        data = request.json
        result = cart_service.update_cart_item(
            session_id,
            product_id,
            data['quantity']
        )
        if not result['success']:
            checkout_api.abort(400, result['error'])
        return {'success': True, 'message': 'Cart updated'}
    
    @checkout_api.doc('remove_from_cart')
    def delete(self, product_id):
        """Remove item from cart"""
        session_id = get_session_id()
        result = cart_service.remove_from_cart(session_id, product_id)
        if not result['success']:
            checkout_api.abort(400, result['error'])
        return {'success': True, 'message': 'Item removed from cart'}

@checkout_api.route('/process')
class ProcessCheckout(Resource):
    @checkout_api.expect(checkout_request, validate=True)
    @checkout_api.marshal_with(payment_intent_response)
    @checkout_api.doc('process_checkout')
    def post(self):
        """Process checkout and create payment intent"""
        session_id = get_session_id()
        data = request.json
        
        # Get cart
        cart = cart_service.get_or_create_cart(session_id)
        if not cart.items:
            checkout_api.abort(400, 'Cart is empty')
        
        # Create order
        payment_service = PaymentService(db.session)
        order, error = payment_service.create_order_from_cart(cart.id, {
            'email': data['email'],
            'name': data['name'],
            'phone': data.get('phone'),
            'shipping_address': data['shipping_address'],
            'currency': data.get('currency', 'USD')
        })
        
        if error:
            checkout_api.abort(400, error)
        
        # Process payment
        result = payment_service.process_payment(
            order.id,
            data['payment_provider'],
            data.get('payment_method_data', {})
        )
        
        if result['success']:
            # Clear session cart ID so a new one is created next time
            session.pop('cart_session_id', None)
            
            return {
                'success': True,
                'order_id': order.id,
                'order_number': order.order_number,
                'amount': float(order.total_amount),
                'currency': order.currency,
                **result
            }
        else:
            return {
                'success': False,
                'error': result.get('error', 'Payment processing failed')
            }

@checkout_api.route('/confirm/<int:order_id>')
@checkout_api.param('order_id', 'Order ID')
class ConfirmPayment(Resource):
    @checkout_api.doc('confirm_payment')
    @checkout_api.param('transaction_id', 'Transaction ID from payment provider')
    def post(self, order_id):
        """Confirm payment completion"""
        transaction_id = request.args.get('transaction_id')
        if not transaction_id:
            checkout_api.abort(400, 'Transaction ID required')
            
        result = payment_service.confirm_payment(order_id, transaction_id)
        return result

@checkout_api.route('/order/<string:order_number>')
@checkout_api.param('order_number', 'Order number')
class OrderStatus(Resource):
    @checkout_api.marshal_with(order_status_response)
    @checkout_api.doc('get_order_status')
    def get(self, order_number):
        """Get order status"""
        from models.payment import Order
        order = Order.query.filter_by(order_number=order_number).first()
        if not order:
            checkout_api.abort(404, 'Order not found')
            
        items = [{
            'product_name': item.product.name,
            'quantity': item.quantity,
            'unit_price': float(item.unit_price),
            'total_price': float(item.total_price)
        } for item in order.items]
        
        return {
            'order_number': order.order_number,
            'status': order.status.value,
            'total_amount': float(order.total_amount),
            'currency': order.currency,
            'created_at': order.created_at,
            'items': items
        }

@checkout_api.route('/webhook/<string:provider>')
@checkout_api.param('provider', 'Payment provider name')
class PaymentWebhook(Resource):
    @checkout_api.doc('payment_webhook', security=None)
    def post(self, provider):
        """Handle payment provider webhooks"""
        data = request.json
        result = payment_service.handle_webhook(provider, data)
        return result
