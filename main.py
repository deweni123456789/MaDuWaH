import re
import os
import asyncio
import tempfile
import shutil
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp
import humanize

# ------------------------------
# CONFIG (replace with your own)
# ------------------------------
API_ID = 5047271          # Telegram API ID
API_HASH = "047d9ed308172e637d4265e1d9ef0c27"    # Telegram API HASH
BOT_TOKEN = "7896090354:AAHC8cSQjnGRhJcPFfciVdyKIqABUkZE1mQ"  # Telegram Bot Token
DEVELOPER_URL = "https://t.me/deweni2"
# ------------------------------

# ------------------------------
# YouTube Downloader Module
# ------------------------------
YOUTUBE_URL_REGEX = re.compile(
    r"(https?://)?(www\.)?(m\.)?(youtube\.com/watch\?v=|youtu\.be/)[A-Za-z0-9_\-]{6,}",
    re.IGNORECASE,
)

CB_AUDIO = "yt_audio"
CB_VIDEO = "yt_video"

def _build_keyboard(url):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📥 Download Audio", callback_data=f"{CB_AUDIO}|{url}"),
                InlineKeyboardButton("🎬 Download Video", callback_data=f"{CB_VIDEO}|{url}")
            ],
            [InlineKeyboardButton("Developer @DEWENI2", url=DEVELOPER_URL)]
        ]
    )

def _build_dev_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Developer @DEWENI2", url=DEVELOPER_URL)]])

def _format_metadata(info, requester_mention):
    title = info.get("title", "Unknown title")
    uploader = info.get("uploader") or info.get("channel") or "Unknown channel"
    upload_date = info.get("upload_date")
    if upload_date:
        try:
            d = datetime.strptime(upload_date, "%Y%m%d")
            upload_date = d.strftime("%Y/%m/%d")
        except Exception:
            pass

    duration = info.get("duration")
    view_count = info.get("view_count")
    like_count = info.get("like_count")
    comment_count = info.get("comment_count")

    text = f"**{title}**\nChannel: {uploader}\n"
    if upload_date:
        text += f"Uploaded: {upload_date}\n"
    if duration:
        text += f"Duration: {humanize.naturaldelta(duration)}\n"
    if view_count:
        text += f"Views: {view_count}\n"
    if like_count:
        text += f"Likes: {like_count}\n"
    if comment_count:
        text += f"Comments: {comment_count}\n"

    text += f"Requested by: {requester_mention}"
    return text

def register_youtube(app: Client):

    @app.on_message(filters.text & (filters.private | filters.group))
    async def yt_detect(client, message):
        m = YOUTUBE_URL_REGEX.search(message.text)
        if not m:
            return
        url = m.group(0)
        await message.reply_text(
            "🔎 YouTube link detected!",
            reply_markup=_build_keyboard(url)
        )

    @app.on_callback_query()
    async def yt_callback(client, cq):
        if not cq.data or "|" not in cq.data:
            return
        kind, url = cq.data.split("|", 1)
        user = cq.from_user
        requester = user.mention if user else "Unknown"

        status = await cq.message.reply_text("⏳ Downloading...")
        tmpdir = tempfile.mkdtemp(prefix="yt_dl_")

        try:
            # Get metadata
            def extract():
                with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
                    return ydl.extract_info(url, download=False)

            loop = asyncio.get_running_loop()
            info = await loop.run_in_executor(None, extract)

            meta = _format_metadata(info, requester)
            outtmpl = os.path.join(tmpdir, "%(title).100s.%(ext)s")

            if kind == CB_AUDIO:
                ydl_opts = {
                    "format": "bestaudio/best",
                    "outtmpl": outtmpl,
                    "postprocessors": [
                        {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
                    ],
                }
            else:
                ydl_opts = {
                    "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4/best",
                    "outtmpl": outtmpl,
                    "merge_output_format": "mp4",
                }

            def download():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=True)

            result = await loop.run_in_executor(None, download)

            # find file
            file_path = None
            for root, _, files in os.walk(tmpdir):
                for f in files:
                    file_path = os.path.join(root, f)
                    break

            if not file_path:
                await status.edit("❌ Download failed.")
                return

            if kind == CB_AUDIO:
                await client.send_audio(
                    chat_id=cq.message.chat.id,
                    audio=file_path,
                    caption=meta,
                    reply_markup=_build_dev_keyboard(),
                    reply_to_message_id=cq.message.id
                )
            else:
                await client.send_video(
                    chat_id=cq.message.chat.id,
                    video=file_path,
                    caption=meta,
                    reply_markup=_build_dev_keyboard(),
                    reply_to_message_id=cq.message.id
                )

            await status.edit("✅ Done!")

        except Exception as e:
            await status.edit(f"⚠️ Error: {e}")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
            try:
                await cq.answer()
            except:
                pass

# ------------------------------
# RUN BOT
# ------------------------------
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
register_youtube(app)
print("🤖 Bot is running...")
app.run()
