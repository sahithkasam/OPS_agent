import random
import time
import numpy as np
from datetime import datetime

class MetricsGenerator:
    def __init__(self):
        self.baseline_cpu = 30.0
        self.baseline_memory = 40.0
        self.baseline_latency = 0.05  # seconds
        self.status = "healthy"
        self._anomaly_mode = None
        self._start_time = None

    def set_anomaly(self, anomaly_type):
        """
        Triggers a specific anomaly mode: 'high_cpu', 'memory_leak', 'network_latency', 'service_down'
        """
        self._anomaly_mode = anomaly_type
        self._start_time = time.time()
        print(f"[Simulation] Anomaly injected: {anomaly_type}")

    def clear_anomaly(self):
        self._anomaly_mode = None
        self._start_time = None
        print("[Simulation] Anomaly cleared. System returning to normal.")

    def generate_metrics(self):
        """
        Returns a dictionary of current metrics.
        """
        current_time = datetime.now().isoformat()
        
        # Base noise
        cpu = self.baseline_cpu + random.uniform(-5, 5)
        memory = self.baseline_memory + random.uniform(-2, 2)
        latency = max(0, self.baseline_latency + random.uniform(-0.01, 0.01))
        
        if self._anomaly_mode == 'high_cpu':
            # Instant spike for demo purposes
            cpu = 95 + random.uniform(-2, 3) # Always > 93%
            
        elif self._anomaly_mode == 'memory_leak':
            # Instant full memory
            memory = 96 + random.uniform(-1, 2)
            if memory > 99: memory = 99

        elif self._anomaly_mode == 'network_latency':
            # Instant High latency
            latency = 2.5 + random.uniform(0.1, 0.5)
            
        elif self._anomaly_mode == 'service_down':
            # Zero CPU, Max Errors (logs generated elsewhere), Zero/Timeout Latency
            cpu = 0
            latency = 0 # No response
            
        return {
            "timestamp": current_time,
            "cpu_percent": round(max(0, min(100, cpu)), 2),
            "memory_percent": round(max(0, min(100, memory)), 2),
            "latency_seconds": round(latency, 4),
            "anomaly_active": self._anomaly_mode
        }
