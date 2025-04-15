from urllib.parse import urlparse, urlunparse
import os
import uuid
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from yt_dlp import YoutubeDL

# ========================
# 🔧 Función para sanitizar URL de TikTok
# ========================
def sanitize_tiktok_url(raw_url):
    parsed = urlparse(raw_url)
    return urlunparse(parsed._replace(query=""))

# ========================
# 📥 Función para descargar videos de TikTok sin marca de agua
# ========================
def download_tiktok_video(url, user_id):
    try:
        clean_url = sanitize_tiktok_url(url)
        print(f"🔗 Enlace limpio: {clean_url}")

        api_url = "https://tiktok-download-without-watermark.p.rapidapi.com/analysis"
        headers = {
            "X-RapidAPI-Key": "c987832c40msh8923556ddd5a6a4p1c1c87jsn3cd43aca712e",  # ⚠️ CAMBIA por os.getenv si usás .env
            "X-RapidAPI-Host": "tiktok-download-without-watermark.p.rapidapi.com",
            "User-Agent": "Mozilla/5.0"
        }
        params = {"url": clean_url}

        response = requests.get(api_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        print("✅ Respuesta recibida:", data)

        video_url = data.get("data", {}).get("play")
        if not video_url:
            print("⚠️ No se encontró el video sin marca de agua.")
            return None

        filename = f"{user_id}_{uuid.uuid4()}.mp4"
        with requests.get(video_url, stream=True) as r:
            r.raise_for_status()
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        print(f"📥 Video guardado: {filename}")
        return filename

    except Exception as e:
        print(f"❌ Error al descargar video TikTok: {e}")
        return None

# ========================
# 🎧 Descarga de contenido MP3 o MP4 desde YouTube
# ========================
def download_content(url, user_id, file_format):
    try:
        unique_name = f"{user_id}_{uuid.uuid4()}"
        output_name = f"{unique_name}.%(ext)s"

        ydl_opts = {
            'format': 'bestaudio/best' if file_format == 'mp3' else 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
            'outtmpl': output_name,
        }

        if file_format == 'mp3':
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_file = ydl.prepare_filename(info)
            if file_format == 'mp3':
                downloaded_file = downloaded_file.replace('.webm', '.mp3').replace('.m4a', '.mp3')
            return downloaded_file

    except Exception as e:
        print(f"Error en yt-dlp: {e}")
        return None

# ========================
# 🤖 Handlers de comandos
# ========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! Este bot puede descargar videos de YouTube y TikTok.\n"
        "Usa uno de los comandos:\n"
        "/mp3 - Descargar audio de YouTube\n"
        "/mp4 - Descargar video de YouTube\n"
        "/tiktok - Descargar video de TikTok sin marca de agua\n"
        "Luego envía el enlace del video."
    )

async def mp3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['format'] = 'mp3'
    await update.message.reply_text("Has seleccionado MP3. Ahora envía un enlace de YouTube.")

async def mp4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['format'] = 'mp4'
    await update.message.reply_text("Has seleccionado MP4. Ahora envía un enlace de YouTube.")

async def tiktok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['format'] = 'tiktok'
    await update.message.reply_text("Has seleccionado TikTok. Ahora envía un enlace válido de TikTok.")

# ========================
# 📥 Handler general de enlaces
# ========================
async def download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    user_id = update.message.from_user.id
    file_format = context.user_data.get('format')

    if not file_format:
        await update.message.reply_text("Por favor selecciona un formato con /mp3, /mp4 o /tiktok primero.")
        return

    print("URL recibida:", url)
    print("Formato seleccionado:", file_format)

    if "youtube.com" in url or "youtu.be" in url:
        await update.message.reply_text(f"Descargando contenido como {file_format.upper()}, por favor espera...")
        file_path = download_content(url, user_id, file_format)
        if file_path:
            try:
                if os.path.getsize(file_path) > 50 * 1024 * 1024:
                    await update.message.reply_text("⚠️ El archivo es muy grande para enviarlo por Telegram.")
                    return
                if file_format == 'mp3':
                    await context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(file_path, 'rb'))
                else:
                    await context.bot.send_video(chat_id=update.effective_chat.id, video=open(file_path, 'rb'))
            finally:
                os.remove(file_path)
                print("🧹 Archivo eliminado")
        else:
            await update.message.reply_text("❌ No se pudo descargar el video/audio. Verifica el enlace.")

    elif ("tiktok.com" in url or "vm.tiktok.com" in url) and file_format == "tiktok":
        await update.message.reply_text("Descargando video de TikTok sin marca de agua, por favor espera...")

        file_path = download_tiktok_video(url, user_id)
        if file_path:
            try:
                if os.path.getsize(file_path) > 50 * 1024 * 1024:
                    await update.message.reply_text("⚠️ El video es muy pesado para enviarlo por Telegram.")
                    return
                await context.bot.send_video(chat_id=update.effective_chat.id, video=open(file_path, 'rb'))
                print("🎬 Video enviado")
            finally:
                os.remove(file_path)
                print("🧹 Video eliminado")
        else:
            await update.message.reply_text("❌ No se pudo descargar el video de TikTok.")

    else:
        await update.message.reply_text("❌ Enlace no válido. Por favor, envía uno de YouTube o TikTok.")

# ========================
# 🚀 Main del bot
# ========================
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
