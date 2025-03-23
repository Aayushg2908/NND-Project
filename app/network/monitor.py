import time
import random
import logging
import threading
import socket
import subprocess
import platform
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('network_monitor')

# Global network status
network_status = {
    'last_updated': None,
    'overall_health': 'good',
    'bandwidth_usage': 0,
    'latency': 0,
    'packet_loss': 0,
    'connected_devices': 0,
    'metrics_history': []
}

def get_network_status():
    """Return the current network status"""
    return network_status

def ping_host(host):
    """Check if a host is reachable using socket connection"""
    try:
        # Use socket instead of ping command
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        result = s.connect_ex((host, 80))
        s.close()
        
        if result == 0:
            return f"Socket connection to {host} successful"
        else:
            return None
    except Exception as e:
        logger.warning(f"Socket connection to {host} failed: {e}")
        return None

def scan_local_network():
    """Scan local network for devices"""
    # This is a simplified version that doesn't actually scan
    # In a real implementation, you would use a library like scapy to scan
    devices = []
    for i in range(1, 4):  # Simulating 3 devices
        devices.append({
            'ip': f'192.168.1.{i}',
            'mac': f'00:00:00:00:00:0{i}',
            'hostname': f'device-{i}',
            'status': 'up' if random.random() > 0.1 else 'down'
        })
    return devices

def collect_metrics():
    """Collect network metrics"""
    global network_status

    # Simulate collecting network metrics
    # In a real implementation, you would use libraries like psutil, scapy, etc.
    
    # Check connectivity to a common host
    try:
        ping_result = ping_host('8.8.8.8')
        latency = random.uniform(10, 100) if ping_result else 1000
    except Exception as e:
        logger.warning(f"Connectivity check failed, using simulated data: {e}")
        ping_result = random.random() > 0.2  # 80% chance of success in simulation
        latency = random.uniform(10, 100) if ping_result else 1000
    
    # Get devices on network
    devices = scan_local_network()
    connected_devices = len([d for d in devices if d['status'] == 'up'])
    
    # Simulate bandwidth usage
    bandwidth_usage = random.uniform(5, 50)  # Mbps
    
    # Calculate packet loss
    packet_loss = 0 if ping_result else random.uniform(10, 50)
    
    # Update network status
    network_status['last_updated'] = datetime.now().isoformat()
    network_status['latency'] = round(latency, 2)
    network_status['bandwidth_usage'] = round(bandwidth_usage, 2)
    network_status['packet_loss'] = round(packet_loss, 2)
    network_status['connected_devices'] = connected_devices
    
    # Determine overall health
    if latency > 500 or packet_loss > 20:
        network_status['overall_health'] = 'critical'
    elif latency > 200 or packet_loss > 5:
        network_status['overall_health'] = 'warning'
    else:
        network_status['overall_health'] = 'good'
    
    # Store metrics in history (keep last 100 entries)
    network_status['metrics_history'].append({
        'timestamp': network_status['last_updated'],
        'latency': network_status['latency'],
        'bandwidth_usage': network_status['bandwidth_usage'],
        'packet_loss': network_status['packet_loss']
    })
    
    if len(network_status['metrics_history']) > 100:
        network_status['metrics_history'] = network_status['metrics_history'][-100:]
    
    # Log status
    logger.info(f"Network status updated: Health={network_status['overall_health']}, " +
                f"Latency={network_status['latency']}ms, " +
                f"Packet Loss={network_status['packet_loss']}%")
    
    # Check for anomalies
    try:
        from app.models.anomaly_detector import AnomalyDetector
        detector = AnomalyDetector()
        anomalies = detector.detect_anomalies(network_status)
        
        if anomalies:
            logger.warning(f"Anomalies detected: {anomalies}")
            # Trigger self-healing
            from app.healing.resolver import NetworkResolver
            resolver = NetworkResolver()
            for anomaly in anomalies:
                resolver.handle_anomaly(anomaly)
    except Exception as e:
        logger.error(f"Error in anomaly detection: {e}")
    
    return network_status

class NetworkMonitor:
    """Network monitoring class to run in a background thread"""
    
    def __init__(self, interval=10):
        """Initialize monitor with collection interval in seconds"""
        self.interval = interval
        self.running = False
        self.thread = None
    
    def start(self):
        """Start the monitoring process"""
        self.running = True
        logger.info("Network monitoring started")
        
        while self.running:
            try:
                collect_metrics()
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
            
            time.sleep(self.interval)
    
    def stop(self):
        """Stop the monitoring process"""
        self.running = False
        logger.info("Network monitoring stopped")

# For testing
if __name__ == "__main__":
    monitor = NetworkMonitor(interval=5)
    monitor.start() 