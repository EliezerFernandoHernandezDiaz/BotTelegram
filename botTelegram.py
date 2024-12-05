import os
import uuid  # Para generar nombres únicos
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from yt_dlp import YoutubeDL

# Función para descargar el contenido
def download_content(url, user_id, file_format):
    try:
        unique_name = f"{user_id}_{uuid.uuid4()}"  # Archivo único por usuario, sin extensión
        output_name = f"{unique_name}.%(ext)s"  # Plantilla para el nombre de archivo
        
        ydl_opts = {
            'format': 'bestaudio/best' if file_format == 'mp3' else 'mp4',
            'outtmpl': output_name,
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192'
                }
            ] if file_format == 'mp3' else None,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # Verifica el nombre del archivo final después de la descarga
            downloaded_file = ydl.prepare_filename(info)
            if file_format == 'mp3':
                downloaded_file = downloaded_file.replace('.webm', '.mp3').replace('.m4a', '.mp3')
            return downloaded_file  # Retorna el archivo final descargado
    except Exception as e:
        print(f"Error al descargar el contenido: {e}")
        return None



# Handler para el comando de /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! Bienvenido a DownloadVideoBot desarrollado por Fernando. Estos son los comandos disponibles:\n"
        "/mp3 - Descarga un video de YouTube como formato MP3.\n"
        "/mp4 - Descarga un video de YouTube como formato MP4.\n"
        "Envía el enlace después de seleccionar un comando."
    )


# Handler para el comando /mp3
async def mp3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['format'] = 'mp3'  # Almacena el formato seleccionado en datos del usuario
    await update.message.reply_text("Envia un enlace de YouTube para comenzar la descarga del audio como MP3.")


# Handler para el comando /mp4
async def mp4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['format'] = 'mp4'  # Almacena el formato seleccionado en datos del usuario
    await update.message.reply_text("Envia un enlace de YouTube para comenzar la descarga del video como MP4.")


async def download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    user_id = update.message.from_user.id  # ID único del usuario
    file_format = context.user_data.get('format')  # Obtiene el formato del comando seleccionado

    if not file_format:
        await update.message.reply_text("Por favor selecciona primeramente un comando (/mp3 o /mp4).")
        return

    if "youtube.com" in url or "youtu.be" in url:
        await update.message.reply_text(f"Descargando el contenido como {file_format.upper()}, por favor espera...")
        file_path = download_content(url, user_id, file_format)
        if file_path:
            if file_format == 'mp3':
                await context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(file_path, 'rb'))
            else:
                await context.bot.send_video(chat_id=update.effective_chat.id, video=open(file_path, 'rb'))
            os.remove(file_path)  # Elimina el archivo después de enviarlo
        else:
            await update.message.reply_text("No se pudo descargar el contenido. Verifica el enlace e inténtalo nuevamente.")
    else:
        await update.message.reply_text("Por favor, envía un enlace válido de YouTube.")


# Configuración principal del bot
def main():
    application = Application.builder().token("7693751923:AAH9i-62eI0I4lrYWs2eNKy7hF8Vi5c2EUA").build()

    # Handlers para comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("mp3", mp3))
    application.add_handler(CommandHandler("mp4", mp4))

    # Handler para texto (enlaces)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_handler))

    # Ejecuta el bot
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
