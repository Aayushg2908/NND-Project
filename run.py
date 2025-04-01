from app import create_app
import threading
from app.network.monitor import NetworkMonitor

if __name__ == "__main__":
    app = create_app()
    
    # Start network monitoring in a separate thread
    monitor = NetworkMonitor(interval=5)
    monitor_thread = threading.Thread(target=monitor.start)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    print("Network monitoring started in background")
    print("Starting web server. Access the dashboard at http://localhost:5000")
    
    # Start Flask application
    app.run(debug=True, host='0.0.0.0') 