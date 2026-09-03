import asyncio
import os

try:
  asyncio.get_event_loop()
except RuntimeError:
  asyncio.set_event_loop(asyncio.new_event_loop())

from flask import Flask, Response, request
from pyrogram import Client
import requests

app = Flask(__name__)


@app.route("/")
def home():
  return "HELLO, WORLD!"


@app.route("/stream/<int:msg_id>")
def stream_telegram(msg_id):
  try:
    api_id_str = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    channel_id_str = os.environ.get("TELEGRAM_CHANNEL_ID")

    if not api_id_str or not api_hash or not bot_token or not channel_id_str:
      return "Error: Faltan variables de entorno en Render", 500

    api_id = int(api_id_str.strip())
    bot_token = bot_token.strip()
    api_hash = api_hash.strip()

    clean_channel = channel_id_str.strip()
    try:
      channel_id = int(clean_channel)
    except ValueError:
      channel_id = clean_channel

    async def get_url():
      session_file = "/tmp/mi_bot_session"
      async with Client(
          session_file,
          api_id=api_id,
          api_hash=api_hash,
          bot_token=bot_token,
      ) as app_client:
        # Registrar el canal obligatoriamente en la sesión limpia
        await app_client.get_chat(channel_id)

        msg = await app_client.get_messages(channel_id, msg_id)
        if msg and (msg.video or msg.document):
          media = msg.video or msg.document
          file_id = media.file_id
          r = requests.get(
              f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"
          ).json()
          if r.get("ok"):
            file_path = r["result"]["file_path"]
            return f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
      return None

    download_url = asyncio.run(get_url())

    if not download_url:
      return "Video no encontrado en el canal o ID incorrecto", 404

    video_req = requests.get(download_url, stream=True)
    return Response(
        video_req.iter_content(chunk_size=1024 * 64),
        content_type=video_req.headers.get("content-type", "video/mp4"),
        status=video_req.status_code,
    )
  except Exception as e:
    return f"Error en el servidor: {str(e)}", 500


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
