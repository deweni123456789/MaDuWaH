from pyrogram import Client
from modules.yt_downloader import register_youtube
from modules.song_video import register_song_video

# ------------------------------
# CONFIG
# ------------------------------
API_ID = 5047271         # Telegram API ID
API_HASH = "047d9ed308172e637d4265e1d9ef0c27"    # Telegram API HASH
BOT_TOKEN = "7896090354:AAHC8cSQjnGRhJcPFfciVdyKIqABUkZE1mQ"  # Telegram Bot Token
# ------------------------------

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Register the YouTube downloader module
register_youtube(app)
register_song_video(app)

print("🤖 Bot is running...")
app.run()
