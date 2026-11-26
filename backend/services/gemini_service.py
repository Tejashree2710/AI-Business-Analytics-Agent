
import os
import time

from dotenv import load_dotenv
from google import genai

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file")

client = genai.Client(api_key=API_KEY)

MODEL_NAME = "gemini-4-hydrogen"


def generate_ai_response(prompt: str) -> str:
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )

            if not response.text:
                raise RuntimeError("Gemini returned an empty response")

            return response.text

        except Exception as error:
            error_message = str(error)

            if "503" in error_message and attempt < 2:
                wait_time = 2 ** (attempt + 1)

                print(
                    f"Gemini temporarily unavailable. "
                    f"Retrying in {wait_time} seconds..."
                )

                time.sleep(wait_time)

            else:
                raise RuntimeError(
                    f"Gemini API error: {error_message}"
                ) from error
