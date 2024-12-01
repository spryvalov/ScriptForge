# Utility Scripts

These scripts are tools I find useful in my daily work as a solutions architect. While there might be more sophisticated or optimized solutions available, I use this repository to have fun.

## About This Repository

This repository serves as a playground for writing and improving Python scripts: small, practical solutions to common problems.

### Why This Exists
In my current role, I don’t code as much as I’d like. Maintaining this repository allows me to stay connected to coding, experiment with ideas.

## Scripts
### Jira Issue Classifier
**Purpose**: Classifies Jira issues into domains and technologies using OpenAI GPT and updates the issue labels in Jira accordingly.
### Complexity assessment
**Purpose**: Analyzes the complexity of Jira tasks based on their summaries and descriptions using OpenAI GPT. It assigns a complexity level (0: Unable to determine, 1: Low, 2: Medium, 3: High) to each issue and updates a custom complexity field in Jira. 


### Usage
1. Clone the Repository:
2. Set Up Environment Variables:
      Create a .env file or export the following variables:
    ```bash
    export JIRA_URL="https://your-jira-instance.atlassian.net"
    export JIRA_API_TOKEN="your-jira-api-token"
    export OPENAI_API_KEY="your-openai-api-key"
    ```
3. Install dependencies
    ```bash
    pip install -r requirements.txt
    ```
4. Run the script
    ```bash
    python jira_issue_classifier.py
    ```

## Requirements

	•	Python 3.8+
	•	Dependencies listed in requirements.txt.

Note:
Use this script only with authorized access to Jira and OpenAI APIs.

### Contributing

This repository is primarily for my personal learning, but if you’d like to suggest improvements or share feedback, feel free to open an issue or submit a pull request.

## License

This repository is licensed under the MIT License. See the LICENSE file for more details.