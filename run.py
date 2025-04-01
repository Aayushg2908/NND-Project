from app import create_app, socketio
import threading
from app.network.monitor import NetworkMonitor
from app.routes import emit_logs, emit_network_status, emit_active_issues, emit_resolved_issues

if __name__ == "__main__":
    app = create_app()
    
    # Start network monitoring in a separate thread
    monitor = NetworkMonitor(interval=5)  # Decreased from default 10 to 5 seconds
    monitor_thread = threading.Thread(target=monitor.start)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    print("Network monitoring started in background")
    print("Starting web server with Socket.IO. Access the dashboard at http://localhost:5000")
    
    # Register periodic events
    @socketio.on('connect')
    def handle_connect():
        print("Client connected")
        # Send initial data on connection
        emit_active_issues()
        emit_resolved_issues()
        emit_logs()
        emit_network_status()
    
    # Start Flask application with Socket.IO
    socketio.run(app, debug=True, host='0.0.0.0', allow_unsafe_werkzeug=True) 