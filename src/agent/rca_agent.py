"""
RCA Agent - Root Cause Analysis using RAG + LLM.
"""

from .base_agent import BaseAgent
from .message_bus import AgentMessage, MessageBus, MessageType
from .llm_client import LLMClient
from typing import Optional
from src.rag.vector_db import KnowledgeBase


class RCAAgent(BaseAgent):

    def __init__(self, name: str = "rca", bus=None, llm_client: Optional[LLMClient] = None):
        bus = bus or MessageBus()
        super().__init__(name, bus)
        self.llm = llm_client
        self.kb = KnowledgeBase()
        self.kb.populate('./data/historical_incidents.json')

    def handle_message(self, message: AgentMessage) -> AgentMessage:
        payload = message.payload
        triage_report = payload.get('triage_report', {})
        diagnostic_report = payload.get('diagnostic_report', {})
        symptoms = payload.get('symptoms') or triage_report.get('symptoms', [])
        metrics = payload.get('metrics_snapshot') or triage_report.get('metrics_snapshot', {})
        log_features = payload.get('log_features') or triage_report.get('log_features', {})

        query_context = diagnostic_report.get('query_context') or (
            ", ".join(symptoms) if symptoms else "system anomaly"
        )

        rag_results = self.kb.search(query_context, n_results=3)
        hypotheses = self._parse_rag_results(rag_results, query_context)

        if not hypotheses:
            hypotheses.append({
                "root_cause": "Unknown Anomaly",
                "action": "Escalate to L3",
                "confidence": 0.1,
                "reasoning": "No RAG matches found."
            })

        hypotheses.sort(key=lambda x: x["confidence"], reverse=True)
        top = hypotheses[0]

        root_cause = top["root_cause"]
        action = top["action"]
        reasoning = top["reasoning"]
        summary = query_context

        if self.llm and self.llm.is_active:
            log_samples = log_features.get('log_samples', [])
            result = self.llm.generate_json(
                system_prompt="You are an expert SRE performing root cause analysis. Respond ONLY as JSON with keys: root_cause, action, reasoning, summary. Keep each field under 80 words.",
                user_prompt=(
                    f"Symptoms: {query_context}\n"
                    f"Recent Logs: {'; '.join(log_samples[:3]) if log_samples else 'None'}\n"
                    f"KB Top Match: {top['root_cause']} → {top['action']}\n"
                    f"CPU: {metrics.get('cpu_percent', 0):.1f}%, "
                    f"Memory: {metrics.get('memory_percent', 0):.1f}%, "
                    f"Latency: {metrics.get('latency_seconds', 0):.2f}s"
                )
            )
            if result:
                root_cause = result.get("root_cause", root_cause)
                action = result.get("action", action)
                reasoning = result.get("reasoning", reasoning)
                summary = result.get("summary", summary)

        self.log(f"RCA complete. Top cause: {root_cause[:60]}... confidence={top['confidence']:.2f}")

        return AgentMessage(
            type=MessageType.RCA_RESULT,
            sender=self.name,
            recipient="orchestrator",
            incident_id=message.incident_id,
            payload={
                'hypotheses': hypotheses,
                'top_root_cause': top,
                'root_cause': root_cause,
                'action': action,
                'reasoning': reasoning,
                'summary': summary,
                'confidence': top['confidence'],
                'llm_powered': bool(self.llm and self.llm.is_active),
            },
            parent_message_id=message.id
        )

    def analyze_incident(self, metrics: dict, logs: dict, incident_id: str = "test") -> dict:
        """Direct compatibility wrapper around the message-based RCA flow."""
        symptoms = self._symptoms_from_metrics(metrics, logs)
        message = AgentMessage(
            type=MessageType.RCA_REQUEST,
            sender="test",
            recipient=self.name,
            incident_id=incident_id,
            payload={
                'symptoms': symptoms,
                'metrics_snapshot': metrics,
                'log_features': logs or {},
            }
        )
        result = self.handle_message(message)
        payload = result.payload
        return {
            "incident_id": incident_id,
            "hypotheses": payload.get("hypotheses", []),
            "top_recommendation": payload.get("action", "Escalate to L3"),
            "severity": self._classify_severity(metrics, logs or {}),
            "needs_approval": True,
            "summary": payload.get("summary", ""),
            "rca_report": payload,
        }

    def _parse_rag_results(self, rag_results, query_context):
        hypotheses = []
        if not rag_results or not rag_results.get("documents"):
            return hypotheses
        for i, doc in enumerate(rag_results["documents"][0]):
            meta = rag_results["metadatas"][0][i]
            dist = rag_results["distances"][0][i]
            confidence = round(1.0 / (1.0 + dist), 3)
            hypotheses.append({
                "root_cause": meta.get("root_cause", "Unknown"),
                "action": meta.get("recommended_action", "Escalate"),
                "confidence": confidence,
                "reasoning": f"Matches past incident: {meta.get('summary', '')} (conf: {confidence:.2f})"
            })
        return hypotheses

    def _symptoms_from_metrics(self, metrics: dict, logs: dict) -> list:
        symptoms = []
        cpu = metrics.get('cpu_percent', 0)
        mem = metrics.get('memory_percent', 0)
        lat = metrics.get('latency_seconds', 0)
        if cpu > 80:
            symptoms.append(f"High CPU ({cpu:.1f}%)")
        if mem > 90:
            symptoms.append(f"High Memory ({mem:.1f}%)")
        if lat > 2.0:
            symptoms.append(f"High Latency ({lat:.3f}s)")
        error_count = (logs or {}).get('recent_errors', 0)
        if error_count > 0:
            symptoms.append(f"{error_count} recent errors detected")
        samples = (logs or {}).get('log_samples', [])
        if samples:
            symptoms.extend(samples[:3])
        return symptoms or ["system anomaly"]

    def _classify_severity(self, metrics: dict, logs: dict) -> str:
        cpu = metrics.get('cpu_percent', 0)
        mem = metrics.get('memory_percent', 0)
        lat = metrics.get('latency_seconds', 0)
        errors = logs.get('recent_errors', 0)
        if cpu > 95 or mem > 95 or lat > 5.0 or errors > 5:
            return "P1"
        if cpu > 80 or mem > 90 or lat > 2.0 or errors > 0:
            return "P2"
        return "P3"
