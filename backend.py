from fastapi import APIRouter
import json

router = APIRouter()

MOVIE_DB = "movies.json"
TVSHOW_DB = "tvshows.json"

def load_db(filename):
    """Loads a database from JSON"""
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except:
        return []

@router.get("/")
async def root():
    return {"message": "API is running!"}

@router.get("/movies")
async def get_movies():
    """Fetch all movies"""
    return {"movies": load_db(MOVIE_DB)}

@router.get("/tvshows")
async def get_tvshows():
    """Fetch all TV shows"""
    return {"tvshows": load_db(TVSHOW_DB)}
