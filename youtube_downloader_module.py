"""
youtube_downloader_module.py

Pyrogram module to auto-detect YouTube links in chats, show inline buttons
(Download Audio, Download Video), and when a button is tapped it downloads
and uploads the requested file with metadata: title, channel, upload_date,
likes, views, comments, duration — and mentions the requester.

Requirements:
    pip install pyrogram tgcrypto yt-dlp humanize

Usage:
    from youtube_downloader_module import register_youtube
    register_youtube(app)

Call register_youtube(app) from your main.py where `app` is your Pyrogram Client.

Notes:
 - Host environment must allow youtube downloads and have enough disk space.
 - Large videos may exceed Telegram upload limits; this module does not split files.
 - Adjust yt-dlp options (format, postprocessors) to suit your needs.

Developer button: @deweni2 (added to keyboard)
"""

import re
import os
import asyncio
import tempfile
import shutil
import time
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import yt_dlp
import humanize

# Regex to detect YouTube URLs (short + full forms)
YOUTUBE_URL_REGEX = re.compile(
    r"(https?://)?(www\.)?(m\.)?(youtube\.com/watch\?v=|youtu\.be/)[A-Za-z0-9_\-]{6,}",
    re.IGNORECASE,
)

# Callback data prefixes
CB_AUDIO = "yt_audio"
CB_VIDEO = "yt_video"

# Developer button URL (replace if you want a different URL/username)
DEVELOPER_USERNAME = "https://t.me/deweni2"


def _build_main_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("Developer @DEWENI2", url=DEVELOPER_USERNAME)]]
    )


def _build_action_keyboard(url):
    # callback_data includes the URL. Be mindful of size — we're using plain URL.
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📥 Download Audio", callback_data=f"{CB_AUDIO}|{url}"),
             InlineKeyboardButton("🎬 Download Video", callback_data=f"{CB_VIDEO}|{url}")],
            [InlineKeyboardButton("Developer @DEWENI2", url=DEVELOPER_USERNAME)],
        ]
    )


async def _edit_progress(msg, text):
    try:
        await msg.edit_text(text)
    except Exception:
        # ignore edit failures (message deleted, no rights, etc.)
        pass


class YTDLPLogger(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)


async def _download_with_yt_dlp(url, output_template, ydl_opts, progress_callback=None):
    loop = asyncio.get_running_loop()

    def run_download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(url, download=True)
            return result

    result = await loop.run_in_executor(None, run_download)
    return result


def _format_metadata(info, requester_mention):
    # info comes from yt_dlp.extract_info(download=False)
    title = info.get("title") or "Unknown title"
    uploader = info.get("uploader") or info.get("channel") or "Unknown channel"
    upload_date = info.get("upload_date")
    if upload_date:
        try:
            d = datetime.strptime(upload_date, "%Y%m%d")
            upload_date = d.strftime("%Y/%m/%d")
        except Exception:
            pass
    duration_seconds = info.get("duration")
    duration = str(duration_seconds) if duration_seconds else "Unknown"
    view_count = info.get("view_count")
    like_count = info.get("like_count")
    comment_count = info.get("comment_count")

    meta = (
        f"**{title}**\n"
        f"Channel: {uploader}\n"
    )
    if upload_date:
        meta += f"Uploaded: {upload_date}\n"
    if duration_seconds:
        meta += f"Duration: {humanize.naturaldelta(duration_seconds)} ({duration_seconds}s)\n"
    if view_count is not None:
        meta += f"Views: {view_count}\n"
    if like_count is not None:
        meta += f"Likes: {like_count}\n"
    if comment_count is not None:
        meta += f"Comments: {comment_count}\n"

    meta += f"Requested by: {requester_mention}"
    return meta


