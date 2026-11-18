"""
Knowledge Retrieval Agent — OpsPilot
Responsible for:
- Searching KB/SOPs and historical tickets using Agentic RAG
- Dynamically mapping SOPs to detected issue types
- Multi-hop retrieval for multi-step diagnostics
Maps to Proposal Section 5.1.2 & Section 6: Agentic RAG
"""

import os
from src.rag.vector_db import KnowledgeBase
from groq import Groq


class KnowledgeAgent:
    """
    Knowledge Retrieval Agent — Agentic RAG-powered KB lookup.
    Unlike traditional RAG, retrieval is driven by agent goals, not just queries.
    """

    KB_PATH = "./data/historical_incidents.json"

    def __init__(self):
        self.kb = KnowledgeBase()
        self.kb.populate(self.KB_PATH)

        api_key = os.getenv("GROQ_API_KEY")
        self.llm_available = bool(api_key)
        self.model = "llama-3.1-70b-versatile"
        if self.llm_available:
            try:
                self.client = Groq(api_key=api_key)
            except Exception:
                self.llm_available = False

    def retrieve(self, symptoms: list, incident_type: str = "", n_results: int = 3) -> list:
        """
        Agentic RAG retrieval: searches KB using symptom context.
        Returns list of ranked hypotheses with root causes and actions.
        """
        # Build rich query from symptoms (agentic goal-driven retrieval)
        query = self._build_goal_driven_query(symptoms, incident_type)

        raw_results = self.kb.search(query, n_results=n_results)
        hypotheses = self._parse_results(raw_results)

        # Multi-hop: if confidence is low, retry with refined query
        if hypotheses and hypotheses[0]["confidence"] < 0.4:
            refined = self._refine_query(symptoms, incident_type, hypotheses)
            retry_results = self.kb.search(refined, n_results=n_results)
            retry_hypotheses = self._parse_results(retry_results)
            # Merge and deduplicate
            seen = {h["root_cause"] for h in hypotheses}
            for h in retry_hypotheses:
                if h["root_cause"] not in seen:
                    hypotheses.append(h)

        hypotheses.sort(key=lambda x: x["confidence"], reverse=True)

        # LLM-enhanced reasoning on top results
        if self.llm_available and hypotheses:
            hypotheses = self._llm_enrich(hypotheses[:3], symptoms, incident_type)

        return hypotheses

    def get_sop(self, incident_type: str) -> str:
        """
        Returns an SOP (Standard Operating Procedure) for the given incident type.
        Uses LLM to generate if not found in KB.
        """
        sop_map = {
            "high_cpu": "1. Identify top CPU-consuming processes. 2. Check for runaway loops. 3. Scale horizontally or restart offending service. 4. Set CPU alerts at 80%.",
            "memory_leak": "1. Take heap dump. 2. Identify memory hogs. 3. Restart affected pods/services. 4. Add memory limit policies.",
            "latency_spike": "1. Check network routes. 2. Inspect DNS resolution times. 3. Flush service caches. 4. Reroute traffic via secondary region.",
            "service_down": "1. Run health check on service endpoints. 2. Check process list. 3. Inspect recent deployment logs. 4. Restart service. 5. Verify health check passes.",
            "disk_usage_high": "1. Find largest files/directories. 2. Archive old logs to object storage. 3. Clear temp directories. 4. Set disk usage alerts.",
            "process_crash": "1. Check process exit code and coredump. 2. Inspect OOM killer logs. 3. Restart worker pool. 4. Add liveness probes.",
            "database_lock": "1. Query pg_locks / information_schema. 2. Identify blocking transaction. 3. Kill blocking query. 4. Optimize slow queries.",
            "ssl_expiry": "1. Check certificate expiry date. 2. Renew via Let's Encrypt / cert manager. 3. Deploy new cert. 4. Reload web server. 5. Set auto-renewal."
        }
        if incident_type in sop_map:
            return sop_map[incident_type]
        if self.llm_available:
            return self._llm_generate_sop(incident_type)
        return "No SOP found. Escalate to L2 support."

    # ── Private Helpers ──────────────────────────────────────────────────────

    def _build_goal_driven_query(self, symptoms: list, incident_type: str) -> str:
        """
        Builds a rich, goal-driven query for RAG retrieval.
        Agentic RAG: retrieval driven by agent goals, not just keywords.
        """
        base = ", ".join(symptoms) if symptoms else incident_type.replace("_", " ")
        goal = f"Find resolution for: {incident_type.replace('_', ' ')}. Symptoms: {base}."
        return goal

    def _refine_query(self, symptoms: list, incident_type: str, prev_hypotheses: list) -> str:
        """Multi-hop: creates a refined query based on initial low-confidence results."""
        prev_causes = [h["root_cause"] for h in prev_hypotheses[:2]]
        refined = (
            f"{incident_type.replace('_', ' ')} "
            f"excluding: {', '.join(prev_causes)}. "
            f"Symptoms: {', '.join(symptoms)}"
        )
        return refined

    def _parse_results(self, raw_results: dict) -> list:
        hypotheses = []
        if not raw_results or not raw_results.get("documents"):
            return hypotheses
        for i, doc in enumerate(raw_results["documents"][0]):
            meta = raw_results["metadatas"][0][i]
            dist = raw_results["distances"][0][i]
            confidence = round(1.0 / (1.0 + dist), 3)
            hypotheses.append({
                "root_cause": meta.get("root_cause", "Unknown"),
                "action": meta.get("recommended_action", "Escalate"),
                "confidence": confidence,
                "summary": meta.get("summary", ""),
                "source": "KB",
                "reasoning": f"Similar past incident: {meta.get('summary', '')} (conf: {confidence:.2f})"
            })
        return hypotheses

    def _llm_enrich(self, hypotheses: list, symptoms: list, incident_type: str) -> list:
        """Uses LLM to enrich hypothesis reasoning with deeper analysis."""
        try:
            hyp_text = "\n".join(
                [f"- Root Cause: {h['root_cause']}, Action: {h['action']}" for h in hypotheses]
            )
            symptom_str = ", ".join(symptoms)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert SRE. Given IT incident symptoms and KB-retrieved hypotheses, "
                            "provide enhanced reasoning for each hypothesis in one sentence each. "
                            "Be technical and specific."
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Incident: {incident_type}\nSymptoms: {symptom_str}\n\n"
                            f"KB Hypotheses:\n{hyp_text}\n\n"
                            f"Enhance the reasoning for each hypothesis (one line each, same order):"
                        )
                    }
                ],
                temperature=0.2,
                max_tokens=300
            )
            lines = response.choices[0].message.content.strip().split("\n")
            lines = [l.strip("- ").strip() for l in lines if l.strip()]
            for i, h in enumerate(hypotheses):
                if i < len(lines):
                    h["reasoning"] = lines[i]
            return hypotheses
        except Exception:
            return hypotheses

    def _llm_generate_sop(self, incident_type: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an IT SRE expert. Generate a concise SOP (Standard Operating Procedure) as numbered steps."
                    },
                    {
                        "role": "user",
                        "content": f"Generate a 4-step SOP for resolving: {incident_type.replace('_', ' ')}"
                    }
                ],
                temperature=0.2,
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return "Escalate to L2 support for manual investigation."
