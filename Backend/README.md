# Test Case Generator API

A small Flask API with seeded Jira-like stories and in-memory test cases. It is
intended for local Postman testing; data resets whenever the app restarts and no
real Jira connection is made.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The API is available at `http://127.0.0.1:5000`. Requests and responses use JSON.

## Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/stories/PROJ-123` | Get a seeded story |
| `GET` | `/api/v1/stories/PROJ-123/related` | Get related seeded stories |
| `POST` | `/api/v1/test-cases/generate` | Generate dummy cases for a story |
| `POST` | `/api/v1/test-cases/preview` | Validate/preview submitted cases |
| `POST` | `/api/v1/test-cases/publish` | Publish generated cases to the in-memory collection |
| `PUT` / `PATCH` | `/api/v1/test-cases/TC-001` | Replace editable fields or partially update an existing case |

### Generate test cases

```http
POST /api/v1/test-cases/generate
Content-Type: application/json
```

```json
{
  "story_key": "PROJ-123"
}
```

The full story object is serialized and passed to `compressor` in
[`compressorEngine.py`](./compressorEngine.py). Its whitespace compaction
preserves all story content. Chroma's persistent collection (`.chroma/`, or the
path in `CHROMA_DB_PATH`) stores the seeded stories and any new stories. The
compressed story is used to retrieve up to three relevant stored stories,
excluding the current story, and the story plus retrieved context is passed to
`LLMHandler.llm_handler` in [`llmHandler.py`](./llmHandler.py). The handler
currently echoes its input as a placeholder for a future LLM API integration.
Chroma uses normalized, deterministic local text vectors for retrieval, so no
embedding model download or embedding-service credentials are needed.

The response contains generated `test_cases`, each with an `id` such as
`GEN-001`, plus `relevant_context` and `llm_response` containing the dummy
handler's echoed prompt. Generation currently returns two deterministic dummy
cases.

For an unknown `story_key`, include a `story` object with non-empty `summary`
and `description`; the story key is taken from `story_key` if `story.key` is
omitted:

```json
{
  "story_key": "PROJ-125",
  "story": {
    "summary": "Unlock a locked account",
    "description": "As a user, I want to unlock my account after verification.",
    "status": "To Do",
    "type": "Story"
  }
}
```

The new story is added to Chroma after it has been processed, so it can
contribute context to later requests and remains available after an app restart.

### Preview test cases

```json
{
  "test_cases": [
    {
      "title": "Verify password reset",
      "story_key": "PROJ-123",
      "preconditions": ["A registered user account exists."],
      "steps": ["Open the password reset page.", "Submit the registered email address."],
      "expected_result": "A password reset email is sent."
    }
  ]
}
```

The endpoint returns `valid` and an `errors` array. The required fields are
`title`, `steps`, and `expected_result`.

### Publish selected generated cases

Pass the generated IDs from the generate response:

```json
{
  "test_case_ids": ["GEN-001"]
}
```

Published cases receive IDs such as `TC-002`. IDs from generation are only
available for publishing until the app restarts.

### Update a test case

`PATCH` accepts one or more editable fields. `PUT` replaces the editable case
representation and therefore requires all five fields:

```json
{
  "title": "Updated password reset test",
  "story_key": "PROJ-123",
  "preconditions": ["A registered user account exists."],
  "steps": ["Open the password reset page.", "Submit the registered email address."],
  "expected_result": "The user receives a reset email."
}
```

## Run tests

```bash
python -m unittest discover -s tests
```
