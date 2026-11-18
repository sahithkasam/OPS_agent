"""
LangGraph Pipeline — OpsPilot
Stateful multi-agent orchestration pipeline using LangGraph.
Implements the full Supervisor → Worker agent topology from the proposal.

Flow:
  Incident Detected
       ↓
  SUPERVISOR (intent analysis, severity)
       ↓
  KNOWLEDGE AGENT (Agentic RAG retrieval)
       ↓
  DIAGNOSTICS AGENT (real shell/HTTP tools)
       ↓
  RESOLUTION AGENT (LLM-powered recommendation)
       ↓
  ESCALATION CHECK (guardrails)
       ↓
  [Human Approval Gate]

Maps to Proposal Section 5.1: Multi-Agent Support Architecture
"""

import os
from typing import TypedDict, List, Optional, Any

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("[Pipeline] LangGraph not installed. Run: pip install langgraph")

from src.agents.supervisor_agent import SupervisorAgent
from src.agents.knowledge_agent import KnowledgeAgent
from src.agents.diagnostics_agent import DiagnosticsAgent
from src.agents.resolution_agent import ResolutionAgent
from src.agents.escalation_agent import EscalationAgent


# ─────────────────────────────────────────────
# Shared State Schema (LangGraph)
# ─────────────────────────────────────────────

class IncidentState(TypedDict):
    # Input
    incident_id: str
    incident_type: str
    metrics: dict
    log_features: dict

    # Supervisor outputs
    intent: str
    severity: str
    symptoms: List[str]
    task_plan: List[str]

    # Knowledge Agent outputs
    kb_results: List[dict]

    # Diagnostics Agent outputs
    diagnostic_results: dict

    # Resolution Agent outputs
    root_cause: str
    top_recommendation: str
    recommended_action: str
    action: str
    confidence: float
    needs_approval: bool
    reasoning: str
    summary: str
    hypotheses: List[dict]
    evidence: str

    # Escalation / Guardrail outputs
    policy_status: str
    policy_reason: str
    blocked: bool


# ─────────────────────────────────────────────
# Node Functions (called by LangGraph)
# ─────────────────────────────────────────────

def supervisor_node(state: IncidentState) -> dict:
    """Node 1: Supervisor — Interprets intent and plans tasks."""
    agent = SupervisorAgent()
    result = agent.analyze_intent(
        state["incident_type"],
        state["metrics"],
        state["log_features"]
    )
    return {
        "intent": result.get("intent", ""),
        "severity": result.get("severity", "P2"),
        "symptoms": result.get("symptoms", []),
        "task_plan": result.get("task_plan", [])
    }


def knowledge_node(state: IncidentState) -> dict:
    """Node 2: Knowledge Agent — Agentic RAG retrieval from KB."""
    agent = KnowledgeAgent()
    results = agent.retrieve(
        symptoms=state.get("symptoms", []),
        incident_type=state.get("incident_type", ""),
        n_results=3
    )
    return {"kb_results": results}


def diagnostics_node(state: IncidentState) -> dict:
    """Node 3: Diagnostics Agent — Runs real shell/HTTP/system tools."""
    agent = DiagnosticsAgent()
    results = agent.run_diagnostics(
        incident_type=state.get("incident_type", ""),
        metrics=state.get("metrics", {})
    )
    return {"diagnostic_results": results}


def resolution_node(state: IncidentState) -> dict:
    """Node 4: Resolution Agent — LLM-powered action recommendation."""
    agent = ResolutionAgent()
    result = agent.recommend(
        symptoms=state.get("symptoms", []),
        kb_results=state.get("kb_results", []),
        diagnostic_results=state.get("diagnostic_results", {}),
        incident_type=state.get("incident_type", "")
    )
    return result


def escalation_node(state: IncidentState) -> dict:
    """Node 5: Escalation & Guardrail Agent — Policy check."""
    agent = EscalationAgent()
    analysis = dict(state)
    updated = agent.check_and_gate(analysis)
    return {
        "policy_status": updated.get("policy_status", "REQUIRES_APPROVAL"),
        "policy_reason": updated.get("policy_reason", ""),
        "needs_approval": updated.get("needs_approval", True),
        "blocked": updated.get("blocked", False),
        "top_recommendation": updated.get("top_recommendation", state.get("top_recommendation", "")),
        "reasoning": updated.get("reasoning", state.get("reasoning", ""))
    }


