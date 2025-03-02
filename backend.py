from fastapi import APIRouter, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import logging

router = APIRouter()

# Enable CORS for frontend (Vercel)
def add_cors_middleware(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow requests from anywhere (Update for security)
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database files (Ensure correct absolute paths)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MOVIE_DB = os.path.join(BASE_DIR, "movies.json")
TVSHOW_DB = os.path.join(BASE_DIR, "tvshows.json")

# Load database function
def load_db(filename):
    """Load JSON database safely."""
    if not os.path.exists(filename):
        logger.warning(f"Database file {filename} not found, returning empty list.")
        return []

    with open(filename, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            logger.error(f"Error reading {filename}, returning empty list.")
            return []

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

    return {"movies": matching_movies, "tvshows": matching_tvshows}
