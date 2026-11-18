"""
Diagnostics Agent — OpsPilot
Responsible for:
- Running shell/HTTP diagnostic tools (ping, curl, health checks)
- Collecting monitoring data for context grounding
Maps to Proposal Section 5.1.2: Diagnostics Agent
"""

import os
from src.tools.diagnostic_tools import run_full_diagnostic, get_system_metrics
from groq import Groq


class DiagnosticsAgent:
    """
    Diagnostics Agent — Runs real shell/HTTP/system tools and interprets results.
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

    def run_diagnostics(self, incident_type: str, metrics: dict) -> dict:
        """
        Runs diagnostics relevant to the incident type.
        Returns a structured diagnostic report with interpretation.
        """
        # Run real diagnostic tools
        report = run_full_diagnostic(incident_type)

        # Add simulated metrics context
        report["simulated_metrics"] = {
            "cpu_percent": metrics.get("cpu_percent", 0),
            "memory_percent": metrics.get("memory_percent", 0),
            "latency_seconds": metrics.get("latency_seconds", 0),
            "disk_percent": metrics.get("disk_percent", 0),
        }

        # LLM interpretation of diagnostic results
        if self.llm_available:
            report["interpretation"] = self._llm_interpret(incident_type, report)
        else:
            report["interpretation"] = self._rule_based_interpret(incident_type, report)

        return report

    # ── Private Helpers ──────────────────────────────────────────────────────

    def _rule_based_interpret(self, incident_type: str, report: dict) -> str:
        issues = report.get("issues_found", [])
        sim = report.get("simulated_metrics", {})

        lines = []
        if issues:
            lines.append(f"Diagnostic issues found: {'; '.join(issues)}.")
        if sim.get("cpu_percent", 0) > 80:
            lines.append(f"Simulated CPU is elevated at {sim['cpu_percent']:.1f}%.")
        if sim.get("memory_percent", 0) > 85:
            lines.append(f"Simulated memory at {sim['memory_percent']:.1f}%.")
        if sim.get("latency_seconds", 0) > 2:
            lines.append(f"Latency degraded at {sim['latency_seconds']:.2f}s.")
        if not lines:
            lines.append(f"No critical host-level issues detected for {incident_type}. Issue may be application-level.")
        return " ".join(lines)

    def _llm_interpret(self, incident_type: str, report: dict) -> str:
        try:
            import json
            report_summary = {
                "incident_type": incident_type,
                "issues_found": report.get("issues_found", []),
                "system_check": report.get("checks", {}).get("system", {}),
                "simulated_metrics": report.get("simulated_metrics", {}),
                "healthy": report.get("healthy", True)
            }
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a senior SRE analyzing diagnostic results. "
                            "Provide a concise 2-sentence technical interpretation of the diagnostic data. "
                            "Mention specific metrics and whether the system health confirms the incident."
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Diagnostic Report:\n{json.dumps(report_summary, indent=2)}\n\n"
                            f"Interpret these diagnostics for the incident: {incident_type}"
                        )
                    }
                ],
                temperature=0.2,
                max_tokens=150
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return self._rule_based_interpret(incident_type, report)
