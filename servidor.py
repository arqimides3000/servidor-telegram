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

# Nueva sesión con depuración de canales
bot = Client(
    "sesion_activa_v7",
    api_id=6,
    api_hash="eb06d4abfb49dc3eeb1aeb98ae0f581e",
    bot_token="8946352821:AAEpOE3cvaRsUiUaoa1CSeuoFjF1B6ZunmY"
)

CANAL_ID = -1004489628455  # Lo cambiaremos si el diagnóstico muestra otro

@app.route('/debug-chats')
def debug_chats():
    """Esta página te mostrará todos los canales y chats a los que tiene acceso tu bot."""
    async def list_chats():
        try:
            if not bot.is_connected:
                await bot.start()
            
            chats_info = []
            async for dialog in bot.get_dialogs():
                chats_info.append({
                    "nombre": dialog.chat.title,
                    "id": dialog.chat.id,
                    "tipo": str(dialog.chat.type)
                })
            return chats_info
        except Exception as e:
            return [{"error": str(e)}]

    try:
        future = asyncio.run_coroutine_threadsafe(list_chats(), loop)
        result = future.result(timeout=25)
        return {"chats_encontrados": result}
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/stream/<int:message_id>')
def stream_video(message_id):
    async def get_media_info():
        try:
            if not bot.is_connected:
                await bot.start()
            
            await bot.get_chat(CANAL_ID)
            
            msg = await bot.get_messages(CANAL_ID, message_id)
            if not msg:
                print(f"[ERROR] El mensaje {message_id} no existe.")
                return None, 0
            
            media = msg.video or msg.document or msg.animation or msg.audio
            if not media:
                print(f"[ERROR] El mensaje no contiene un archivo multimedia compatible.")
                return None, 0
                
            return msg, media.file_size
        except Exception as e:
            print(f"[ERROR] Excepción al obtener mensaje de Telegram: {e}")
            return None, 0

    try:
        future = asyncio.run_coroutine_threadsafe(get_media_info(), loop)
        msg, file_size = future.result(timeout=20)
    except Exception as e:
        return f"Error de tiempo de espera o conexión con Telegram: {e}", 504

    if not msg or file_size == 0:
        return f"El mensaje {message_id} no es un video válido o el bot no tiene acceso al canal.", 404

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
            skipped = 0
            async for chunk in bot.stream_media(msg):
                if byte_start > 0:
                    if skipped + len(chunk) <= byte_start:
                        skipped += len(chunk)
                        continue
                    elif skipped < byte_start:
                        diff = byte_start - skipped
                        chunk = chunk[diff:]
                        skipped = byte_start
                
                q.put(chunk)
                
                if byte_end < file_size - 1 and skipped >= byte_end:
                    break
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
