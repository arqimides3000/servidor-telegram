import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pyrogram import Client

app = FastAPI()

api_id = int(os.environ.get("TELEGRAM_API_ID", 0))
api_hash = os.environ.get("TELEGRAM_API_HASH", "")
session_string = os.environ.get("SESSION_STRING", "")
channel_input = os.environ.get("TELEGRAM_CHANNEL_ID", "")


@app.get("/")
def home():
  return {"status": "SERVIDOR ACTIVO - PELIS ROLANDO"}


@app.get("/stream/{msg_id}")
async def stream_telegram(msg_id: int, request: Request):
  if not api_id or not api_hash or not session_string or not channel_input:
    raise HTTPException(status_code=500, detail="Faltan variables de entorno")

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
    raise HTTPException(status_code=404, detail="Video no encontrado")

  media = msg.video or msg.document
  file_size = media.file_size
  mime_type = getattr(media, "mime_type", "video/mp4")

  accept_header = request.headers.get("accept", "")

  # Si se abre desde la computadora (navegador web), mostramos el reproductor online
  if "text/html" in accept_header:
    await client.stop()
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

  # Para la app de Android o streaming directo, enviamos los fragmentos en tiempo real
  async def generate():
    try:
      async for chunk in client.stream_media(msg):
        yield chunk
    finally:
      await client.stop()

  return StreamingResponse(
      generate(),
      media_type=mime_type,
      headers={
          "Content-Length": str(file_size),
          "Accept-Ranges": "bytes",
      },
  )


if __name__ == "__main__":
  import uvicorn

  port = int(os.environ.get("PORT", 10000))
  uvicorn.run("servidor:app", host="0.0.0.0", port=port)
