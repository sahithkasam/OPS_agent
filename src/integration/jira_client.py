import random


class JiraConnector:
    """Jira REST adapter, or an in-memory mock.

    The connection (and the import of the `jira` package) happens on first
    use, not at startup, so a cold start doesn't wait on a network call to
    Atlassian. If connecting fails, the connector falls back to mock mode.
    """

    def __init__(self, url=None, username=None, token=None, project_key="OPS", mock=True):
        self.project_key = project_key
        self.tickets = {}  # In-memory store for mock
        self.client = None
        self._url, self._username, self._token = url, username, token
        self._connected = False
        # Real mode only if asked for and fully configured.
        self.mock = mock or not (url and username and token)

    def _ensure_client(self):
        """Connect once, on first use. Returns True when the real client is usable."""
        if self.mock:
            return False
        if not self._connected:
            self._connected = True
            try:
                from jira import JIRA
            except ImportError:
                print("Jira library not installed. Falling back to mock.")
                self.mock = True
                return False
            try:
                self.client = JIRA(server=self._url, basic_auth=(self._username, self._token))
                print(f"Connected to Jira: {self._url}")
            except Exception as e:
                print(f"Failed to connect to Jira: {e}")
                self.mock = True
                return False
        return self.client is not None

    def create_ticket(self, incident_data):
        """
        Creates a new Jira ticket.
        """
        summary = incident_data.get('summary')
        description = incident_data.get('root_cause')
        priority = incident_data.get('severity', 'Medium') # Map P1/P2 to Jira Priority if needed
        
        if self._ensure_client():
            try:
                issue_dict = {
                    'project': {'key': self.project_key},
                    'summary': summary,
                    'description': description,
                    'issuetype': {'name': 'Task'},
                }
                new_issue = self.client.create_issue(fields=issue_dict)
                return new_issue.key
            except Exception as e:
                print(f"[Jira Error] Create failed: {e}")
                return f"ERROR: {str(e)}"
        
        # Mock Logic
        ticket_id = f"{self.project_key}-{random.randint(1000, 9999)}"
        ticket = {
            "id": ticket_id,
            "summary": summary,
            "description": description,
            "severity": priority,
            "status": "OPEN",
            "assignee": "L1 Agent"
        }
        self.tickets[ticket_id] = ticket
        print(f"[Jira Mock] Created Ticket {ticket_id}: {summary}")
        return ticket_id

    def update_status(self, ticket_id, status, comment=None):
        if self._ensure_client():
            try:
                # Add comment
                if comment:
                    self.client.add_comment(ticket_id, comment)
                
                # Transitioning status is complex in Jira (needs transition ID).
                # For this simplified agent, we might just add a comment properly.
                # Attempting reasonable transition names:
                # Attempting reasonable transition names:
                transitions = self.client.transitions(ticket_id)
                trans_name_map = {t['name'].lower(): t['id'] for t in transitions}
                print(f"[Jira] Available transitions for {ticket_id}: {list(trans_name_map.keys())}")
                
                target_trans = None
                if status == "RESOLVED":
                    target_trans = trans_name_map.get('done') or trans_name_map.get('resolve') or trans_name_map.get('closed')
                elif status == "ESCALATED":
                    # Try to find an 'Escalate' workflow, otherwise 'In Progress' with High Priority
                    target_trans = trans_name_map.get('escalate') or trans_name_map.get('in progress') or trans_name_map.get('to do')
                
                if target_trans:
                    self.client.transition_issue(ticket_id, target_trans)
                    print(f"[Jira] Transitioned {ticket_id} via ID {target_trans}")
                    return True
                else:
                    print(f"[Jira] No matching transition found for {status}. Comment added only.")
                    return True # Comment added at least
            except Exception as e:
                print(f"[Jira Error] Update failed: {e}")
                return False

        # Mock Logic
        if ticket_id in self.tickets:
            self.tickets[ticket_id]['status'] = status
            print(f"[Jira Mock] Ticket {ticket_id} updated to {status}. Comment: {comment}")
            return True
        return False
        
    def get_ticket_status(self, ticket_id):
        """
        Retrieves the status of a Jira ticket.
        """
        if self._ensure_client():
            try:
                issue = self.client.issue(ticket_id)
                return issue.fields.status.name
            except Exception as e:
                print(f"[Jira Error] Get status failed: {e}")
                return None
                
        # Mock Logic
        if ticket_id in self.tickets:
            return self.tickets[ticket_id]['status']
        return "OPEN"
