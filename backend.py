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

@app.get("/")
async def root():
    return {"message": "API is running!"}

@app.get("/movies")
async def get_movies():
    """Fetch all movies"""
    return {"movies": load_db(MOVIE_DB)}

@app.get("/tvshows")
async def get_tvshows():
    """Fetch all TV shows"""
    return {"tvshows": load_db(TVSHOW_DB)}
