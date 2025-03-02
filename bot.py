from pyrogram import Client, filters
import json
import os

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MOVIE_CHANNEL_ID = int(os.getenv("MOVIE_CHANNEL_ID"))
TVSHOW_CHANNEL_ID = int(os.getenv("TVSHOW_CHANNEL_ID"))

app = Client("scan_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

MOVIE_DB = "movies.json"
TVSHOW_DB = "tvshows.json"

def save_db(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

async def fetch_all_files(channel_id, category):
    """Fetches all movies/TV shows from Telegram channels"""
    async with app:
        messages = await app.get_chat_history(channel_id, limit=1000)
        items = [
            {
                "title": msg.video.file_name if msg.video else msg.document.file_name,
                "file_id": msg.video.file_id if msg.video else msg.document.file_id,
            }
            for msg in messages if msg.video or msg.document
        ]
    save_db(MOVIE_DB if category == "movies" else TVSHOW_DB, items)
    print(f"✅ Scanned {len(items)} {category}")

@app.on_message(filters.command("scan"))
async def scan_all(client, message):
    """Command to scan entire Telegram channel"""
    await fetch_all_files(MOVIE_CHANNEL_ID, "movies")
    await fetch_all_files(TVSHOW_CHANNEL_ID, "tvshows")
    await message.reply("✅ Scanning completed. Database updated.")

app.run()
