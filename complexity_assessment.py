import logging
from jira import JIRA
import openai
from config import config

logging.basicConfig(level=logging.INFO)

jira = JIRA(server=config.jira_url, options={"server": config.jira_url}, token_auth=config.jira_api_token)
client = openai.OpenAI(api_key=config.openai_api_key)


def analyze_complexity(summary: str, description: str) -> int:
    """
    Uses OpenAI to classify the complexity of a Jira task.

    Args:
        summary (str): The task summary.
        description (str): The task description.

    Returns:
        int: Complexity level (1, 2, or 3), or 0 if unable to determine.
    """
    prompt = f"""
You are a task complexity classification assistant.

Classify the complexity level of the following Jira task based on these detailed criteria:
- 0: Unable to determine - The task details are too vague, incomplete, or ambiguous to assess complexity accurately.
- 1: Low - Tasks with clear and well-defined requirements, minimal dependencies, and no custom development.
- 2: Medium - Tasks with some technical or business dependencies, manageable within a known framework, or requiring moderate custom development.
- 3: High - Tasks with significant dependencies, vague requirements, or involving new/unproven technologies.

Additional considerations:
- Evaluate the **clarity of requirements** (e.g., vague tasks should lean towards 0 or 3 depending on context).
- Assess the **number of dependencies** (e.g., systems, teams, or APIs involved).
- Factor in **technical difficulty**, including the need for custom development or advanced tools.
- Consider **strategic importance** (e.g., business-critical tasks should lean towards higher complexity).

Task Summary: {summary}
Task Description: {description}

Respond **only** with the number representing the complexity level (0, 1, 2, or 3). Do not add any explanation or additional text.

Example:
Input:
Task Summary: Fix a typo on the About Us page.
Task Description: Correct a spelling mistake in the company mission statement.
Output: 1

Input:
Task Summary: Migrate legacy database.
Task Description: No details provided.
Output: 0

Input:
Task Summary: Build a customer-facing mobile app.
Task Description: Develop an iOS/Android app for e-commerce with secure payments, real-time order tracking, and personalized product recommendations.
Output: 3
"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an assistant for task complexity analysis."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=10,
            temperature=0.2,
        )
        complexity = response.choices[0].message.content.replace("Output: ", "").strip()
        if complexity in {"1", "2", "3"}:
            logging.info(f"Complexity analyzed: {complexity}")
            return int(complexity)
        else:
            logging.warning(f"Unexpected response: {complexity}")
            return 0
    except Exception as e:
        logging.error(f"Failed to analyze complexity: {e}")
        return 0


def update_complexity_field(issue_key: str, complexity_value: int) -> None:
    """
    Updates the custom Complexity field for a Jira task.

    Args:
        issue_key (str): The Jira issue key.
        complexity_value (int): The complexity value (1, 2, or 3).
    """
    try:
        issue = jira.issue(issue_key)
        # TODO: Replace 'customfield_XXXXX' with Complexity field ID
        customfield_id = "customfield_XXXXX"  # Replace with actual field ID
        # TODO: Uncomment issue.update(fields={customfield_id: complexity_value})
        logging.info(f"Updated Complexity for {issue_key} to {complexity_value}")
    except Exception as e:
        logging.error(f"Failed to update Complexity for {issue_key}: {e}")


def process_issues(jql_query: str) -> None:
    """
    Fetches Jira issues matching the JQL query and processes their complexity.

    Args:
        jql_query (str): The JQL query to fetch issues.
    """
    try:
        issues = jira.search_issues(jql_query, maxResults=100)
        logging.info(f"Found {len(issues)} tasks to analyze.")

        for issue in issues:
            issue_key = issue.key
            summary = issue.fields.summary
            description = issue.fields.description or "No description available"

            logging.info(f"Analyzing Complexity for Jira Task: {issue_key}")
            complexity = analyze_complexity(summary, description)

            if complexity:
                update_complexity_field(issue_key, complexity)
            else:
                logging.warning(f"Skipping update for {issue_key} due to invalid complexity.")
    except Exception as e:
        logging.error(f"Error processing issues: {e}")


if __name__ == "__main__":
    process_issues(config.jql_query)
