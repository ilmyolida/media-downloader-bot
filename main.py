import os
import re
import time
import threading
import http.server
import socketserver
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from yt_dlp import YoutubeDL

# --- SOZLAMALAR ---
BOT_TOKEN = "8846850825:AAFNUneuiSG_EPlvcs1MC5Z7uz1cfphZj-Q"
TG_CHANNEL = "oqivaqotaril"  # Boshida @ belgisiz
YT_CHANNEL_URL = "https://youtube.com/@islamicummah571?si=cdnypvM7njA3knKB"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# Xotira
user_langs = {}
verified_users = set()
click_timers = {}
user_links = {}
user_formats = {} # Har bir foydalanuvchining video sifatlari ro'yxati
users_db = set()

# --- MULTI-LANGUAGE ---
TEXTS = {
    'uz': {
        'welcome': "👋 **Xush kelibsiz!**\n\nMen **YouTube, Instagram, TikTok va Facebook**-dan video va audiolarni yuqori sifatda yuklab beruvchi mukammal botman.\n\nMenga video havolasini (link) yuboring!",
        'select_lang': "🌐 **Iltimos, muloqot tilini tanlang:**",
        'lang_changed': "✅ **Til o'zgartirildi!**",
        'sub_required': "⚠️ **Botdan foydalanish uchun bir marta kanallarimizga obuna bo'ling!**\n\nA'zo bo'lgach, **Obunani Tasdiqlash** tugmasini bosing.",
        'btn_tg': "1️⃣ Telegram Kanal",
        'btn_yt': "2️⃣ YouTube Kanal",
        'btn_verify': "✅ Obunani Tasdiqlash",
        'timer_wait': "⏳ Obuna bo'lish uchun kanallarga o'ting va kamida 4 soniya kuting!",
        'checking_link': "🔍 **Video ma'lumotlari va sifatlari yuklanmoqda...**\nIltimos, kuting.",
        'select_quality': "🎬 **Video sifatini yoki formatni tanlang:**",
        'downloading': "🔄 **Media yuklanmoqda...**\nIltimos, biroz kuting.",
        'sending': "🚀 **Fayl yuborilmoqda...**",
        'success': "✨ **Muvaffaqiyatli yuklab berildi!**\n\n🕊 @oqivaqotaril loyihasi.",
        'error_link': "❌ Iltimos, faqat to'g'ri YouTube, Instagram, TikTok yoki Facebook havolasini yuboring!",
        'error_download': "❌ **Xatolik:** Video yuklab bo'lmadi (Hajmi 50MB dan katta bo'lishi yoki havola yopiq profildan bo'lishi mumkin).",
        'stats': "📊 **Bot Statistikasi:**\n\n👥 Jami foydalanuvchilar: **{}** ta",
        'btn_menu_lang': "🌐 Tilni o'zgartirish",
        'btn_menu_stats': "📊 Statistika",
        'btn_menu_help': "ℹ️ Yordam"
    }
}

def get_txt(user_id, key):
    lang = user_langs.get(str(user_id), 'uz')
    return TEXTS.get(lang, TEXTS['uz']).get(key, TEXTS['uz'][key])

def main_menu_keyboard(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton(get_txt(user_id, 'btn_menu_lang')), KeyboardButton(get_txt(user_id, 'btn_menu_stats')))
    markup.row(KeyboardButton(get_txt(user_id, 'btn_menu_help')))
    return markup

def language_inline_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="setlang_uz"))
    return markup

@bot.message_handler(commands=['start', 'lang'])
def start_handler(message):
    user_id = message.from_user.id
    users_db.add(user_id)
    if str(user_id) not in user_langs:
        bot.reply_to(message, TEXTS['uz']['select_lang'], reply_markup=language_inline_keyboard())
    else:
        bot.reply_to(message, get_txt(user_id, 'welcome'), reply_markup=main_menu_keyboard(user_id))

@bot.callback_query_handler(func=lambda call: call.data.startswith("setlang_"))
def set_language_callback(call):
    user_id = call.from_user.id
    user_langs[str(user_id)] = call.data.replace("setlang_", "")
    bot.answer_callback_query(call.id, get_txt(user_id, 'lang_changed'))
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    bot.send_message(call.message.chat.id, get_txt(user_id, 'welcome'), reply_markup=main_menu_keyboard(user_id))

# --- OBUNA TEKSHIRUVI (BIR MARTALIK) ---
@bot.callback_query_handler(func=lambda call: call.data == "verify_sub")
def verify_callback(call):
    user_id = call.from_user.id
    url = user_links.get(str(user_id))
    
    current_time = time.time()
    start_time = click_timers.get(str(user_id), current_time)
    
    if (current_time - start_time) < 4.0:
        bot.answer_callback_query(call.id, get_txt(user_id, 'timer_wait'), show_alert=True)
        return

    verified_users.add(user_id)
    bot.answer_callback_query(call.id, "✅ Obuna tasdiqlandi!")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    
    if url:
        fetch_and_show_formats(call.message.chat.id, user_id, url)

