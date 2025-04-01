from flask import Flask
import os
from flask_socketio import SocketIO

# Create the SocketIO instance outside the factory function
socketio = SocketIO()

def create_app():
    """Application factory function"""
    app = Flask(__name__)
    
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    
    # Register blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    # Initialize SocketIO with the app
    socketio.init_app(app, cors_allowed_origins="*")
    
    return app 