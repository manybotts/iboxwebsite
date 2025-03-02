from fastapi import FastAPI
import backend
import admin_backend

app = FastAPI()

# Include backend routes (User API)
app.include_router(backend.router, prefix="")

# Include admin routes (Admin API)
app.include_router(admin_backend.router, prefix="/admin")
