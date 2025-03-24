from flask import Blueprint, render_template, jsonify, request
from app.network.monitor import get_network_status
from app.models.anomaly_detector import AnomalyDetector
from app.healing.resolver import NetworkResolver

main_bp = Blueprint('main', __name__)

# Initialize components as global variables
anomaly_detector = AnomalyDetector()
network_resolver = NetworkResolver()

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

@main_bp.route('/api/healing/resolve', methods=['POST'])
def resolve_issue():
    """Manually trigger resolution for an issue"""
    issue_id = request.json.get('issue_id')
    result = network_resolver.resolve_issue(issue_id)
    return jsonify(result) 