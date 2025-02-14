import os
import uuid
import asyncio  # Necesario para manejar coroutines
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from yt_dlp import YoutubeDL
from TikTokApi import TikTokApi
from playwright.async_api import async_playwright  # 🔹 Playwright debe ser asíncrono

# Función asíncrona para descargar TikToks sin marca de agua
async def descargaTiktok(url, user_id):
    try:
        print("🔹 Iniciando descarga de TikTok:", url)

        # Iniciar Playwright manualmente
        async with async_playwright() as p:
            api = TikTokApi(p)
            video = await api.video(url)  # ✅ Se debe usar await

            # Descargar los bytes del video
            video_data = await video.bytes()  # ✅ Se debe usar await

            # Generar un nombre de archivo único
            unique_name = f"{user_id}_{uuid.uuid4()}.mp4"
            with open(unique_name, 'wb') as videofile:
                videofile.write(video_data)

            print(f"✅ Video de TikTok guardado como: {unique_name}")
            return unique_name
    except Exception as e:
        print(f"❌ Error en descargaTiktok: {e}")
        return None


# Función para descargar contenido en MP3 o MP4
def download_content(url, user_id, file_format):
    try:
        unique_name = f"{user_id}_{uuid.uuid4()}"  # Nombre único sin extensión
        output_name = f"{unique_name}.%(ext)s"

        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': output_name,
            'merge_output_format': 'mp4',  # 🔹 Asegura que el video final sea MP4 con audio
            'postprocessors': [],
        }

        # Agregar postprocesador para MP3
        if file_format == 'mp3':
            ydl_opts['postprocessors'].append(
                {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}
            )

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_file = ydl.prepare_filename(info)

            # Ajustar el nombre del archivo si es MP3 o MP4
            if file_format == 'mp3':
                downloaded_file = downloaded_file.replace('.webm', '.mp3').replace('.m4a', '.mp3')
            elif file_format == 'mp4':
                downloaded_file = downloaded_file.replace('.webm', '.mp4').replace('.mkv', '.mp4')

            print(f"✅ Archivo descargado correctamente: {downloaded_file}")
            return downloaded_file
    except Exception as e:
        print(f"❌ Error en yt-dlp: {e}")
        return None


# Handlers de Telegram
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! Este bot puede descargar videos de YouTube en MP3 o MP4 y TikTok.\n"
        "Usa uno de los comandos:\n"
        "/mp3 - Para descargar en formato MP3 (audio).\n"
        "/mp4 - Para descargar en formato MP4 (video).\n"
        "/tiktok - Para descargar videos de TikTok sin marca de agua.\n"
        "Luego, envía el enlace del video."
    )

async def tiktok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['format'] = 'tiktok'
    await update.message.reply_text("Has seleccionado TikTok. Ahora envía un enlace de TikTok.")

async def mp3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['format'] = 'mp3'
    await update.message.reply_text("Has seleccionado MP3. Ahora envía un enlace de YouTube.")

async def mp4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['format'] = 'mp4'
    await update.message.reply_text("Has seleccionado MP4. Ahora envía un enlace de YouTube.")

async def download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    user_id = update.message.from_user.id
    file_format = context.user_data.get('format')

    if not file_format:
        await update.message.reply_text("Por favor selecciona primero un formato usando /mp3, /mp4 o /tiktok.")
        return

    print("🔹 URL recibida:", url)
    print("🔹 Formato seleccionado:", file_format)

    if "youtube.com" in url or "youtu.be" in url:
        await update.message.reply_text(f"Descargando {file_format.upper()}, por favor espera...")
        
        file_path = download_content(url, user_id, file_format)

        if file_path and os.path.exists(file_path):
            print(f"✅ Archivo final disponible: {file_path}")

            if file_format == 'mp3':
                await context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(file_path, 'rb'))
            else:
                await context.bot.send_video(chat_id=update.effective_chat.id, video=open(file_path, 'rb'))

            os.remove(file_path)
        else:
            await update.message.reply_text("No se pudo procesar el video. Inténtalo de nuevo.")

    elif "tiktok.com" in url:
        print("🔹 Recibido enlace de TikTok:", url)
        await update.message.reply_text("Descargando video de TikTok, por favor espera...")

        file_path = await descargaTiktok(url, user_id)  # ✅ Ahora sí con await

        if file_path:
            print(f"✅ Video de TikTok descargado: {file_path}")

            if os.path.exists(file_path):
                await context.bot.send_video(chat_id=update.effective_chat.id, video=open(file_path, 'rb'))
                os.remove(file_path)
            else:
                print("❌ Error: No se encontró el archivo después de la descarga.")
                await update.message.reply_text("Hubo un problema al procesar el video de TikTok.")
        else:
            print("❌ Error: La descarga de TikTok falló.")
            await update.message.reply_text("No se pudo descargar el video de TikTok. Verifica el enlace e inténtalo nuevamente.")

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
