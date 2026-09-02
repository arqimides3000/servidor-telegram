import asyncio
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import threading
import queue
import re
import os
from flask import Flask, Response, request
from pyrogram import Client

app = Flask(__name__)

bot = Client(
    "sesion_nube",
    api_id=6,
    api_hash="eb06d4abfb49dc3eeb1aeb98ae0f581e",
    bot_token="8946352821:AAEH1axx8FBMUbfdIRSqBPU9UC0f5VBP1z0"
)

CANAL_ID = -1004489628455

@app.route('/stream/<int:message_id>')
def stream_video(message_id):
    q = queue.Queue()

    async def fetch_and_stream():
        try:
            msg = await bot.get_messages(CANAL_ID, message_id)
            if not msg:
                print(f"Error: El mensaje {message_id} no existe en el canal.")
                return
            if not (msg.video or msg.document):
                print(f"Error: El mensaje {message_id} no es un video válido.")
                return
            async for chunk in bot.stream_media(msg):
                q.put(chunk)
        except Exception as e:
            print(f"Excepción en streaming: {e}")
        finally:
            q.put(None)

    asyncio.run_coroutine_threadsafe(fetch_and_stream(), bot.loop)

    def generate():
        while True:
            chunk = q.get()
            if chunk is None:
                break
            yield chunk

    return Response(generate(), mimetype="video/mp4", direct_passthrough=True)

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    bot.run()
