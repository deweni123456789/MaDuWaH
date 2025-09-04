from pyrogram import Client
from pyrogram.errors import FloodWait
from modules.yt_downloader import register_youtube
from modules.song_video import register_song_video
import asyncio

API_ID = 5047271
API_HASH = "047d9ed308172e637d4265e1d9ef0c27"
BOT_TOKEN = "7896090354:AAHC8cSQjnGRhJcPFfciVdyKIqABUkZE1mQ"

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

register_youtube(app)
register_song_video(app)

async def start_bot():
    while True:
        try:
            print("🤖 Bot is running...")
            await app.start()
            await app.idle()
            break  # exit loop when stopped normally
        except FloodWait as e:
            print(f"[FLOOD_WAIT] Telegram asked to wait {e.x} seconds. Sleeping...")
            await asyncio.sleep(e.x)

if __name__ == "__main__":
    asyncio.run(start_bot())
