import os
import uuid
import asyncio  # Necesario para manejar coroutines
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from yt_dlp import YoutubeDL
from TikTokApi import TikTokApi
import random

# Función asíncrona para descargar TikToks sin marca de agua
async def descargaTiktok(url, user_id):
   try:
        print("🔹 Iniciando descarga de TikTok:", url)

        # Iniciar TikTokApi con Playwright
        async with TikTokApi() as api:
            video = await api.video(url)

            # Descargar los bytes del video
            video_data = await video.bytes()

            # Guardar el archivo con un nombre único
            unique_name = f"{user_id}_{random.randint(1000, 9999)}.mp4"
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
            'format': 'bestaudio/best' if file_format == 'mp3' else 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
            'outtmpl': output_name,
            'postprocessors': [],
        }

        # Agregar postprocesador para MP3
        if file_format == 'mp3':
            ydl_opts['postprocessors'].append(
                {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}
            )
        else:  # Para MP4
            ydl_opts['postprocessors'].append(
                {'key': 'FFmpegVideoRemuxer', 'preferedformat': 'mp4'}
            )

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_file = ydl.prepare_filename(info)
            
            # Log para verificar el nombre del archivo final
            print(f"Archivo descargado y convertido a MP4: {downloaded_file}")

            # Si es MP3, ajustar nombre del archivo
            if file_format == 'mp3':
                downloaded_file = downloaded_file.replace('.webm', '.mp3').replace('.m4a', '.mp3')

            return downloaded_file
    except Exception as e:
        print(f"Error en yt-dlp: {e}")
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

    print("URL recibida:", url)
    print("Formato seleccionado:", file_format)

    if "youtube.com" in url or "youtu.be" in url:
        await update.message.reply_text(f"Descargando {file_format.upper()}, por favor espera...")
        file_path = download_content(url, user_id, file_format)

        if file_path and os.path.exists(file_path):  # 🔹 Verificar si el archivo existe antes de enviarlo
            print(f"Archivo final disponible: {file_path}")
            
            if file_format == 'mp3':
                await context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(file_path, 'rb'))
            else:
                await context.bot.send_video(chat_id=update.effective_chat.id, video=open(file_path, 'rb'))

            os.remove(file_path)  # 🔹 Eliminar archivo después de enviarlo
        else:
            await update.message.reply_text("No se pudo procesar el video. Inténtalo de nuevo.")

    elif "tiktok.com" in url:
     print("🔹 Recibido enlace de TikTok:", url)  # Agregar log para verificar el enlace recibido
    await update.message.reply_text("Descargando video de TikTok, por favor espera...")
    
    file_path = await descargaTiktok(url, user_id)  # ✅ AWAIT necesario
    
    if file_path:
        print(f"✅ Video de TikTok descargado: {file_path}")  # Log para ver si el video se guardó correctamente
        
        if os.path.exists(file_path):  # Verificar si el archivo existe antes de enviarlo
            await context.bot.send_video(chat_id=update.effective_chat.id, video=open(file_path, 'rb'))
            os.remove(file_path)  # Borrar archivo después de enviarlo
        else:
            print("❌ Error: No se encontró el archivo después de la descarga.")  # Agregar error en la consola
            await update.message.reply_text("Hubo un problema al procesar el video de TikTok.")
    else:
        print("❌ Error: La descarga de TikTok falló.")  # Indicar que la descarga falló
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
