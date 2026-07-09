import os
import re
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from yt_dlp import YoutubeDL

# --- SOZLAMALAR ---
# --- SOZLAMALAR ---
API_ID = 33118317
API_HASH = "53aae636122c27a99a6c211ecc5d0c68"
BOT_TOKEN = "8846850825:AAFNUneuiSG_EPlvcs1MC5Z7uz1cfphZj-Q"

# Pyrogram Bot Kliyentini yaratish
app = Client("media_downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_links = {}

@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply_text(
        "👋 **Xush kelibsiz!**\n\nMen har qanday hajmdagi (hatto 5-6 soatlik, 2 GB gacha) videolarni yuklovchi **Professional Tizimman**.\n\nMenga link yuboring!"
    )

@app.on_message(filters.text & ~filters.command(["start", "lang"]))
async def handle_links(client, message):
    url = message.text.strip()
    
    if not re.match(r'(https?://)?(www\.)?(youtube\.com|youtu\.be|instagram\.com|tiktok\.com|facebook\.com)/.+', url):
        await message.reply_text("❌ Iltimos, to'g'ri havola yuboring!")
        return

    user_links[message.from_user.id] = url
    
    # Format tanlash tugmalari
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📹 Video (Eng yaxshi sifat)", callback_data="dl_video")],
        [InlineKeyboardButton("🎵 Audio (MP3 format)", callback_data="dl_audio")]
    ])
    
    await message.reply_text("🎬 **Formatni tanlang:**\nUshbu video har qanday hajda bo'lsa ham professional tizim orqali yuklanadi.", reply_markup=markup)

@app.on_callback_query(filters.regex(r"^dl_"))
async def download_callback(client, callback_query):
    user_id = callback_query.from_user.id
    fmt = callback_query.data.replace("dl_", "")
    url = user_links.get(user_id)
    
    if not url:
        await callback_query.answer("Havola topilmadi!", show_alert=True)
        return

    await callback_query.answer("🔄 Jarayon boshlandi...")
    status_msg = await callback_query.message.edit_text("🔍 **Video tahlil qilinmoqda va yuklanmoqda...**\nBu o'ta uzun videolar uchun biroz vaqt olishi mumkin.")
    
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
        
    out_template = f"downloads/{user_id}_{int(time.time())}.%(ext)s"
    
    # Professional yuklash sozlamalari (Cheklovlarsiz)
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
        # 5-6 soatlik videolarni 2GB dan oshirib yubormaslik uchun o'rtacha eng yaxshi sifatni tanlaydi
        ydl_opts['format'] = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best'

    filename = None
    try:
        # Sinxron yuklashni asinxron fonda ishga tushirish
        loop = asyncio.get_event_loop()
        with YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            filename = ydl.prepare_filename(info)
            if fmt == "audio" and not filename.endswith(".mp3"):
                filename = os.path.splitext(filename)[0] + ".mp3"
                
        await status_msg.edit_text("🚀 **Video serverga yuklab bo'lindi. Endi Telegram'ga yuborilmoqda...**")
        
        # Pyrogram orqali 2 GB GACHA FAYLLARNI YUKLASH (Katta tezlikda va uzilishlarsiz)
        if fmt == "audio":
            await client.send_audio(chat_id=message.chat.id, audio=filename, caption="✨ @oqivaqotaril loyihasi.")
        else:
            await client.send_video(chat_id=callback_query.message.chat.id, video=filename, caption="✨ @oqivaqotaril loyihasi.")
            
        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit_text(f"❌ **Xatolik yuz berdi:**\nServer xotirasi to'ldi yoki video hajmi o'ta ulkan.")
    finally:
        if filename and os.path.exists(filename):
            os.remove(filename)

if __name__ == "__main__":
    print("🚀 Mukammal MTProto Bot Ishga Tushdi!")
    app.run()