def register_youtube(app: Client):
    """Register handlers on the provided Pyrogram Client instance.

    Call this from your main application code: register_youtube(app)
    """

    @app.on_message(filters.private | filters.group)
    async def _on_message(client, message):
        if not message.text:
            return

        m = YOUTUBE_URL_REGEX.search(message.text)
        if not m:
            return

        url = m.group(0)
        # Quick feedback
        sent = await message.reply_text("🔎 Found YouTube link — fetching info...", reply_markup=_build_main_keyboard())

        # extract info (no download)
        ydl_opts_info = {
            "quiet": True,
            "skip_download": True,
            "logger": YTDLPLogger(),
        }
        try:
            loop = asyncio.get_running_loop()
            def info_extract():
                with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
                    return ydl.extract_info(url, download=False)
            info = await loop.run_in_executor(None, info_extract)
        except Exception as e:
            await sent.edit_text(f"⚠️ Failed to fetch info: {e}")
            return

        # Build the preview caption and buttons
        requester = message.from_user
        requester_mention = requester.mention if requester else "Unknown"
        title = info.get("title", "YouTube video")
        channel = info.get("uploader") or info.get("channel") or "Unknown"
        thumb = None
        # Try to get thumbnail URL
        thumbnails = info.get("thumbnails") or []
        if thumbnails:
            # pick the best available
            thumb = thumbnails[-1].get("url")

        caption = f"**{title}**\nChannel: {channel}\nRequested by: {requester_mention}"

        # send thumbnail preview if available
        try:
            if thumb:
                await sent.edit_text("Preview ready.")
                # We send a new message with photo + inline buttons so it looks clean
                await message.reply_photo(photo=thumb, caption=caption, reply_markup=_build_action_keyboard(url))
                await sent.delete()
            else:
                await sent.edit_text("Preview ready.")
                await message.reply_text(caption, reply_markup=_build_action_keyboard(url))
                await sent.delete()
        except Exception:
            # fallback
            await sent.edit_text("Preview ready. (failed to show thumbnail)")
            await message.reply_text(caption, reply_markup=_build_action_keyboard(url))
            await sent.delete()

    @app.on_callback_query()
    async def _on_callback(client, callback_query):
        data = callback_query.data or ""
        if not (data.startswith(CB_AUDIO) or data.startswith(CB_VIDEO)):
            return

        kind, url = data.split("|", 1)
        user = callback_query.from_user
        requester_mention = user.mention if user else "Unknown"

        status_msg = await callback_query.message.reply_text("⏳ Preparing download...")
        # Prepare temp dir
        tmpdir = tempfile.mkdtemp(prefix="yt_dl_")

        try:
            # Get info again to have fresh metadata
            ydl_opts_info = {"quiet": True, "skip_download": True, "logger": YTDLPLogger()}
            loop = asyncio.get_running_loop()
            def info_extract():
                with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
                    return ydl.extract_info(url, download=False)
            info = await loop.run_in_executor(None, info_extract)

            meta_text = _format_metadata(info, requester_mention)

            # Prepare yt-dlp options depending on requested kind
            out_template = os.path.join(tmpdir, "%(title).100s.%(ext)s")
            if kind == CB_AUDIO:
                ydl_opts = {
                    "format": "bestaudio/best",
                    "outtmpl": out_template,
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }],
                    "logger": YTDLPLogger(),
                    "noplaylist": True,
                }
            else:  # video
                # pick best mp4 fallback
                ydl_opts = {
                    "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4/best",
                    "outtmpl": out_template,
                    "merge_output_format": "mp4",
                    "logger": YTDLPLogger(),
                    "noplaylist": True,
                }

            await status_msg.edit_text("⬇️ Download started... this may take a while")

            # run download
            def run_download_sync():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=True)

            result = await loop.run_in_executor(None, run_download_sync)

            # find downloaded file in tmpdir
            downloaded_file = None
            for root, _, files in os.walk(tmpdir):
                for f in files:
                    downloaded_file = os.path.join(root, f)
                    break
                if downloaded_file:
                    break

            if not downloaded_file or not os.path.exists(downloaded_file):
                await status_msg.edit_text("❌ Download failed or produced no files.")
                return

            filesize = os.path.getsize(downloaded_file)
            pretty_size = humanize.naturalsize(filesize)
            await status_msg.edit_text(f"✅ Downloaded ({pretty_size}). Uploading to Telegram...")

            # Upload as audio or video with metadata caption
            caption = meta_text
            # If file is audio and has .mp3 extension, send as audio
            if kind == CB_AUDIO:
                try:
                    await client.send_audio(
                        chat_id=callback_query.message.chat.id,
                        audio=downloaded_file,
                        caption=caption,
                        reply_markup=_build_main_keyboard(),
                        reply_to_message_id=callback_query.message.message_id,
                    )
                except Exception as e:
                    await status_msg.edit_text(f"📤 Upload failed: {e}")
                    return
            else:
                try:
                    await client.send_video(
                        chat_id=callback_query.message.chat.id,
                        video=downloaded_file,
                        caption=caption,
                        reply_markup=_build_main_keyboard(),
                        reply_to_message_id=callback_query.message.message_id,
                    )
                except Exception as e:
                    # fallback to document
                    try:
                        await client.send_document(
                            chat_id=callback_query.message.chat.id,
                            document=downloaded_file,
                            caption=caption,
                            reply_markup=_build_main_keyboard(),
                            reply_to_message_id=callback_query.message.message_id,
                        )
                    except Exception as e2:
                        await status_msg.edit_text(f"📤 Upload failed: {e2}")
                        return

            await status_msg.edit_text("✅ Done — file uploaded.")

        except Exception as exc:
            await status_msg.edit_text(f"⚠️ Error: {exc}")
        finally:
            # cleanup
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass

            # try to answer callback to remove "loading" on user's side
            try:
                await callback_query.answer()
            except Exception:
                pass


# If module is executed directly for testing
if __name__ == "__main__":
    print("This module is intended to be imported and used inside a Pyrogram Client.")
