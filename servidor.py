import os
import requests
from flask import Flask, Response

app = Flask(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")


@app.route("/")
def home():
  return "HELLO, WORLD!"


@app.route("/stream/<file_id>")
def stream_telegram(file_id):
  try:
    if not BOT_TOKEN:
      return "TELEGRAM_BOT_TOKEN no configurado", 500

    api_url = (
        f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
    )
    respuesta_tg = requests.get(api_url).json()

    if not respuesta_tg.get("ok"):
      return (
          f"Error de Telegram:"
          f" {respuesta_tg.get('description', 'Desconocido')}",
          400,
      )

    file_path = respuesta_tg["result"]["file_path"]
    download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

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
