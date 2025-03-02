from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import json
import asyncio
import logging

# Setup logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MOVIE_CHANNEL_ID = int(os.getenv("MOVIE_CHANNEL_ID"))
TVSHOW_CHANNEL_ID = int(os.getenv("TVSHOW_CHANNEL_ID"))
ADMINS = [int(admin) for admin in os.getenv("ADMINS", "").split(",") if admin]

# Initialize bot
app = Client("movie_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Database files
MOVIE_DB = "movies.json"
TVSHOW_DB = "tvshows.json"

# Asynchronous lock
lock = asyncio.Lock()

# Track indexing status
class IndexStatus:
    CANCEL = False
    CURRENT = 0

temp = IndexStatus()

# Load database
def load_db(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_db(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

@app.on_message(filters.command("start"))
async def start(client, message):
    """Send a welcome message"""
    await message.reply(
        "**🎬 Welcome to the Telegram Movie Bot!**\n\n"
        "✅ This bot indexes movies & TV shows from authorized channels.\n"
        "📡 Forward a message from a channel to start indexing.\n"
        "🔍 Type a movie name to search.\n"
        "🚀 **Forward a message now to begin!**"
    )

async def index_files_to_db(bot, chat, lst_msg_id, msg):
    """Index files from a given chat ID with proper stopping conditions."""
    global temp
    temp.CANCEL = False

    async with lock:
        found_files = 0
        category = "movies" if chat == MOVIE_CHANNEL_ID else "tvshows"
        db_file = MOVIE_DB if category == "movies" else TVSHOW_DB
        items = load_db(db_file)
        existing_file_ids = {item["file_id"] for item in items}

        offset = temp.CURRENT
        while True:
            if temp.CANCEL:
                await msg.edit("❌ **Indexing canceled!**")
                return

            start_id = max(1, lst_msg_id - offset - 99)  # Ensure start_id is at least 1
            end_id = lst_msg_id - offset + 1

            # **🚀 FIX: Stop if there are no more messages**
            if start_id >= end_id:
                break  

            message_ids = list(range(start_id, end_id))
            messages = await bot.get_messages(chat, message_ids)

            if not messages:
                break  

            for message in messages:
                if not message or not message.media:
                    continue

                # ✅ Efficient file processing
                file_name = message.video.file_name if message.video else message.document.file_name
                file_id = message.video.file_id if message.video else message.document.file_id

                if file_id not in existing_file_ids:
                    items.append({"title": file_name, "file_id": file_id})
                    existing_file_ids.add(file_id)
                    found_files += 1

            if found_files % 20 == 0:
                await msg.edit(f"📡 Indexing `{category}`: {found_files} files indexed...")

            offset += 100
            await asyncio.sleep(0.5)  

        # ✅ Save changes **after processing**
        save_db(db_file, items)
        await msg.edit(f"✅ **Indexing completed!** {found_files} files added.")

@app.on_message(filters.forwarded)
async def forwarded_index(client, message):
    """Handle forwarded messages"""
    if message.forward_from_chat:  
        chat_id = message.forward_from_chat.id
        lst_msg_id = message.forward_from_message_id

        if chat_id not in [MOVIE_CHANNEL_ID, TVSHOW_CHANNEL_ID]:
            await message.reply("❌ **Invalid channel!** Only authorized channels can be indexed.")
            return

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes, Index Full Channel", callback_data=f"index_full_{chat_id}_{lst_msg_id}")],
            [InlineKeyboardButton("❌ No, Just Save This File", callback_data=f"index_single_{chat_id}_{lst_msg_id}")]
        ])
        await message.reply("📡 **Do you want to index the full channel or just this message?**", reply_markup=buttons)

    else:  
        if message.document or message.video:
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎬 Movie", callback_data="classify_manual_movie")],
                [InlineKeyboardButton("📺 TV Show", callback_data="classify_manual_tvshow")]
            ])
            await message.reply("📡 **Is this a Movie or a TV Show?**", reply_markup=buttons)

@app.on_callback_query(filters.regex("^classify_manual_(movie|tvshow)$"))
async def classify_manual_callback(client, callback_query):
    """Handles manual file classification."""
    category = callback_query.data.split("_")[2]
    message = callback_query.message.reply_to_message

    if message.document or message.video:
        file_name = message.video.file_name if message.video else message.document.file_name
        file_id = message.video.file_id if message.video else message.document.file_id

        db_file = MOVIE_DB if category == "movie" else TVSHOW_DB
        items = load_db(db_file)

        if not any(item["file_id"] == file_id for item in items):
            items.append({"title": file_name, "file_id": file_id})
            save_db(db_file, items)
            await callback_query.message.edit_text(f"✅ **Saved `{file_name}` to {category.capitalize()}!**")
        else:
            await callback_query.message.edit_text(f"✅ **`{file_name}` already exists!**")

@app.on_callback_query(filters.regex("^index_full_"))
async def full_index_callback(client, callback_query):
    """Handles full channel indexing."""
    data_parts = callback_query.data.split("_")
    chat_id = int(data_parts[2])
    lst_msg_id = int(data_parts[3])

    msg = await callback_query.message.edit_text("⏳ **Starting full indexing... Please wait.**")
    await index_files_to_db(client, chat_id, lst_msg_id, msg)

@app.on_message(filters.command("cancel") & filters.user(ADMINS))
async def cancel_indexing(client, message):
    """Allows admins to cancel indexing"""
    temp.CANCEL = True
    await message.reply("❌ **Indexing has been canceled!**")

@app.on_message(filters.text)
async def search_movie(client, message):
    """Search for a movie or TV show by name"""
    query = message.text.lower()
    movies = load_db(MOVIE_DB)
    tvshows = load_db(TVSHOW_DB)

    matching_movies = [m for m in movies if query in m["title"].lower()]
    matching_tvshows = [t for t in tvshows if query in t["title"].lower()]

    response = "🎬 **Search Results:**\n\n"
    response += "\n".join(f"🎥 `{m['title']}`" for m in matching_movies)
    response += "\n".join(f"📺 `{t['title']}`" for t in matching_tvshows)

    await message.reply(response or "❌ No results found.", disable_web_page_preview=True)

app.run()
