"""
Resolution Agent — OpsPilot
Responsible for:
- Executing resolutions: restart services, enable access, reset passwords, etc.
- Invoking APIs or CLI tools safely
- Recommending corrective actions based on full context
Maps to Proposal Section 5.1.2: Resolution/Action Agent
"""

import os
from groq import Groq


class ResolutionAgent:
    """
    Resolution Agent — Proposes and describes corrective actions using LLM reasoning.
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

    def recommend(
        self,
        symptoms: list,
        kb_results: list,
        diagnostic_results: dict,
        incident_type: str
    ) -> dict:
        """
        Produces the final action recommendation by synthesizing:
        - KB/RAG results (historical resolutions)
        - Diagnostic tool results
        - Symptom context
        Returns a structured recommendation matching the engine's expected format.
        """
        # Best KB match
        top_kb = kb_results[0] if kb_results else None
        top_action = top_kb["action"] if top_kb else self._default_action(incident_type)
        top_confidence = top_kb["confidence"] if top_kb else 0.3
        top_root_cause = top_kb["root_cause"] if top_kb else self._default_root_cause(incident_type)

        # Build hypotheses list from KB results
        hypotheses = []
        for h in kb_results[:3]:
            hypotheses.append({
                "root_cause": h.get("root_cause", "Unknown"),
                "action": h.get("action", "Escalate"),
                "confidence": h.get("confidence", 0.3),
                "reasoning": h.get("reasoning", "Matched from knowledge base.")
            })
        if not hypotheses:
            hypotheses.append({
                "root_cause": top_root_cause,
                "action": top_action,
                "confidence": 0.3,
                "reasoning": "No KB matches. Using rule-based fallback."
            })

        # Generate LLM reasoning if available
        if self.llm_available:
            llm_result = self._llm_recommend(
                symptoms, top_root_cause, top_action,
                diagnostic_results, incident_type
            )
            root_cause = llm_result.get("root_cause", top_root_cause)
            reasoning = llm_result.get("reasoning", "")
            summary = llm_result.get("summary", "")
            action = llm_result.get("action", top_action)
        else:
            root_cause = top_root_cause
            action = top_action
            symptom_str = ", ".join(symptoms) if symptoms else "anomalous behaviour"
            reasoning = (
                f"Based on {len(kb_results)} KB matches, the most likely root cause is '{root_cause}'. "
                f"Recommended action: {action}."
            )
            summary = f"{symptom_str}."

        # Needs approval check (based on policy)
        needs_approval = not (top_confidence > 0.85 and "Restart" in action)

        return {
            "root_cause": root_cause,
            "top_recommendation": action,
            "recommended_action": action,
            "action": action,
            "confidence": top_confidence,
            "needs_approval": needs_approval,
            "reasoning": reasoning,
            "summary": summary,
            "hypotheses": hypotheses,
            "evidence": diagnostic_results.get("interpretation", "Diagnostic data collected."),
        }

    # ── Private Helpers ──────────────────────────────────────────────────────

    def _llm_recommend(
        self,
        symptoms: list,
        root_cause: str,
        action: str,
        diagnostic_results: dict,
        incident_type: str
    ) -> dict:
        try:
            symptom_str = ", ".join(symptoms) if symptoms else "unknown symptoms"
            diag_summary = diagnostic_results.get("interpretation", "No diagnostic data.")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert SRE providing IT incident resolution recommendations. "
                            "Be concise, technical, and actionable. "
                            "Respond ONLY as JSON with keys: root_cause, action, reasoning, summary. "
                            "Keep each value under 100 words."
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Incident: {incident_type.replace('_', ' ').title()}\n"
                            f"Symptoms: {symptom_str}\n"
                            f"KB Root Cause: {root_cause}\n"
                            f"KB Suggested Action: {action}\n"
                            f"Diagnostic Findings: {diag_summary}\n\n"
                            f"Provide final root cause analysis and recommended action as JSON."
                        )
                    }
                ],
                temperature=0.2,
                max_tokens=300
            )
            import json
            content = response.choices[0].message.content.strip()
            # Sanitize: extract JSON even if LLM adds explanation
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(content[start:end])
            return {}
        except Exception:
            return {}

    def _default_action(self, incident_type: str) -> str:
        defaults = {
            "high_cpu": "Scale Resources",
            "memory_leak": "Restart Service",
            "latency_spike": "Clear Cache",
            "service_down": "Restart Service",
            "disk_usage_high": "Clear Disk Space",
            "process_crash": "Restart Service",
            "database_lock": "Terminate Blocking Query",
            "ssl_expiry": "Renew SSL Certificate"
        }
        return defaults.get(incident_type, "Escalate to L3")

    def _default_root_cause(self, incident_type: str) -> str:
        defaults = {
            "high_cpu": "Excessive CPU consumption by application process.",
            "memory_leak": "Memory not released after object lifecycle — heap exhaustion.",
            "latency_spike": "Network congestion or slow downstream dependency.",
            "service_down": "Process crashed or failed to bind to port.",
            "disk_usage_high": "Log files or artifacts filling up disk partition.",
            "process_crash": "Worker process terminated unexpectedly (OOM or exception).",
            "database_lock": "Deadlock between concurrent database transactions.",
            "ssl_expiry": "TLS certificate reached expiry date."
        }
        return defaults.get(incident_type, "Unknown root cause. Manual investigation required.")
