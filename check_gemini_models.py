
from backend.services.gemini_service import client

print("\nAvailable Gemini models:\n")

for model in client.models.list():
    actions = getattr(model, "supported_actions", [])

    if "generateContent" in actions:
        print(model.name)
