from copy import deepcopy
from itertools import count
import json

from flask import Flask, jsonify, request

from compressorEngine import compressor
from llmHandler import LLMHandler


def _new_store():
    return {
        "stories": {
            "PROJ-123": {
                "key": "PROJ-123",
                "summary": "Reset a forgotten password",
                "description": (
                    "As a user, I want to reset my password by email so I can "
                    "regain access to my account."
                ),
                "status": "In Progress",
                "type": "Story",
            },
            "PROJ-124": {
                "key": "PROJ-124",
                "summary": "Sign in with valid credentials",
                "description": "As a user, I want to sign in to my account.",
                "status": "To Do",
                "type": "Story",
            },
        },
        "related_stories": {
            "PROJ-123": ["PROJ-124"],
            "PROJ-124": ["PROJ-123"],
        },
        "test_cases": {
            "TC-001": {
                "id": "TC-001",
                "title": "Password reset email is sent",
                "story_key": "PROJ-123",
                "preconditions": ["A registered user account exists."],
                "steps": ["Open the password reset page.", "Submit the registered email address."],
                "expected_result": "A password reset email is sent to the registered address.",
            }
        },
        "generated": {},
        "next_test_case_id": count(2),
        "next_generated_id": count(1),
    }


def _json_body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return None
    return body


def _validate_test_case(test_case, index):
    if not isinstance(test_case, dict):
        return f"test_cases[{index}] must be an object."

    for field in ("title", "steps", "expected_result"):
        if field not in test_case:
            return f"test_cases[{index}].{field} is required."

    if not isinstance(test_case["title"], str) or not test_case["title"].strip():
        return f"test_cases[{index}].title must be a non-empty string."
    if not isinstance(test_case["steps"], list) or not test_case["steps"]:
        return f"test_cases[{index}].steps must be a non-empty array."
    if any(not isinstance(step, str) or not step.strip() for step in test_case["steps"]):
        return f"Every step in test_cases[{index}].steps must be a non-empty string."
    if not isinstance(test_case["expected_result"], str) or not test_case["expected_result"].strip():
        return f"test_cases[{index}].expected_result must be a non-empty string."
    return None


