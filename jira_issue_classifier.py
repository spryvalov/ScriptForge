import logging
from typing import Callable, TypeVar, Any, Optional, List, Tuple, cast

import openai
import typer
from jira import JIRA, Issue

from constants import POSSIBLE_DOMAINS, TECHNOLOGIES

logging.basicConfig(level=logging.INFO)

app = typer.Typer()
ReturnType = TypeVar('ReturnType')


@app.command()
def main(
        jira_url: str = typer.Option(..., help="Jira URL (e.g., https://your-jira-instance.atlassian.net)"),
        jira_api_token: str = typer.Option(..., help="Jira API token for authentication"),
        openai_api_key: str = typer.Option(..., help="OpenAI API key"),
        jql_query: str = typer.Argument(..., help="JQL query to fetch issues")) -> None:
    try:
        jira = JIRA(server=jira_url, options={"server": jira_url}, token_auth=jira_api_token)
        client = openai.OpenAI(api_key=openai_api_key)
        issue_keys = fetch_all_issues(jql_query, jira)
        logging.info(f"Found {len(issue_keys)} tasks to process.")
        for issue_key in issue_keys:
            process_issue(client, jira, issue_key)
    except Exception as e:
        logging.error(f"Main execution failed: {e}")


def process_issue(client: openai.OpenAI, jira: JIRA, issue_key: str) -> None:
    try:
        issue = jira.issue(issue_key)
        summary, description = issue.fields.summary, issue.fields.description or "No description available"
        logging.info(f"Processing Jira Task: {issue_key}")

        # Classify domain and technology
        domains, technologies = classify_task(client, summary, description)
        logging.info(f"Classified Domains: {domains}, Technologies: {technologies}")

        # Add tags to Jira
        update_jira_labels(jira, issue_key, domains + technologies, POSSIBLE_DOMAINS + TECHNOLOGIES)
        logging.info(f"Tags added to Jira issue {issue_key}: {domains + technologies}")
    except Exception as e:
        logging.error(f"Failed to process issue {issue_key}: {e}")


def classify_task(client: openai.OpenAI, summary: str, description: str) -> Tuple[List[str], List[str]]:
    prompt = f"""
    Based on the following task details, determine:
    1. The most suitable domain(s) (up to 2) from this list: {", ".join(POSSIBLE_DOMAINS)}.
    2. The most suitable technology(s) (up to 2) from this list: {", ".join(TECHNOLOGIES)}.

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
        domains_line = (result or "").split("\n")[0].replace("Domains: ", "").strip()
        technologies_line = (result or "").split("\n")[1].replace("Technologies: ", "").strip()
        domains = [d.strip() for d in domains_line.split(";")]
        technologies = [t.strip() for t in technologies_line.split(";")]
        # Filter possible domains and technologies to avoid hallucinations
        return [d for d in domains if d in POSSIBLE_DOMAINS], [t for t in technologies if t in TECHNOLOGIES]
    except Exception as e:
        logging.error(f"Error parsing OpenAI response: {e}")
        return [], []


def execute_safe_call(api_function: Callable[..., ReturnType], *args: Any, **kwargs: Any) -> Optional[ReturnType]:
    try:
        return api_function(*args, **kwargs)
    except Exception as e:
        logging.error(f"API call failed: {e}")
        return None


def fetch_all_issues(jql_query: str, jira: JIRA) -> List[str]:
    issues: List[Issue] = []
    start_at = 0
    max_results = 50
    while True:
        batch: Optional[List[Issue]] = cast(Optional[List[Issue]], jira.search_issues(jql_query, startAt=start_at, maxResults=max_results, fields="key"))
        if not batch:
            break
        issues.extend(batch)
        start_at += max_results
        if len(batch) < max_results:
            break
    return [issue.key for issue in issues]


def update_jira_labels(jira: JIRA, issue_key: str, new_tags: List[str], tags_to_clear: List[str]) -> None:
    issue = jira.issue(issue_key)
    current_labels = issue.fields.labels
    # Remove tags set previously by this exact script
    filtered_labels = [label for label in current_labels if label not in tags_to_clear]
    updated_labels = list(set(filtered_labels + new_tags))
    if issue.fields.status.name.lower() == "closed":
        transition_with_labels(jira, issue, updated_labels)
    else:
        # Directly update labels for open issues
        issue.update(fields={"labels": updated_labels})
        logging.info(f"Labels updated for open issue {issue_key}: {updated_labels}")


def transition_with_labels(jira: JIRA, issue: Issue, updated_labels: List[str]) -> None:
    logging.info(f"Issue {issue.key} is closed. Attempting to re-resolve.")
    # Transition issue to "closed" while updating the labels
    closed_transition_id = next(
        (t['id'] for t in jira.transitions(issue) if t['name'].lower() == "closed"), None
    )
    if closed_transition_id:
        jira.transition_issue(
            issue,
            transition=closed_transition_id,
            fields={"labels": updated_labels}
        )
        logging.info(f"Issue {issue.key} re-resolved and labels updated: {updated_labels}")
    else:
        logging.error(f"No 'closed' transition available for issue {issue.key}. Labels not updated.")


if __name__ == "__main__":
    app()