# ─────────────────────────────────────────────
# Pipeline Class
# ─────────────────────────────────────────────

class OpsPilotPipeline:
    """
    OpsPilot Multi-Agent Pipeline using LangGraph stateful loops.
    Implements the hierarchical Supervisor–Worker agent topology.
    Maps to Proposal Section 5.1.
    """

    def __init__(self):
        self._graph = None
        if LANGGRAPH_AVAILABLE:
            self._graph = self._build_graph()
        else:
            print("[Pipeline] Running in fallback mode (LangGraph unavailable).")

    def _build_graph(self):
        """Builds the LangGraph StateGraph."""
        workflow = StateGraph(IncidentState)

        # Register nodes
        workflow.add_node("supervisor", supervisor_node)
        workflow.add_node("knowledge", knowledge_node)
        workflow.add_node("diagnostics", diagnostics_node)
        workflow.add_node("resolution", resolution_node)
        workflow.add_node("escalation", escalation_node)

        # Define edges (pipeline flow)
        workflow.set_entry_point("supervisor")
        workflow.add_edge("supervisor", "knowledge")
        workflow.add_edge("knowledge", "diagnostics")
        workflow.add_edge("diagnostics", "resolution")
        workflow.add_edge("resolution", "escalation")
        workflow.add_edge("escalation", END)

        return workflow.compile()

    def run(
        self,
        incident_id: str,
        incident_type: str,
        metrics: dict,
        log_features: dict
    ) -> dict:
        """
        Runs the full multi-agent pipeline for an incident.
        Returns analysis dict compatible with engine.py expectations.
        """
        initial_state: IncidentState = {
            "incident_id": incident_id,
            "incident_type": incident_type,
            "metrics": metrics,
            "log_features": log_features,
            # Pre-filled defaults (agents will fill their fields)
            "intent": "",
            "severity": "P2",
            "symptoms": [],
            "task_plan": [],
            "kb_results": [],
            "diagnostic_results": {},
            "root_cause": "",
            "top_recommendation": "",
            "recommended_action": "",
            "action": "",
            "confidence": 0.0,
            "needs_approval": True,
            "reasoning": "",
            "summary": "",
            "hypotheses": [],
            "evidence": "",
            "policy_status": "",
            "policy_reason": "",
            "blocked": False,
        }

        if self._graph:
            try:
                result = self._graph.invoke(initial_state)
            except Exception as e:
                print(f"[Pipeline] LangGraph execution error: {e}. Running fallback.")
                result = self._run_fallback(initial_state)
        else:
            result = self._run_fallback(initial_state)

        # Return dict matching engine.py's expected analysis format
        return {
            "incident_id": incident_id,
            "severity": result.get("severity", "P2"),
            "summary": result.get("summary", ""),
            "root_cause": result.get("root_cause", ""),
            "action": result.get("action") or result.get("recommended_action") or result.get("top_recommendation", "Escalate to L3"),
            "top_recommendation": result.get("top_recommendation") or result.get("action", "Escalate to L3"),
            "confidence": result.get("confidence", 0.3),
            "needs_approval": result.get("needs_approval", True),
            "hypotheses": result.get("hypotheses", []),
            "evidence": result.get("evidence", ""),
            "reasoning": result.get("reasoning", ""),
            "intent": result.get("intent", ""),
            "symptoms": result.get("symptoms", []),
            "diagnostic_results": result.get("diagnostic_results", {}),
            "policy_status": result.get("policy_status", "REQUIRES_APPROVAL"),
        }

    def _run_fallback(self, state: dict) -> dict:
        """
        Sequential fallback when LangGraph is unavailable.
        Runs agents in order directly.
        """
        print("[Pipeline] Running sequential fallback pipeline...")

        # Step 1: Supervisor
        s_result = supervisor_node(state)
        state.update(s_result)

        # Step 2: Knowledge
        k_result = knowledge_node(state)
        state.update(k_result)

        # Step 3: Diagnostics
        d_result = diagnostics_node(state)
        state.update(d_result)

        # Step 4: Resolution
        r_result = resolution_node(state)
        state.update(r_result)

        # Step 5: Escalation
        e_result = escalation_node(state)
        state.update(e_result)

        return state
