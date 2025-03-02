from pyrogram import Client, filters
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

@app.on_message(filters.command("index") & filters.user(ADMINS))
async def index_channel(client, message):
    """Manually scan all existing movies and TV shows"""
    status_message = await message.reply("⏳ **Starting full indexing... Please wait.**")

    await index_files_to_db(client, MOVIE_CHANNEL_ID, 0, status_message)
    await index_files_to_db(client, TVSHOW_CHANNEL_ID, 0, status_message)

    await status_message.edit("✅ **Full scan completed!** Movies & TV shows updated.")

@app.on_message(filters.video | filters.document)
async def auto_index(client, message):
    """Automatically index new movies or TV shows as they are uploaded"""
    chat_id = message.chat.id
    category = "movies" if chat_id == MOVIE_CHANNEL_ID else "tvshows"

    file_name = message.video.file_name if message.video else message.document.file_name
    file_id = message.video.file_id if message.video else message.document.file_id

    db_file = MOVIE_DB if category == "movies" else TVSHOW_DB
    items = load_db(db_file)

    # Avoid duplicate entries
    if not any(item["file_id"] == file_id for item in items):
        items.append({"title": file_name, "file_id": file_id})
        save_db(db_file, items)

        await message.reply(f"✅ **Automatically indexed `{file_name}` in {category.capitalize()}!**")

@app.on_message(filters.forwarded)
async def forwarded_index(client, message):
    """Trigger indexing when a forwarded message is received"""
    if not message.forward_from_chat:
        await message.reply("❌ **Invalid forward!** Please forward a message from a movie channel.")
        return

    chat_id = message.forward_from_chat.id
    lst_msg_id = message.forward_from_message_id

    if chat_id not in [MOVIE_CHANNEL_ID, TVSHOW_CHANNEL_ID]:
        await message.reply("❌ **Invalid channel!** This bot only indexes authorized movie/TV show channels.")
        return

    msg = await message.reply("⏳ **Starting indexing from this message...**")
    await index_files_to_db(client, chat_id, lst_msg_id, msg)

@app.on_message(filters.regex(r"https://t.me/c/(\d+)/(\d+)"))
async def link_index(client, message):
    """Trigger indexing when a channel link is sent"""
    match = re.search(r"https://t.me/c/(\d+)/(\d+)", message.text)
    if not match:
        await message.reply("❌ **Invalid link!** Please send a valid channel message link.")
        return

    chat_id, lst_msg_id = int(match.group(1)), int(match.group(2))

    if chat_id not in [MOVIE_CHANNEL_ID, TVSHOW_CHANNEL_ID]:
        await message.reply("❌ **Invalid channel!** This bot only indexes authorized movie/TV show channels.")
        return

    msg = await message.reply("⏳ **Starting indexing from this message...**")
    await index_files_to_db(client, chat_id, lst_msg_id, msg)

@app.on_message(filters.command("setskip") & filters.user(ADMINS))
async def set_skip(client, message):
    """Allows admins to set how many messages to skip before indexing"""
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.reply("❌ **Invalid usage!** Use `/setskip <number>`")
        return

    temp.CURRENT = int(args[1])
    await message.reply(f"✅ **Skip set to {temp.CURRENT} messages!**")

@app.on_message(filters.command("cancel") & filters.user(ADMINS))
async def cancel_indexing(client, message):
    """Allows admins to cancel indexing"""
    temp.CANCEL = True
    await message.reply("❌ **Indexing has been canceled!**")

app.run()
