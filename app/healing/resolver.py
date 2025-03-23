import os
import logging
import json
import uuid
import subprocess
import platform
import time
from datetime import datetime
import threading

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('network_resolver')

# Define file paths
DATA_DIR = os.path.join('data', 'healing')
ISSUES_FILE = os.path.join(DATA_DIR, 'active_issues.json')
HISTORY_FILE = os.path.join(DATA_DIR, 'resolution_history.json')

# Make sure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

class NetworkResolver:
    """Network issue resolution and self-healing"""
    
    def __init__(self):
        """Initialize the network resolver"""
        # Load active issues
        self.active_issues = {}
        if os.path.exists(ISSUES_FILE):
            try:
                with open(ISSUES_FILE, 'r') as f:
                    self.active_issues = json.load(f)
            except Exception as e:
                logger.error(f"Error loading active issues: {e}")
        
        # Load resolution history
        self.resolution_history = []
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r') as f:
                    self.resolution_history = json.load(f)
            except Exception as e:
                logger.error(f"Error loading resolution history: {e}")
    
    def _save_active_issues(self):
        """Save active issues to file"""
        with open(ISSUES_FILE, 'w') as f:
            json.dump(self.active_issues, f, indent=2)
    
    def _save_resolution_history(self):
        """Save resolution history to file"""
        with open(HISTORY_FILE, 'w') as f:
            json.dump(self.resolution_history, f, indent=2)
    
    def handle_anomaly(self, anomaly):
        """Handle detected anomaly by creating an issue and attempting resolution"""
        # Generate a unique ID for this issue
        issue_id = str(uuid.uuid4())
        
        # Create issue from anomaly
        issue = {
            'id': issue_id,
            'title': self._get_title_for_anomaly_type(anomaly['type']),
            'description': self._get_description_for_anomaly(anomaly),
            'status': 'new',
            'anomaly': anomaly,
            'detected_at': anomaly['detected_at'],
            'resolution_attempts': 0,
            'resolution_actions': []
        }
        
        # Add to active issues
        self.active_issues[issue_id] = issue
        self._save_active_issues()
        
        logger.info(f"Created new issue {issue_id} for anomaly type {anomaly['type']}")
        
        # Try to auto-resolve
        threading.Thread(target=self.auto_resolve, args=(issue_id,)).start()
        
        return issue_id
    
    def _get_title_for_anomaly_type(self, anomaly_type):
        """Get user-friendly title for anomaly type"""
        titles = {
            'high_latency': 'High Network Latency Detected',
            'packet_loss': 'Packet Loss Issues Detected',
            'general_anomaly': 'Network Anomaly Detected'
        }
        return titles.get(anomaly_type, 'Network Issue Detected')
    
    def _get_description_for_anomaly(self, anomaly):
        """Generate user-friendly description for anomaly"""
        if anomaly['type'] == 'high_latency':
            latency = anomaly['details']['latency']
            threshold = anomaly['details']['threshold']
            return f"Network latency is high ({latency}ms), exceeding the threshold of {threshold}ms."
        
        elif anomaly['type'] == 'packet_loss':
            packet_loss = anomaly['details']['packet_loss']
            return f"Packet loss of {packet_loss}% detected on the network."
        
        elif anomaly['type'] == 'general_anomaly':
            feature_str = ', '.join([f"{k}: {v:.2f}" for k, v in anomaly['details']['features'].items()])
            return f"Unusual network behavior detected. Metrics: {feature_str}"
        
        return "Unknown network issue detected."
    
    def get_active_issues(self):
        """Return list of active issues"""
        return list(self.active_issues.values())
    
    def auto_resolve(self, issue_id):
        """Attempt to automatically resolve an issue"""
        if issue_id not in self.active_issues:
            logger.error(f"Cannot resolve issue {issue_id} - not found")
            return {'success': False, 'message': 'Issue not found'}
        
        issue = self.active_issues[issue_id]
        
        if issue['status'] in ['resolved', 'resolving']:
            logger.info(f"Issue {issue_id} is already {issue['status']}")
            return {'success': True, 'message': f"Issue is already {issue['status']}"}
        
        logger.info(f"Attempting to resolve issue {issue_id}")
        
        # Update issue status
        issue['status'] = 'resolving'
        issue['resolution_attempts'] += 1
        self._save_active_issues()
        
        # Get resolution strategy based on anomaly type
        resolution_strategy = self._get_resolution_strategy(issue)
        
        # Record the resolution action
        action = {
            'timestamp': datetime.now().isoformat(),
            'strategy': resolution_strategy['name'],
            'commands': resolution_strategy['commands'].copy() if 'commands' in resolution_strategy else []
        }
        issue['resolution_actions'].append(action)
        
        # Execute resolution commands
        success = True
        result_messages = []
        
        if 'commands' in resolution_strategy:
            for cmd in resolution_strategy['commands']:
                try:
                    logger.info(f"Executing command: {cmd}")
                    if not os.environ.get('SIMULATION_MODE'):
                        # In real mode, execute the actual command
                        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                        exit_code = result.returncode
                        output = result.stdout
                    else:
                        # In simulation mode, just pretend to execute
                        exit_code = 0
                        output = "Command simulated successfully"
                    
                    result_messages.append(f"Command '{cmd}' completed with exit code {exit_code}")
                    
                    if exit_code != 0:
                        success = False
                        result_messages.append(f"Command failed: {output}")
                except Exception as e:
                    success = False
                    error_msg = f"Error executing '{cmd}': {str(e)}"
                    result_messages.append(error_msg)
                    logger.error(error_msg)
        
        # Update issue with results
        action['result'] = {
            'success': success,
            'messages': result_messages
        }
        
        # Wait for verification period
        time.sleep(resolution_strategy.get('verification_wait', 2))
        
        # Check if resolution was successful
        if success:
            # In a real implementation, we would verify the issue is actually resolved
            # For this demo, we'll assume success for some strategies
            if resolution_strategy.get('success_rate', 1.0) > 0.7:
                issue['status'] = 'resolved'
                logger.info(f"Issue {issue_id} marked as resolved")
            else:
                issue['status'] = 'pending'
                logger.info(f"Issue {issue_id} marked as pending - needs verification")
        else:
            issue['status'] = 'failed'
            logger.warning(f"Issue {issue_id} resolution failed")
        
        # Save changes
        self._save_active_issues()
        
        # Add to resolution history
        history_entry = {
            'issue_id': issue_id,
            'anomaly_type': issue['anomaly']['type'],
            'detected_at': issue['detected_at'],
            'resolved_at': datetime.now().isoformat() if issue['status'] == 'resolved' else None,
            'resolution_success': issue['status'] == 'resolved',
            'resolution_actions': issue['resolution_actions']
        }
        self.resolution_history.append(history_entry)
        self._save_resolution_history()
        
        # If resolved, remove from active issues
        if issue['status'] == 'resolved':
            self.active_issues.pop(issue_id)
            self._save_active_issues()
        
        return {'success': success, 'message': '\n'.join(result_messages)}
    
    def resolve_issue(self, issue_id):
        """Manually resolve an issue (triggered from UI)"""
        return self.auto_resolve(issue_id)
    
    def _get_resolution_strategy(self, issue):
        """Determine the appropriate resolution strategy based on the issue type"""
        anomaly_type = issue['anomaly']['type']
        
        if anomaly_type == 'high_latency':
            return {
                'name': 'Flush DNS and Reset Network',
                'description': 'Flush DNS cache and reset network configuration to resolve latency issues',
                'commands': [
                    # Windows commands
                    'ipconfig /flushdns' if platform.system() == 'Windows' else 'sudo systemd-resolve --flush-caches',
                    'ipconfig /release' if platform.system() == 'Windows' else 'sudo dhclient -r',
                    'ipconfig /renew' if platform.system() == 'Windows' else 'sudo dhclient'
                ],
                'verification_wait': 5,
                'success_rate': 0.8
            }
        
        elif anomaly_type == 'packet_loss':
            return {
                'name': 'Reset Network Adapter',
                'description': 'Disable and re-enable network adapter to resolve packet loss issues',
                'commands': [
                    # These would be replaced with actual commands in production
                    # These are simulations
                    'echo "Disabling network adapter..."',
                    'sleep 2',
                    'echo "Enabling network adapter..."'
                ],
                'verification_wait': 5,
                'success_rate': 0.7
            }
        
        else:  # general_anomaly or unknown
            return {
                'name': 'Basic Network Troubleshooting',
                'description': 'Basic network troubleshooting steps to resolve general issues',
                'commands': [
                    'ipconfig /flushdns' if platform.system() == 'Windows' else 'sudo systemd-resolve --flush-caches',
                    'netsh winsock reset' if platform.system() == 'Windows' else 'echo "Winsock reset not applicable"'
                ],
                'verification_wait': 3,
                'success_rate': 0.5
            }

# For testing
if __name__ == "__main__":
    resolver = NetworkResolver()
    
    # Test with simulated anomaly
    anomaly = {
        'type': 'high_latency',
        'score': -0.5,
        'details': {
            'latency': 250,
            'threshold': 200
        },
        'detected_at': datetime.now().isoformat()
    }
    
    issue_id = resolver.handle_anomaly(anomaly)
    print(f"Created issue {issue_id}")
    
    # Get active issues
    issues = resolver.get_active_issues()
    print(f"Active issues: {len(issues)}")
    
    # Resolve an issue
    result = resolver.resolve_issue(issue_id)
    print(f"Resolution result: {result}") 