from flask import Flask, render_template
from models.product import db
from config import Config
from routes.product_bp import bp as product_bp, api_bp
from routes.store_bp import store_bp
from routes.admin_bp import admin_bp
import os

app = Flask(__name__)
app.config.from_object(Config)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fit_sports_hub.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize db with app
db.init_app(app)

# Create upload directories
os.makedirs(os.path.join(app.root_path, 'static', 'uploads', 'products'), exist_ok=True)

# Register blueprints
app.register_blueprint(product_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')  # Add URL prefix for admin routes
app.register_blueprint(store_bp, url_prefix='/store')  # Add URL prefix for store routes
app.register_blueprint(api_bp, url_prefix='/api')  # Add URL prefix for API

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)