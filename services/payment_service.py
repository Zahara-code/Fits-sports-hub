import stripe
import africastalking
import uuid
from decimal import Decimal
from abc import ABC, abstractmethod
from flask import current_app
from models.payment import Order, OrderItem, Payment, PaymentStatus, PaymentProvider, Cart, CartItem
from models.product import Product, Price, Stock
from services.product_service import ProductService

class PaymentProviderInterface(ABC):
    @abstractmethod
    def create_payment_intent(self, amount, currency, order_id, metadata=None):
        pass
    
    @abstractmethod
    def confirm_payment(self, payment_intent_id):
        pass
    
    @abstractmethod
    def refund_payment(self, payment_id, amount=None):
        pass

class StripeProvider(PaymentProviderInterface):
    def __init__(self, api_key):
        stripe.api_key = api_key
        
    def create_payment_intent(self, amount, currency, order_id, metadata=None):
        try:
            # Convert amount to cents for Stripe
            amount_cents = int(amount * 100)
            
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency.lower(),
                metadata={'order_id': order_id, **(metadata or {})}
            )
            return {
                'success': True,
                'payment_intent_id': intent.id,
                'client_secret': intent.client_secret,
                'amount': amount,
                'currency': currency
            }
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def confirm_payment(self, payment_intent_id):
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return {
                'success': intent.status == 'succeeded',
                'status': intent.status,
                'payment_id': intent.id
            }
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def refund_payment(self, payment_id, amount=None):
        try:
            refund_params = {'payment_intent': payment_id}
            if amount:
                refund_params['amount'] = int(amount * 100)
                
            refund = stripe.Refund.create(**refund_params)
            return {
                'success': True,
                'refund_id': refund.id,
                'status': refund.status
            }
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            }

