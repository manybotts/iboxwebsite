from fastapi import APIRouter, Query, HTTPException
import json
import os

router = APIRouter()

# Database files
MOVIE_DB = "movies.json"
TVSHOW_DB = "tvshows.json"

# Load database function
def load_db(filename):
    """Load JSON database safely."""
    if os.path.exists(filename):
        with open(filename, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

# Save database function
def save_db(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

@router.get("/")
async def root():
    return {"message": "Welcome to the Telegram Movie API"}

@router.get("/movies")
async def get_movies():
    """Fetch all movies"""
    movies = load_db(MOVIE_DB)
    if not movies:
        raise HTTPException(status_code=404, detail="No movies found")
    return {"movies": movies}

@router.get("/tvshows")
async def get_tvshows():
    """Fetch all TV shows"""
    tvshows = load_db(TVSHOW_DB)
    if not tvshows:
        raise HTTPException(status_code=404, detail="No TV shows found")
    return {"tvshows": tvshows}

@router.get("/search")
async def search(query: str = Query(..., title="Search Query")):
    """Search for a movie or TV show by name"""
    query = query.lower()
    movies = load_db(MOVIE_DB)
    tvshows = load_db(TVSHOW_DB)

    matching_movies = [m for m in movies if query in m["title"].lower()]
    matching_tvshows = [t for t in tvshows if query in t["title"].lower()]

    if not matching_movies and not matching_tvshows:
        raise HTTPException(status_code=404, detail="No matching results found")

    return {
        "movies": matching_movies,
        "tvshows": matching_tvshows
    }
