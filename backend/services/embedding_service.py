
import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

API_KEYS = [
    os.getenv("GEMINI_API_KEY_1"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3")
]

API_KEYS = [key for key in API_KEYS if key]

if not API_KEYS:
    raise ValueError("No Gemini API keys found in .env file")

EMBEDDING_MODEL = "gemini-embedding-2"
EMBEDDING_DIMENSIONS = 768

clients = [
    genai.Client(
        api_key=key,
        http_options=types.HttpOptions(timeout=45000)
    )
    for key in API_KEYS
]


def generate_embedding(text: str):
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    last_error = None

    for index, client in enumerate(clients):
        try:
            response = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text,
                config=types.EmbedContentConfig(
                    output_dimensionality=EMBEDDING_DIMENSIONS
                )
            )

            if not response.embeddings:
                raise ValueError("No embedding returned by Gemini")

            print(f"Embedding generated using API key {index + 1}")

            return response.embeddings[0].values

        except Exception as error:
            error_message = str(error).lower()
            status_code = getattr(error, "code", None)

            if status_code is None:
                status_code = getattr(error, "status_code", None)

            is_quota_error = (
                status_code == 429
                or "resource_exhausted" in error_message
                or "quota exceeded" in error_message
            )

            if is_quota_error:
                print(
                    f"API key {index + 1} quota exhausted. "
                    "Trying next key..."
                )
                last_error = error
                continue

            is_temporary_error = (
                status_code in (500, 502, 503, 504)
                or any(
                    code in error_message
                    for code in ("500", "502", "503", "504")
                )
            )

            if is_temporary_error:
                print("Gemini temporarily unavailable. Retrying once...")
                time.sleep(2)

                try:
                    response = client.models.embed_content(
                        model=EMBEDDING_MODEL,
                        contents=text,
                        config=types.EmbedContentConfig(
                            output_dimensionality=EMBEDDING_DIMENSIONS
                        )
                    )

                    if response.embeddings:
                        return response.embeddings[0].values

                except Exception as retry_error:
                    last_error = retry_error

                continue

            raise RuntimeError(
                f"Gemini embedding generation failed: {error}"
            ) from error

    raise RuntimeError(
        "All Gemini API keys are exhausted or unavailable. "
        "Please try again after the quotas reset."
    ) from last_error


def generate_embeddings(texts: list[str]):
    if not texts:
        return []

    return [generate_embedding(text) for text in texts]
