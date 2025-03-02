from fastapi import FastAPI
from backend import router as backend_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Telegram Movie API", version="1.0")

# Enable CORS to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (Update this for production security)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include backend routes
app.include_router(backend_router, prefix="/api")

@app.get("/health")
async def health_check():
    """Health check endpoint to verify API is running"""
    return {"status": "OK"}
