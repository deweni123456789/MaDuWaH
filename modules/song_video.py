# modules/song_video.py
import os
import asyncio
import tempfile
import shutil
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp
import humanize

DEVELOPER_URL = "https://t.me/deweni2"
COOKIES_FILE = "cookies.txt"  # optional

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
        except:
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
    text += f"\nRequested by: {requester_mention}"
    return text

def register_song_video(app: Client):
    async def download_media(query, requester, is_audio=True):
        tmpdir = tempfile.mkdtemp(prefix="song_video_dl_")
        ydl_opts = {
            "format": "bestaudio/best" if is_audio else "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4/best",
            "noplaylist": True,
            "outtmpl": os.path.join(tmpdir, "%(title).100s.%(ext)s"),
            "quiet": True,
            "default_search": "ytsearch1",
        }
        if is_audio:
            ydl_opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]

        if os.path.exists(COOKIES_FILE):
            ydl_opts["cookiefile"] = COOKIES_FILE

        loop = asyncio.get_running_loop()

        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(query, download=True)

        info = await loop.run_in_executor(None, download)
        file_path = None
        for root, _, files in os.walk(tmpdir):
            for f in files:
                file_path = os.path.join(root, f)
                break
            if file_path:
                break
        return file_path, _format_metadata(info, requester), tmpdir

    @app.on_message(filters.command("song", prefixes=["/", "!"]))
    async def song_handler(client, message):
        if len(message.command) < 2:
            return await message.reply_text("❌ Please provide a song name.\nUsage: `/song Shape of You`")
        query = " ".join(message.command[1:])
        requester = message.from_user.mention if message.from_user else "Unknown"

        status = await message.reply_text(f"🎶 Searching `{query}` ...")
        try:
            file_path, meta, tmpdir = await download_media(query, requester, is_audio=True)
            if not file_path:
                await status.edit("❌ Download failed.")
                await asyncio.sleep(3)
                await status.delete()
                return

            await client.send_audio(chat_id=message.chat.id, audio=file_path, caption=meta, reply_markup=_build_dev_keyboard(), reply_to_message_id=message.id)
            await status.delete()
        except Exception as e:
            await status.edit(f"⚠️ Error: {e}")
            await asyncio.sleep(4)
            await status.delete()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    @app.on_message(filters.command("video", prefixes=["/", "!"]))
    async def video_handler(client, message):
        if len(message.command) < 2:
            return await message.reply_text("❌ Please provide a video name.\nUsage: `/video <name>`")
        query = " ".join(message.command[1:])
        requester = message.from_user.mention if message.from_user else "Unknown"

        status = await message.reply_text(f"🎬 Searching `{query}` ...")
        try:
            file_path, meta, tmpdir = await download_media(query, requester, is_audio=False)
            if not file_path:
                await status.edit("❌ Download failed.")
                await asyncio.sleep(3)
                await status.delete()
                return

            await client.send_video(chat_id=message.chat.id, video=file_path, caption=meta, reply_markup=_build_dev_keyboard(), reply_to_message_id=message.id)
            await status.delete()
        except Exception as e:
            await status.edit(f"⚠️ Error: {e}")
            await asyncio.sleep(4)
            await status.delete()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
