import os
import uuid  # Para generar nombres únicos
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from yt_dlp import YoutubeDL

# Función para descargar el video
def download_video(url, user_id):
    try:
        unique_name = f"{user_id}_{uuid.uuid4()}.mp4"  # Archivo único por usuario
        ydl_opts = {
            'format': 'mp4',
            'outtmpl': unique_name,
        }
        with YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
            return unique_name  # Retorna el nombre único del archivo descargado
    except Exception as e:
        print(f"Error al descargar el video: {e}")
        return None

# Handler para manejar los enlaces recibidos
async def download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    user_id = update.message.from_user.id  # ID único del usuario

    if "youtube.com" in url or "youtu.be" in url:
        await update.message.reply_text("Descargando el video, por favor espera...")
        video_path = download_video(url, user_id)
        if video_path:
            await context.bot.send_video(chat_id=update.effective_chat.id, video=open(video_path, 'rb'))
            os.remove(video_path)  # Elimina el archivo después de enviarlo
        else:
            await update.message.reply_text("No se pudo descargar el video. Verifica el enlace e inténtalo nuevamente.")
    else:
        await update.message.reply_text("Por favor, envía un enlace válido de YouTube.")

# Configuración principal del bot
def main():
    application = Application.builder().token("7693751923:AAH9i-62eI0I4lrYWs2eNKy7hF8Vi5c2EUA").build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_handler))
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
