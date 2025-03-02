from pyrogram import Client, filters
import os

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Client("telegram_movie_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start"))
async def start(client, message):
    print("📩 Received /start command")  # ✅ Debugging
    await message.reply("🎬 Welcome to the Telegram Movie Bot!\n\nUse `/scan` to fetch movies.")

@app.on_message(filters.command("scan"))
async def scan(client, message):
    print("📩 Received /scan command")  # ✅ Debugging
    await message.reply("🔍 Scanning for movies...")

@app.on_message(filters.text)
async def handle_messages(client, message):
    print(f"📨 Received message: {message.text}")  # ✅ Debugging

app.run()
