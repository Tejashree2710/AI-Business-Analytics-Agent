
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file")

client = genai.Client(api_key=API_KEY)

EMBEDDING_MODEL = "gemini-embedding-2"
EMBEDDING_DIMENSIONS = 768


def generate_embedding(text: str):
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

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

        return response.embeddings[0].values

    except Exception as error:
        raise RuntimeError(
            f"Gemini embedding generation failed: {error}"
        ) from error


def generate_embeddings(texts: list[str]):
    if not texts:
        return []

    embeddings = []

    for text in texts:
        embeddings.append(generate_embedding(text))

    return embeddings
