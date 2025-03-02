from fastapi import FastAPI
from backend import router as backend_router

app = FastAPI(title="Telegram Movie API", version="1.0")

# Include the backend routes
app.include_router(backend_router, prefix="/api")

@app.get("/health")
async def health_check():
    """Health check endpoint to verify API is running"""
    return {"status": "OK"}
