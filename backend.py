from fastapi import APIRouter
import json
import os

router = APIRouter()

MOVIE_DB = "movies.json"
TVSHOW_DB = "tvshows.json"

def load_db(filename):
    """Loads the database from JSON"""
    if not os.path.exists(filename):
        return []  # Return empty list if the file doesn't exist
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []  # Return empty list if JSON is corrupted

def save_db(filename, data):
    """Saves data to JSON"""
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

@router.get("/movies")
async def get_movies():
    """Fetch all movies"""
    return {"movies": load_db(MOVIE_DB)}

@router.get("/tvshows")
async def get_tvshows():
    """Fetch all TV shows"""
    return {"tvshows": load_db(TVSHOW_DB)}

@router.post("/movies")
async def add_movie(movie: dict):
    """Add a new movie manually"""
    movies = load_db(MOVIE_DB)
    movies.append(movie)
    save_db(MOVIE_DB, movies)
    return {"status": "✅ Movie added"}

@router.post("/tvshows")
async def add_tvshow(tvshow: dict):
    """Add a new TV show manually"""
    tvshows = load_db(TVSHOW_DB)
    tvshows.append(tvshow)
    save_db(TVSHOW_DB, tvshows)
    return {"status": "✅ TV show added"}

@router.delete("/movies/clear")
async def clear_movies():
    """Clear all movies"""
    save_db(MOVIE_DB, [])
    return {"status": "✅ All movies cleared"}

@router.delete("/tvshows/clear")
async def clear_tvshows():
    """Clear all TV shows"""
    save_db(TVSHOW_DB, [])
    return {"status": "✅ All TV shows cleared"}
