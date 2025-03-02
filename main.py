from fastapi import FastAPI
from backend import router as backend_router
from admin_backend import router as admin_router

app = FastAPI()

# Include backend (user) routes
app.include_router(backend_router)

# Include admin routes with prefix
app.include_router(admin_router, prefix="/admin")

@app.get("/")
async def root():
    return {"message": "API is running!"}
