from fastapi import FastAPI
from backend import router as backend_router
from admin_backend import router as admin_router

app = FastAPI()

# Include backend routes (User API)
app.include_router(backend_router, prefix="")

# Include admin routes (Admin API)
app.include_router(admin_router, prefix="/admin")
