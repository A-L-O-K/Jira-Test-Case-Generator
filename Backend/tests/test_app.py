import json
import tempfile
import unittest
from unittest.mock import patch

import app
from app import create_app


class TestCaseApiTests(unittest.TestCase):
    def setUp(self):
        self.chroma_directory = tempfile.TemporaryDirectory()
        self.chroma_path = self.chroma_directory.name
        self.llm_patcher = patch.object(
            app.LLMHandler,
            "llm_handler",
            return_value=json.dumps(
                {
                    "test_cases": [
                        {
                            "title": "User can reset password with a registered email",
                            "preconditions": ["A registered account exists."],
                            "steps": ["Open reset page.", "Submit registered email."],
                            "expected_result": "A reset email is sent.",
                        },
                        {
                            "title": "Unregistered email is handled",
                            "preconditions": [],
                            "steps": ["Open reset page.", "Submit an unknown email."],
                            "expected_result": "A non-disclosing error is shown.",
                        },
                    ]
                }
            ),
        )
        self.llm_patcher.start()
        self.addCleanup(self.llm_patcher.stop)
        self.client = create_app(chroma_path=self.chroma_path).test_client()

    def tearDown(self):
        self.chroma_directory.cleanup()

    def test_get_story_and_related_stories(self):
        story = self.client.get("/api/v1/stories/PROJ-123")
        related = self.client.get("/api/v1/stories/PROJ-123/related")

        self.assertEqual(story.status_code, 200)
        self.assertEqual(story.json["data"]["key"], "PROJ-123")
        self.assertEqual(related.status_code, 200)
        self.assertEqual(related.json["data"][0]["key"], "PROJ-124")

    def test_generate_preview_and_publish_test_cases(self):
        with patch.object(
            app.LLMHandler,
            "llm_handler",
            return_value=json.dumps(
                {
                    "test_cases": [
                        {
                            "title": "Generated from model response",
                            "preconditions": ["An account exists."],
                            "steps": ["Perform the requested action."],
                            "expected_result": "The requested action succeeds.",
                        }
                    ]
                }
            ),
        ):
            generated = self.client.post(
                "/api/v1/test-cases/generate",
                json={"story_key": "PROJ-123"},
            )
        self.assertEqual(generated.status_code, 201)
        cases = generated.json["data"]["test_cases"]
        self.assertEqual(
            generated.json["data"]["llm_response"],
            json.dumps(
                {
                    "test_cases": [
                        {
                            "title": "Generated from model response",
                            "preconditions": ["An account exists."],
                            "steps": ["Perform the requested action."],
                            "expected_result": "The requested action succeeds.",
                        }
                    ]
                }
            ),
        )
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0]["title"], "Generated from model response")
        self.assertEqual(
            generated.json["data"]["relevant_context"],
            ['{"key": "PROJ-124", "summary": "Sign in with valid credentials", '
             '"description": "As a user, I want to sign in to my account.", '
             '"status": "To Do", "type": "Story"}'],
        )

        preview = self.client.post(
            "/api/v1/test-cases/preview",
            json={"test_cases": cases},
        )
        self.assertEqual(preview.status_code, 200)
        self.assertTrue(preview.json["data"]["valid"])

        published = self.client.post(
            "/api/v1/test-cases/publish",
            json={"test_case_ids": [cases[0]["id"]]},
        )
        self.assertEqual(published.status_code, 201)
        self.assertEqual(published.json["data"]["published"][0]["id"], "TC-002")

    def test_generate_sends_full_story_through_compressor_and_llm_handler(self):
        compressed_text = '{"compressed":"story"}'
        llm_result = json.dumps(
            {
                "test_cases": [
                    {
                        "title": "Generated case",
                        "preconditions": [],
                        "steps": ["Do the action."],
                        "expected_result": "Action succeeds.",
                    }
                ]
            }
        )
        with (
            patch("app.compressor", return_value=compressed_text) as compressor_mock,
            patch.object(
                app.LLMHandler,
                "fetchFromRag",
                return_value=["related story context"],
            ),
            patch.object(app.LLMHandler, "llm_handler", return_value=llm_result) as llm_mock,
        ):
            response = self.client.post(
                "/api/v1/test-cases/generate",
                json={"story_key": "PROJ-123"},
            )

        self.assertEqual(response.status_code, 201)
        story = response.json["data"]["story"]
        compressor_mock.assert_called_once_with(json.dumps(story, ensure_ascii=False))
        llm_mock.assert_called_once()
        llm_prompt = llm_mock.call_args.args[0]
        self.assertIn("Return only a valid JSON object", llm_prompt)
        self.assertIn(f"Story:\n{compressed_text}", llm_prompt)
        self.assertTrue(llm_prompt.endswith("Relevant context:\nrelated story context"))
        self.assertEqual(response.json["data"]["llm_response"], llm_result)

    def test_generate_returns_error_when_llm_response_is_not_valid_json(self):
        with patch.object(
            app.LLMHandler,
            "llm_handler",
            return_value="This is not JSON",
        ):
            response = self.client.post(
                "/api/v1/test-cases/generate",
                json={"story_key": "PROJ-123"},
            )

        self.assertEqual(response.status_code, 502)
        self.assertIn("invalid JSON", response.json["error"])

    def test_generate_rejects_invalid_llm_test_case(self):
        with patch.object(
            app.LLMHandler,
            "llm_handler",
            return_value=json.dumps(
                {"test_cases": [{"title": "", "steps": [], "expected_result": ""}]}
            ),
        ):
            response = self.client.post(
                "/api/v1/test-cases/generate",
                json={"story_key": "PROJ-123"},
            )

        self.assertEqual(response.status_code, 502)
        self.assertIn("invalid test case", response.json["error"])

    def test_new_story_is_saved_and_available_as_future_rag_context(self):
        new_story = {
            "story_key": "PROJ-125",
            "story": {
                "summary": "Unlock a locked account",
                "description": "As a user, I want to unlock my account after verification.",
                "status": "To Do",
                "type": "Story",
            },
        }
        first_response = self.client.post("/api/v1/test-cases/generate", json=new_story)
        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(first_response.json["data"]["story"]["key"], "PROJ-125")

        second_response = self.client.post(
            "/api/v1/test-cases/generate",
            json={"story_key": "PROJ-123"},
        )
        self.assertEqual(second_response.status_code, 201)
        self.assertTrue(
            any("PROJ-125" in context for context in second_response.json["data"]["relevant_context"])
        )
        self.assertEqual(
            self.client.get("/api/v1/stories/PROJ-125").json["data"]["summary"],
            "Unlock a locked account",
        )

        restarted_client = create_app(chroma_path=self.chroma_path).test_client()
        persisted_story = restarted_client.get("/api/v1/stories/PROJ-125")
        self.assertEqual(persisted_story.status_code, 200)
        self.assertEqual(persisted_story.json["data"]["description"], new_story["story"]["description"])

    def test_unknown_story_requires_details(self):
        response = self.client.post(
            "/api/v1/test-cases/generate",
            json={"story_key": "PROJ-999"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("story object", response.json["error"])

    def test_preview_reports_invalid_case(self):
        response = self.client.post(
            "/api/v1/test-cases/preview",
            json={"test_cases": [{"title": "Missing details"}]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json["data"]["valid"])
        self.assertGreater(len(response.json["data"]["errors"]), 0)

    def test_update_existing_test_case(self):
        response = self.client.patch(
            "/api/v1/test-cases/TC-001",
            json={"title": "Updated password reset case"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"]["title"], "Updated password reset case")

    def test_put_requires_complete_editable_representation(self):
        response = self.client.put(
            "/api/v1/test-cases/TC-001",
            json={"title": "Replacement case"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("steps", response.json["fields"])

    def test_unknown_story_returns_not_found(self):
        response = self.client.get("/api/v1/stories/NOPE-404")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
