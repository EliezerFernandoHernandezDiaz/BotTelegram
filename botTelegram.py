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

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# User agents para rotar y evitar detección de bot
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0'
]

def retry_on_bot_detection(max_retries=3, base_delay=5):
    """Decorator para reintentar en caso de detección de bot"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_msg = str(e)
                    
                    if ("Sign in to confirm" in error_msg or 
                        "bot" in error_msg.lower() or 
                        "ExtractorError" in error_msg):
                        
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt) + random.uniform(0, 5)
                            logger.warning(f"Bot detectado, reintentando en {delay:.1f}s (intento {attempt + 1}/{max_retries})")
                            time.sleep(delay)
                            continue
                        else:
                            logger.error("Máximo de reintentos alcanzado")
                            raise Exception("YouTube ha bloqueado las descargas temporalmente. Intenta en unos minutos.")
                    
                    # Si es otro tipo de error, lanzarlo inmediatamente
                    raise e
            
            return None
        return wrapper
    return decorator

# Función mejorada para descargar contenido
@retry_on_bot_detection(max_retries=3)
def download_content(url, user_id, file_format):
    try:
        unique_name = f"{user_id}_{uuid.uuid4()}"
        output_name = f"{unique_name}.%(ext)s"

        # Configuración robusta para yt-dlp
        ydl_opts = {
            'format': 'bestaudio/best' if file_format == 'mp3' else 'best[ext=mp4][height<=720]/best[ext=mp4]/best',
            'outtmpl': output_name,
            'http_headers': {
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip,deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
            },
            'sleep_interval': random.uniform(1, 3),
            'max_sleep_interval': 10,
            'ignoreerrors': False,
            'no_warnings': False,
        }

        # Añadir cookies si existen
        cookies_file = 'youtube_cookies.txt'
        if os.path.exists(cookies_file):
            ydl_opts['cookiefile'] = cookies_file
            logger.info("Usando archivo de cookies")

        # Configuración específica para MP3
        if file_format == 'mp3':
            ydl_opts['postprocessors'] = [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }
            ]

        logger.info(f"Descargando: {url} en formato {file_format}")
        
        with YoutubeDL(ydl_opts) as ydl:
            # Extraer información primero para validar
            info = ydl.extract_info(url, download=False)
            
            # Validar duración (máximo 30 minutos)
            duration = info.get('duration', 0)
            if duration > 1800:  # 30 minutos
                raise Exception("❌ Video demasiado largo (máximo 30 minutos)")
            
            # Proceder con la descarga
            info = ydl.extract_info(url, download=True)
            downloaded_file = ydl.prepare_filename(info)
            
            # Ajustar nombre del archivo para MP3
            if file_format == 'mp3':
                downloaded_file = downloaded_file.replace('.webm', '.mp3').replace('.m4a', '.mp3')
            
            logger.info(f"Descarga completada: {info.get('title', 'Sin título')}")
            return downloaded_file
            
    except Exception as e:
        logger.error(f"Error en descarga: {e}")
        raise e

# Handler para el comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 ¡Hola! Este bot puede descargar videos de YouTube en MP3 o MP4.\n\n"
        "📋 Comandos disponibles:\n"
        "/mp3 - Para descargar en formato MP3 (audio)\n"
        "/mp4 - Para descargar en formato MP4 (video)\n\n"
        "Luego, envía el enlace del video de YouTube."
    )

# Handler para seleccionar MP3
async def mp3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['format'] = 'mp3'
    await update.message.reply_text("🎵 Has seleccionado MP3. Ahora envía un enlace de YouTube.")

# Handler para seleccionar MP4
async def mp4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['format'] = 'mp4'
    await update.message.reply_text("🎥 Has seleccionado MP4. Ahora envía un enlace de YouTube.")

# Handler mejorado para manejar el enlace
async def download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    user_id = update.message.from_user.id
    file_format = context.user_data.get('format')

    if not file_format:
        await update.message.reply_text(
            "⚠️ Por favor selecciona primero un formato usando /mp3 o /mp4."
        )
        return

    # Validar URL de YouTube
    if not ("youtube.com" in url or "youtu.be" in url):
        await update.message.reply_text(
            "❌ Por favor, envía un enlace válido de YouTube."
        )
        return

    logger.info(f"URL recibida: {url}")
    logger.info(f"Formato seleccionado: {file_format}")

    # Mensaje de procesamiento
    processing_msg = await update.message.reply_text(
        f"🔄 Descargando el contenido como {file_format.upper()}, por favor espera...\n"
        "⏳ Esto puede tomar unos minutos."
    )

    try:
        file_path = download_content(url, user_id, file_format)
        
        if file_path and os.path.exists(file_path):
            logger.info(f"Archivo descargado: {file_path}")
            
            # Verificar tamaño del archivo
            file_size = os.path.getsize(file_path)
            if file_size > 50 * 1024 * 1024:  # 50 MB
                await processing_msg.edit_text(
                    "❌ El archivo es demasiado grande para enviarlo por Telegram (máximo 50MB)."
                )
                os.remove(file_path)
                return

            # Actualizar mensaje de estado
            await processing_msg.edit_text("📤 Enviando archivo...")

            # Enviar archivo según el formato
            try:
                with open(file_path, 'rb') as file:
                    if file_format == 'mp3':
                        await context.bot.send_audio(
                            chat_id=update.effective_chat.id, 
                            audio=file,
                            caption="🎵 Descarga completada"
                        )
                    else:
                        await context.bot.send_video(
                            chat_id=update.effective_chat.id, 
                            video=file,
                            caption="🎥 Descarga completada"
                        )
                
                # Eliminar mensaje de procesamiento
                await processing_msg.delete()
                
            except Exception as send_error:
                logger.error(f"Error enviando archivo: {send_error}")
                await processing_msg.edit_text(
                    "❌ Error al enviar el archivo. El archivo puede estar corrupto."
                )
            finally:
                # Limpiar archivo
                if os.path.exists(file_path):
                    os.remove(file_path)
        else:
            await processing_msg.edit_text(
                "❌ No se pudo descargar el contenido. Verifica el enlace."
            )
            
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error en download_handler: {error_message}")
        
        # Mensaje de error más amigable
        if "YouTube ha bloqueado" in error_message:
            await processing_msg.edit_text(
                "⚠️ YouTube ha bloqueado las descargas temporalmente.\n"
                "Intenta de nuevo en unos minutos."
            )
        elif "demasiado largo" in error_message:
            await processing_msg.edit_text(error_message)
        else:
            await processing_msg.edit_text(
                "❌ Error al descargar el video. Verifica que el enlace sea válido y que el video esté disponible."
            )

# Handler para errores
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja errores del bot"""
    logger.error(f"Update {update} caused error {context.error}")
    
    # Manejo específico de errores 409
    if isinstance(context.error, Conflict):
        logger.warning("Error 409: Conflicto con otra instancia del bot")
        await asyncio.sleep(10)  # Esperar antes de continuar
        return
    
    # Otros errores de red
    if isinstance(context.error, (NetworkError, TimedOut)):
        logger.warning(f"Error de red: {context.error}")
        return

