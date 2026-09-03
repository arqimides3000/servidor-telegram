import asyncio
import os

try:
  asyncio.get_event_loop()
except RuntimeError:
  asyncio.set_event_loop(asyncio.new_event_loop())

from flask import Flask, redirect, request
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
    channel_input = os.environ.get("TELEGRAM_CHANNEL_ID")

    if not api_id_str or not api_hash or not bot_token or not channel_input:
      return "Error: Faltan variables de entorno en Render", 500

    api_id = int(api_id_str.strip())
    bot_token = bot_token.strip()
    api_hash = api_hash.strip()
    channel_id_str = channel_input.strip()

    if channel_id_str.lstrip("-").isdigit():
      channel_id = int(channel_id_str)
    else:
      channel_id = (
          channel_id_str
          if channel_id_str.startswith("@")
          else "@" + channel_id_str
      )

    async def get_url():
      async with Client(
          "bot_session",
          api_id=api_id,
          api_hash=api_hash,
          bot_token=bot_token,
          in_memory=True,
      ) as app_client:
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

    # Detectar si la petición viene del reproductor nativo de la app o de un navegador web
    user_agent = request.headers.get("User-Agent", "").lower()
    is_media_player = any(
        agent in user_agent for agent in ["stagefright", "android", "dalvik"]
    )

    if is_media_player:
      # Para tu app de Android: redirección directa para streaming nativo dentro de tu reproductor
      return redirect(download_url)
    else:
      # Para navegadores web de PC: mostrar el reproductor HTML de prueba
      html_player = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Reproductor - Telegram Stream</title>
                <meta charset="utf-8">
                <style>
                    body {{ background-color: #0b0b0b; margin: 0; display: flex; justify-content: center; align-items: center; height: 100vh; }}
                    video {{ width: 100%; max-width: 900px; max-height: 90vh; outline: none; }}
                </style>
            </head>
            <body>
                <video controls autoplay playsinline>
                    <source src="{download_url}" type="video/mp4">
                    Tu navegador no soporta la reproducción de video.
                </video>
            </body>
            </html>
            """
      return html_player

  except Exception as e:
    return f"Error en el servidor: {str(e)}", 500


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
