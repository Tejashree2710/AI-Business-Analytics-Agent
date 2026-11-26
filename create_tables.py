
from backend.database import Base, engine
from backend.models import (
    User,
    ChatSession,
    UploadedFile,
    DocumentChunk,
    ChatMessage
)

Base.metadata.create_all(bind=engine)

print("Database tables checked successfully!")
