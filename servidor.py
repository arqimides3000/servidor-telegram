import asyncio
import os
from flask import Flask, Response, request
from pyrogram import Client
import requests

app = Flask(__name__)

API_ID = int(os.environ.get("TELEGRAM_API_ID", 0))
API_HASH = os.environ.get("TELEGRAM_API_HASH")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

channel_id_env = os.environ.get("TELEGRAM_CHANNEL_ID")
try:
  CHANNEL_ID = int(channel_id_env) if channel_id_env else 0
except ValueError:
  CHANNEL_ID = channel_id_env


@app.route("/")
def home():
  return "HELLO, WORLD!"


@app.route("/stream/<int:msg_id>")
def stream_telegram(msg_id):
  try:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def get_url():
      async with Client(
          "mi_bot_session",
          api_id=API_ID,
          api_hash=API_HASH,
          bot_token=BOT_TOKEN,
          in_memory=True,
      ) as app_client:
        msg = await app_client.get_messages(CHANNEL_ID, msg_id)
        if msg and (msg.video or msg.document):
          media = msg.video or msg.document
          file_id = media.file_id
          r = requests.get(
              f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
          ).json()
          if r.get("ok"):
            file_path = r["result"]["file_path"]
            return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
      return None

    download_url = loop.run_until_complete(get_url())
    loop.close()

    if not download_url:
      return "Video no encontrado en el canal", 404

    video_req = requests.get(download_url, stream=True)
    return Response(
        video_req.iter_content(chunk_size=1024 * 64),
        content_type=video_req.headers.get("content-type", "video/mp4"),
        status=video_req.status_code,
    )
  except Exception as e:
    return f"Error en el servidor: {str(e)}", 500


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=10000)
