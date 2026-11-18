import random
from datetime import datetime


# Per-incident-type log signatures: (probability per line, status, level, message, latency range).
# Messages mirror what these failures look like in real application logs, so
# the diagnostics agent and RAG search get meaningful text to work with.
ANOMALY_LOGS = {
    "service_down": (1.0, 503, "CRITICAL", "Service Unavailable: Connection refused to backend DB", (0.001, 0.005)),
    "high_cpu": (0.3, 504, "ERROR", "Gateway Timeout: Upstream processing too slow", (2.0, 5.0)),
    "network_latency": (0.25, 504, "ERROR", "Upstream connect timeout: packet loss to us-east-1b", (1.0, 3.0)),
    "memory_leak": (0.35, 500, "ERROR", "Container OOMKilled: java.lang.OutOfMemoryError: Java heap space", (0.5, 2.0)),
    "disk_usage_high": (0.4, 500, "ERROR", "IOError: [Errno 28] No space left on device: '/var/log/app'", (0.05, 0.3)),
    "process_crash": (0.4, 502, "CRITICAL", "Worker process exited with signal 11 (SIGSEGV); restarting", (1.0, 2.5)),
    "database_lock": (0.45, 500, "ERROR", "Lock wait timeout exceeded; try restarting transaction (orders table)", (4.0, 7.0)),
    "ssl_expiry": (0.5, 495, "ERROR", "TLS handshake failed: x509: certificate has expired or is not yet valid", (0.01, 0.05)),
    "bad_deploy": (0.5, 500, "ERROR", "Release v2.14.3: config validation failed: unknown field 'retry_policy'", (0.5, 2.0)),
    "dns_failure": (0.5, 502, "ERROR", "DNS resolution failed: SERVFAIL looking up db.internal.svc.cluster.local", (3.0, 5.0)),
    # Log-only anomaly (no metrics effect)
    "db_connection_error": (1.0, 500, "ERROR", "Database Connection Failed: Pool exhausted", (0.05, 0.2)),
}


class LogGenerator:
    def __init__(self):
        self.endpoints = ["/api/v1/login", "/api/v1/dashboard", "/api/v1/search", "/api/v1/user/profile"]
        self.methods = ["GET", "POST"]
        self.user_agents = ["Mozilla/5.0", "Curl/7.68.0", "PostmanRuntime/7.29.0"]

    def generate_log(self, anomaly_mode=None):
        """
        Generates a single log entry. Correlates with metrics anomaly if present.
        `anomaly_mode` may be a comma-separated list when several incidents are
        active; each line then reflects one of them.
        """
        ts = datetime.now().isoformat()
        endpoint = random.choice(self.endpoints)
        method = random.choice(self.methods)

        status_code = 200
        latency = random.uniform(0.01, 0.1)
        level = "INFO"
        message = "Request processed successfully"

        modes = [m for m in (anomaly_mode or "").split(",") if m]
        mode = random.choice(modes) if modes else None
        sig = ANOMALY_LOGS.get(mode)
        if sig:
            prob, sig_status, sig_level, sig_msg, (lo, hi) = sig
            latency = random.uniform(lo, hi)
            if random.random() < prob:
                status_code, level, message = sig_status, sig_level, sig_msg

        # Chance of random noise error 500 even in healthy state (realism)
        if mode is None and random.random() < 0.01:
            status_code = 500
            level = "ERROR"
            message = "Internal Server Error: NullPointerException in handler"

        return {
            "timestamp": ts,
            "level": level,
            "method": method,
            "endpoint": endpoint,
            "status": status_code,
            "latency": round(latency, 4),
            "message": message,
        }
