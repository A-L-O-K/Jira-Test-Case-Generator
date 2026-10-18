import base64
import json
import os
import unittest
from io import BytesIO
from unittest.mock import patch

from jira_client import JiraApiError, JiraClient


class JiraClientTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(
            os.environ,
            {
                "JIRA_BASE_URL": "https://example.atlassian.net/",
                "JIRA_EMAIL": "qa@example.com",
                "JIRA_API_TOKEN": "test-token",
            },
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.client = JiraClient()

    def test_create_task_uses_cloud_auth_and_includes_test_case_details(self):
        with patch(
            "jira_client.urlopen",
            return_value=BytesIO(b'{"key":"PROJ-456"}'),
        ) as urlopen:
            issue_key = self.client.create_task(
                "PROJ-123",
                {
                    "title": "Reset password",
                    "preconditions": ["Account exists."],
                    "steps": ["Open reset page."],
                    "expected_result": "Email is sent.",
                },
            )

        self.assertEqual(issue_key, "PROJ-456")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://example.atlassian.net/rest/api/3/issue")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(
            request.get_header("Authorization"),
            "Basic " + base64.b64encode(b"qa@example.com:test-token").decode("ascii"),
        )
        payload = json.loads(request.data)
        self.assertEqual(payload["fields"]["project"]["key"], "PROJ")
        self.assertEqual(payload["fields"]["issuetype"]["name"], "Task")
        self.assertEqual(payload["fields"]["summary"], "TC : Reset password")
        paragraphs = payload["fields"]["description"]["content"]
        self.assertEqual(paragraphs[0]["content"][0]["text"], "Preconditions")
        self.assertIn("1. Open reset page.", paragraphs[3]["content"][0]["text"])

    def test_create_task_does_not_duplicate_test_case_prefix(self):
        with patch(
            "jira_client.urlopen",
            return_value=BytesIO(b'{"key":"PROJ-456"}'),
        ) as urlopen:
            self.client.create_task(
                "PROJ-123",
                {
                    "title": "TC : Reset password",
                    "preconditions": [],
                    "steps": ["Open reset page."],
                    "expected_result": "Email is sent.",
                },
            )

        payload = json.loads(urlopen.call_args.args[0].data)
        self.assertEqual(payload["fields"]["summary"], "TC : Reset password")

    def test_link_to_story_uses_relates_issue_link(self):
        with patch("jira_client.urlopen", return_value=BytesIO(b"")) as urlopen:
            self.client.link_to_story("PROJ-123", "PROJ-456")

        request = urlopen.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/rest/api/3/issueLink"))
        self.assertEqual(
            json.loads(request.data),
            {
                "type": {"name": "Relates"},
                "inwardIssue": {"key": "PROJ-123"},
                "outwardIssue": {"key": "PROJ-456"},
            },
        )

    def test_client_requires_credentials_and_https(self):
        with patch.dict(os.environ, {"JIRA_API_TOKEN": ""}):
            with self.assertRaisesRegex(JiraApiError, "JIRA_BASE_URL"):
                JiraClient()
        with patch.dict(os.environ, {"JIRA_BASE_URL": "http://example.atlassian.net"}):
            with self.assertRaisesRegex(JiraApiError, "HTTPS"):
                JiraClient()


if __name__ == "__main__":
    unittest.main()
