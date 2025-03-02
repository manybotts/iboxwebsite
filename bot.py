from pyrogram import Client, filters
import json
import os

# Telegram API Config
API_ID = os.getenv("API_ID", "YOUR_TELEGRAM_API_ID")
API_HASH = os.getenv("API_HASH", "YOUR_TELEGRAM_API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
MOVIE_CHANNEL_ID = int(os.getenv("MOVIE_CHANNEL_ID", "YOUR_MOVIE_CHANNEL_ID"))
TVSHOW_CHANNEL_ID = int(os.getenv("TVSHOW_CHANNEL_ID", "YOUR_TVSHOW_CHANNEL_ID"))
ADMIN_ID = int(os.getenv("ADMIN_ID", "YOUR_TELEGRAM_USER_ID"))

app = Client("movie_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

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

@app.on_message(filters.private & filters.command("request"))
async def request_movie(client, message):
    """Handles user movie requests and searches existing collection"""
    try:
        _, title = message.text.split(maxsplit=1)
    except ValueError:
        await message.reply("❌ Error: Use `/request <movie-name>`")
        return

    movies = load_db(MOVIE_DB)
    for movie in movies:
        if title.lower() in movie["title"].lower():
            await message.reply(f"✅ **{movie['title']}** is available!\n🎥 Watch here: [Click to Stream](https://your-stream-domain.com/watch/{movie['file_id']})", disable_web_page_preview=True)
            return

    requests = load_db(REQUESTS_DB)
    requests.append({"title": title, "user_id": message.chat.id, "username": message.from_user.username})
    save_db(REQUESTS_DB, requests)

    await message.reply(f"⚠️ **{title}** is not available. Your request has been logged ✅.")

app.run()
