import os
import uuid
import time
import requests
import yt_dlp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

# 🔥 Cargar variables de entorno desde Railway
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# 🔍 Depuración: Mostrar el token en logs (NO RECOMENDADO EN PRODUCCIÓN)
print(f"🔍 BOT_TOKEN en Railway: {BOT_TOKEN}")

# ⚠ Verificar que la variable BOT_TOKEN no esté vacía
if not BOT_TOKEN:
    raise ValueError("❌ ERROR: No se encontró BOT_TOKEN en las variables de entorno.")

# 📂 Carpeta de descargas
DOWNLOAD_DIR = "Downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

### 🔥 FUNCIÓN PARA DESCARGAR MP3 O MP4 DE YOUTUBE
def download_youtube(url, user_id, file_format):
    try:
        unique_name = f"{user_id}_{uuid.uuid4()}"
        output_name = f"{DOWNLOAD_DIR}/{unique_name}.%(ext)s"

        ydl_opts = {
            "outtmpl": output_name,
            "format": "bestaudio/best" if file_format == "mp3" else "bestvideo+bestaudio",
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}] if file_format == "mp3" else [],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_file = ydl.prepare_filename(info).replace(".webm", ".mp3" if file_format == "mp3" else ".mp4")
            return downloaded_file
    except Exception as e:
        print(f"Error en yt-dlp: {e}")
        return None

### 🔥 FUNCIÓN PARA DESCARGAR TIKTOK SIN MARCA DE AGUA
def download_tiktok(video_url, user_id):
    try:
        # Expandir enlace corto si es necesario
        if "vm.tiktok.com" in video_url or "vt.tiktok.com" in video_url:
            video_url = requests.head(video_url, allow_redirects=True).url
            print(f"✅ Enlace expandido: {video_url}")

        video_id = video_url.split("/")[-1].split("?")[0]  # Obtener ID único del video
        output_path = f"{DOWNLOAD_DIR}/tiktok_{user_id}_{video_id}.mp4"

        options = webdriver.ChromeOptions()
        options.binary_location = "/usr/bin/google-chrome"
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-accelerated-2d-canvas")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--remote-debugging-port=9222")

        driver = webdriver.Chrome(options=options)
        driver.get("https://ssstik.io/")

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "main_page_text")))

        input_box = driver.find_element(By.ID, "main_page_text")
        input_box.send_keys(video_url)
        input_box.send_keys(Keys.RETURN)

        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, "//a[contains(@class, 'without_watermark')]")))

        download_button = driver.find_element(By.XPATH, "//a[contains(@class, 'without_watermark')]")
        video_download_url = download_button.get_attribute("href")

        if video_download_url:
            headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://ssstik.io/"}
            video_response = requests.get(video_download_url, headers=headers, stream=True)

            if video_response.status_code == 200:
                with open(output_path, "wb") as f:
                    for chunk in video_response.iter_content(1024):
                        f.write(chunk)
                driver.quit()
                return output_path
    except Exception as e:
        print(f"❌ Error en TikTok: {e}")
    finally:
        driver.quit()
    return None

### 🔥 HANDLERS DEL BOT DE TELEGRAM
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 ¡Hola! Envíame un enlace de **YouTube o TikTok** y te lo descargaré.")

async def download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    user_id = update.message.from_user.id

    if "tiktok.com" in url:
        await update.message.reply_text("🎥 Descargando video de TikTok, espera...")
        video_path = download_tiktok(url, user_id)
        if video_path:
            await context.bot.send_video(chat_id=update.effective_chat.id, video=open(video_path, 'rb'))
            os.remove(video_path)
        else:
            await update.message.reply_text("❌ Error al descargar el video de TikTok.")

    elif "youtube.com" in url or "youtu.be" in url:
        file_format = "mp4"
        await update.message.reply_text(f"📥 Descargando en **{file_format.upper()}**, espera...")
        file_path = download_youtube(url, user_id, file_format)
        if file_path:
            await context.bot.send_video(chat_id=update.effective_chat.id, video=open(file_path, 'rb'))
            os.remove(file_path)
        else:
            await update.message.reply_text("❌ No se pudo descargar el contenido.")

### 🔥 INICIAR EL BOT
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_handler))

    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
