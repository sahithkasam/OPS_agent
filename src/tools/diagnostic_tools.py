"""
Diagnostic Tools — OpsPilot
Real shell/HTTP/system diagnostic tools callable by the Diagnostics Agent.
Maps to Proposal Section 5.1.2: Diagnostics Agent (runs shell/HTTP tools).
"""

import subprocess
import socket
import shutil
import platform
import time
import requests

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


# ─────────────────────────────────────────────
# 1. Network Diagnostics
# ─────────────────────────────────────────────

def ping_host(host: str = "8.8.8.8", count: int = 3) -> dict:
    """
    Pings a host and returns packet loss and avg latency.
    Works on Mac/Linux.
    """
    try:
        flag = "-n" if platform.system().lower() == "windows" else "-c"
        result = subprocess.run(
            ["ping", flag, str(count), host],
            capture_output=True, text=True, timeout=10
        )
        output = result.stdout + result.stderr
        success = result.returncode == 0

        # Parse latency from output (mac/linux)
        avg_ms = None
        for line in output.splitlines():
            if "avg" in line or "average" in line:
                parts = line.split("/")
                if len(parts) >= 5:
                    try:
                        avg_ms = float(parts[4])
                    except:
                        pass

        return {
            "tool": "ping",
            "host": host,
            "reachable": success,
            "avg_latency_ms": avg_ms,
            "output": output[:300]
        }
    except subprocess.TimeoutExpired:
        return {"tool": "ping", "host": host, "reachable": False, "error": "Timeout"}
    except Exception as e:
        return {"tool": "ping", "host": host, "reachable": False, "error": str(e)}


def check_http_endpoint(url: str = "http://localhost:8000/health", timeout: int = 5) -> dict:
    """
    HTTP health check — equivalent to curl.
    """
    try:
        start = time.time()
        response = requests.get(url, timeout=timeout)
        latency = round((time.time() - start) * 1000, 2)
        return {
            "tool": "http_check",
            "url": url,
            "status_code": response.status_code,
            "healthy": response.status_code < 400,
            "latency_ms": latency,
            "response_preview": response.text[:200]
        }
    except requests.exceptions.ConnectionError:
        return {"tool": "http_check", "url": url, "healthy": False, "error": "Connection refused"}
    except requests.exceptions.Timeout:
        return {"tool": "http_check", "url": url, "healthy": False, "error": "Request timeout"}
    except Exception as e:
        return {"tool": "http_check", "url": url, "healthy": False, "error": str(e)}


def check_port(host: str = "localhost", port: int = 8080, timeout: int = 3) -> dict:
    """
    Checks if a TCP port is open on a host.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        is_open = result == 0
        return {
            "tool": "port_check",
            "host": host,
            "port": port,
            "open": is_open,
            "status": "OPEN" if is_open else "CLOSED"
        }
    except Exception as e:
        return {"tool": "port_check", "host": host, "port": port, "open": False, "error": str(e)}


# ─────────────────────────────────────────────
# 2. System Resource Diagnostics
# ─────────────────────────────────────────────

def get_system_metrics() -> dict:
    """
    Returns real CPU, memory, disk metrics from the host system.
    Uses psutil if available, else uses platform commands.
    """
    if PSUTIL_AVAILABLE:
        try:
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            cpu = psutil.cpu_percent(interval=0.5)
            return {
                "tool": "system_metrics",
                "cpu_percent": cpu,
                "memory_percent": mem.percent,
                "memory_used_gb": round(mem.used / (1024 ** 3), 2),
                "memory_total_gb": round(mem.total / (1024 ** 3), 2),
                "disk_percent": disk.percent,
                "disk_used_gb": round(disk.used / (1024 ** 3), 2),
                "disk_total_gb": round(disk.total / (1024 ** 3), 2),
                "source": "psutil"
            }
        except Exception as e:
            return {"tool": "system_metrics", "error": str(e)}
    else:
        # Fallback using shutil for disk
        disk = shutil.disk_usage("/")
        return {
            "tool": "system_metrics",
            "disk_percent": round(disk.used / disk.total * 100, 1),
            "disk_used_gb": round(disk.used / (1024 ** 3), 2),
            "disk_total_gb": round(disk.total / (1024 ** 3), 2),
            "source": "shutil"
        }


def check_disk_usage(path: str = "/") -> dict:
    """
    Checks disk usage at a given path.
    """
    try:
        usage = shutil.disk_usage(path)
        used_pct = round(usage.used / usage.total * 100, 1)
        return {
            "tool": "disk_usage",
            "path": path,
            "used_percent": used_pct,
            "used_gb": round(usage.used / (1024 ** 3), 2),
            "free_gb": round(usage.free / (1024 ** 3), 2),
            "total_gb": round(usage.total / (1024 ** 3), 2),
            "critical": used_pct > 85
        }
    except Exception as e:
        return {"tool": "disk_usage", "path": path, "error": str(e)}


# ─────────────────────────────────────────────
# 3. Process Diagnostics
# ─────────────────────────────────────────────

def list_top_processes(n: int = 5) -> dict:
    """
    Lists top N processes by CPU usage.
    """
    if not PSUTIL_AVAILABLE:
        return {"tool": "top_processes", "error": "psutil not installed"}
    try:
        procs = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                procs.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        procs.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
        return {
            "tool": "top_processes",
            "top_processes": procs[:n]
        }
    except Exception as e:
        return {"tool": "top_processes", "error": str(e)}


# ─────────────────────────────────────────────
# 4. Composite Health Check
# ─────────────────────────────────────────────

def run_full_diagnostic(incident_type: str) -> dict:
    """
    Runs a set of diagnostics relevant to the given incident type.
    Returns a unified diagnostic report.
    """
    report = {
        "incident_type": incident_type,
        "checks": {}
    }

    # Always run system metrics
    report["checks"]["system"] = get_system_metrics()

    # Incident-specific checks
    if incident_type in ("high_cpu", "process_crash"):
        report["checks"]["top_processes"] = list_top_processes(5)

    if incident_type in ("disk_usage_high",):
        report["checks"]["disk"] = check_disk_usage("/")

    if incident_type in ("service_down", "latency_spike"):
        report["checks"]["network"] = ping_host("8.8.8.8")
        report["checks"]["localhost"] = check_http_endpoint("http://localhost:8080/health")

    if incident_type == "ssl_expiry":
        report["checks"]["port_443"] = check_port("localhost", 443)

    if incident_type == "database_lock":
        report["checks"]["db_port"] = check_port("localhost", 5432)

    # Summary
    issues = []
    for check_name, result in report["checks"].items():
        if result.get("error"):
            issues.append(f"{check_name}: {result['error']}")
        elif result.get("cpu_percent", 0) > 85:
            issues.append(f"High CPU: {result['cpu_percent']}%")
        elif result.get("memory_percent", 0) > 85:
            issues.append(f"High Memory: {result['memory_percent']}%")
        elif result.get("disk_percent", 0) > 85:
            issues.append(f"Disk Critical: {result['disk_percent']}%")
        elif result.get("reachable") is False:
            issues.append(f"Host unreachable via ping")
        elif result.get("healthy") is False:
            issues.append(f"HTTP endpoint unhealthy: {result.get('url')}")

    report["issues_found"] = issues
    report["healthy"] = len(issues) == 0

    return report
