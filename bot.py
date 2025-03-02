from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import json
import asyncio
import re

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

# Asynchronous lock to prevent concurrent indexing
lock = asyncio.Lock()

# Track indexing status
class IndexStatus:
    CANCEL = False
    CURRENT = 0  # Skip this many messages before starting

temp = IndexStatus()

# Load database
def load_db(filename):
    if not os.path.exists(filename):
        return []
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_db(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

@app.on_message(filters.command("start"))
async def start(client, message):
    """Send a welcome message when the user starts the bot"""
    await message.reply(
        "**🎬 Welcome to the Telegram Movie Bot!**\n\n"
        "✅ This bot automatically indexes movies & TV shows from channels.\n"
        "📡 Use `/index` to scan all existing files in the channels.\n"
        "🔍 Just type a movie name to search for it!\n\n"
        "🚀 **Start by forwarding a message from the channel or sending a channel link!**"
    )

async def index_files_to_db(bot, chat, lst_msg_id, msg):
    """Index files from a given chat ID using iter_messages"""
    global temp
    temp.CANCEL = False

    async with lock:
        found_files = 0
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

            # Avoid duplicate entries
            if not any(item["file_id"] == file_id for item in items):
                items.append({"title": file_name, "file_id": file_id})
                save_db(db_file, items)
                found_files += 1

            # Send progress update every 20 files
            if found_files % 20 == 0:
                await msg.edit(f"📡 Indexing `{category}`: {found_files} files indexed...")

    await msg.edit(f"✅ **Indexing completed!** {found_files} files added.")

@app.on_message(filters.forwarded)
async def forwarded_index(client, message):
    """Handle forwarded messages from channels"""
    if message.forward_from_chat:
        # Message was forwarded from a channel
        chat_id = message.forward_from_chat.id
        lst_msg_id = message.forward_from_message_id

        if chat_id not in [MOVIE_CHANNEL_ID, TVSHOW_CHANNEL_ID]:
            await message.reply("❌ **Invalid channel!** This bot only indexes authorized movie/TV show channels.")
            return
        
        # Ask user whether to index full channel or just this message
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes, Index Full Channel", callback_data=f"index_full_{chat_id}_{lst_msg_id}")],
            [InlineKeyboardButton("❌ No, Just Save This File", callback_data=f"index_single_{chat_id}_{lst_msg_id}")]
        ])
        await message.reply("📡 **Do you want to index the full channel or just this message?**", reply_markup=buttons)
    
    else:
        # Message was manually forwarded (no "Forwarded from" tag)
        if message.document or message.video:
            file_name = message.document.file_name if message.document else message.video.file_name
            file_id = message.document.file_id if message.document else message.video.file_id

            category = "movies"
            db_file = MOVIE_DB if category == "movies" else TVSHOW_DB
            items = load_db(db_file)

            # Avoid duplicate entries
            if not any(item["file_id"] == file_id for item in items):
                items.append({"title": file_name, "file_id": file_id})
                save_db(db_file, items)

                await message.reply(f"✅ **Saved `{file_name}` successfully!**")

@app.on_callback_query(filters.regex("^index_full_(\\d+)_(\\d+)$"))
async def full_index_callback(client, callback_query):
    """Handles full indexing when user selects 'Yes'"""
    chat_id, lst_msg_id = map(int, callback_query.data.split("_")[2:])
    
    msg = await callback_query.message.edit_text("⏳ **Starting full indexing... Please wait.**")
    await index_files_to_db(client, chat_id, lst_msg_id, msg)

@app.on_callback_query(filters.regex("^index_single_(\\d+)_(\\d+)$"))
async def single_index_callback(client, callback_query):
    """Handles single file indexing when user selects 'No'"""
    chat_id, lst_msg_id = map(int, callback_query.data.split("_")[2:])

    async for message in client.iter_messages(chat_id, lst_msg_id):
        if message.document or message.video:
            file_name = message.document.file_name if message.document else message.video.file_name
            file_id = message.document.file_id if message.document else message.video.file_id

            category = "movies"
            db_file = MOVIE_DB if category == "movies" else TVSHOW_DB
            items = load_db(db_file)

            if not any(item["file_id"] == file_id for item in items):
                items.append({"title": file_name, "file_id": file_id})
                save_db(db_file, items)

            await callback_query.message.edit_text(f"✅ **Saved `{file_name}` successfully!**")
            return

@app.on_message(filters.command("cancel") & filters.user(ADMINS))
async def cancel_indexing(client, message):
    """Allows admins to cancel indexing"""
    temp.CANCEL = True
    await message.reply("❌ **Indexing has been canceled!**")

app.run()
