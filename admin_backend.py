from fastapi import FastAPI, APIRouter
import json

app = FastAPI()
router = APIRouter(prefix="/admin")  # Ensure prefix is set

MOVIE_DB = "movies.json"
TVSHOW_DB = "tvshows.json"
REQUESTS_DB = "requests.json"

def load_db(filename):
    """Loads a database from JSON"""
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except:
        return []

def save_db(filename, data):
    """Saves data to JSON"""
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

@router.get("/movies")
async def get_movies():
    """Admin API to Fetch All Movies"""
    return {"movies": load_db(MOVIE_DB)}

@router.get("/tvshows")
async def get_tvshows():
    """Admin API to Fetch All TV Shows"""
    return {"tvshows": load_db(TVSHOW_DB)}

@router.get("/requests")
async def get_requests():
    """Admin API to View Pending Requests"""
    return {"requests": load_db(REQUESTS_DB)}

@router.delete("/requests/clear")
async def clear_requests():
    """Admin API to Clear All Requests"""
    save_db(REQUESTS_DB, [])
    return {"status": "✅ All requests cleared."}

app.include_router(router)  # Ensure the router is added to FastAPI