class AfricasTalkingProvider(PaymentProviderInterface):
    def __init__(self, username, api_key):
        africastalking.initialize(username, api_key)
        self.payment = africastalking.Payment
        
    def create_payment_intent(self, amount, currency, order_id, metadata=None):
        # Africa's Talking uses a different flow - mobile checkout
        phone_number = metadata.get('phone_number') if metadata else None
        if not phone_number:
            return {
                'success': False,
                'error': 'Phone number required for mobile money payment'
            }
            
        try:
            response = self.payment.mobile_checkout(
                product_name=f"Order {order_id}",
                phone_number=phone_number,
                currency_code=currency,
                amount=float(amount),
                metadata={'order_id': str(order_id)}
            )
            
            return {
                'success': response['status'] == 'PendingConfirmation',
                'transaction_id': response.get('transactionId'),
                'checkout_token': response.get('checkoutToken'),
                'description': response.get('description')
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def confirm_payment(self, transaction_id):
        # Africa's Talking uses webhooks for confirmation
        # This would be called from webhook handler
        return {
            'success': True,
            'status': 'pending_webhook',
            'transaction_id': transaction_id
        }
    
    def refund_payment(self, payment_id, amount=None):
        # Implement refund logic for Africa's Talking
        return {
            'success': False,
            'error': 'Refunds not yet implemented for mobile money'
        }

class PaymentService:
    def __init__(self, db_session):
        self.db = db_session
        self._providers = {}
        # Don't initialize providers here
    
    def _initialize_providers(self):
        """Lazy initialization of payment providers"""
        if not self._providers:  # Only initialize if not already done
            from flask import current_app
            stripe_key = current_app.config.get('STRIPE_SECRET_KEY')
            if stripe_key:
                self._providers['stripe'] = StripeProvider(stripe_key)
            
            # Add other providers as needed
    
    def create_order_from_cart(self, cart_id, user_data):
        """Create an order from cart items"""
        cart = Cart.query.get(cart_id)
        if not cart or not cart.items:
            return None, "Cart is empty"
            
        # Calculate total
        total_amount = Decimal('0')
        order_items = []
        
        for cart_item in cart.items:
            product = cart_item.product
            if not product.price:
                return None, f"Product {product.name} has no price"
                
            # Check stock availability
            if not product.stock or product.stock.quantity < cart_item.quantity:
                return None, f"Product {product.name} is out of stock"
                
            unit_price = product.price.amount
            item_total = unit_price * cart_item.quantity
            total_amount += item_total
            
            order_items.append({
                'product_id': product.id,
                'quantity': cart_item.quantity,
                'unit_price': unit_price,
                'total_price': item_total
            })
        
        # Create order
        order = Order(
            order_number=self._generate_order_number(),
            user_email=user_data.get('email'),
            user_name=user_data.get('name'),
            user_phone=user_data.get('phone'),
            shipping_address=user_data.get('shipping_address'),
            total_amount=total_amount,
            currency=user_data.get('currency', 'USD')
        )
        
        self.db.add(order)
        self.db.flush()  # Get order ID
        
        # Create order items
        for item_data in order_items:
            order_item = OrderItem(
                order_id=order.id,
                **item_data
            )
            self.db.add(order_item)
            
            # Update stock
            stock = Stock.query.filter_by(product_id=item_data['product_id']).first()
            stock.quantity -= item_data['quantity']
        
        # Clear cart
        for item in cart.items:
            self.db.delete(item)
            
        self.db.commit()
        return order, None
    
    def process_payment(self, order_id, provider, payment_method_data):
        """Process payment for an order"""
        self._initialize_providers()  # Initialize when needed
        
        order = Order.query.get(order_id)
        if not order:
            return {'success': False, 'error': 'Order not found'}
            
        provider_enum = PaymentProvider(provider)
        if provider_enum not in self._providers:
            return {'success': False, 'error': f'Payment provider {provider} not available'}
            
        provider_instance = self._providers[provider_enum]
        
        # Create payment record
        payment = Payment(
            order_id=order_id,
            provider=provider_enum,
            amount=order.total_amount,
            currency=order.currency
        )
        self.db.add(payment)
        self.db.flush()
        
        # Process with provider
        metadata = {
            'order_number': order.order_number,
            'user_email': order.user_email,
            **payment_method_data
        }
        
        result = provider_instance.create_payment_intent(
            order.total_amount,
            order.currency,
            order_id,
            metadata
        )
        
        if result['success']:
            payment.transaction_id = result.get('payment_intent_id') or result.get('transaction_id')
            payment.provider_response = result
            order.status = PaymentStatus.PROCESSING
        else:
            payment.status = PaymentStatus.FAILED
            payment.provider_response = result
            
        self.db.commit()
        return result
    
    def confirm_payment(self, order_id, transaction_id):
        """Confirm payment completion"""
        payment = Payment.query.filter_by(
            order_id=order_id,
            transaction_id=transaction_id
        ).first()
        
        if not payment:
            return {'success': False, 'error': 'Payment not found'}
            
        provider_instance = self._providers[payment.provider]
        result = provider_instance.confirm_payment(transaction_id)
        
        if result['success']:
            payment.status = PaymentStatus.COMPLETED
            payment.order.status = PaymentStatus.COMPLETED
        else:
            payment.status = PaymentStatus.FAILED
            payment.order.status = PaymentStatus.FAILED
            
        self.db.commit()
        return result
    
    def _generate_order_number(self):
        """Generate unique order number"""
        return f"ORD-{uuid.uuid4().hex[:8].upper()}"
    
    def handle_webhook(self, provider, data):
        """Handle payment provider webhooks"""
        if provider == 'stripe':
            return self._handle_stripe_webhook(data)
        elif provider == 'africas_talking':
            return self._handle_at_webhook(data)
        return {'success': False, 'error': 'Unknown provider'}
    
    def _handle_stripe_webhook(self, event_data):
        """Handle Stripe webhook events"""
        event_type = event_data.get('type')
        
        if event_type == 'payment_intent.succeeded':
            payment_intent = event_data['data']['object']
            order_id = payment_intent['metadata'].get('order_id')
            if order_id:
                return self.confirm_payment(order_id, payment_intent['id'])
                
        return {'success': True}
    
    def _handle_at_webhook(self, data):
        """Handle Africa's Talking webhook"""
        transaction_id = data.get('transactionId')
        status = data.get('status')
        
        payment = Payment.query.filter_by(transaction_id=transaction_id).first()
        if payment:
            if status == 'Success':
                payment.status = PaymentStatus.COMPLETED
                payment.order.status = PaymentStatus.COMPLETED
            else:
                payment.status = PaymentStatus.FAILED
                payment.order.status = PaymentStatus.FAILED
                
            self.db.commit()
            
        return {'success': True}
