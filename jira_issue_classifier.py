import os
import logging
from jira import JIRA
import openai
from constants import POSSIBLE_DOMAINS, TECHNOLOGIES
from config import config

logging.basicConfig(level=logging.INFO)


# Initialize APIs
jira = JIRA(server=config.jira_url, options={"server": config.jira_url}, token_auth=config.jira_api_token)
client = openai.OpenAI(api_key=config.openai_api_key)


def execute_safe_call(api_function, *args, **kwargs):
    try:
        return api_function(*args, **kwargs)
    except Exception as e:
        logging.error(f"API call failed: {e}")
        return None


def fetch_all_issues(jql_query, jira_client):
    issues = []
    start_at = 0
    max_results = 50
    while True:
        batch = execute_safe_call(jira_client.search_issues, jql_query, startAt=start_at, maxResults=max_results,
                                  fields="key")
        if not batch:
            break
        issues.extend(batch)
        start_at += max_results
        if len(batch) < max_results:
            break
    return [issue.key for issue in issues]


def process_issue(issue_key, jira_client, domains, technologies):
    try:
        issue = jira_client.issue(issue_key)
        summary, description = issue.fields.summary, issue.fields.description or "No description available"
        logging.info(f"Processing Jira Task: {issue_key}")

        # Classify domain and technology
        domains, technologies = classify_task(summary, description, domains, technologies)
        logging.info(f"Classified Domains: {domains}, Technologies: {technologies}")

        # Add tags to Jira
        update_jira_labels(issue_key, domains + technologies, POSSIBLE_DOMAINS + TECHNOLOGIES)
        logging.info(f"Tags added to Jira issue {issue_key}: {domains + technologies}")
    except Exception as e:
        logging.error(f"Failed to process issue {issue_key}: {e}")


def classify_task(summary, description, domains, technologies):
    prompt = f"""
    Based on the following task details, determine:
    1. The most suitable domain(s) (up to 2) from this list: {", ".join(domains)}.
    2. The most suitable technology(s) (up to 2) from this list: {", ".join(technologies)}.

    Task Summary: {summary}
    Task Description: {description}

    Respond in this format:
    Domains: <semicolon-separated list of domains>
    Technologies: <semicolon-separated list of technologies>
    """

    response = execute_safe_call(client.chat.completions.create, model="gpt-3.5-turbo", messages=[
        {"role": "system", "content": "You are an assistant for domain and technology classification."},
        {"role": "user", "content": prompt}
    ], max_tokens=200, temperature=0.2)

    if not response:
        return [], []

    # Parse the response
    try:
        result = response.choices[0].message.content
        domains_line = result.split("\n")[0].replace("Domains: ", "").strip()
        technologies_line = result.split("\n")[1].replace("Technologies: ", "").strip()
        return [d.strip() for d in domains_line.split(";")], [t.strip() for t in technologies_line.split(";")]
    except Exception as e:
        logging.error(f"Error parsing OpenAI response: {e}")
        return [], []


def update_jira_labels(issue_key, new_tags, possible_tags):
    issue = jira.issue(issue_key)
    current_labels = issue.fields.labels
    # Remove tags set previously by this exact script
    filtered_labels = [label for label in current_labels if label not in possible_tags]
    updated_labels = list(set(filtered_labels + new_tags))
    issue.update(fields={"labels": updated_labels})


def main():
    try:
        issue_keys = fetch_all_issues(config.jql_query, jira)
        logging.info(f"Found {len(issue_keys)} tasks to process.")
        for issue_key in issue_keys:
            process_issue(issue_key, jira, POSSIBLE_DOMAINS, TECHNOLOGIES)
    except Exception as e:
        logging.error(f"Main execution failed: {e}")


if __name__ == "__main__":
    main()
