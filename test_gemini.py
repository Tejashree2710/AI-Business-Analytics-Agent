from backend.services.gemini_service import generate_ai_response

try:
    response = generate_ai_response("Say Hello")
    print("SUCCESS!")
    print(response)

except Exception as error:
    print("FAILED!")
    print(error)