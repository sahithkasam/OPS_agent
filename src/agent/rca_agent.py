"""
RCA Agent — OpsPilot (Updated with Groq/Llama 3.1)
Now uses the full OpsPilot multi-agent pipeline internally.
Kept for backward compatibility with engine.py.
"""

import os
import json
from src.rag.vector_db import KnowledgeBase

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


class RCAAgent:
    """
    RCA Agent — Root Cause Analysis using Groq/Llama 3.1 + Agentic RAG.
    Backward-compatible interface for engine.py, now powered by the
    full multi-agent OpsPilot Pipeline internally.
    """

    def __init__(self):
        self.kb = KnowledgeBase()
        self.kb.populate('./data/historical_incidents.json')

        # Groq LLM Setup (Llama 3.1 — as specified in proposal)
        api_key = os.getenv("GROQ_API_KEY")
        self.llm_available = GROQ_AVAILABLE and bool(api_key)
        self.model = "llama-3.1-70b-versatile"

        if self.llm_available:
            try:
                self.client = Groq(api_key=api_key)
                print("[RCAAgent] ✅ Groq LLM (Llama 3.1) initialized.")
            except Exception as e:
                print(f"[RCAAgent] ⚠️ Groq init failed: {e}. Falling back to RAG-only mode.")
                self.llm_available = False
        else:
            print("[RCAAgent] ℹ️ No GROQ_API_KEY. Using RAG-only analysis (add key to .env for LLM mode).")

    def analyze_incident(self, metrics_snapshot: dict, recent_logs: dict, incident_id: str = None) -> dict:
        """
        Analyzes an incident using Groq LLM + RAG.
        Returns analysis dict compatible with engine.py.
        """
        # 1. Extract symptoms
        symptoms = self._extract_symptoms(metrics_snapshot, recent_logs)
        query_context = ", ".join(symptoms)

        # 2. RAG retrieval
        rag_results = self.kb.search(query_context, n_results=3)
        hypotheses = self._parse_rag_results(rag_results, query_context)

        # Fallback hypothesis
        if not hypotheses:
            hypotheses.append({
                "root_cause": "Unknown Anomaly",
                "action": "Escalate to L3",
                "confidence": 0.1,
                "reasoning": "No RAG matches found."
            })

        hypotheses.sort(key=lambda x: x["confidence"], reverse=True)
        top = hypotheses[0]

        # 3. LLM-enhanced root cause analysis
        if self.llm_available:
            llm_analysis = self._llm_analyze(symptoms, top, metrics_snapshot, recent_logs)
            root_cause = llm_analysis.get("root_cause", top["root_cause"])
            reasoning = llm_analysis.get("reasoning", top["reasoning"])
            summary = llm_analysis.get("summary", query_context + ".")
            action = llm_analysis.get("action", top["action"])
        else:
            root_cause = top["root_cause"]
            reasoning = top["reasoning"]
            summary = self._build_summary(symptoms, recent_logs)
            action = top["action"]

        # 4. Severity and approval logic
        severity = self._calculate_severity(metrics_snapshot)
        needs_approval = not (top["confidence"] > 0.85 and "Restart" in action)

        return {
            "incident_id": incident_id,
            "hypotheses": hypotheses,
            "top_recommendation": action,
            "action": action,
            "severity": severity,
            "needs_approval": needs_approval,
            "summary": summary,
            "evidence": query_context,
            "root_cause": root_cause,
            "reasoning": reasoning,
            "confidence": top["confidence"],
            "llm_powered": self.llm_available,
        }

    # ── Private Helpers ──────────────────────────────────────────────────────

    def _extract_symptoms(self, metrics: dict, recent_logs: dict) -> list:
        symptoms = []
        if metrics.get("cpu_percent", 0) > 80:
            symptoms.append(f"High CPU ({metrics['cpu_percent']:.1f}%)")
        if metrics.get("memory_percent", 0) > 90:
            symptoms.append(f"High Memory ({metrics['memory_percent']:.1f}%)")
        if metrics.get("latency_seconds", 0) > 2.0:
            symptoms.append(f"High Latency ({metrics['latency_seconds']:.2f}s)")
        error_count = recent_logs.get("recent_errors", 0)
        if error_count > 0:
            symptoms.append(f"{error_count} Errors/sec")
        log_samples = recent_logs.get("log_samples", [])
        for log in log_samples[:2]:
            if "Exception" in log or "ERROR" in log:
                symptoms.append(f"Log: {log[:60]}...")
        return symptoms

    def _parse_rag_results(self, rag_results: dict, query_context: str) -> list:
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
                "reasoning": f"Matches past incident: {meta.get('summary', '')} (conf: {confidence:.2f}). Evidence: {query_context[:80]}..."
            })
        return hypotheses

    def _llm_analyze(self, symptoms: list, top_hyp: dict, metrics: dict, logs: dict) -> dict:
        try:
            symptom_str = ", ".join(symptoms) if symptoms else "anomalous behaviour"
            log_samples = logs.get("log_samples", [])
            log_str = "; ".join(log_samples[:3]) if log_samples else "No recent logs."

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert IT SRE performing root cause analysis. "
                            "Analyze the incident and respond ONLY as JSON with keys: "
                            "root_cause, action, reasoning, summary. "
                            "Keep each field under 80 words. Be specific and technical."
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Symptoms: {symptom_str}\n"
                            f"Recent Logs: {log_str}\n"
                            f"KB Top Match — Root Cause: {top_hyp['root_cause']}, Action: {top_hyp['action']}\n"
                            f"CPU: {metrics.get('cpu_percent', 0):.1f}%, "
                            f"Memory: {metrics.get('memory_percent', 0):.1f}%, "
                            f"Latency: {metrics.get('latency_seconds', 0):.2f}s\n\n"
                            f"Provide enhanced root cause analysis as JSON."
                        )
                    }
                ],
                temperature=0.2,
                max_tokens=350
            )
            content = response.choices[0].message.content.strip()
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(content[start:end])
            return {}
        except Exception as e:
            print(f"[RCAAgent] LLM error: {e}")
            return {}

    def _build_summary(self, symptoms: list, logs: dict) -> str:
        parts = list(symptoms)
        samples = logs.get("log_samples", [])
        if samples:
            parts.append(f"Log samples indicate application errors.")
        return ". ".join(parts) + "." if parts else "Anomaly detected."

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
