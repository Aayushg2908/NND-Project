from flask import Blueprint, render_template, jsonify, request, current_app
from app.network.monitor import get_network_status, scan_local_network
from app.models.anomaly_detector import AnomalyDetector
from app.healing.resolver import NetworkResolver
import os
import json
from app import socketio
from flask_socketio import emit

main_bp = Blueprint('main', __name__)

# Initialize components as global variables
anomaly_detector = AnomalyDetector()
network_resolver = NetworkResolver()

# Socket.IO event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print("Client connected")
    # Send initial data on connection
    emit_active_issues()
    emit_resolved_issues()
    emit_logs()
    emit_network_status()

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print("Client disconnected")

# Helper functions to emit Socket.IO events
def emit_active_issues():
    """Emit active issues to all clients"""
    issues = network_resolver.get_active_issues()
    socketio.emit('active_issues_update', issues)

def emit_resolved_issues():
    """Emit resolved issues to all clients"""
    history = []
    if os.path.exists(os.path.join('data', 'healing', 'resolution_history.json')):
        try:
            with open(os.path.join('data', 'healing', 'resolution_history.json'), 'r') as f:
                history = json.load(f)
        except Exception as e:
            print(f"Error loading resolution history: {e}")
    socketio.emit('resolved_issues_update', history)

def emit_logs():
    """Emit system logs to all clients"""
    logs = get_latest_logs_data()
    socketio.emit('logs_update', logs)

def emit_network_status():
    """Emit network status to all clients"""
    status = get_network_status()
    socketio.emit('network_status_update', status)

# Register these emit functions with the NetworkResolver for callbacks
network_resolver.register_update_callback(emit_active_issues)
network_resolver.register_resolution_callback(emit_resolved_issues)

@main_bp.route('/')
def index():
    """Main dashboard view"""
    return render_template('index.html')

@main_bp.route('/api/network/status')
def network_status():
    """API endpoint to get current network status"""
    status = get_network_status()
    return jsonify(status)

@main_bp.route('/api/network/history')
def network_history():
    """API endpoint to get network metrics history"""
    status = get_network_status()
    history = status.get('metrics_history', [])
    return jsonify(history)

@main_bp.route('/api/network/devices')
def network_devices():
    """API endpoint to get list of network devices"""
    # Simplified for now - would fetch from actual network
    devices = [
        {'id': 1, 'name': 'Router-1', 'ip': '192.168.1.1', 'status': 'online'},
        {'id': 2, 'name': 'Switch-1', 'ip': '192.168.1.2', 'status': 'online'},
        {'id': 3, 'name': 'AP-1', 'ip': '192.168.1.3', 'status': 'warning'}
    ]
    return jsonify(devices)

@main_bp.route('/api/healing/issues')
def get_issues():
    """Get current detected issues"""
    # Force reload issues from file to ensure we have the latest state
    network_resolver._load_active_issues()
    issues = network_resolver.get_active_issues()
    return jsonify(issues)

@main_bp.route('/api/healing/resolved')
def get_resolved_issues():
    """Get history of resolved issues"""
    # Force reload of resolution history to ensure we have the latest data
    network_resolver._load_resolution_history()
    
    # Return a copy of the list to avoid potential concurrency issues
    history = network_resolver.resolution_history.copy() if network_resolver.resolution_history else []
    
    # Add debugging info
    print(f"Returning {len(history)} resolved issues")
    
    return jsonify(history)

@main_bp.route('/api/healing/resolve', methods=['POST'])
def resolve_issue():
    """Manually trigger resolution for an issue"""
    try:
        data = request.json
        if not data or 'issue_id' not in data:
            print(f"Invalid request data: {data}")
            return jsonify({'success': False, 'message': 'Missing issue_id in request'}), 400
            
        issue_id = data.get('issue_id')
        print(f"Attempting to resolve issue: {issue_id}")
        
        result = network_resolver.resolve_issue(issue_id)
        print(f"Resolution result: {result}")
        
        # Force reload active issues after resolution attempt
        network_resolver._load_active_issues()
        
        # Emit updates
        emit_active_issues()
        emit_resolved_issues()
        emit_logs()
        
        return jsonify(result)
    except Exception as e:
        print(f"Error resolving issue: {str(e)}")
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@main_bp.route('/api/logs')
def get_latest_logs():
    """Get latest system logs"""
    logs = get_latest_logs_data()
    return jsonify(logs)

def get_latest_logs_data():
    """Helper function to get the latest logs data"""
    import logging
    import time
    from datetime import datetime
    
    # Check if log file exists and read from it
    log_file = os.path.join('logs', 'app.log')
    logs = []
    
    # If log file exists, get the latest entries
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r') as f:
                log_lines = f.readlines()
                # Get the last 20 lines
                log_lines = log_lines[-50:] if len(log_lines) > 50 else log_lines
                
                for line in log_lines:
                    try:
                        # Parse log line (format: YYYY-MM-DD HH:MM:SS,MS - name - level - message)
                        parts = line.strip().split(' - ', 3)
                        if len(parts) >= 4:
                            timestamp_str, source, level, message = parts
                            logs.append({
                                "timestamp": timestamp_str,
                                "level": level,
                                "source": source,
                                "message": message
                            })
                    except Exception as e:
                        print(f"Error parsing log line: {e}")
        except Exception as e:
            print(f"Error reading log file: {e}")
    
    # If no logs found in file or file doesn't exist, use simulated logs
    if not logs:
        current_time = datetime.now().isoformat()
        logs = [
            {"timestamp": current_time, "level": "INFO", "source": "monitor", "message": "Network monitoring started"},
            {"timestamp": current_time, "level": "INFO", "source": "monitor", "message": "Network status updated: Health=good, Latency=45ms, Packet Loss=0.5%"},
            {"timestamp": current_time, "level": "WARNING", "source": "detector", "message": "Detected anomaly: high_latency (score: -0.75)"},
            {"timestamp": current_time, "level": "INFO", "source": "resolver", "message": "Created new issue for anomaly type high_latency"},
            {"timestamp": current_time, "level": "INFO", "source": "resolver", "message": "Executing command: Simulating: Flushing DNS cache..."},
            {"timestamp": current_time, "level": "INFO", "source": "resolver", "message": "Issue marked as resolved"}
        ]
    
    return logs 