# --- VIDEO SIFATLARINI ANIQLASH VA TUGMA QILISH ---
def fetch_and_show_formats(chat_id, user_id, url):
    msg = bot.send_message(chat_id, get_txt(user_id, 'checking_link'))
    
    ydl_opts = {'quiet': True, 'no_warnings': True}
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            markup = InlineKeyboardMarkup()
            # Standart sifat variantlari va Audio
            markup.add(
                InlineKeyboardButton("📹 Eng yuqori sifat (HD)", callback_data="dl_best"),
                InlineKeyboardButton("📹 O'rta sifat (480p/720p)", callback_data="dl_medium")
            )
            markup.add(InlineKeyboardButton("🎵 Faqat Audio (MP3)", callback_data="dl_mp3"))
            
            bot.delete_message(chat_id, msg.message_id)
            bot.send_message(chat_id, f"🎬 **{info.get('title', 'Video')}**\n\n{get_txt(user_id, 'select_quality')}", reply_markup=markup)
    except Exception as e:
        bot.edit_message_text(get_txt(user_id, 'error_download'), chat_id, msg.message_id)

# --- SIFAT TANLANGANDA YUKLASH ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("dl_"))
def download_selected_format(call):
    user_id = call.from_user.id
    url = user_links.get(str(user_id))
    fmt_type = call.data.replace("dl_", "")
    
    if not url:
        bot.answer_callback_query(call.id, "❌ Havola topilmadi!", show_alert=True)
        return

    bot.answer_callback_query(call.id, "🔄 Yuklash boshlandi...")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    
    download_and_send(call.message.chat.id, url, user_id, fmt_type)

# --- LINK KELGANDA ---
@bot.message_handler(func=lambda message: True)
def message_handler(message):
    user_id = message.from_user.id
    users_db.add(user_id)
    text = message.text.strip()

    if text in [TEXTS[l]['btn_menu_lang'] for l in TEXTS if 'btn_menu_lang' in TEXTS[l]]:
        bot.reply_to(message, get_txt(user_id, 'select_lang'), reply_markup=language_inline_keyboard())
        return
    if text in [TEXTS[l]['btn_menu_stats'] for l in TEXTS if 'btn_menu_stats' in TEXTS[l]]:
        bot.reply_to(message, get_txt(user_id, 'stats').format(len(users_db)))
        return

    if not re.match(r'(https?://)?(www\.)?(youtube\.com|youtu\.be|instagram\.com|tiktok\.com|facebook\.com)/.+', text):
        bot.reply_to(message, get_txt(user_id, 'error_link'))
        return

    user_links[str(user_id)] = text

    if user_id in verified_users:
        fetch_and_show_formats(message.chat.id, user_id, text)
    else:
        click_timers[str(user_id)] = time.time()
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(get_txt(user_id, 'btn_tg'), url=f"https://t.me/{TG_CHANNEL}"))
        markup.add(InlineKeyboardButton(get_txt(user_id, 'btn_yt'), url=YT_CHANNEL_URL))
        markup.add(InlineKeyboardButton(get_txt(user_id, 'btn_verify'), callback_data="verify_sub"))
        bot.reply_to(message, get_txt(user_id, 'sub_required'), reply_markup=markup)

# --- YUKLASH FUNKSIYASI ---
def download_and_send(chat_id, url, user_id, fmt_type):
    status_msg = bot.send_message(chat_id, get_txt(user_id, 'downloading'))
    
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
        
    out_template = f"downloads/{user_id}_{int(time.time())}.%(ext)s"
    
    # Sifatga qarab format tanlash
    if fmt_type == "mp3":
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': out_template,
            'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}],
            'max_filesize': 49 * 1024 * 1024,
            'quiet': True
        }
    elif fmt_type == "medium":
        ydl_opts = {
            'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]/best',
            'outtmpl': out_template,
            'max_filesize': 49 * 1024 * 1024,
            'quiet': True
        }
    else: # best
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
            'outtmpl': out_template,
            'max_filesize': 49 * 1024 * 1024,
            'quiet': True
        }

    filename = None
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if fmt_type == "mp3" and not filename.endswith(".mp3"):
                filename = os.path.splitext(filename)[0] + ".mp3"
            
        bot.edit_message_text(get_txt(user_id, 'sending'), chat_id, status_msg.message_id)
        
        with open(filename, 'rb') as file_data:
            if fmt_type == "mp3":
                bot.send_audio(chat_id=chat_id, audio=file_data, caption=get_txt(user_id, 'success'))
            else:
                bot.send_video(chat_id=chat_id, video=file_data, caption=get_txt(user_id, 'success'))
            
        bot.delete_message(chat_id, status_msg.message_id)
        
    except Exception as e:
        bot.edit_message_text(get_txt(user_id, 'error_download'), chat_id, status_msg.message_id)
    finally:
        if filename and os.path.exists(filename):
            os.remove(filename)

# --- ISHGA TUSHIRISH ---
if __name__ == "__main__":
    def run_dummy_server():
        PORT = int(os.environ.get("PORT", 8080))
        Handler = http.server.SimpleHTTPRequestHandler
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            httpd.serve_forever()

    threading.Thread(target=run_dummy_server, daemon=True).start()
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
