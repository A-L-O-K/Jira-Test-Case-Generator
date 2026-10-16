import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

import chromadb
from dotenv import load_dotenv
from groq import Groq


load_dotenv(Path(__file__).resolve().parent / ".env")


def _embed_text(text: str) -> list[float]:
    tokens = re.findall(r"[a-z0-9]+", text.casefold())
    features = tokens + [f"{left}_{right}" for left, right in zip(tokens, tokens[1:])]
    vector = [0.0] * 512
    for feature in features:
        digest = hashlib.sha256(feature.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % len(vector)
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[index] += sign

    magnitude = sum(value * value for value in vector) ** 0.5
    if magnitude:
        vector = [value / magnitude for value in vector]
    return vector


class LLMHandler:
    def __init__(self, persist_directory: str | None = None) -> None:
        self.database_path = persist_directory or os.environ.get(
            "CHROMA_DB_PATH",
            str(Path(__file__).resolve().parent / ".chroma"),
        )
        self._collection = None

    @property
    def collection(self) -> Any:
        if self._collection is None:
            client = chromadb.PersistentClient(path=self.database_path)
            self._collection = client.get_or_create_collection(
                name="jira_stories",
                metadata={"hnsw:space": "cosine"},
                embedding_function=None,
            )
        return self._collection

    def fetchFromRag(
        self,
        text: str,
        exclude_story_key: str | None = None,
        limit: int = 3,
    ) -> list[str]:
        """Retrieve the most relevant stored story texts from Chroma."""
        collection_size = self.collection.count()
        if collection_size == 0:
            return []

        result_count = min(collection_size, limit + (1 if exclude_story_key else 0))
        results = self.collection.query(
            query_embeddings=[_embed_text(text)],
            n_results=result_count,
        )
        documents = results.get("documents", [[]])[0]
        identifiers = results.get("ids", [[]])[0]
        return [
            document
            for identifier, document in zip(identifiers, documents)
            if document and identifier != exclude_story_key
        ][:limit]

    def addInRag(self, story_key: str, story_text: str) -> None:
        """Persist a story in Chroma so future requests can retrieve it."""
        self.collection.upsert(
            ids=[story_key],
            documents=[story_text],
            metadatas=[{"story_key": story_key}],
            embeddings=[_embed_text(story_text)],
        )

    def getStory(self, story_key: str) -> dict[str, Any] | None:
        """Load a story previously stored in Chroma by its key."""
        result = self.collection.get(ids=[story_key], include=["documents"])
        documents = result.get("documents", [])
        if not documents or documents[0] is None:
            return None
        story = json.loads(documents[0])
        if not isinstance(story, dict):
            raise ValueError(f"Stored story {story_key} is not a JSON object.")
        return story

    def llm_handler(self, text: str) -> str:
        """Generate a response from Groq using the configured API key."""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is not set. Add it to Backend/.env; "
                "see Backend/.env.example."
            )

        client = Groq(api_key=api_key)
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": text}],
            temperature=1,
            max_completion_tokens=2048,
            top_p=1,
            reasoning_effort="medium",
            response_format={"type": "json_object"},
            stream=True,
            stop=None,
        )

        return "".join(
            chunk.choices[0].delta.content or ""
            for chunk in completion
        )
