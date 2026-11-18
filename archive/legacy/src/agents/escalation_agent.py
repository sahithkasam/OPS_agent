"""
Escalation & Guardrail Agent — OpsPilot
Responsible for:
- Escalating to human engineer with full context
- Ensuring safe and compliant actions
- Enforcing policy guardrails (extends PolicyEngine)
Maps to Proposal Section 5.1.2: Escalation & Guardrail Agent
"""

import os
from src.orchestration.policy_engine import PolicyEngine
from groq import Groq


class EscalationAgent:
    """
    Escalation & Guardrail Agent — Safety checks and human escalation logic.
    """

    def __init__(self, slack_notifier=None):
        self.policy = PolicyEngine()
        self.slack = slack_notifier

        api_key = os.getenv("GROQ_API_KEY")
        self.llm_available = bool(api_key)
        self.model = "llama-3.1-70b-versatile"
        if self.llm_available:
            try:
                self.client = Groq(api_key=api_key)
            except Exception:
                self.llm_available = False

    def check_and_gate(self, analysis: dict) -> dict:
        """
        Checks the proposed action against policy guardrails.
        Returns updated analysis with approval gate decision.
        Maps to Proposal: 'Ensures safe and compliant actions'
        """
        action = analysis.get("top_recommendation", "")
        status, reason = self.policy.check_safety(action)

        analysis["policy_status"] = status
        analysis["policy_reason"] = reason

        if status == "BLOCKED":
            analysis["needs_approval"] = True
            analysis["blocked"] = True
            analysis["top_recommendation"] = "Escalate to L3"
            analysis["reasoning"] = (
                f"Action '{action}' is BLOCKED by safety policy. "
                f"Reason: {reason}. Escalating to L3 support."
            )
        elif status == "REQUIRES_APPROVAL":
            analysis["needs_approval"] = True
            analysis["blocked"] = False
        else:  # ALLOWED
            analysis["needs_approval"] = False
            analysis["blocked"] = False

        return analysis

    def escalate_to_human(self, incident_id: str, incident_type: str, analysis: dict, reason: str) -> dict:
        """
        Escalates to human engineer with full context.
        Maps to Proposal: 'Escalates to human engineer with full context'
        """
        context = self._build_escalation_context(incident_id, incident_type, analysis, reason)

        result = {"escalated": True, "context": context}

        # Notify via Slack if available
        if self.slack:
            try:
                escalation_data = {
                    "severity": analysis.get("severity", "P2"),
                    "summary": f"[ESCALATED] {analysis.get('summary', 'Incident requires human intervention')}",
                    "root_cause": analysis.get("root_cause", "Unknown"),
                    "action": f"Reason: {reason}. Please review and take manual action.",
                    "confidence": analysis.get("confidence", 0.0)
                }
                resp = self.slack.post_incident(escalation_data, ticket_id=incident_id)
                result["slack_response"] = resp
            except Exception as e:
                result["slack_error"] = str(e)

        return result

    def generate_escalation_summary(self, incident_id: str, analysis: dict) -> str:
        """
        Uses LLM to generate a clear escalation summary for L3 engineers.
        """
        if self.llm_available:
            return self._llm_escalation_summary(incident_id, analysis)
        return (
            f"Incident {incident_id} requires L3 intervention.\n"
            f"Root Cause: {analysis.get('root_cause', 'Unknown')}\n"
            f"Attempted Action: {analysis.get('top_recommendation', 'N/A')}\n"
            f"Reason for Escalation: AI confidence below threshold or action blocked by policy."
        )

    # ── Private Helpers ──────────────────────────────────────────────────────

    def _build_escalation_context(self, incident_id, incident_type, analysis, reason) -> dict:
        return {
            "incident_id": incident_id,
            "incident_type": incident_type,
            "severity": analysis.get("severity", "P2"),
            "root_cause": analysis.get("root_cause", "Unknown"),
            "proposed_action": analysis.get("top_recommendation", "N/A"),
            "confidence": analysis.get("confidence", 0.0),
            "symptoms": analysis.get("symptoms", []),
            "reasoning": analysis.get("reasoning", ""),
            "evidence": analysis.get("evidence", ""),
            "escalation_reason": reason,
            "policy_status": analysis.get("policy_status", "UNKNOWN")
        }

    def _llm_escalation_summary(self, incident_id: str, analysis: dict) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an IT operations AI. Write a clear, concise escalation summary "
                            "for an L3 human engineer. Include: what happened, what was tried, and what they need to do."
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Incident: {incident_id}\n"
                            f"Root Cause: {analysis.get('root_cause', 'Unknown')}\n"
                            f"Proposed Action: {analysis.get('top_recommendation', 'N/A')}\n"
                            f"AI Confidence: {analysis.get('confidence', 0):.2f}\n"
                            f"Symptoms: {', '.join(analysis.get('symptoms', []))}\n\n"
                            f"Write a 3-sentence escalation summary for L3 engineer."
                        )
                    }
                ],
                temperature=0.2,
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return f"Incident {incident_id} escalated to L3. Review required."
