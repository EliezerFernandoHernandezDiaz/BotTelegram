import os
import uuid
import requests
import subprocess
import json
import shutil
from urllib.parse import urlparse, urlunparse
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from yt_dlp import YoutubeDL

# ====== Copiar cookies.txt si está disponible ======
if os.path.exists("youtube_cookies.txt"):
    shutil.copy("youtube_cookies.txt", "/data/youtube_cookies.txt")
    print("✅ Archivo de cookies copiado correctamente.")
else:
    print("❌ Archivo youtube_cookies.txt no encontrado.")

# ====== TikTok ======
def resolve_tiktok_redirect(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        return response.url
    except:
        return url

def sanitize_tiktok_url(raw_url):
    parsed = urlparse(raw_url)
    return urlunparse(parsed._replace(query=""))

def reencode_video_for_telegram(file_path):
    output_path = f"reencoded_{file_path}"
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
             'stream=codec_type', '-of', 'json', file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=True
        )
        data = json.loads(result.stdout)
        has_video = bool(data.get("streams"))
    except:
        has_video = False

    try:
        if has_video:
            command = [
                "ffmpeg", "-y", "-i", file_path,
                "-t", "60", "-map", "0:v:0", "-map", "0:a:0",
                "-c:v", "libx264", "-c:a", "aac",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                output_path
            ]
        else:
            image_temp = f"black_{uuid.uuid4()}.jpg"
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", "color=black:s=1280x720:d=1",
                "-frames:v", "1", image_temp
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

            command = [
                "ffmpeg", "-y", "-loop", "1", "-i", image_temp,
                "-i", file_path, "-shortest",
                "-c:v", "libx264", "-c:a", "aac",
                "-pix_fmt", "yuv420p", "-tune", "stillimage",
                "-movflags", "+faststart", output_path
            ]

        subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return output_path
    except:
        return file_path

