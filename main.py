from fastapi import FastAPI
from backend import router as backend_router
from admin_backend import router as admin_router

app = FastAPI(
    title="Telegram Movie Streaming API",
    description="API for fetching and managing movies & TV shows from Telegram",
    version="1.0.0"
)

# Include user API routes
app.include_router(backend_router)

# Include admin API routes with prefix
app.include_router(admin_router, prefix="/admin")

@app.get("/")
async def root():
    """Root API to check if the server is running"""
    return {"message": "✅ API is running!"}
