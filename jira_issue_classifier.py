import logging
from typing import Callable, TypeVar, Any, Optional, List, cast

import openai
import re
import requests
import spacy
import typer
from jira import JIRA, Issue

from constants import POSSIBLE_DOMAINS, OLD_TAGS, POSSIBLE_TECH_EXPERTISE

logging.basicConfig(level=logging.INFO)

app = typer.Typer()
ReturnType = TypeVar('ReturnType')
nlp = spacy.load('en_core_web_sm')
EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_RE = re.compile(r"(?:\+?\d[\d\s\-\(\)]{7,}\d)")


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
        comments = ";;\n".join(c.body for c in issue.fields.comment.comments)
        logging.info(f"Processing Jira Task: {issue_key}")

        domains = classify_task(client, summary, description, comments)
        logging.info(f"Classified Domains: {domains}")

        # Add tags to Jira
        update_jira_labels(jira, issue_key, domains, list(set(OLD_TAGS + POSSIBLE_DOMAINS)), True)
        logging.info(f"Tags added to Jira issue {issue_key}: {domains}")
    except Exception as e:
        logging.error(f"Failed to process issue {issue_key}: {e}")


def classify_task(client: openai.OpenAI, summary: str, description: str, comments: str) -> List[str]:
    prompt = f"""
    Based on the provided pre-sale details, determine if there's enough information to clearly assign the task to specific technical expertise from the following domains:
    {", ".join(POSSIBLE_TECH_EXPERTISE)}.
    
    Only classify if explicitly supported by the details. DO NOT guess or infer expertise if details are vague or minimal.

    Task Summary: {anonymize_text(summary)}
    Task Description: {anonymize_text(description)}
    Task Comments separated by ';;': {anonymize_text(comments)}
    
    Respond strictly in this format:
    Expertise: <semicolon-separated list of 0-2 domains, or leave empty if unsure>
    """

    response = execute_safe_call(client.chat.completions.create, model="gpt-4-turbo", messages=[
        {"role": "system", 
         "content": ("You are an assistant for domain classification. "
                     "Classify tickets into relevant technical expertise domains ONLY if the task explicitly matches one of these domains. "
                     "If there's not enough information, leave the expertise field empty without guessing.")},
        {"role": "user", "content": prompt}
    ], max_tokens=150, temperature=0.0)

    if not response:
        return []

    # Parse the response
    try:
        result = response.choices[0].message.content
        labels_line = (result or "").split("\n")[0].replace("Expertise: ", "").strip()
        labels = [d.strip() for d in labels_line.split(";")]
        # Filter possible domains and technologies to avoid hallucinations
        return [d for d in labels if d in POSSIBLE_TECH_EXPERTISE]
    except Exception as e:
        logging.error(f"Error parsing OpenAI response: {e}")
        return []


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


def update_jira_labels(jira: JIRA, issue_key: str, new_tags: List[str], tags_to_clear: List[str], clear_old_labels: bool) -> None:
    issue = jira.issue(issue_key)
    current_labels = issue.fields.labels
    # Remove tags set previously by this exact script
    filtered_labels = [label for label in current_labels if label not in tags_to_clear]
    updated_labels = new_tags if clear_old_labels else list(set(filtered_labels + new_tags))
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


def anonymize_text(text):
    doc = nlp(text)
    anonymized = text
    
    for ent in reversed(doc.ents):  # reverse so offsets don't shift
        if ent.label_ == "PERSON":
            anonymized = anonymized[:ent.start_char] + "[PersonName]" + anonymized[ent.end_char:]
        elif ent.label_ == "ORG":
            anonymized = anonymized[:ent.start_char] + "[CompanyName]" + anonymized[ent.end_char:]
        elif ent.label_ in ("GPE","LOC","FAC","ADDRESS"):
            anonymized = anonymized[:ent.start_char] + "[Address]" + anonymized[ent.end_char:]
    
    anonymized = EMAIL_RE.sub("[Email]", anonymized)
    anonymized = PHONE_RE.sub("[PhoneNumber]", anonymized)
    
    # If nothing was replaced, return original
    return anonymized if anonymized != text else text


if __name__ == "__main__":
    app()
