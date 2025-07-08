from models.payment import Cart, CartItem
from models.product import Product, Stock
import uuid

class CartService:
    def __init__(self, db_session):
        self.db = db_session
        
    def get_or_create_cart(self, session_id):
        """Get existing cart or create new one"""
        cart = Cart.query.filter_by(session_id=session_id).first()
        if not cart:
            cart = Cart(session_id=session_id)
            self.db.add(cart)
            self.db.commit()
        return cart
    
    def add_to_cart(self, session_id, product_id, quantity=1):
        """Add product to cart"""
        cart = self.get_or_create_cart(session_id)
        
        # Check if product exists and has stock
        product = Product.query.get(product_id)
        if not product:
            return {'success': False, 'error': 'Product not found'}
            
        if not product.stock or product.stock.quantity < quantity:
            return {'success': False, 'error': 'Insufficient stock'}
        
        # Check if item already in cart
        cart_item = CartItem.query.filter_by(
            cart_id=cart.id,
            product_id=product_id
        ).first()
        
        if cart_item:
            # Update quantity
            new_quantity = cart_item.quantity + quantity
            if product.stock.quantity < new_quantity:
                return {'success': False, 'error': 'Insufficient stock'}
            cart_item.quantity = new_quantity
        else:
            # Add new item
            cart_item = CartItem(
                cart_id=cart.id,
                product_id=product_id,
                quantity=quantity
            )
            self.db.add(cart_item)
        
        self.db.commit()
        return {'success': True, 'cart_item': cart_item}
    
    def update_cart_item(self, session_id, product_id, quantity):
        """Update cart item quantity"""
        cart = Cart.query.filter_by(session_id=session_id).first()
        if not cart:
            return {'success': False, 'error': 'Cart not found'}
            
        cart_item = CartItem.query.filter_by(
            cart_id=cart.id,
            product_id=product_id
        ).first()
        
        if not cart_item:
            return {'success': False, 'error': 'Item not in cart'}
            
        # Check stock
        product = Product.query.get(product_id)
        if product.stock.quantity < quantity:
            return {'success': False, 'error': 'Insufficient stock'}
            
        if quantity == 0:
            self.db.delete(cart_item)
        else:
            cart_item.quantity = quantity
            
        self.db.commit()
        return {'success': True}
    
    def remove_from_cart(self, session_id, product_id):
        """Remove item from cart"""
        return self.update_cart_item(session_id, product_id, 0)
    
    def get_cart_items(self, session_id):
        """Get all items in cart with details"""
        cart = Cart.query.filter_by(session_id=session_id).first()
        if not cart:
            return []
            
        items = []
        total = 0
        
        for cart_item in cart.items:
            product = cart_item.product
            price = product.price.amount if product.price else 0
            item_total = price * cart_item.quantity
            total += item_total
            
            items.append({
                'product_id': product.id,
                'product_name': product.name,
                'quantity': cart_item.quantity,
                'unit_price': float(price),
                'total_price': float(item_total),
                'stock_available': product.stock.quantity if product.stock else 0,
                'image': product.images[0].filepath if product.images else None
            })
            
        return {
            'items': items,
            'total': float(total),
            'item_count': sum(item['quantity'] for item in items)
        }
    
    def clear_cart(self, session_id):
        """Clear all items from cart"""
        cart = Cart.query.filter_by(session_id=session_id).first()
        if cart:
            for item in cart.items:
                self.db.delete(item)
            self.db.commit()
        return {'success': True}
