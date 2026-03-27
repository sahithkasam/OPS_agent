"""
Supervisor Agent — OpsPilot
Orchestrator responsible for:
- Interpreting IT issue intent
- Breaking down the problem into tasks
- Delegating tasks to worker agents
- Calculating severity
Maps to Proposal Section 5.1.1: Supervisor Agent (Orchestrator)
"""

import os
from groq import Groq


class SupervisorAgent:
    """
    Supervisor Agent — Interprets IT issue intent and creates a task plan.
    Uses Llama 3.1 via Groq for natural language reasoning.
    """

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        self.llm_available = bool(api_key)
        self.model = "llama-3.1-70b-versatile"
        if self.llm_available:
            try:
                self.client = Groq(api_key=api_key)
            except Exception:
                self.llm_available = False

    def analyze_intent(self, incident_type: str, metrics: dict, log_features: dict) -> dict:
        """
        Interprets the IT incident intent and returns a task plan.
        """
        symptoms = self._extract_symptoms(metrics, log_features)
        severity = self._calculate_severity(metrics)

        if self.llm_available:
            intent = self._llm_intent(incident_type, symptoms)
        else:
            type_str = incident_type.replace("_", " ").title()
            intent = (
                f"IT Incident Detected: {type_str}. "
                f"Observed symptoms: {', '.join(symptoms) if symptoms else 'anomalous behaviour detected'}. "
                f"Severity: {severity}. Initiating automated diagnostics and resolution pipeline."
            )

        return {
            "intent": intent,
            "severity": severity,
            "symptoms": symptoms,
            "incident_type": incident_type,
            "task_plan": [
                "knowledge_retrieval",
                "diagnostics",
                "resolution",
                "ticketing"
            ]
        }

    def parse_natural_language_incident(self, message: str) -> dict:
        """
        Parses a natural language IT complaint (e.g. from Slack/email)
        and maps it to a structured incident type.
        Maps to Proposal Section 8.2: Slack/Email Incident Parsing.
        """
        if self.llm_available:
            return self._llm_parse_nl(message)

        # Fallback keyword matching
        message_lower = message.lower()
        mapping = {
            "vpn": "service_down",
            "slow": "latency_spike",
            "cpu": "high_cpu",
            "memory": "memory_leak",
            "disk": "disk_usage_high",
            "crash": "process_crash",
            "database": "database_lock",
            "db": "database_lock",
            "ssl": "ssl_expiry",
            "certificate": "ssl_expiry",
            "access": "service_down",
            "down": "service_down",
            "unavailable": "service_down",
            "timeout": "latency_spike",
        }
        for keyword, incident_type in mapping.items():
            if keyword in message_lower:
                return {
                    "incident_type": incident_type,
                    "severity": "P2",
                    "parsed_intent": f"User reported: '{message}'. Mapped to {incident_type}.",
                    "original_message": message
                }
        return {
            "incident_type": "service_down",
            "severity": "P3",
            "parsed_intent": f"Could not determine specific incident type. Defaulting to service_down.",
            "original_message": message
        }

    # ── Private Helpers ─────────────────────────────────────────────────────

    def _extract_symptoms(self, metrics: dict, log_features: dict) -> list:
        symptoms = []
        if metrics.get("cpu_percent", 0) > 80:
            symptoms.append(f"High CPU ({metrics['cpu_percent']:.1f}%)")
        if metrics.get("memory_percent", 0) > 85:
            symptoms.append(f"High Memory ({metrics['memory_percent']:.1f}%)")
        if metrics.get("latency_seconds", 0) > 2.0:
            symptoms.append(f"High Latency ({metrics['latency_seconds']:.2f}s)")
        if metrics.get("disk_percent", 0) > 85:
            symptoms.append(f"Disk Usage High ({metrics['disk_percent']:.1f}%)")
        if log_features.get("recent_errors", 0) > 0:
            symptoms.append(f"{log_features['recent_errors']} errors/sec in logs")
        if log_features.get("log_samples"):
            samples = log_features["log_samples"]
            if samples:
                symptoms.append(f"Recent log: {str(samples[0])[:80]}")
        return symptoms

    def _calculate_severity(self, metrics: dict) -> str:
        cpu = metrics.get("cpu_percent", 0)
        mem = metrics.get("memory_percent", 0)
        lat = metrics.get("latency_seconds", 0)

        if cpu > 95 or mem > 95 or lat > 5:
            return "P1"
        elif cpu > 80 or mem > 85 or lat > 2:
            return "P2"
        elif cpu > 70 or mem > 75 or lat > 1:
            return "P3"
        return "P4"

    def _llm_intent(self, incident_type: str, symptoms: list) -> str:
        try:
            symptom_str = ", ".join(symptoms) if symptoms else "anomalous system behaviour"
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert IT Site Reliability Engineer (SRE) at a large enterprise. "
                            "Analyze IT incidents concisely and professionally. "
                            "Respond in 2-3 sentences describing the incident intent and business impact."
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Incident Type: {incident_type.replace('_', ' ').title()}\n"
                            f"Observed Symptoms: {symptom_str}\n\n"
                            f"Describe the IT issue intent and its potential business impact."
                        )
                    }
                ],
                temperature=0.3,
                max_tokens=150
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return (
                f"IT incident: {incident_type.replace('_', ' ').title()}. "
                f"Symptoms: {', '.join(symptoms)}."
            )

    def _llm_parse_nl(self, message: str) -> dict:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an IT helpdesk AI. Classify user-reported IT issues. "
                            "Map them to exactly one of these incident types: "
                            "high_cpu, memory_leak, latency_spike, service_down, "
                            "disk_usage_high, process_crash, database_lock, ssl_expiry. "
                            "Also assign severity: P1/P2/P3/P4. "
                            "Respond ONLY as JSON: {\"incident_type\": \"...\", \"severity\": \"...\", \"parsed_intent\": \"...\"}"
                        )
                    },
                    {
                        "role": "user",
                        "content": f"User complaint: \"{message}\""
                    }
                ],
                temperature=0.1,
                max_tokens=100
            )
            import json
            content = response.choices[0].message.content.strip()
            parsed = json.loads(content)
            parsed["original_message"] = message
            return parsed
        except Exception:
            return {
                "incident_type": "service_down",
                "severity": "P2",
                "parsed_intent": f"Parsed from: '{message}'",
                "original_message": message
            }
