import numpy as np
from sklearn.ensemble import IsolationForest

class AnomalyDetector:
    def __init__(self):
        # Hybrid approach: Rule-based for obvious L1 issues + ML for subtle drifts
        self.model = IsolationForest(contamination=0.1, random_state=42)
        self.training_data = []
        self.is_fitted = False
        
        # Rule thresholds
        self.CPU_THRESHOLD = 80.0
        self.MEMORY_THRESHOLD = 90.0
        self.LATENCY_THRESHOLD = 2.0 # seconds

    def train_initial(self, normal_data_points):
        """
        Feeds initial 'healthy' data to train the Isolation Forest.
        data_points: list of [cpu, memory, latency]
        """
        if len(normal_data_points) > 10:
            self.model.fit(normal_data_points)
            self.is_fitted = True

    def detect(self, metric_snapshot):
        """
        Returns a dict with 'is_anomaly' (bool), 'score' (float), and 'reason' (str).
        """
        cpu = metric_snapshot['cpu_percent']
        mem = metric_snapshot['memory_percent']
        lat = metric_snapshot['latency_seconds']
        
        reasons = []
        
        # 1. Rule-Based Checks (Deterministic for L1/L2 Demo)
        if cpu > self.CPU_THRESHOLD:
            reasons.append(f"CPU usage {cpu}% exceeds threshold {self.CPU_THRESHOLD}%")
        if mem > self.MEMORY_THRESHOLD:
            reasons.append(f"Memory usage {mem}% exceeds threshold {self.MEMORY_THRESHOLD}%")
        if lat > self.LATENCY_THRESHOLD:
            reasons.append(f"Latency {lat}s exceeds threshold {self.LATENCY_THRESHOLD}s")

        # 2. ML-Based Check (Anomaly Score)
        ml_score = 0.0
        if self.is_fitted:
            # Reshape for sklearn
            vector = np.array([[cpu, mem, lat]])
            # IsolationForest returns -1 for anomaly, 1 for normal
            pred = self.model.predict(vector)[0]
            # score_samples returns negative float, lower is more anomalous
            raw_score = self.model.score_samples(vector)[0]
            ml_score = round(raw_score, 4)
            
            if pred == -1 and not reasons:
                # Only add if rules didn't catch it, to show "AI value"
                reasons.append(f"ML Model detected deviation (score: {ml_score})")

        is_anomaly = len(reasons) > 0
        
        return {
            "is_anomaly": is_anomaly,
            "reasons": reasons,
            "ml_score": ml_score
        }
