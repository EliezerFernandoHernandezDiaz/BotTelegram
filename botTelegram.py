import os
import uuid
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from yt_dlp import YoutubeDL

# Función para descargar contenido (audio o video)
def download_content(url, user_id, file_format):
    try:
        unique_name = f"{user_id}_{uuid.uuid4()}.{file_format}"  # Archivo único por usuario
        ydl_opts = {
            'format': 'bestaudio/best' if file_format == 'mp3' else 'bestvideo+bestaudio',
            'outtmpl': unique_name,
            'merge_output_format': 'mp4' if file_format == 'mp4' else None,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }] if file_format == 'mp3' else None,
        }

        with YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
            return unique_name  # Retorna el nombre único del archivo descargado
    except Exception as e:
        print(f"Error al descargar el contenido: {e}")
        return None

# Handler para el comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! Soy un bot para descargar videos o audios de YouTube.\n\n"
        "Comandos disponibles:\n"
        "/mp3 - Descargar un video como audio MP3\n"
        "/mp4 - Descargar un video en formato MP4\n"
        "Después de usar un comando, envíame el enlace de YouTube."
    )

# Handler para el comando /mp3
async def mp3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['format'] = 'mp3'  # Almacena el formato seleccionado en datos del usuario
    await update.message.reply_text("Envíame un enlace de YouTube para descargar el audio como MP3.")

# Handler para el comando /mp4
async def mp4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['format'] = 'mp4'  # Almacena el formato seleccionado en datos del usuario
    await update.message.reply_text("Envíame un enlace de YouTube para descargar el video como MP4.")

# Handler para manejar los enlaces recibidos
async def download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    user_id = update.message.from_user.id  # ID único del usuario
    file_format = context.user_data.get('format')  # Obtiene el formato del comando seleccionado

    if not file_format:
        await update.message.reply_text("Primero selecciona un formato usando /mp3 o /mp4.")
        print("Formato no seleccionado")
        return

    if "youtube.com" in url or "youtu.be" in url:
        await update.message.reply_text(f"Descargando el contenido en formato {file_format.upper()}, por favor espera...")
        print(f"URL recibido: {url}, Formato: {file_format}")

        file_path = download_content(url, user_id, file_format)

        if file_path and os.path.exists(file_path):
            if file_format == 'mp3':
                await context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(file_path, 'rb'))
            else:
                await context.bot.send_video(chat_id=update.effective_chat.id, video=open(file_path, 'rb'))
            os.remove(file_path)  # Elimina el archivo después de enviarlo
        else:
            await update.message.reply_text("Error al descargar el contenido. Verifica el enlace e inténtalo nuevamente.")
            print("No se pudo encontrar el archivo descargado.")
    else:
        await update.message.reply_text("Por favor, envía un enlace válido de YouTube.")
        print("URL inválido recibido.")

# Configuración principal del bot
def main():
    application = Application.builder().token("TU_TOKEN_DEL_BOT").build()

    # Handlers para comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("mp3", mp3))
    application.add_handler(CommandHandler("mp4", mp4))

    # Handler para enlaces de YouTube
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_handler))

    # Ejecuta el bot
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
