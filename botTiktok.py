import os
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from playwright.sync_api import sync_playwright  # Playwright en lugar de Selenium

# 🔥 Cargar variables de entorno
load_dotenv()
BOT_TOKEN_TT = os.getenv("BOT_TOKEN_TT")  # Token separado si lo deseas

# 📂 Carpeta de descargas
DOWNLOAD_DIR = "Downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

### 🔥 FUNCIÓN PARA DESCARGAR TIKTOK SIN MARCA DE AGUA
def download_tiktok(video_url, user_id):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://ssstik.io/")

            # Ingresar el link del video
            page.fill("input#main_page_text", video_url)
            page.keyboard.press("Enter")

            # Esperar a que aparezca el botón de descarga
            page.wait_for_selector("a.without_watermark", timeout=10000)

            # Obtener el enlace de descarga
            download_url = page.get_attribute("a.without_watermark", "href")
            browser.close()

            # Descargar el video
            if download_url:
                output_path = f"{DOWNLOAD_DIR}/tiktok_{user_id}.mp4"
                response = requests.get(download_url, stream=True)
                with open(output_path, "wb") as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                return output_path
    except Exception as e:
        print(f"❌ Error en TikTok: {e}")
        return None

### 🔥 HANDLERS DEL BOT DE TELEGRAM
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 ¡Hola! Envíame un enlace de **TikTok** y te lo descargaré.")

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

### 🔥 INICIAR EL BOT
def run_tiktok_bot():
    application = Application.builder().token(BOT_TOKEN_TT).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_handler))
    application.run_polling(drop_pending_updates=True)