def create_app(chroma_path: str | None = None):
    app = Flask(__name__)
    app.json.sort_keys = False
    store = _new_store()
    llm_handler = LLMHandler(persist_directory=chroma_path)
    rag_initialized = False

    def initialize_rag():
        nonlocal rag_initialized
        if rag_initialized:
            return
        for seeded_story in store["stories"].values():
            if llm_handler.getStory(seeded_story["key"]) is None:
                llm_handler.addInRag(
                    seeded_story["key"],
                    json.dumps(seeded_story, ensure_ascii=False),
                )
        rag_initialized = True

    @app.get("/api/v1/stories/<story_key>")
    def get_story(story_key):
        story_key = story_key.upper()
        story = store["stories"].get(story_key) or llm_handler.getStory(story_key)
        if story is None:
            return jsonify(error="Story not found.", story_key=story_key), 404
        store["stories"][story_key] = story
        return jsonify(data=deepcopy(story))

    @app.get("/api/v1/stories/<story_key>/related")
    def get_related_stories(story_key):
        story_key = story_key.upper()
        if story_key not in store["stories"]:
            return jsonify(error="Story not found.", story_key=story_key), 404
        related = [
            deepcopy(store["stories"][key])
            for key in store["related_stories"].get(story_key, [])
            if key in store["stories"]
        ]
        return jsonify(data=related)

    @app.post("/api/v1/test-cases/generate")
    def generate_test_cases():
        initialize_rag()
        body = _json_body()
        if body is None:
            return jsonify(error="Request body must be a JSON object."), 400

        story_key = body.get("story_key")
        if not isinstance(story_key, str) or not story_key.strip():
            return jsonify(error="story_key is required and must be a string."), 400
        story_key = story_key.strip().upper()
        story = store["stories"].get(story_key) or llm_handler.getStory(story_key)
        if story is None:
            submitted_story = body.get("story")
            if not isinstance(submitted_story, dict):
                return jsonify(
                    error="Unknown story. Provide its details in the story object.",
                    story_key=story_key,
                ), 400

            submitted_key = submitted_story.get("key", story_key)
            if not isinstance(submitted_key, str) or submitted_key.strip().upper() != story_key:
                return jsonify(error="story.key must match story_key."), 400
            summary = submitted_story.get("summary")
            description = submitted_story.get("description")
            if not isinstance(summary, str) or not summary.strip():
                return jsonify(error="story.summary must be a non-empty string."), 400
            if not isinstance(description, str) or not description.strip():
                return jsonify(error="story.description must be a non-empty string."), 400

            story = {
                **submitted_story,
                "key": story_key,
                "summary": summary.strip(),
                "description": description.strip(),
            }

        story_text = json.dumps(story, ensure_ascii=False)
        compressed_story = compressor(story_text)
        relevant_context = llm_handler.fetchFromRag(
            compressed_story,
            exclude_story_key=story_key,
        )
        context_text = "\n".join(relevant_context)
        llm_input = (
            f"Story:\n{compressed_story}\n\n"
            f"Relevant context:\n{context_text}"
        )
        llm_response = llm_handler.llm_handler(llm_input)
        if store["stories"].get(story_key) is None and llm_handler.getStory(story_key) is None:
            llm_handler.addInRag(story_key, story_text)
        store["stories"][story_key] = story

        test_cases = [
            {
                "id": f"GEN-{next(store['next_generated_id']):03d}",
                "title": f"Verify the user can {story['summary'].lower()}",
                "story_key": story_key,
                "preconditions": ["The application is available."],
                "steps": [
                    f"Open the application flow for: {story['summary']}.",
                    "Complete the required action using valid information.",
                ],
                "expected_result": f"The action completes successfully for story {story_key}.",
            },
            {
                "id": f"GEN-{next(store['next_generated_id']):03d}",
                "title": f"Verify invalid input is handled for {story['summary'].lower()}",
                "story_key": story_key,
                "preconditions": ["The application is available."],
                "steps": [
                    f"Open the application flow for: {story['summary']}.",
                    "Submit missing or invalid information.",
                ],
                "expected_result": "A helpful validation message is shown and no change is applied.",
            },
        ]
        for test_case in test_cases:
            store["generated"][test_case["id"]] = deepcopy(test_case)
        return jsonify(
            data={
                "story": deepcopy(story),
                "relevant_context": relevant_context,
                "test_cases": test_cases,
                "llm_response": llm_response,
            }
        ), 201

    @app.post("/api/v1/test-cases/preview")
    def preview_test_cases():
        body = _json_body()
        if body is None:
            return jsonify(error="Request body must be a JSON object."), 400
        test_cases = body.get("test_cases")
        if not isinstance(test_cases, list) or not test_cases:
            return jsonify(error="test_cases must be a non-empty array."), 400

        errors = [
            error
            for index, test_case in enumerate(test_cases)
            if (error := _validate_test_case(test_case, index)) is not None
        ]
        return jsonify(data={"valid": not errors, "test_cases": test_cases, "errors": errors})

    @app.post("/api/v1/test-cases/publish")
    def publish_test_cases():
        body = _json_body()
        if body is None:
            return jsonify(error="Request body must be a JSON object."), 400
        test_case_ids = body.get("test_case_ids")
        if not isinstance(test_case_ids, list) or not test_case_ids:
            return jsonify(error="test_case_ids must be a non-empty array."), 400
        if any(not isinstance(case_id, str) for case_id in test_case_ids):
            return jsonify(error="Every test_case_id must be a string."), 400
        if len(set(test_case_ids)) != len(test_case_ids):
            return jsonify(error="test_case_ids must not contain duplicates."), 400

        missing_ids = [case_id for case_id in test_case_ids if case_id not in store["generated"]]
        if missing_ids:
            return jsonify(error="One or more generated test cases were not found.", missing_ids=missing_ids), 404

        published = []
        for case_id in test_case_ids:
            test_case = deepcopy(store["generated"][case_id])
            published_id = f"TC-{next(store['next_test_case_id']):03d}"
            test_case["id"] = published_id
            store["test_cases"][published_id] = test_case
            published.append(deepcopy(test_case))
        return jsonify(data={"published": published}), 201

    @app.route("/api/v1/test-cases/<test_case_id>", methods=["PUT", "PATCH"])
    def update_test_case(test_case_id):
        test_case_id = test_case_id.upper()
        existing = store["test_cases"].get(test_case_id)
        if existing is None:
            return jsonify(error="Test case not found.", test_case_id=test_case_id), 404

        body = _json_body()
        if body is None or not body:
            return jsonify(error="Request body must be a non-empty JSON object."), 400

        allowed_fields = {"title", "story_key", "preconditions", "steps", "expected_result"}
        unknown_fields = sorted(set(body) - allowed_fields)
        if unknown_fields:
            return jsonify(error="Request contains unsupported fields.", fields=unknown_fields), 400

        if request.method == "PUT":
            missing_fields = sorted(allowed_fields - set(body))
            if missing_fields:
                return jsonify(error="PUT requires all editable fields.", fields=missing_fields), 400
            updated = {**body, "id": test_case_id}
        else:
            updated = {**existing, **body, "id": test_case_id}
        validation_error = _validate_test_case(updated, 0)
        if validation_error:
            return jsonify(error=validation_error), 400
        if "story_key" in body:
            if not isinstance(body["story_key"], str) or body["story_key"].upper() not in store["stories"]:
                return jsonify(error="story_key must reference an existing story."), 400
            updated["story_key"] = body["story_key"].upper()
        if "preconditions" in body and (
            not isinstance(body["preconditions"], list)
            or any(not isinstance(item, str) for item in body["preconditions"])
        ):
            return jsonify(error="preconditions must be an array of strings."), 400

        store["test_cases"][test_case_id] = updated
        return jsonify(data=deepcopy(updated))

    return app


app = create_app()


if __name__ == "__main__":
    app.run()
