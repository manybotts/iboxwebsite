from pyrogram import Client, filters
import json
import os
import asyncio

# Load environment variables
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MOVIE_CHANNEL_ID = int(os.getenv("MOVIE_CHANNEL_ID"))
TVSHOW_CHANNEL_ID = int(os.getenv("TVSHOW_CHANNEL_ID"))

app = Client("telegram_movie_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

MOVIE_DB = "movies.json"
TVSHOW_DB = "tvshows.json"

def save_db(filename, data):
    """Saves data to JSON file"""
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

def load_db(filename):
    """Loads data from JSON file"""
    if not os.path.exists(filename):
        return []
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

async def fetch_all_files(client, chat_id, category, message):
    """Fetches all movies/TV shows from a Telegram channel"""
    items = []
    async for msg in client.get_chat_history(chat_id, limit=1000):
        if msg.video or msg.document:
            file_name = msg.video.file_name if msg.video else msg.document.file_name
            file_id = msg.video.file_id if msg.video else msg.document.file_id
            items.append({"title": file_name, "file_id": file_id})

            # Send progress update every 50 files
            if len(items) % 50 == 0:
                await message.edit(f"📡 Indexing `{category}`: {len(items)} files found...")

    # Save to database
    save_db(MOVIE_DB if category == "movies" else TVSHOW_DB, items)
    await message.edit(f"✅ `{category}` indexing completed! Total: {len(items)} files.")

@app.on_message(filters.command("start"))
async def start(client, message):
    """Send a welcome message when the user starts the bot"""
    await message.reply(
        "**🎬 Welcome to the Telegram Movie Bot!**\n\n"
        "✅ This bot allows you to stream movies directly from Telegram.\n"
        "📡 Use `/scan` to index all available movies & TV shows.\n"
        "🔍 You can search for a movie by name, and the bot will check if it's available.\n\n"
        "🚀 **Get started by sending `/scan` to update the movie list!**"
    )

@app.on_message(filters.command("scan"))
async def scan_all(client, message):
    """Command to scan all movies and TV shows"""
    status_message = await message.reply("⏳ Starting full scan... Please wait.")
    
    await fetch_all_files(client, MOVIE_CHANNEL_ID, "movies", status_message)
    await fetch_all_files(client, TVSHOW_CHANNEL_ID, "tvshows", status_message)
    
    await status_message.edit("✅ **Full scan completed!** Movies & TV shows updated.")

@app.on_message(filters.text)
async def search_movie(client, message):
    """Search for a movie or TV show by name"""
    query = message.text.lower()
    movies = load_db(MOVIE_DB)
    tvshows = load_db(TVSHOW_DB)

    matching_movies = [m for m in movies if query in m["title"].lower()]
    matching_tvshows = [t for t in tvshows if query in t["title"].lower()]

    if matching_movies or matching_tvshows:
        response = "🎬 **Search Results:**\n\n"
        for movie in matching_movies:
            response += f"🎥 `{movie['title']}` - [Watch](https://t.me/{client.me.username}?start={movie['file_id']})\n"
        for show in matching_tvshows:
            response += f"📺 `{show['title']}` - [Watch](https://t.me/{client.me.username}?start={show['file_id']})\n"
        await message.reply(response, disable_web_page_preview=True)
    else:
        await message.reply("❌ No results found. Try another name.")

app.run()
