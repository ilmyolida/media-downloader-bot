import asyncio
import os
import re
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.methods.utilities.idle import idle
from yt_dlp import YoutubeDL

# --- SOZLAMALAR ---
API_ID = 33118317
API_HASH = "53aae636122c27a99a6c211ecc5d0c68"
BOT_TOKEN = "8846850825:AAFNUneuiSG_EPlvcs1MC5Z7uz1cfphZj-Q"

TG_CHANNEL = "oqivaqotaril" # Boshida @ belgisiz
YT_CHANNEL_URL = "https://youtube.com/@islamicummah571?si=cdnypvM7njA3knKB"

app = Client("media_downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
click_timers = {}

# --- MAJBURIY OBUNA TEKSHIRUVI ---
async def check_subscriptions(user_id):
    try:
        member = await app.get_chat_member(TG_CHANNEL, user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except Exception:
        return False
    return False

# --- START BUYRUG'I ---
@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    await message.reply(
        "👋 **Xush kelibsiz!**\n\n"
        "Men **YouTube, Instagram, TikTok va Facebook**-dan videolarni bepul va tez yuklab beruvchi botman.\n"
        "Menga shunchaki video havolasini (link) yuboring!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Telegram Kanalimiz", url=f"https://t.me/{TG_CHANNEL}")],
            [InlineKeyboardButton("📺 YouTube Kanalimiz", url=YT_CHANNEL_URL)]
        ])
    )

# --- LINK KELGANDA ISHLOVCHI QISM ---
@app.on_message(filters.text & filters.private)
async def link_handler(client, message):
    user_id = message.from_user.id
    url = message.text.strip()

    # Linkni tekshirish
    if not re.match(r'(https?://)?(www\.)?(youtube\.com|youtu\.be|instagram\.com|tiktok\.com|facebook\.com)/.+', url):
        await message.reply("❌ Iltimos, faqat to'g'ri YouTube, Instagram, TikTok yoki Facebook havolasini yuboring!")
        return

    # Obunani tekshirish
    is_tg_sub = await check_subscriptions(user_id)
    
    if not is_tg_sub:
        click_timers[str(user_id)] = time.time()
        
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("1️⃣ Telegramga Obuna Bo'lish", url=f"https://t.me/{TG_CHANNEL}")],
            [InlineKeyboardButton("2️⃣ YouTube-ga Obuna Bo'lish", url=YT_CHANNEL_URL)],
            [InlineKeyboardButton("✅ Obunani Tasdiqlash", callback_data=f"verify_{url}")]
        ])
        await message.reply(
            "⚠️ **Botdan foydalanish uchun kanallarimizga obuna bo'lishingiz shart!**\n\n"
            "A'zo bo'lgach, **Obunani Tasdiqlash** tugmasini bosing.",
            reply_markup=btn
        )
        return

    await download_and_send_video(message, url)

# --- TASDIQLASH TUGMASI ---
@app.on_callback_query(filters.regex(r"^verify_"))
async def verify_callback(client, callback):
    user_id = callback.from_user.id
    url = callback.data.replace("verify_", "")
    
    current_time = time.time()
    start_time = click_timers.get(str(user_id), current_time)
    
    if (current_time - start_time) < 4.0:
        await callback.answer("⏳ YouTube kanalga obuna bo'lish uchun havolaga o'ting va kamida 4 soniya kuting!", show_alert=True)
        return

    is_tg_sub = await check_subscriptions(user_id)
    if is_tg_sub:
        await callback.answer("✅ Obuna tasdiqlandi! Video yuklanmoqda...", show_alert=False)
        await callback.message.delete()
        await download_and_send_video(callback.message, url)
    else:
        await callback.answer("❌ Siz hali Telegram kanalimizga a'zo bo'lmadingiz!", show_alert=True)

# --- VIDEO YUKLASH FUNKSIYASI ---
async def download_and_send_video(message, url):
    status_msg = await message.reply("🔄 **Video yuklanmoqda...**\nIltimos, biroz kuting.")
    
    out_template = f"downloads/{message.from_user.id}_%(id)s.%(ext)s"
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': out_template,
        'max_filesize': 48 * 1024 * 1024,
        'quiet': True
    }
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            filename = ydl.prepare_filename(info)
            
        await status_msg.edit_text("🚀 **Video jo'natilmoqda...**")
        
        await app.send_video(
            chat_id=message.chat.id,
            video=filename,
            caption="✨ **Video muvaffaqiyatli yuklab berildi!**\n\n🕊 @oqivaqotaril loyihasi."
        )
        
        if os.path.exists(filename):
            os.remove(filename)
            
        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit_text("❌ **Xatolik:** Video juda katta bo'lishi mumkin yoki havola noto'g'ri.")
        if 'filename' in locals() and os.path.exists(filename):
            os.remove(filename)

# --- ASOSIY ISHGA TUSHIRISH QISMI ---
async def main():
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
    
    print("🚀 Bot ishga tushmoqda...")
    await app.start()
    print("✅ Bot Telegramga muvaffaqiyatli ulandi va faol holatda!")
    
    # Pyrogram botni xavfsiz va uzluksiz ushlab turuvchi professional metod
    await idle()
    
    await app.stop()

if __name__ == "__main__":
    # Render muhitidagi asinxron event loop muammosini hal qiluvchi start
    asyncio.run(main())
        
