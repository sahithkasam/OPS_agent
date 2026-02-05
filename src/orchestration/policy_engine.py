class PolicyEngine:
    def __init__(self):
        # Actions that are always safe to check or run
        self.SAFE_ACTIONS = ["Check Logs", "Ping Service", "Run Diagnostics"]
        
        # Actions that require human approval
        self.APPROVAL_REQUIRED_ACTIONS = [
            "Restart Service", 
            "Scale Resources", 
            "Rollback Deployment", 
            "Clear Cache"
        ]
        
        # Actions that are never allowed by L1/L2 agent
        self.BLOCKED_ACTIONS = ["Delete Database", "Change Firewall Rules", "SSH Access"]

    def check_safety(self, action_name):
        """
        Returns: (status: str, message: str)
        status in ['ALLOWED', 'REQUIRES_APPROVAL', 'BLOCKED']
        """
        normalized = action_name.strip()
        
        # Simple string matching for demo (in production would be strict enum)
        if any(safe in normalized for safe in self.SAFE_ACTIONS):
             return "ALLOWED", "Safe to execute automatically."
             
        if any(req in normalized for req in self.APPROVAL_REQUIRED_ACTIONS):
            return "REQUIRES_APPROVAL", "High-risk action. Human approval mandatory."
            
        if any(blocked in normalized for blocked in self.BLOCKED_ACTIONS):
            return "BLOCKED", "Action violates safety policy. Escalation required."
        
        # Default to caution
        return "REQUIRES_APPROVAL", "Unknown action type. Approval required."
