from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import json
import asyncio
import re
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Load environment variables
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MOVIE_CHANNEL_ID = int(os.getenv("MOVIE_CHANNEL_ID"))  # Keep as int for now, but string is generally safer
TVSHOW_CHANNEL_ID = int(os.getenv("TVSHOW_CHANNEL_ID"))   # Keep as int for now
ADMINS = [int(admin) for admin in os.getenv("ADMINS", "").split(",") if admin]

# Initialize bot
app = Client("movie_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Database files
MOVIE_DB = "movies.json"
TVSHOW_DB = "tvshows.json"

# Asynchronous lock to prevent concurrent indexing
lock = asyncio.Lock()

# Track indexing status
class IndexStatus:
    CANCEL = False
    CURRENT = 0  # Skip this many messages

temp = IndexStatus()

# Load database
def load_db(filename):
    if not os.path.exists(filename):
        return []
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.exception("Error decoding JSON from %s", filename)
        return []
    except Exception as e:
        logger.exception("Error loading database from %s: %s", filename, e)
        return []

def save_db(filename, data):
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.exception("Error saving to database %s: %s", filename, e)

@app.on_message(filters.command("start"))
async def start(client, message):
    """Send a welcome message"""
    await message.reply(
        "**🎬 Welcome to the Telegram Movie Bot!**\n\n"
        "✅ This bot indexes movies & TV shows from authorized channels.\n"
        "📡 Forward a message from a channel or send a channel link to start indexing.\n"
        "🔍 Type a movie name to search.\n"
        "🚀 **Forward a message now to begin!**"
    )

async def index_files_to_db(bot, chat, lst_msg_id, msg):
    """Index files from a given chat ID."""
    global temp
    temp.CANCEL = False

    async with lock:
        found_files = 0
        try:
            async for message in bot.iter_messages(chat, lst_msg_id, offset_id=temp.CURRENT):
                if temp.CANCEL:
                    await msg.edit("❌ **Indexing canceled!**")
                    return

                if not message or not message.media:
                    continue

                file_name = message.document.file_name if message.document else message.video.file_name
                file_id = message.document.file_id if message.document else message.video.file_id

                category = "movies" if chat == MOVIE_CHANNEL_ID else "tvshows"
                db_file = MOVIE_DB if category == "movies" else TVSHOW_DB
                items = load_db(db_file)

                if not any(item["file_id"] == file_id for item in items):
                    items.append({"title": file_name, "file_id": file_id})
                    save_db(db_file, items)
                    found_files += 1

                if found_files % 20 == 0:
                    await msg.edit(f"📡 Indexing `{category}`: {found_files} files indexed...")

                await asyncio.sleep(0.5)  # Rate limiting

        except Exception as e:
            logger.exception("Error during indexing: %s", e)
            await msg.edit(f"❌ **An error occurred during indexing: {e}**")
            return

    await msg.edit(f"✅ **Indexing completed!** {found_files} files added.")


@app.on_message(filters.forwarded)
async def forwarded_index(client, message):
    """Handle forwarded messages from channels"""
    if message.forward_from_chat:
        chat_id = message.forward_from_chat.id
        lst_msg_id = message.forward_from_message_id

        if chat_id not in [MOVIE_CHANNEL_ID, TVSHOW_CHANNEL_ID]:
            await message.reply("❌ **Invalid channel!** Only authorized channels can be indexed.")
            return

        try:
            chat_member = await client.get_chat_member(chat_id, "me")
            if chat_member.status not in (enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER):
                await message.reply("❌ **I am not an administrator in this channel. I need to be an admin to index files.**")
                return

        except Exception as e:
            await message.reply(f"❌ Error accesssing channel information {e}")
            return

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes, Index Full Channel", callback_data=f"index_full_{chat_id}_{lst_msg_id}")],
            [InlineKeyboardButton("❌ No, Just Save This File", callback_data=f"index_single_{chat_id}_{lst_msg_id}")]
        ])
        await message.reply("📡 **Do you want to index the full channel or just this message?**", reply_markup=buttons)

    else:
        # Handle manually forwarded messages (no "Forwarded from" tag)
        if message.document or message.video:
            file_name = message.document.file_name if message.document else message.video.file_name
            file_id = message.document.file_id if message.document else message.video.file_id
            category = "movies"  # Default to movies, or try to determine from context if possible
            db_file = MOVIE_DB if category == "movies" else TVSHOW_DB
            items = load_db(db_file)

            if not any(item["file_id"] == file_id for item in items):
                items.append({"title": file_name, "file_id": file_id})
                save_db(db_file, items)
                await message.reply(f"✅ **Saved `{file_name}` successfully!**")

@app.on_callback_query(filters.regex("^index_full_(\\d+)_(\\d+)$"))
async def full_index_callback(client, callback_query):
    """Handles full channel indexing."""
    chat_id, lst_msg_id = map(int, callback_query.data.split("_")[2:])

    msg = await callback_query.message.edit_text("⏳ **Starting full indexing... Please wait.**")
    await index_files_to_db(client, chat_id, lst_msg_id, msg)

@app.on_callback_query(filters.regex("^index_single_(\\d+)_(\\d+)$"))
async def single_index_callback(client, callback_query):
    """Handles single file indexing."""
    chat_id, lst_msg_id = map(int, callback_query.data.split("_")[2:])

    try:
        async for message in client.iter_messages(chat_id, lst_msg_id, limit=1):  # Limit to 1
            if message.document or message.video:
                file_name = message.document.file_name if message.document else message.video.file_name
                file_id = message.document.file_id if message.document else message.video.file_id
                category = "movies"  # Default to movies
                db_file = MOVIE_DB if category == "movies" else TVSHOW_DB
                items = load_db(db_file)

                if not any(item["file_id"] == file_id for item in items):
                    items.append({"title": file_name, "file_id": file_id})
                    save_db(db_file, items)
                    await callback_query.message.edit_text(f"✅ **Saved `{file_name}` successfully!**")
                    return # Exit after saving one file
    except Exception as e:
        await callback_query.message.edit_text(f"❌ **An error occurred: {e}**")

@app.on_message(filters.command("setskip") & filters.user(ADMINS))
async def set_skip(client, message):
    if len(message.command) > 1:
        try:
            skip_count = int(message.command[1])
            temp.CURRENT = skip_count
            await message.reply(f"✅ Skip count set to {skip_count}")
        except ValueError:
            await message.reply("❌ Invalid skip count. Please provide a number.")
    else:
        await message.reply("❌ Please provide a skip count (e.g., `/setskip 100`).")


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

    if matching_movies or matching_tvshows:
        response = "🎬 **Search Results:**\n\n"
        for movie in matching_movies:
            response += f"🎥 `{movie['title']}`\n"
        for show in matching_tvshows:
            response += f"📺 `{show['title']}`\n"
        await message.reply(response, disable_web_page_preview=True)
    else:
        await message.reply("❌ No results found. Try another name.")
app.run()
