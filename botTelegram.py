import os
import uuid
import time
import random
import logging
import asyncio
from functools import wraps
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import Conflict, NetworkError, TimedOut
from yt_dlp import YoutubeDL
import nest_asyncio 

# Activar compatibilidad para entornos con loops activos (como Render)
nest_asyncio.apply()

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Lista de user agents para evitar bloqueo por bot
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0'
]

def retry_on_bot_detection(max_retries=3, base_delay=5):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if any(word in str(e).lower() for word in ["sign in to confirm", "bot", "extractorerror"]):
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt) + random.uniform(0, 5)
                            logger.warning(f"Bot detectado. Reintentando en {delay:.1f}s...")
                            time.sleep(delay)
                        else:
                            logger.error("Máximo de reintentos alcanzado.")
                            raise Exception("YouTube bloqueó temporalmente. Intenta en unos minutos.")
                    else:
                        raise e
        return wrapper
    return decorator

@retry_on_bot_detection(max_retries=3)
def download_content(url, user_id, file_format):
    unique_name = f"{user_id}_{uuid.uuid4()}"
    output_name = f"{unique_name}.%(ext)s"

    ydl_opts = {
        'format': 'bestaudio/best' if file_format == 'mp3' else 'best[ext=mp4][height<=720]/best[ext=mp4]/best',
        'outtmpl': output_name,
        'http_headers': {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
        },
        'sleep_interval': random.uniform(1, 3),
        'max_sleep_interval': 10,
        'ignoreerrors': False,
        'no_warnings': False,
    }

    if os.path.exists("youtube_cookies.txt"):
        ydl_opts["cookiefile"] = "youtube_cookies.txt"

    if file_format == "mp3":
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if info.get('duration', 0) > 1800:
            raise Exception("❌ Video demasiado largo (máximo 30 minutos)")
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)

        if file_format == 'mp3':
            file_path = file_path.replace('.webm', '.mp3').replace('.m4a', '.mp3')

        return file_path

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 ¡Hola! Este bot descarga de YouTube en MP3 o MP4.\n\n"
        "Comandos:\n/mp3 para audio\n/mp4 para video\nLuego envía el enlace."
    )

async def mp3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["format"] = "mp3"
    await update.message.reply_text("🎵 MP3 seleccionado. Enviá el enlace.")

async def mp4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["format"] = "mp4"
    await update.message.reply_text("🎥 MP4 seleccionado. Enviá el enlace.")

async def download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    file_format = context.user_data.get("format")
    user_id = update.message.from_user.id

    if not file_format:
        await update.message.reply_text("⚠️ Usa /mp3 o /mp4 primero.")
        return

    if "youtu" not in url:
        await update.message.reply_text("❌ Enlace inválido de YouTube.")
        return

    msg = await update.message.reply_text(f"🔄 Descargando en {file_format.upper()}...")

    try:
        file_path = download_content(url, user_id, file_format)

        if not file_path or not os.path.exists(file_path):
            await msg.edit_text("❌ No se pudo descargar el video.")
            return

        if os.path.getsize(file_path) > 50 * 1024 * 1024:
            await msg.edit_text("❌ El archivo excede el límite de 50MB.")
            os.remove(file_path)
            return

        await msg.edit_text("📤 Enviando archivo...")

        with open(file_path, "rb") as f:
            if file_format == "mp3":
                await context.bot.send_audio(update.effective_chat.id, audio=f, caption="🎵 Aquí está tu MP3")
            else:
                await context.bot.send_video(update.effective_chat.id, video=f, caption="🎥 Aquí está tu MP4")
        await msg.delete()

    except Exception as e:
        logger.error(f"Error en download_handler: {e}")
        await msg.edit_text(str(e))
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    if isinstance(context.error, (Conflict, NetworkError, TimedOut)):
        await asyncio.sleep(5)

async def clear_webhook(application):
    try:
        await application.bot.delete_webhook()
        logger.info("Webhook eliminado exitosamente")
    except Exception as e:
        logger.warning(f"No se pudo eliminar webhook: {e}")

if __name__ == "__main__":
    token = os.getenv("BOT_TOKEN")
    if not token:
        logger.error("❌ BOT_TOKEN no encontrado")
        exit(1)

    application = Application.builder().token(token).build()
    application.add_error_handler(error_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("mp3", mp3))
    application.add_handler(CommandHandler("mp4", mp4))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_handler))

    asyncio.run(clear_webhook(application))

    logger.info("🚀 Iniciando bot...")
    application.run_polling(drop_pending_updates=True)
