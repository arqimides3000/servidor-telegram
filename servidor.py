import asyncio
import threading
import queue
import re
import os
from flask import Flask, Response, request
from pyrogram import Client

app = Flask(__name__)

# Configuración de Pyrogram
bot = Client(
    "sesion_nube",
    api_id=6,
    api_hash="eb06d4abfb49dc3eeb1aes98ae0f581e",
    bot_token="PEGAS_AQUÍ_TU_TOKEN_DE_BOT"  # <-- Asegúrate de poner tu token real aquí entre las comillas
)

CANAL_ID = -1004489628455

@app.route('/stream/<int:message_id>')
def stream_video(message_id):
    q = queue.Queue()

    async def fetch_and_stream():
        try:
            # Obtener el mensaje del canal privado
            msg = await bot.get_messages(CANAL_ID, message_id)
            if not msg:
                print(f"Error: El mensaje {message_id} no existe en el canal.")
                return
            
            # Validar que contenga un video o documento multimedia
            if not (msg.video or msg.document):
                print(f"Error: El mensaje {message_id} no es un video ni un archivo multimedia válido.")
                return
            
            # Transmitir los fragmentos del archivo
            async for chunk in bot.stream_media(msg):
                q.put(chunk)
        except Exception as e:
            print(f"Excepción atrapada en el streaming del mensaje {message_id}: {e}")
        finally:
            q.put(None)  # Señal de finalización para el reproductor

    # Ejecutar la tarea asíncrona en el bucle de Pyrogram
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
    # Iniciar Flask en un hilo secundario independiente
    threading.Thread(target=run_flask, daemon=True).start()
    # Iniciar el cliente de Telegram en el hilo principal
    bot.run()
