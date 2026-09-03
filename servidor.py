import asyncio

try:
  asyncio.get_event_loop()
except RuntimeError:
  asyncio.set_event_loop(asyncio.new_event_loop())

import os
from flask import Flask, Response, request, stream_with_context
from pyrogram import Client

app = Flask(__name__)

api_id = int(os.environ.get("TELEGRAM_API_ID", 0))
api_hash = os.environ.get("TELEGRAM_API_HASH", "")
session_string = os.environ.get("SESSION_STRING", "")
channel_input = os.environ.get("TELEGRAM_CHANNEL_ID", "")


@app.route("/")
def home():
  return "SERVIDOR ACTIVO - PELIS ROLANDO"


@app.route("/stream/<int:msg_id>")
async def stream_telegram(msg_id):
  if not api_id or not api_hash or not session_string or not channel_input:
    return "Faltan variables de entorno", 500

  channel_id = (
      int(channel_input)
      if channel_input.lstrip("-").isdigit()
      else (
          channel_input
          if channel_input.startswith("@")
          else "@" + channel_input
      )
  )

  client = Client(
      "server_session",
      api_id=api_id,
      api_hash=api_hash,
      session_string=session_string,
      in_memory=True,
  )

  await client.start()
  msg = await client.get_messages(channel_id, msg_id)

  if not msg or not (msg.video or msg.document):
    await client.stop()
    return "Video no encontrado", 404

  media = msg.video or msg.document
  file_size = media.file_size
  mime_type = getattr(media, "mime_type", "video/mp4")

  accept_header = request.headers.get("accept", "")
  if "text/html" in accept_header:
    await client.stop()
    stream_url = request.url
    html_player = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Reproductor - Pelis Rolando</title>
            <meta charset="utf-8">
            <style>
                body {{ background-color: #0b0b0b; margin: 0; display: flex; justify-content: center; align-items: center; height: 100vh; }}
                video {{ width: 100%; max-width: 900px; max-height: 90vh; outline: none; }}
            </style>
        </head>
        <body>
            <video controls autoplay playsinline src="{stream_url}">
                Tu navegador no soporta la reproducción de video.
            </video>
        </body>
        </html>
        """
    return html_player

  async def generate():
    try:
      async for chunk in client.stream_media(msg):
        yield chunk
    finally:
      await client.stop()

  response = Response(
      stream_with_context(generate()),
      mimetype=mime_type,
      direct_passthrough=True,
  )
  response.headers.add("Content-Length", str(file_size))
  response.headers.add("Accept-Ranges", "bytes")
  return response


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
