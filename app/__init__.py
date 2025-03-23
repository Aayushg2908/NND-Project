from flask import Flask
import os

def create_app():
    """Application factory function"""
    app = Flask(__name__)
    
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    
    # Register blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    return app 