
import os
import uuid
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from yt_dlp import YoutubeDL

# Función para descargar contenido en MP3 o MP4
def download_content(url, user_id, file_format):
    try:
        unique_name = f"{user_id}_{uuid.uuid4()}"  # Nombre único sin extensión
        output_name = f"{unique_name}.%(ext)s"
        
        # Configura las opciones según el formato
        ydl_opts = {
            'format': 'bestaudio/best' if file_format == 'mp3' else 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
            'outtmpl': output_name,
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }
            ] if file_format == 'mp3' else None,
            'merge_output_format': 'mp4' if file_format == 'mp4' else None,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_file = ydl.prepare_filename(info)
            if file_format == 'mp3':
                downloaded_file = downloaded_file.replace('.webm', '.mp3').replace('.m4a', '.mp3')
            return downloaded_file
    except Exception as e:
        print(f"Error al descargar el contenido: {e}")
        return None

# Handler para el comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! Este bot puede descargar videos de YouTube en MP3 o MP4.\n"
        "Usa uno de los comandos:\n"
        "/mp3 - Para descargar en formato MP3 (audio).\n"
        "/mp4 - Para descargar en formato MP4 (video).\n"
        "Luego, envía el enlace del video."
    )

# Handler para seleccionar MP3
async def mp3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['format'] = 'mp3'  # Guarda la preferencia del usuario
    await update.message.reply_text("Has seleccionado MP3. Ahora envía un enlace de YouTube.")

# Handler para seleccionar MP4
async def mp4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['format'] = 'mp4'  # Guarda la preferencia del usuario
    await update.message.reply_text("Has seleccionado MP4. Ahora envía un enlace de YouTube.")

# Handler para manejar el enlace
async def download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    user_id = update.message.from_user.id
    file_format = context.user_data.get('format')  # Obtiene el formato seleccionado por el usuario

    if not file_format:
        await update.message.reply_text("Por favor selecciona primero un formato usando /mp3 o /mp4.")
        return

    if "youtube.com" in url or "youtu.be" in url:
        await update.message.reply_text(f"Descargando el contenido como {file_format.upper()}, por favor espera...")
        file_path = download_content(url, user_id, file_format)
        if file_path:
            try:
                if file_format == 'mp3':
                    await context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(file_path, 'rb'))
                else:
                    await context.bot.send_video(chat_id=update.effective_chat.id, video=open(file_path, 'rb'))
            finally:
                os.remove(file_path)  # Elimina el archivo después de enviarlo
        else:
            await update.message.reply_text("No se pudo descargar el contenido. Verifica el enlace e inténtalo nuevamente.")
    else:
        await update.message.reply_text("Por favor, envía un enlace válido de YouTube.")

# Configuración principal del bot
def main():
    # Crea la aplicación
    application = Application.builder().token("7693751923:AAH9i-62eI0I4lrYWs2eNKy7hF8Vi5c2EUA").build()

    # Agrega los comandos y handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("mp3", mp3))
    application.add_handler(CommandHandler("mp4", mp4))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_handler))

    # Ejecuta el bot
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
