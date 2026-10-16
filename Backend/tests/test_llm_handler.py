import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from llmHandler import LLMHandler


class LLMHandlerTests(unittest.TestCase):
    @patch("llmHandler.Groq")
    def test_llm_handler_streams_groq_response(self, groq_client):
        chunks = [
            SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="Generated "))]
            ),
            SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="cases."))]
            ),
        ]
        groq_client.return_value.chat.completions.create.return_value = chunks

        with patch.dict(os.environ, {"GROQ_API_KEY": "test-api-key"}):
            response = LLMHandler().llm_handler("Create test cases")

        self.assertEqual(response, "Generated cases.")
        groq_client.assert_called_once_with(api_key="test-api-key")
        groq_client.return_value.chat.completions.create.assert_called_once_with(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": "Create test cases"}],
            temperature=1,
            max_completion_tokens=2048,
            top_p=1,
            reasoning_effort="medium",
            stream=True,
            stop=None,
        )

    def test_llm_handler_requires_api_key(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}):
            with self.assertRaisesRegex(ValueError, "GROQ_API_KEY is not set"):
                LLMHandler().llm_handler("Create test cases")


if __name__ == "__main__":
    unittest.main()
