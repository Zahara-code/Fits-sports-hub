from flask import Flask, render_template
from flask_login import LoginManager
from models.product import db
from models.user import User, Admin
from config import Config
from routes.product_bp import bp as product_bp, api_bp
from routes.auth import auth_bp, admin_auth_bp
from routes.admin_bp import admin_bp
from routes.store_bp import store_bp
import os

app = Flask(__name__)
app.config.from_object(Config)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fit_sports_hub.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this to a secure secret key

# Initialize db with app
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    # Use db.session.get() instead of Query.get() for SQLAlchemy 2.0 compatibility
    # Try to load as regular user first
    user = db.session.get(User, int(user_id))
    if user:
        return user
    # If not found, try admin
    return db.session.get(Admin, int(user_id))

# Create upload directories
os.makedirs(os.path.join(app.root_path, 'static', 'uploads', 'products'), exist_ok=True)

# Register blueprints
app.register_blueprint(product_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(admin_auth_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(store_bp, url_prefix='/store')
app.register_blueprint(api_bp, url_prefix='/api')  # This should include store_api

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)