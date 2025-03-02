from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import json
import asyncio
import re
import logging

# Setup logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
    if not os.path.exists(filename):
        return []
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.error(f"Error loading {filename}: {e}")
        return []
    except Exception as e:
        logger.exception(f"Unexpected error loading {filename}: {e}")
        return []

def save_db(filename, data):
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.exception(f"Error saving to {filename}: {e}")


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
    """Index files from a given chat ID."""
    global temp
    temp.CANCEL = False

    async with lock:
        found_files = 0
        try:
            # Load the appropriate database *once* outside the loop
            category = "movies" if chat == MOVIE_CHANNEL_ID else "tvshows"
            db_file = MOVIE_DB if category == "movies" else TVSHOW_DB
            items = load_db(db_file)
            existing_file_ids = {item["file_id"] for item in items} # Use a set for efficiency

            offset = temp.CURRENT
            while True:
                if temp.CANCEL:
                    await msg.edit("❌ **Indexing canceled!**")
                    return

                messages = await bot.get_messages(chat, list(range(lst_msg_id - offset - 99, lst_msg_id - offset + 1)))

                if not messages:
                    break
                
                for message in reversed(messages):  # Process messages in correct order
                    if not message or not message.media:
                        continue

                    file_name = message.document.file_name if message.document else message.video.file_name
                    file_id = message.document.file_id if message.document else message.video.file_id

                    if file_id not in existing_file_ids:
                        items.append({"title": file_name, "file_id": file_id})
                        existing_file_ids.add(file_id)  # Add to the set
                        found_files += 1

                if found_files % 20 == 0:
                        await msg.edit(f"📡 Indexing `{category}`: {found_files} files indexed...")
                offset += 100
                await asyncio.sleep(0.5)

        except Exception as e:
            logger.exception(f"Error during indexing: {e}")
            await msg.edit(f"❌ **An error occurred during indexing: {e}**")
            return
        finally:
            # Save changes to the database *after* the loop (or in the except block)
            save_db(db_file, items)
            await msg.edit(f"✅ **Indexing completed!** {found_files} files added.")




@app.on_message(filters.forwarded)
async def forwarded_index(client, message):
    """Handle forwarded messages"""
    if message.forward_from_chat:  # Forwarded from a channel
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
            await message.reply(f"❌ Error accessing channel information {e}")
            return


        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes, Index Full Channel", callback_data=f"index_full_{chat_id}_{lst_msg_id}")],
            [InlineKeyboardButton("❌ No, Just Save This File", callback_data=f"index_single_{chat_id}_{lst_msg_id}")]
        ])
        await message.reply("📡 **Do you want to index the full channel or just this message?**", reply_markup=buttons)

    else: # Manually forwarded
        if message.document or message.video:
             buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎬 Movie", callback_data=f"save_manual_movie")],
                [InlineKeyboardButton("📺 TV Show", callback_data=f"save_manual_tvshow")]
            ])
             await message.reply("Is this a movie or a TV show?", reply_markup=buttons)

@app.on_callback_query(filters.regex("^save_manual_(movie|tvshow)$"))
async def save_manual_callback(client, callback_query):
    message = callback_query.message.reply_to_message
    category = callback_query.data.split("_")[2]
    if message.document or message.video:
        file_name = message.document.file_name if message.document else message.video.file_name
        file_id = message.document.file_id if message.document else message.video.file_id
        db_file = MOVIE_DB if category == "movie" else TVSHOW_DB
        items = load_db(db_file)
        if not any(item["file_id"] == file_id for item in items):
                items.append({"title": file_name, "file_id": file_id})
                save_db(db_file, items)
                await callback_query.message.edit_text(f"✅ **Saved `{file_name}` to {category}!**")
        else:
                await callback_query.message.edit_text(f"✅ **`{file_name}` already exists!**")

@app.on_callback_query(filters.regex("^index_full_"))
async def full_index_callback(client, callback_query):
    """Handles full channel indexing."""
    data_parts = callback_query.data.split("_")
    chat_id_str = data_parts[2]  # Get chat_id as string
    lst_msg_id = int(data_parts[3])  # lst_msg_id is always an integer

    # Handle both numeric IDs and usernames
    try:
        chat_id = int(chat_id_str) if chat_id_str.lstrip("-").isdigit() else chat_id_str
    except ValueError:
        await callback_query.message.edit_text("❌ Invalid chat ID format.")
        return
    msg = await callback_query.message.edit_text("⏳ **Starting full indexing... Please wait.**")
    await index_files_to_db(client, chat_id, lst_msg_id, msg)  # Await the function call


@app.on_callback_query(filters.regex("^index_single_"))
async def single_index_callback(client, callback_query):
    """Handles single file indexing."""
    data_parts = callback_query.data.split("_")
    chat_id_str = data_parts[2]
    lst_msg_id = int(data_parts[3])

    try:
        chat_id = int(chat_id_str) if chat_id_str.lstrip("-").isdigit() else chat_id_str
    except ValueError:
        await callback_query.message.edit_text("❌ Invalid chat ID format.")
        return

    try:
        message = await client.get_messages(chat_id, lst_msg_id) # Use get_messages for a single message
        if message.document or message.video:
                file_name = message.document.file_name if message.document else message.video.file_name
                file_id = message.document.file_id if message.document else message.video.file_id
                category = "movies" if chat_id == MOVIE_CHANNEL_ID else "tvshows" # Determine based on the channel
                db_file = MOVIE_DB if category == "movies" else TVSHOW_DB
                items = load_db(db_file)

                if not any(item["file_id"] == file_id for item in items):
                    items.append({"title": file_name, "file_id": file_id})
                    save_db(db_file, items)
                    await callback_query.message.edit_text(f"✅ **Saved `{file_name}` successfully!**")
                else:
                    await callback_query.message.edit_text(f"✅ **`{file_name}` already exists!**")
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
