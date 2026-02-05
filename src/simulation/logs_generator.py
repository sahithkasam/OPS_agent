import random
from datetime import datetime
import time

class LogGenerator:
    def __init__(self):
        self.endpoints = ["/api/v1/login", "/api/v1/dashboard", "/api/v1/search", "/api/v1/user/profile"]
        self.methods = ["GET", "POST"]
        self.user_agents = ["Mozilla/5.0", "Curl/7.68.0", "PostmanRuntime/7.29.0"]

    def generate_log(self, anomaly_mode=None):
        """
        Generates a single log entry. Correlates with metrics anomaly if present.
        """
        ts = datetime.now().isoformat()
        endpoint = random.choice(self.endpoints)
        method = random.choice(self.methods)
        
        status_code = 200
        latency = random.uniform(0.01, 0.1)
        level = "INFO"
        message = f"Request processed successfully"

        if anomaly_mode == "service_down":
            status_code = 503
            level = "CRITICAL"
            message = "Service Unavailable: Connection refused to backend DB"
            latency = 0.001
        
        elif anomaly_mode == "high_cpu":
            # Slow responses, some timeouts
            latency = random.uniform(2.0, 5.0)
            if random.random() < 0.3:
                status_code = 504
                level = "ERROR"
                message = "Gateway Timeout: Upstream processing too slow"
        
        elif anomaly_mode == "network_latency":
            latency = random.uniform(1.0, 3.0)
            
        elif anomaly_mode == "db_connection_error": # Special log-only anomaly
             status_code = 500
             level = "ERROR"
             message = "Database Connection Failed: Pool exhausted"
             
        # Chance of random noise error 500 even in healthy state (realism)
        if anomaly_mode is None and random.random() < 0.01:
            status_code = 500
            level = "ERROR"
            message = "Internal Server Error: NullPointerException in handler"

        log_entry = {
            "timestamp": ts,
            "level": level,
            "method": method,
            "endpoint": endpoint,
            "status": status_code,
            "latency": round(latency, 4),
            "message": message
        }
        return log_entry
