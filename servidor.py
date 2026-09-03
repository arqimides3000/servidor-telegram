import asyncio

try:
  asyncio.get_event_loop()
except RuntimeError:
  asyncio.set_event_loop(asyncio.new_event_loop())

import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from pyrogram import Client

app = FastAPI()

api_id = int(os.environ.get("TELEGRAM_API_ID", 0))
api_hash = os.environ.get("TELEGRAM_API_HASH", "")
session_string = os.environ.get("SESSION_STRING", "")
channel_input = os.environ.get("TELEGRAM_CHANNEL_ID", "")

TEMP_DIR = "/tmp"
bot_client = None


@app.on_event("startup")
async def startup_event():
  global bot_client
  if api_id and api_hash and session_string:
    bot_client = Client(
        "server_session",
        api_id=api_id,
        api_hash=api_hash,
        session_string=session_string,
        in_memory=True,
    )
    await bot_client.start()


@app.on_event("shutdown")
async def shutdown_event():
  if bot_client:
    await bot_client.stop()


@app.get("/")
def home():
  return {"status": "SERVIDOR ACTIVO - PELIS ROLANDO"}


@app.get("/stream/{msg_id}")
async def stream_telegram(msg_id: int, request: Request):
  if not bot_client:
    raise HTTPException(
        status_code=500, detail="Cliente de Telegram no iniciado"
    )

  channel_id = (
      int(channel_input)
      if channel_input.lstrip("-").isdigit()
      else (
          channel_input
          if channel_input.startswith("@")
          else "@" + channel_input
      )
  )

  msg = await bot_client.get_messages(channel_id, msg_id)
  if not msg or not (msg.video or msg.document):
    raise HTTPException(status_code=404, detail="Video no encontrado")

  media = msg.video or msg.document
  file_name = (
      getattr(media, "file_name", f"video_{msg_id}.mp4")
      or f"video_{msg_id}.mp4"
  )
  local_path = os.path.join(TEMP_DIR, f"{msg_id}_{file_name}")

  # Descarga el archivo completo a la memoria temporal de Render una sola vez
  if not os.path.exists(local_path):
    await bot_client.download_media(msg, file_name=local_path)

  mime_type = getattr(media, "mime_type", "video/mp4")

  accept_header = request.headers.get("accept", "")
  if "text/html" in accept_header:
    stream_url = str(request.url)
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
    return HTMLResponse(content=html_player)

  # FileResponse entrega el archivo local gestionando los saltos de bytes perfectamente
  return FileResponse(local_path, media_type=mime_type, filename=file_name)


if __name__ == "__main__":
  import uvicorn

  port = int(os.environ.get("PORT", 10000))
  uvicorn.run("servidor:app", host="0.0.0.0", port=port)
