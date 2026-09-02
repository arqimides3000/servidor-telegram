import asyncio
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

import os
import threading
import queue
import re
from flask import Flask, Response, request
from pyrogram import Client

app = Flask(__name__)

@app.route('/')
def home():
    return "Servidor de streaming activo y en línea.", 200

bot = Client(
    "sesion_nube",
    api_id=6,
    api_hash="eb06d4abfb49dc3eeb1aeb98ae0f581e",
    bot_token="8946352821:AAEH1axx8FBMUbfdIRSqBPU9UC0F5VBP1z0"
)

CANAL_ID = -1004489628455

@app.route('/stream/<int:message_id>')
def stream_video(message_id):
    # Obtener la información y el tamaño real del video antes de transmitir
    async def get_media_info():
        if not bot.is_connected:
            await bot.start()
        msg = await bot.get_messages(CANAL_ID, message_id)
        if not msg or not (msg.video or msg.document):
            return None, 0
        media = msg.video or msg.document
        return msg, media.file_size

    future = asyncio.run_coroutine_threadsafe(get_media_info(), loop)
    msg, file_size = future.result()

    if not msg or file_size == 0:
        return "Video no encontrado o inválido", 404

    range_header = request.headers.get('Range', None)
    byte_start = 0
    byte_end = file_size - 1

    if range_header:
        match = re.search(r'bytes=(\d+)-(\d*)', range_header)
        if match:
            byte_start = int(match.group(1))
            if match.group(2):
                byte_end = int(match.group(2))

    q = queue.Queue()

    async def fetch_and_stream():
        try:
            chunk_size = 1024 * 1024  # 1MB
            offset = byte_start // chunk_size
            async for chunk in bot.stream_media(msg, offset=offset):
                q.put(chunk)
        except Exception as e:
            print(f"Error en streaming: {e}")
        finally:
            q.put(None)

    asyncio.run_coroutine_threadsafe(fetch_and_stream(), loop)

    def generate():
        while True:
            chunk = q.get()
            if chunk is None:
                break
            yield chunk

    content_length = (byte_end - byte_start) + 1

    if range_header:
        resp = Response(generate(), status=206, mimetype="video/mp4", direct_passthrough=True)
        resp.headers.add('Content-Range', f'bytes {byte_start}-{byte_end}/{file_size}')
        resp.headers.add('Accept-Ranges', 'bytes')
        resp.headers.add('Content-Length', str(content_length))
        return resp

    resp = Response(generate(), status=200, mimetype="video/mp4", direct_passthrough=True)
    resp.headers.add('Content-Length', str(file_size))
    resp.headers.add('Accept-Ranges', 'bytes')
    return resp

def run_loop():
    if not loop.is_running():
        loop.run_forever()

if __name__ == '__main__':
    threading.Thread(target=run_loop, daemon=True).start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
