import os
import re
import time
import threading
import http.server
import socketserver
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from yt_dlp import YoutubeDL

BOT_TOKEN = "8846850825:AAFNUneuiSG_EPlvcs1MC5Z7uz1cfphZj-Q"
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

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

# --- BOT INTERFEYSI ---
@bot.message_handler(commands=['start'])
def start_handler(message):
    bot.reply_to(
        message, 
        "👋 **Xush kelibsiz!**\n\nMen **YouTube, Instagram, TikTok** platformalaridan har qanday video va audiolarni professional tarzda yuklovchi botman.\n\nMenga video havolasini yuboring!"
    )

@bot.message_handler(func=lambda message: True)
def message_handler(message):
    url = message.text.strip()

    if not re.match(r'(https?://)?(www\.)?(youtube\.com|youtu\.be|instagram\.com|tiktok\.com|facebook\.com)/.+', url):
        bot.reply_to(message, "❌ Iltimos, to'g'ri video havolasini yuboring!")
        return

    user_links[str(message.from_user.id)] = url

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("📹 Video (MP4)", callback_data="dl_video"),
        InlineKeyboardButton("🎵 Audio (MP3)", callback_data="dl_audio")
    )
    bot.reply_to(message, "🎬 **Formatni tanlang:**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("dl_"))
def download_callback(call):
    user_id = str(call.from_user.id)
    fmt = call.data.replace("dl_", "")
    url = user_links.get(user_id)

    if not url:
        bot.answer_callback_query(call.id, "Havola topilmadi!", show_alert=True)
        return

    bot.answer_callback_query(call.id, "🔄 Yuklash boshlandi...")
    status_msg = bot.send_message(call.message.chat.id, "🔍 **Media yuklanmoqda...**\nUzun videolar uchun biroz vaqt talab etiladi.")
    
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass

    # Yuklash oqimini alohida Thread'ga olamiz (Server qotib qolmasligi uchun)
    threading.Thread(target=download_and_send, args=(call.message.chat.id, url, user_id, fmt, status_msg.message_id)).start()

def download_and_send(chat_id, url, user_id, fmt, status_msg_id):
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
        # Bepul server xotirasidan chiqib ketmasligi uchun o'rta-yaxshi sifatni (720p gacha) tanlaydi
        ydl_opts['format'] = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]/best'

    filename = None
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if fmt == "audio" and not filename.endswith(".mp3"):
                filename = os.path.splitext(filename)[0] + ".mp3"

        bot.edit_message_text("🚀 **Fayl Telegram'ga yuborilmoqda...**", chat_id, status_msg_id)

        with open(filename, 'rb') as file_data:
            if fmt == "audio":
                bot.send_audio(chat_id=chat_id, audio=file_data, caption="✨ @oqivaqotaril loyihasi.")
            else:
                bot.send_video(chat_id=chat_id, video=file_data, caption="✨ @oqivaqotaril loyihasi.")

        bot.delete_message(chat_id, status_msg_id)

    except Exception as e:
        bot.edit_message_text("❌ **Yuklashda xatolik:** Video o'ta ulkan yoki havola yopiq.", chat_id, status_msg_id)
    finally:
        if filename and os.path.exists(filename):
            os.remove(filename)

if __name__ == "__main__":
    print("🚀 Bot muvaffaqiyatli ishga tushdi!")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
