import os
import uuid
import asyncio  # Importa la librería asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from yt_dlp import YoutubeDL
from playwright.sync_api import sync_playwright  # Importa la librería Playwright
from TikTokApi import TikTokApi  # Importa la librería TikTokApi

#______________________________________________________________________________________

# 📌 **Función para descargar contenido de TikTok sin marca de agua**
def descargaTikTok(url, user_id):
    try:
        print("Iniciando descarga del TikTok sin marca de agua:", url)
        with sync_playwright() as p:
            api = TikTokApi(p)
            video = api.video(url)
            video_data = video.bytes()  # Asegurar que bytes() se llama correctamente

            # Guarda el video en un archivo único
            unique_name = f"{user_id}_{uuid.uuid4()}.mp4"
            with open(unique_name, 'wb') as video_file:
                video_file.write(video_data)

        print(f"✅ Video de TikTok guardado como: {unique_name}")
        return unique_name
    except Exception as e:
        print(f"❌ Error al descargar el video de TikTok: {e}")
        return None
#______________________________________________________________________________________-


# 📌 **Función para descargar contenido en MP3 o MP4**
def download_content(url, user_id, file_format):
    try:
        unique_name = f"{user_id}_{uuid.uuid4()}"  # Nombre único sin extensión
        output_name = f"{unique_name}.%(ext)s"

        # Configura las opciones según el formato
        ydl_opts = {
            'format': 'bestaudio/best' if file_format == 'mp3' else 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
            'outtmpl': output_name,
        }

        # Agregar postprocesadores solo si es MP3
        if file_format == 'mp3':
            ydl_opts['postprocessors'] = [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }
            ]

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_file = ydl.prepare_filename(info)

            if file_format == 'mp3':
                downloaded_file = downloaded_file.replace('.webm', '.mp3').replace('.m4a', '.mp3')

            return downloaded_file
    except Exception as e:
        print(f"❌ Error en yt-dlp: {e}")
        raise e


# 📌 **Handlers de Telegram**
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! Este bot puede descargar videos de YouTube en MP3 o MP4 y TikTok.\n"
        "Usa uno de los comandos:\n"
        "/mp3 - Para descargar en formato MP3 (audio).\n"
        "/mp4 - Para descargar en formato MP4 (video).\n"
        "/tiktok - Para descargar videos de TikTok sin marca de agua.\n"
        "Luego, envía el enlace del video."
    )


async def mp3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['format'] = 'mp3'
    await update.message.reply_text("Has seleccionado MP3. Ahora envía un enlace de YouTube.")


async def mp4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['format'] = 'mp4'
    await update.message.reply_text("Has seleccionado MP4. Ahora envía un enlace de YouTube.")


async def tiktok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['format'] = 'tiktok'
    await update.message.reply_text("Has seleccionado TikTok. Ahora envía un enlace de TikTok.")


# 📌 **Manejar enlaces de YouTube o TikTok**
async def download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    user_id = update.message.from_user.id
    file_format = context.user_data.get('format')

    if not file_format:
        await update.message.reply_text("Por favor selecciona primero un formato usando /mp3, /mp4 o /tiktok.")
        return

    print("URL recibida:", url)
    print("Formato seleccionado:", file_format)

    if "youtube.com" in url or "youtu.be" in url:
        await update.message.reply_text(f"Descargando el contenido como {file_format.upper()}, por favor espera...")
        file_path = download_content(url, user_id, file_format)

        if file_path:
            print("✅ Archivo descargado:", file_path)
            try:
                # Verifica el tamaño del archivo antes de enviarlo
                if os.path.getsize(file_path) > 50 * 1024 * 1024:
                    await update.message.reply_text("El archivo es demasiado grande para enviarlo por Telegram.")
                    return

                if file_format == 'mp3':
                    await context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(file_path, 'rb'))
                else:
                    await context.bot.send_video(chat_id=update.effective_chat.id, video=open(file_path, 'rb'))
            finally:
                os.remove(file_path)  # Elimina el archivo después de enviarlo
        else:
            await update.message.reply_text("No se pudo descargar el contenido. Verifica el enlace.")

    elif "tiktok.com" in url:
        await update.message.reply_text("Descargando el contenido de TikTok sin marca de agua, por favor espera...")
        file_path = descargaTikTok(url, user_id)

        if file_path and os.path.exists(file_path):
            print("✅ Video de TikTok sin marca de agua descargado con éxito:", file_path)
            await context.bot.send_video(chat_id=update.effective_chat.id, video=open(file_path, 'rb'))
            os.remove(file_path)
        else:
            print("❌ No se pudo descargar el video de TikTok sin marca de agua")
            await update.message.reply_text("No se pudo descargar el video de TikTok sin marca de agua. Verifica el enlace e inténtalo nuevamente.")

    else:
        await update.message.reply_text("Por favor, envía un enlace válido de YouTube o TikTok.")


# 📌 **Configuración principal del bot**
def main():
    application = Application.builder().token("7693751923:AAH9i-62eI0I4lrYWs2eNKy7hF8Vi5c2EUA").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("mp3", mp3))
    application.add_handler(CommandHandler("mp4", mp4))
    application.add_handler(CommandHandler("tiktok", tiktok))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_handler))

    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
