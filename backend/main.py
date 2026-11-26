
from fastapi import FastAPI
from backend.routes.upload import router as upload_router

app = FastAPI(
    title="AI Business Analytics & Decision Support Agent",
    description="An AI-powered platform for business analytics and decision support.",
    version="1.0.0"
)
app.include_router(upload_router)

@app.get("/")
def home():
    return {
        "message": "AI Business Analytics Agent API is running",
        "status": "success"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }
