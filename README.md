# Jira-Test-Case-Generator
This is a prototype project that use publicly available API to create test cases for a Jira story. Since it uses rag, and has access to related stories, it can create much better test cases


# Jira Test Case Generator extension

This is a Manifest V3 browser extension that adds a **Generate test cases**
button to Jira issue pages. Clicking the button opens a dialog for optional
generation instructions. **Submit** sends the story details and instructions
as JSON to `http://127.0.0.1:5000/api/v1/test-cases/generate`. Returned test
cases are displayed with individual checkboxes. **Create** logs each selected
test case to the browser console; **Cancel** closes the dialog without logging.

## Install in Chrome or Edge

1. Start the backend at `http://127.0.0.1:5000`.
2. Open `chrome://extensions` (or `edge://extensions`) and enable
   **Developer mode**.
3. Choose **Load unpacked** and select this `Frontend` folder.
4. Open a Jira issue URL such as `/browse/PROJ-123`, then click
   **Generate test cases**.

The extension requests permission to contact only the local backend. The
content script is configured for Atlassian Cloud and Jira `/browse/` routes.
The Jira page must expose a readable summary and description for generation.
