import base64
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class JiraApiError(Exception):
    pass


class JiraClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("JIRA_BASE_URL", "").rstrip("/")
        self.email = os.getenv("JIRA_EMAIL", "")
        self.api_token = os.getenv("JIRA_API_TOKEN") or os.getenv("JIRA_API_KEY", "")
        if not self.base_url or not self.email or not self.api_token:
            raise JiraApiError(
                "JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN (or JIRA_API_KEY) "
                "must be set in Backend/.env before creating Jira issues."
            )
        if not self.base_url.startswith("https://"):
            raise JiraApiError("JIRA_BASE_URL must use HTTPS.")

    def _request(self, method: str, path: str, body: dict) -> dict:
        credentials = base64.b64encode(
            f"{self.email}:{self.api_token}".encode("utf-8")
        ).decode("ascii")
        request = Request(
            f"{self.base_url}/rest/api/3/{path}",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/json",
            },
            method=method,
        )
        try:
            with urlopen(request, timeout=20) as response:
                response_body = response.read()
        except HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            try:
                error_body = json.loads(details)
                messages = error_body.get("errorMessages", [])
                detail = "; ".join(messages) if messages else details
            except (json.JSONDecodeError, AttributeError):
                detail = details
            raise JiraApiError(
                f"Jira returned HTTP {error.code}"
                + (f": {detail}" if detail else ".")
            ) from error
        except URLError as error:
            raise JiraApiError(f"Could not reach Jira: {error.reason}") from error

        if not response_body:
            return {}
        try:
            result = json.loads(response_body)
        except json.JSONDecodeError as error:
            raise JiraApiError("Jira returned an invalid JSON response.") from error
        if not isinstance(result, dict):
            raise JiraApiError("Jira returned an unexpected response.")
        return result

    @staticmethod
    def _paragraph(text: str) -> dict:
        return {
            "type": "paragraph",
            "content": [{"type": "text", "text": text}],
        }

    @classmethod
    def _description(cls, test_case: dict) -> dict:
        content = []

        preconditions = test_case.get("preconditions", [])
        if preconditions:
            content.append(cls._paragraph("Preconditions"))
            content.extend(cls._paragraph(item) for item in preconditions)

        content.append(cls._paragraph("Steps"))
        content.extend(
            cls._paragraph(f"{index}. {step}")
            for index, step in enumerate(test_case["steps"], start=1)
        )
        content.append(cls._paragraph("Expected result"))
        content.append(cls._paragraph(test_case["expected_result"]))
        return {"type": "doc", "version": 1, "content": content}

    def create_task(self, story_key: str, test_case: dict) -> str:
        project_key = story_key.rsplit("-", 1)[0]
        title = test_case["title"]
        summary = title if title.startswith("TC : ") else f"TC : {title}"
        result = self._request(
            "POST",
            "issue",
            {
                "fields": {
                    "project": {"key": project_key},
                    "summary": summary,
                    "description": self._description(test_case),
                    "issuetype": {"name": "Task"},
                }
            },
        )
        issue_key = result.get("key")
        if not isinstance(issue_key, str) or not issue_key:
            raise JiraApiError("Jira created an issue but did not return its key.")
        return issue_key

    def link_to_story(self, story_key: str, task_key: str) -> None:
        self._request(
            "POST",
            "issueLink",
            {
                "type": {"name": "Relates"},
                "inwardIssue": {"key": story_key},
                "outwardIssue": {"key": task_key},
            },
        )
