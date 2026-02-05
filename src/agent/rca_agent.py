import json
from src.rag.vector_db import KnowledgeBase

class RCAAgent:
    def __init__(self):
        self.kb = KnowledgeBase()
        self.kb.populate('./data/historical_incidents.json')
        # Placeholder for real LLM client (OpenAI/Ollama)
        # For this demo, we can simulate the LLM response if no key is provided, 
        # but the structure will be ready for real integration.
        self.mock_mode = True 

    def analyze_incident(self, metrics_snapshot, recent_logs):
        """
        Main entry point for the agent.
        1. Construct context from metrics + logs.
        2. Query Vector DB for similar past incidents.
        3. (Mock) Generate LLM response based on inputs.
        """
        # 1. Summarize current situation
        symptoms = []
        if metrics_snapshot['cpu_percent'] > 80: symptoms.append("High CPU")
        if metrics_snapshot['memory_percent'] > 90: symptoms.append("High Memory")
        if metrics_snapshot['latency_seconds'] > 2.0: symptoms.append("High Latency")
        
        error_logs = [l for l in recent_logs if l['level'] in ['ERROR', 'CRITICAL']]
        if error_logs:
            symptoms.append(f"{len(error_logs)} Error Logs Found")
            # Extract unique error messages logic simplified
            uniq_errs = list(set([l['message'] for l in error_logs]))
            symptoms.extend(uniq_errs[:2]) # Top 2 errors

        query_context = ", ".join(symptoms)
        
        # 2. Retrieve RAG context
        rag_results = self.kb.search(query_context, n_results=1)
        
        # Defaults
        past_incident = "No similar history found."
        params = {}
        distance = 1.0 # Default high distance (low confidence)
        
        if rag_results and rag_results['documents'] and len(rag_results['documents'][0]) > 0:
             past_incident = rag_results['documents'][0][0]
             params = rag_results['metadatas'][0][0]
             if 'distances' in rag_results and rag_results['distances'][0]:
                 distance = rag_results['distances'][0][0]

        # 3. Dynamic Analysis based on RAG
        # Calculate Confidence: Using inverse distance (Closer = Higher Confidence)
        # ChromaDB Cosine distance: 0 = exact match, 1 = orthogonal, 2 = opposite.
        # Simple heuristic: confidence = 1 / (1 + distance)
        confidence = 1.0 / (1.0 + distance)
        
        # Extract Knowledge from Historical Match
        matched_action = params.get('recommended_action', 'Escalate to L3')
        matched_cause = params.get('root_cause', 'Unknown Anomaly')
        matched_severity = params.get('severity', 'P2')
        matched_summary = params.get('summary', 'Unknown Incident')

        analysis_text = f"**Observation**: System is experiencing {', '.join(symptoms)}.\n"
        analysis_text += f"**Context**: The symptoms are chemically similar (Distance: {distance:.2f}) to historic incident: *'{matched_summary}'*.\n"
        analysis_text += f"**Inference**: Based on historical resolution patterns, this matches the signature of *{matched_cause}*."

        # Decision Logic
        recommendation = matched_action
        root_cause = matched_cause
        severity = matched_severity
        escalation_reason = None

        # Policy: If confidence is low, strictly escalate
        if confidence < 0.65:
            recommendation = "Escalate to L3"
            escalation_reason = f"Low confidence ({confidence:.2f}) in diagnosis. Signature does not strongly match known incidents."
            severity = "P2"
            root_cause = "Ambiguous Anomaly Signature"
        
        # Override for 'Service Down' - heuristic override is still useful for critical safety
        if "Service Unavailable" in str(symptoms) and confidence < 0.9:
             # Safety net: If service is down, we usually always want to restart unless we are sure.
             # But for pure RAG demo, let's trust the RAG if it finds the Service Down incident.
             pass

        return {
            "summary": f"Detected {', '.join(symptoms)}",
            "root_cause": root_cause,
            "analysis": analysis_text,
            "recommended_action": recommendation,
            "rag_context": past_incident,
            "severity": severity,
            "confidence": confidence,
            "escalation_reason": escalation_reason
        }
