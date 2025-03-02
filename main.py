from fastapi import FastAPI
from backend import app as backend_app
from admin_backend import app as admin_app

app = FastAPI()

# Mount the backend routes
app.mount("/", backend_app)

# Mount the admin routes
app.mount("/admin", admin_app)
