from pyrogram import Client
from modules.yt_downloader import register_youtube

# ------------------------------
# CONFIG
# ------------------------------
API_ID = 123456          # Telegram API ID
API_HASH = "abcdef123"    # Telegram API HASH
BOT_TOKEN = "YOUR_BOT_TOKEN"  # Telegram Bot Token
# ------------------------------

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Register the YouTube downloader module
register_youtube(app)

print("🤖 Bot is running...")
app.run()
