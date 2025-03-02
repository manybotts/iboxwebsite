from fastapi import FastAPI, Query
import json
import os

app = FastAPI()

# Database files
MOVIE_DB = "movies.json"
TVSHOW_DB = "tvshows.json"

# Load database function
def load_db(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

@app.get("/")
async def root():
    return {"message": "Welcome to the Telegram Movie API"}

@app.get("/movies")
async def get_movies():
    """Fetch all movies"""
    return {"movies": load_db(MOVIE_DB)}

@app.get("/tvshows")
async def get_tvshows():
    """Fetch all TV shows"""
    return {"tvshows": load_db(TVSHOW_DB)}

@app.get("/search")
async def search(query: str = Query(..., title="Search Query")):
    """Search for a movie or TV show by name"""
    query = query.lower()
    movies = load_db(MOVIE_DB)
    tvshows = load_db(TVSHOW_DB)

    matching_movies = [m for m in movies if query in m["title"].lower()]
    matching_tvshows = [t for t in tvshows if query in t["title"].lower()]

    return {
        "movies": matching_movies,
        "tvshows": matching_tvshows
    }
