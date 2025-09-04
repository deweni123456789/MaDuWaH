from pyrogram import Client
from youtube_downloader_module import register_youtube

app = Client("my_bot")
register_youtube(app)

app.run()
