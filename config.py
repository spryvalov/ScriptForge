import os


class Config:
    def __init__(self):
        self.jira_url = os.getenv("JIRA_URL", "http://your-jira-domain")
        self.jira_email = os.getenv("JIRA_EMAIL", "")
        self.jira_api_token = os.getenv("JIRA_API_TOKEN", "")
        self.jql_query = os.getenv("JQL_QUERY", "assignee=currentUser()")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")


config = Config()
