import os
import logging
import numpy as np
import pickle
import json
from datetime import datetime
from collections import deque
from sklearn.ensemble import IsolationForest
import joblib

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('anomaly_detector')

# Define the model file paths
MODEL_DIR = os.path.join('data', 'models')
MODEL_FILE = os.path.join(MODEL_DIR, 'anomaly_model.pkl')
HISTORY_FILE = os.path.join(MODEL_DIR, 'training_history.json')

# Make sure model directory exists
os.makedirs(MODEL_DIR, exist_ok=True)

class AnomalyDetector:
    """Anomaly detection for network metrics using Isolation Forest"""
    
    def __init__(self):
        """Initialize the anomaly detector and load or create model"""
        # Keep a buffer of recent observations for retraining
        self.observations = deque(maxlen=1000)
        
        # Feature names to extract from network status
        self.features = ['latency', 'bandwidth_usage', 'packet_loss']
        
        # Create or load the model
        if os.path.exists(MODEL_FILE):
            logger.info(f"Loading existing anomaly detection model from {MODEL_FILE}")
            self.model = joblib.load(MODEL_FILE)
        else:
            logger.info("Creating new anomaly detection model")
            self.model = IsolationForest(
                n_estimators=100,
                contamination=0.05,  # Expect about 5% anomalies
                random_state=42
            )
            # We'll train on first batch of data
        
        # Load training history if it exists
        self.training_history = []
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r') as f:
                    self.training_history = json.load(f)
            except Exception as e:
                logger.error(f"Error loading training history: {e}")
    
    def _extract_features(self, network_status):
        """Extract relevant features from network status"""
        features = []
        for feature in self.features:
            features.append(network_status.get(feature, 0))
        return features
    
    def detect_anomalies(self, network_status):
        """Detect anomalies in current network status"""
        # Extract features
        features = self._extract_features(network_status)
        
        # Add to observation buffer for later retraining
        self.observations.append(features)
        
        # Check if model needs initial training
        if not hasattr(self.model, 'fit_') or not self.model.fit_:
            if len(self.observations) >= 50:  # Wait for enough data
                self._train_model()
            return []  # Return no anomalies until model is trained
        
        # Make prediction (1 = normal, -1 = anomaly)
        prediction = self.model.predict([features])[0]
        anomaly_score = self.model.decision_function([features])[0]
        
        # No anomaly detected
        if prediction == 1:
            return []
        
        # Determine the anomaly type based on feature values
        anomalies = []
        
        if network_status['latency'] > 200:
            anomalies.append({
                'type': 'high_latency',
                'score': float(anomaly_score),
                'details': {
                    'latency': network_status['latency'],
                    'threshold': 200
                },
                'detected_at': datetime.now().isoformat()
            })
        
        if network_status['packet_loss'] > 10:
            anomalies.append({
                'type': 'packet_loss',
                'score': float(anomaly_score),
                'details': {
                    'packet_loss': network_status['packet_loss'],
                    'threshold': 10
                },
                'detected_at': datetime.now().isoformat()
            })
        
        if len(anomalies) == 0 and prediction == -1:
            # General anomaly without specific cause
            anomalies.append({
                'type': 'general_anomaly',
                'score': float(anomaly_score),
                'details': {
                    'features': dict(zip(self.features, features))
                },
                'detected_at': datetime.now().isoformat()
            })
        
        # Log the anomaly
        logger.warning(f"Detected {len(anomalies)} anomalies: {anomalies}")
        
        # Check if we should retrain model
        if len(self.observations) >= 500:  # Retrain after collecting enough new data
            self._train_model()
        
        return anomalies
    
    def _train_model(self):
        """Train or retrain the model with current observations"""
        logger.info(f"Training anomaly detection model with {len(self.observations)} observations")
        
        # Convert observations to numpy array
        X = np.array(list(self.observations))
        
        # Fit the model
        self.model.fit(X)
        
        # Save the model
        joblib.dump(self.model, MODEL_FILE)
        logger.info(f"Model saved to {MODEL_FILE}")
        
        # Record training event
        training_event = {
            'timestamp': datetime.now().isoformat(),
            'samples': len(self.observations),
            'features': self.features
        }
        self.training_history.append(training_event)
        
        # Save training history
        with open(HISTORY_FILE, 'w') as f:
            json.dump(self.training_history, f, indent=2)
        
        logger.info("Model training completed")
    
    def record_feedback(self, anomaly_id, is_real_anomaly):
        """Record user feedback on anomaly detection results for model improvement"""
        # This would be connected to UI feedback
        # We could use this to adjust model parameters or create labeled data
        logger.info(f"Received feedback for anomaly {anomaly_id}: is_real_anomaly={is_real_anomaly}")
        # In a more sophisticated implementation, this would be used to improve the model

# For testing
if __name__ == "__main__":
    detector = AnomalyDetector()
    # Test with simulated data
    for _ in range(100):
        status = {
            'latency': np.random.normal(50, 20),
            'bandwidth_usage': np.random.normal(20, 5),
            'packet_loss': np.random.normal(1, 0.5)
        }
        anomalies = detector.detect_anomalies(status)
        if anomalies:
            print(f"Detected anomalies: {anomalies}") 