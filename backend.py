from fastapi import FastAPI
import json

app = FastAPI()

MOVIE_DB = "movies.json"
TVSHOW_DB = "tvshows.json"

def load_db(filename):
    """Loads a database from JSON"""
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except:
        return []

@app.get("/movies")
async def get_movies():
    """Fetches all movies from the database"""
    return {"movies": load_db(MOVIE_DB)}

@app.get("/tvshows")
async def get_tvshows():
    """Fetches all TV shows from the database"""
    return {"tvshows": load_db(TVSHOW_DB)}
