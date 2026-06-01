"""
RCA Agent - Root Cause Analysis using RAG + LLM.
"""

from .base_agent import BaseAgent
from .message_bus import AgentMessage, MessageType
from .llm_client import LLMClient
from typing import Optional
from src.rag.vector_db import KnowledgeBase


class RCAAgent(BaseAgent):

    def __init__(self, name: str, bus, llm_client: Optional[LLMClient] = None):
        super().__init__(name, bus)
        self.llm = llm_client
        self.kb = KnowledgeBase()
        self.kb.populate('./data/historical_incidents.json')

    def handle_message(self, message: AgentMessage) -> AgentMessage:
        payload = message.payload
        symptoms = payload.get('symptoms', [])
        metrics = payload.get('metrics_snapshot', {})
        log_features = payload.get('log_features', {})

        query_context = ", ".join(symptoms) if symptoms else "system anomaly"

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
