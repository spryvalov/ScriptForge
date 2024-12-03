# Utility Scripts

These scripts are tools I find useful in my daily work as a solutions architect. While there might be more sophisticated or optimized solutions available, I use this repository to have fun.

## About This Repository

This repository serves as a playground for writing and improving Python scripts: small, practical solutions to common problems.

### Why This Exists
In my current role, I don’t code as much as I’d like. Maintaining this repository allows me to stay connected to coding, experiment with ideas.

## Scripts Overview

1. **`jira_issue_classifier.py`**:
    - **Purpose**: Classifies Jira issues into predefined domains and technologies.
    - **Key Features**:
        - Fetches issues from Jira using JQL.
        - Uses OpenAI to classify issues based on their summaries and descriptions.
        - Updates the classification labels in Jira.
    - **Usage**:
      ```bash
      python jira_issue_classifier.py --jira-url <JIRA_URL> --jira-api-token <API_TOKEN> --openai-api-key <OPENAI_KEY> <JQL>
      ```

2. **`complexity_assessment.py`**:
    - **Purpose**: Assesses the complexity of Jira tasks using OpenAI.
    - **Key Features**:
        - Fetches issues without complexity values using JQL.
        - Uses OpenAI to evaluate task complexity (Low, Medium, High).
        - Updates the custom Complexity field in Jira.
    - **Usage**:
      ```bash
      python complexity_assessment.py --jira-url <JIRA_URL> --jira-api-token <API_TOKEN> --openai-api-key <OPENAI_KEY> <JQL>
      ```

## Requirements

- Python 3.8+
- Dependencies:
    - `jira`
    - `openai`
    - `typer`

Install all dependencies with:
```bash
pip install -r requirements.txt
```

### Contributing

This repository is primarily for my personal learning, but if you’d like to suggest improvements or share feedback, feel free to open an issue or submit a pull request.

## License

This repository is licensed under the MIT License. See the LICENSE file for more details.