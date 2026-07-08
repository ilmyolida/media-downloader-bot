import os
import re
import time
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from yt_dlp import YoutubeDL

# --- SOZLAMALAR ---
BOT_TOKEN = "8846850825:AAFNUneuiSG_EPlvcs1MC5Z7uz1cfphZj-Q"
TG_CHANNEL = "oqivaqotaril"  # Boshida @ belgisiz
YT_CHANNEL_URL = "https://youtube.com/@islamicummah571?si=cdnypvM7njA3knKB"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
click_timers = {}
user_links = {}  # Uzun linklarni vaqtinchalik saqlash uchun lug'at

# --- MAJBURIY OBUNA TEKSHIRUVI ---
def check_subscriptions(user_id):
    try:
        member = bot.get_chat_member(f"@{TG_CHANNEL}", user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except Exception:
        return False
    return False

# --- START BUYRUG'I ---
@bot.message_handler(commands=['start'])
def start_handler(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📢 Telegram Kanalimiz", url=f"https://t.me/{TG_CHANNEL}"))
    markup.add(InlineKeyboardButton("📺 YouTube Kanalimiz", url=YT_CHANNEL_URL))
    
    bot.reply_to(
        message,
        "👋 **Xush kelibsiz!**\n\n"
        "Men **YouTube, Instagram, TikTok va Facebook**-dan videolarni bepul va tez yuklab beruvchi botman.\n"
        "Menga shunchaki video havolasini (link) yuboring!",
        reply_markup=markup
    )

# --- TASDIQLASH TUGMASI ISHLOVCHI QISM ---
@bot.callback_query_handler(func=lambda call: call.data == "verify_sub")
def verify_callback(call):
    user_id = call.from_user.id
    url = user_links.get(str(user_id))
    
    if not url:
        bot.answer_callback_query(call.id, "❌ Havola topilmadi, iltimos linkni qaytadan yuboring!", show_alert=True)
        return
    
    current_time = time.time()
    start_time = click_timers.get(str(user_id), current_time)
    
    if (current_time - start_time) < 4.0:
        bot.answer_callback_query(call.id, "⏳ YouTube kanalga obuna bo'lish uchun havolaga o'ting va kamida 4 soniya kuting!", show_alert=True)
        return

    is_tg_sub = check_subscriptions(user_id)
    if is_tg_sub:
        bot.answer_callback_query(call.id, "✅ Obuna tasdiqlandi! Video yuklanmoqda...")
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        download_and_send_video(call.message, url, user_id)
    else:
        bot.answer_callback_query(call.id, "❌ Siz hali Telegram kanalimizga a'zo bo'lmadingiz!", show_alert=True)

# --- LINK KELGANDA ISHLOVCHI QISM ---
@bot.message_handler(func=lambda message: True)
def link_handler(message):
    user_id = message.from_user.id
    url = message.text.strip()

    # Linkni tekshirish
    if not re.match(r'(https?://)?(www\.)?(youtube\.com|youtu\.be|instagram\.com|tiktok\.com|facebook\.com)/.+', url):
        bot.reply_to(message, "❌ Iltimos, faqat to'g'ri YouTube, Instagram, TikTok yoki Facebook havolasini yuboring!")
        return

    # Obunani tekshirish
    is_tg_sub = check_subscriptions(user_id)
    
    if not is_tg_sub:
        click_timers[str(user_id)] = time.time()
        user_links[str(user_id)] = url  # Havolani vaqtinchalik xotiraga olamiz
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("1️⃣ Telegramga Obuna Bo'lish", url=f"https://t.me/{TG_CHANNEL}"))
        markup.add(InlineKeyboardButton("2️⃣ YouTube-ga Obuna Bo'lish", url=YT_CHANNEL_URL))
        markup.add(InlineKeyboardButton("✅ Obunani Tasdiqlash", callback_data="verify_sub"))
        
        bot.reply_to(
            message,
            "⚠️ **Botdan foydalanish uchun kanallarimizga obuna bo'lishingiz shart!**\n\n"
            "A'zo bo'lgach, **Obunani Tasdiqlash** tugmasini bosing.",
            reply_markup=markup
        )
        return

    download_and_send_video(message, url, user_id)

# --- VIDEO YUKLASH FUNKSIYASI ---
def download_and_send_video(message, url, user_id):
    status_msg = bot.send_message(message.chat.id, "🔄 **Video yuklanmoqda...**\nIltimos, biroz kuting.")
    
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
        
    out_template = f"downloads/{user_id}_%(id)s.%(ext)s"
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': out_template,
        'max_filesize': 48 * 1024 * 1024,
        'quiet': True
    }
    
    filename = None
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
        bot.edit_message_text("🚀 **Video jo'natilmoqda...**", message.chat.id, status_msg.message_id)
        
        with open(filename, 'rb') as video_file:
            bot.send_video(
                chat_id=message.chat.id,
                video=video_file,
                caption="✨ **Video muvaffaqiyatli yuklab berildi!**\n\n🕊 @oqivaqotaril loyihasi."
            )
            
        bot.delete_message(message.chat.id, status_msg.message_id)
        
    except Exception as e:
        bot.edit_message_text("❌ **Xatolik:** Video juda katta bo'lishi mumkin yoki havola noto'g'ri.", message.chat.id, status_msg.message_id)
    finally:
        if filename and os.path.exists(filename):
            os.remove(filename)

# --- BOTNI ISHGA TUSHIRISH ---
if __name__ == "__main__":
    import threading
    import http.server
    import socketserver

    def run_dummy_server():
        PORT = int(os.environ.get("PORT", 8080))
        Handler = http.server.SimpleHTTPRequestHandler
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            httpd.serve_forever()

    threading.Thread(target=run_dummy_server, daemon=True).start()

    print("🚀 Bot muvaffaqiyatli ishga tushdi!")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)


