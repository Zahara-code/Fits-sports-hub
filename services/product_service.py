# services/product_service.py
from models.product import Category, Price, Product, ProductImage, Stock


class ProductService:
    def __init__(self, db_session):
        self.db = db_session

    def create_category(self, name, description=None):
        cat = Category(name=name, description=description)
        self.db.add(cat)
        self.db.commit()
        return cat

    def create_product(self, name, category_id, description=None):
        prod = Product(name=name, category_id=category_id, description=description)
        self.db.add(prod)
        self.db.commit()
        return prod

    def add_image(self, product_id, url):
        img = ProductImage(product_id=product_id, url=url)
        self.db.add(img)
        self.db.commit()
        return img

    def add_product_image(self, product_id, filename, filepath):
        """Add image file to product"""
        img = ProductImage(
            product_id=product_id,
            filename=filename,
            filepath=filepath
        )
        self.db.add(img)
        self.db.commit()
        return img

    def set_stock(self, product_id, quantity):
        stock = Stock.query.filter_by(product_id=product_id).first()
        if not stock:
            stock = Stock(product_id=product_id, quantity=quantity)
            self.db.add(stock)
        else:
            stock.quantity = quantity
        self.db.commit()
        return stock

    def set_price(self, product_id, amount, currency='USD'):
        price = Price.query.filter_by(product_id=product_id).first()
        if not price:
            price = Price(product_id=product_id, amount=amount, currency=currency)
            self.db.add(price)
        else:
            price.amount = amount
            price.currency = currency
        self.db.commit()
        return price
