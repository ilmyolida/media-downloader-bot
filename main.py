import os
import re
import time
import asyncio
import http.server
import socketserver
import threading
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from yt_dlp import YoutubeDL

# --- SOZLAMALAR ---
API_ID = 33118317
API_HASH = "53aae636122c27a99a6c211ecc5d0c68"
BOT_TOKEN = "8846850825:AAFNUneuiSG_EPlvcs1MC5Z7uz1cfphZj-Q"

app = Client("media_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_links = {}

# --- DUMMY SERVER (Render o'chib qolmasligi uchun) ---
def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            httpd.serve_forever()
    except Exception:
        pass

threading.Thread(target=run_dummy_server, daemon=True).start()

# --- BOT BUYRUQLARI ---
@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply_text(
        "👋 **Xush kelibsiz!**\n\nMen **5-6 soatlik va har qanday hajmdagi** video hamda audiolarni yuklab beruvchi professional botman.\n\nMenga video havolasini yuboring!"
    )

@app.on_message(filters.text & ~filters.command(["start"]))
async def handle_links(client, message):
    url = message.text.strip()
    
    if not re.match(r'(https?://)?(www\.)?(youtube\.com|youtu\.be|instagram\.com|tiktok\.com|facebook\.com)/.+', url):
        await message.reply_text("❌ Iltimos, to'g'ri havola yuboring!")
        return

    user_links[message.from_user.id] = url
    
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📹 Video (MP4)", callback_data="dl_video")],
        [InlineKeyboardButton("🎵 Audio (MP3)", callback_data="dl_audio")]
    ])
    
    await message.reply_text("🎬 **Formatni tanlang:**", reply_markup=markup)

@app.on_callback_query(filters.regex(r"^dl_"))
async def download_callback(client, callback_query):
    user_id = callback_query.from_user.id
    fmt = callback_query.data.replace("dl_", "")
    url = user_links.get(user_id)
    
    if not url:
        await callback_query.answer("Havola topilmadi!", show_alert=True)
        return

    await callback_query.answer("🔄 Jarayon boshlandi...")
    status_msg = await callback_query.message.edit_text("🔍 **Media yuklanmoqda...**\nUzun videolar uchun biroz vaqt talab etiladi.")
    
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
        
    out_template = f"downloads/{user_id}_{int(time.time())}.%(ext)s"
    
    ydl_opts = {
        'outtmpl': out_template,
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
    }
    
    if fmt == "audio":
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}]
    else:
        ydl_opts['format'] = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]/best'

    filename = None
    try:
        loop = asyncio.get_running_loop()
        def extract():
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)

        filename = await loop.run_in_executor(None, extract)
        
        if fmt == "audio" and not filename.endswith(".mp3"):
            filename = os.path.splitext(filename)[0] + ".mp3"
                
        await status_msg.edit_text("🚀 **Fayl Telegram'ga yuborilmoqda...**")
        
        if fmt == "audio":
            await client.send_audio(chat_id=callback_query.message.chat.id, audio=filename, caption="✨ Muvaffaqiyatli yuklab berildi!")
        else:
            await client.send_video(chat_id=callback_query.message.chat.id, video=filename, caption="✨ Muvaffaqiyatli yuklab berildi!")
            
        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit_text(f"❌ **Xatolik:** Video o'ta katta yoki havola bilan muammo bor.")
    finally:
        if filename and os.path.exists(filename):
            os.remove(filename)

# --- XATOLIKLARNI OLDINI OLUVCHI STRATEGIYA ---
async def main():
    await app.start()
    print("🚀 Bot muvaffaqiyatli ishga tushdi!")
    # Tizim doimiy ishlab turishi uchun blokirovka
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