def download_tiktok_video(url, user_id):
    try:
        resolved_url = resolve_tiktok_redirect(url)
        clean_url = sanitize_tiktok_url(resolved_url)

        api_url = "https://tiktok-download-without-watermark.p.rapidapi.com/analysis"
        headers = {
            "X-RapidAPI-Key": "c987832c40msh8923556ddd5a6a4p1c1c87jsn3cd43aca712e",
            "X-RapidAPI-Host": "tiktok-download-without-watermark.p.rapidapi.com",
            "User-Agent": "Mozilla/5.0"
        }
        params = {"url": clean_url}

        response = requests.get(api_url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        video_url = data.get("data", {}).get("play")

        if video_url:
            filename = f"{user_id}_{uuid.uuid4()}.mp4"
            with requests.get(video_url, stream=True) as r:
                r.raise_for_status()
                with open(filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            return filename
    except:
        return "TRY_TIKWM"

# ====== YouTube ======
def convert_to_mp3(input_file, output_file):
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", input_file,
            "-vn", "-ar", "44100", "-ac", "2",
            "-b:a", "192k", output_file
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return output_file
    except:
        return input_file

def fallback_download_youtube(video_id, file_format, user_id):
    try:
        response = requests.get(
            "https://ytstream-download-youtube-videos.p.rapidapi.com/dl",
            params={"id": video_id},
            headers={
                "X-RapidAPI-Key": "c987832c40msh8923556ddd5a6a4p1c1c87jsn3cd43aca712e",
                "X-RapidAPI-Host": "ytstream-download-youtube-videos.p.rapidapi.com"
            }
        )
        data = response.json()

        if file_format == 'mp3':
            for itag in ['251', '250', '249']:
                audio_obj = next(
                    (a for a in data.get('link', {}).get('audio', {}).values() if a.get('itag') == itag),
                    None
                )
                if audio_obj and 'url' in audio_obj:
                    video_url = audio_obj['url']
                    break
            else:
                video_url = None
        else:
            video_streams = [
                v for v in data.get('link', {}).get('mp4', {}).values()
                if v.get('url')
            ]
            video_streams.sort(key=lambda x: x.get('bitrate', 0), reverse=True)
            video_url = video_streams[0]['url'] if video_streams else None

        if video_url:
            ext = 'webm' if file_format == 'mp3' else 'mp4'
            filename = f"{user_id}_{uuid.uuid4()}.{ext}"
            with requests.get(video_url, stream=True) as r:
                with open(filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            if file_format == 'mp3':
                mp3_name = filename.replace(".webm", ".mp3")
                mp3_path = convert_to_mp3(filename, mp3_name)
                os.remove(filename)
                return mp3_path
            return filename
        return None
    except:
        return None

def fallback_download_pipedapi(video_id, file_format, user_id):
    API_HOSTS = [
        "https://pipedapi.kavin.rocks",
        "https://pipedapi.adminforge.de",
        "https://pipedapi.joom.social",
        "https://pipedapi.lunar.icu",
        "https://pipedapi.moomoo.me"
    ]

    for host in API_HOSTS:
        try:
            print(f"🌐 Intentando fallback con PipedAPI: {host}")
            api_url = f"{host}/streams/{video_id}"
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if file_format == 'mp3':
                audio_streams = data.get('audioStreams', [])
                best_audio = max(audio_streams, key=lambda x: x.get('bitrate', 0)) if audio_streams else None
                video_url = best_audio.get('url') if best_audio else None
                ext = 'webm'
            else:
                video_streams = [
                    v for v in data.get('videoStreams', [])
                    if v.get('container') == 'mp4'
                ]
                best_video = max(video_streams, key=lambda x: x.get('bitrate', 0)) if video_streams else None
                video_url = best_video.get('url') if best_video else None
                ext = 'mp4'

            if video_url:
                filename = f"{user_id}_{uuid.uuid4()}.{ext}"
                with requests.get(video_url, stream=True) as r:
                    r.raise_for_status()
                    with open(filename, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                if file_format == 'mp3':
                    mp3_name = filename.replace(".webm", ".mp3")
                    mp3_path = convert_to_mp3(filename, mp3_name)
                    os.remove(filename)
                    print(f"✅ Fallback PipedAPI exitoso desde {host}")
                    return mp3_path
                print(f"✅ Fallback PipedAPI exitoso desde {host}")
                return filename
        except Exception as e:
            print(f"⚠️ Falló con {host}: {e}")
            continue

    print("❌ Todos los PipedAPI fallaron.")
    return None


def download_content(url, user_id, file_format):
    import re
    output_name = f"{user_id}_{uuid.uuid4()}.%(ext)s"
    video_id = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
    video_id = video_id.group(1) if video_id else None

    def try_download(client_type):
        try:
            ydl_opts = {
                'format': 'bestaudio/best' if file_format == 'mp3' 
                else 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
                'outtmpl': output_name,
                'cookiefile': '/data/youtube_cookies.txt',
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'http_headers': {
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                },
                'geo_bypass': True,
                'nocheckcertificate': True,
                'player_client': client_type,
                'quiet': False,
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
            print(f"⚠️ yt-dlp falló con client '{client_type}': {e}")
            return None

    file_path = try_download('android')
    if file_path:
        print("✅ Descargado con yt-dlp usando client 'android'")
    else:
        file_path = try_download('tvhtml5')
        if file_path:
            print("✅ Descargado con yt-dlp usando client 'tvhtml5'")

    if not file_path and video_id:
        file_path = fallback_download_youtube(video_id, file_format, user_id)
        if file_path:
            print("✅ Descargado con fallback RapidAPI (ytstream)")

    if not file_path and video_id:
        file_path = fallback_download_pipedapi(video_id, file_format, user_id)
        if file_path:
            print("✅ Descargado con fallback PipedAPI")
        else:
            print("❌ Todos los métodos fallaron")

    return file_path

# ====== Telegram Handlers ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hola! Este bot descarga videos de YouTube y TikTok.\n\n" +
        "/mp3 - Descargar MP3 de YouTube\n" +
        "/mp4 - Descargar MP4 de YouTube\n" +
        "/tiktok - Descargar video de TikTok"
    )

async def mp3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['format'] = 'mp3'
    await update.message.reply_text("Envíame el link de YouTube para descargar el MP3.")

async def mp4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['format'] = 'mp4'
    await update.message.reply_text("Envíame el link de YouTube para descargar el MP4.")

async def tiktok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['format'] = 'tiktok'
    await update.message.reply_text("Envíame el link de TikTok para descargarlo sin marca de agua.")

async def download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    user_id = update.message.from_user.id
    file_format = context.user_data.get('format')

    if not file_format:
        await update.message.reply_text("Por favor, usa primero /mp3, /mp4 o /tiktok.")
        return

    if "youtube.com" in url or "youtu.be" in url:
        await update.message.reply_text("Procesando YouTube...")
        file_path = download_content(url, user_id, file_format)
        if file_path:
            if os.path.getsize(file_path) > 50 * 1024 * 1024:
                await update.message.reply_text("El archivo es demasiado grande para Telegram.")
                return
            if file_format == 'mp3':
                await context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(file_path, 'rb'))
            else:
                await context.bot.send_video(chat_id=update.effective_chat.id, video=open(file_path, 'rb'))
            os.remove(file_path)
        else:
            await update.message.reply_text("No se pudo descargar el contenido.")

    elif "tiktok.com" in url or "vm.tiktok.com" in url:
        await update.message.reply_text("Procesando TikTok...")
        file_path = download_tiktok_video(url, user_id)
        if file_path == "TRY_TIKWM":
            await update.message.reply_text("Intentando otro servidor, espera un momento...")
            try:
                response = requests.get("https://tikwm.com/api/", params={"url": url}, timeout=10)
                data = response.json()
                video_url = data.get("data", {}).get("play")
                if video_url:
                    file_path = f"{user_id}_{uuid.uuid4()}.mp4"
                    with requests.get(video_url, stream=True) as r:
                        with open(file_path, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
            except:
                await update.message.reply_text("No se pudo descargar el video.")
                return

        if file_path:
            reencoded_path = reencode_video_for_telegram(file_path)
            if os.path.getsize(reencoded_path) > 50 * 1024 * 1024:
                await update.message.reply_text("Video muy grande para Telegram.")
                return
            await context.bot.send_video(chat_id=update.effective_chat.id, video=open(reencoded_path, 'rb'))
            os.remove(file_path)
            if reencoded_path != file_path:
                os.remove(reencoded_path)
        else:
            await update.message.reply_text("No se pudo procesar el video.")
    else:
        await update.message.reply_text("Link no reconocido. Solo YouTube o TikTok")

# ====== Main ======
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