# Función para limpiar webhooks antes de iniciar
async def clear_webhook(token):
    """Limpia cualquier webhook existente"""
    import aiohttp
    
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{token}/deleteWebhook"
            async with session.post(url) as response:
                if response.status == 200:
                    logger.info("Webhook eliminado exitosamente")
                else:
                    logger.warning(f"No se pudo eliminar webhook: {response.status}")
    except Exception as e:
        logger.error(f"Error al limpiar webhook: {e}")

# Configuración principal del bot
async def main():
    # Obtener token
    token = os.getenv("BOT_TOKEN")
    if not token:
        logger.error("❌ Error: BOT_TOKEN no encontrado en las variables de entorno")
        return
    
    # Limpiar webhook antes de iniciar
    await clear_webhook(token)
    
    # Esperar un poco para asegurar que no hay conflictos
    await asyncio.sleep(5)
    
    # Crear aplicación con configuración especial para Render
    application = Application.builder().token(token).build()
    
    # Agregar handler de errores
    application.add_error_handler(error_handler)

    # Agregar handlers de comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("mp3", mp3))
    application.add_handler(CommandHandler("mp4", mp4))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_handler))

    # Configuración especial para evitar conflictos
    logger.info("🚀 Iniciando bot...")
    
    try:
        # Iniciar con configuración especial
        await application.initialize()
        await application.start()
        
        # Usar polling con configuración especial
        await application.updater.start_polling(
            drop_pending_updates=True,
            poll_interval=2.0,
            timeout=30,
            bootstrap_retries=5
        )
        
        logger.info("✅ Bot iniciado correctamente")
        
        # Mantener el bot corriendo
        await application.updater.idle()
        
    except Exception as e:
        logger.error(f"Error al iniciar el bot: {e}")
    finally:
        # Limpiar recursos
        await application.stop()
        await application.shutdown()

if __name__ == "__main__":
    asyncio.run(main())