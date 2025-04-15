
import os
import uuid
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from yt_dlp import YoutubeDL
import requests

# Función para descargar contenido en MP3 o MP4
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
        print(f"Error en yt-dlp: {e}")
        raise e


  def sanitize_tiktok_url(raw_url):
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(raw_url)
    return urlunparse(parsed._replace(query=""))

def download_tiktok_video(url, user_id):
    try:
        clean_url = sanitize_tiktok_url(url)
        print(f"🔗 Enlace limpio: {clean_url}")

        api_url = "https://tiktok-download-without-watermark.p.rapidapi.com/analysis"
        headers = {
            "X-RapidAPI-Key": "RAPIDAPI_KEY", #c987832c40msh8923556ddd5a6a4p1c1c87jsn3cd43aca712e
            "X-RapidAPI-Host": "tiktok-download-without-watermark.p.rapidapi.com",
            "User-Agent": "Mozilla/5.0"
        }
        params = {"url": clean_url}  # este es el nombre correcto del parámetro

        response = requests.get(api_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        print("✅ Respuesta recibida de API:", data)

        video_url = data.get("data", {}).get("play")
        if not video_url:
            print("⚠️ No se encontró el enlace del video sin marca de agua.")
            return None

        filename = f"{user_id}_{uuid.uuid4()}.mp4"
        with requests.get(video_url, stream=True) as r:
            r.raise_for_status()
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return filename

    except Exception as e:
        print(f"❌ Error al descargar video TikTok: {e}")
        return None

# Handler para el comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! Este bot puede descargar videos de YouTube en MP3 o MP4.\n"
        "Usa uno de los comandos:\n"
        "/mp3 - Para descargar en formato MP3 (audio).\n"
        "/mp4 - Para descargar en formato MP4 (video).\n"
        "/tiktok - Para descargar un video de tiktok sin marca de agua (video). \n"
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
    
#Handler para tiktok 
async def tiktok(update:Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['format']= "tiktok"
    await update.message.reply_text("Has seleccionado descarga por tiktok sin marca de agua, Ahora envia un enlace válido de un tiktok")

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
            print("Archivo descargado:", file_path)
            try:
                if os.path.getsize(file_path) > 50 * 1024 * 1024:
                    await update.message.reply_text("El archivo es demasiado grande para enviarlo por Telegram.")
                    return
                if file_format == 'mp3':
                    await context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(file_path, 'rb'))
                else:
                    await context.bot.send_video(chat_id=update.effective_chat.id, video=open(file_path, 'rb'))
            finally:
                os.remove(file_path)
        else:
            await update.message.reply_text("No se pudo descargar el contenido. Verifica el enlace.")
    
    elif "tiktok.com" in url and file_format == "tiktok":
        await update.message.reply_text("Descargando video de TikTok sin marca de agua, espera un momento...")
        file_path = download_tiktok_video(url, user_id)
        if file_path:
            try:
                if os.path.getsize(file_path) > 50 * 1024 * 1024:
                    await update.message.reply_text("El archivo es demasiado grande para enviarlo por Telegram.")
                    return
                await context.bot.send_video(chat_id=update.effective_chat.id, video=open(file_path, 'rb'))
            finally:
                os.remove(file_path)
        else:
            await update.message.reply_text("No se pudo descargar el video. Asegúrate que el enlace es válido.")
    
    else:
        await update.message.reply_text("Por favor, envía un enlace válido de YouTube o TikTok.")


# Configuración principal del bot
def main():
    # Crea la aplicación
    application = Application.builder().token("7693751923:AAH9i-62eI0I4lrYWs2eNKy7hF8Vi5c2EUA").build()

    # Agrega los comandos y handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("mp3", mp3))
    application.add_handler(CommandHandler("mp4", mp4))
    application.add_handler(CommandHandler("tiktok",tiktok))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_handler))

    # Ejecuta el bot
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()