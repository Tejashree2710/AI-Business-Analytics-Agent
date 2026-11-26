
import os
import time
import httpx

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

MODEL_NAME = "gemini-4-hydrogen"

clients = [
    genai.Client(
        api_key=key,
        http_options=types.HttpOptions(timeout=90000)
    )
    for key in API_KEYS
]


def get_status_code(error):
    status_code = getattr(error, "code", None)

    if status_code is None:
        status_code = getattr(error, "status_code", None)

    return status_code


def generate_ai_response(prompt: str) -> str:
    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty")

    last_error = None
    quota_failures = 0
    temporary_failures = 0

    for index, client in enumerate(clients):

        for attempt in range(2):
            try:
                start_time = time.time()

                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=prompt
                )

                if not response.text:
                    raise RuntimeError(
                        "Gemini returned an empty response"
                    )

                elapsed_time = round(
                    time.time() - start_time, 2
                )

                print(
                    f"Gemini response generated using API key "
                    f"{index + 1} in {elapsed_time} seconds"
                )

                return response.text

            except Exception as error:
                last_error = error
                error_message = str(error).lower()
                status_code = get_status_code(error)

                is_quota_error = (
                    status_code == 429
                    or "resource_exhausted" in error_message
                    or "quota exceeded" in error_message
                )

                if is_quota_error:
                    quota_failures += 1

                    print(
                        f"API key {index + 1} quota exhausted. "
                        "Trying next key..."
                    )
                    break

                is_timeout_error = (
                    isinstance(
                        error,
                        (TimeoutError, httpx.TimeoutException)
                    )
                    or "timed out" in error_message
                    or "timeout" in error_message
                )

                is_temporary_error = (
                    is_timeout_error
                    or status_code in (500, 502, 503, 504)
                    or any(
                        code in error_message
                        for code in (
                            "500", "502", "503", "504"
                        )
                    )
                )

                if is_temporary_error:
                    temporary_failures += 1

                    if attempt == 0:
                        print(
                            f"Temporary Gemini error with API "
                            f"key {index + 1}. Retrying once..."
                        )
                        time.sleep(3)
                        continue

                    print(
                        f"API key {index + 1} is temporarily "
                        "unavailable. Trying next key..."
                    )
                    break

                raise RuntimeError(
                    f"Gemini API error: {error}"
                ) from error

    if quota_failures == len(clients):
        message = (
            "All configured Gemini API keys have exhausted "
            "their available quota."
        )

    elif temporary_failures > 0:
        message = (
            "Gemini is temporarily unavailable across the "
            "configured API keys. Please try again later."
        )

    else:
        message = (
            "Gemini could not generate a response. "
            "Please try again later."
        )

    raise RuntimeError(message) from last_error
