import os
import re
import time
import threading
import http.server
import socketserver
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from yt_dlp import YoutubeDL

BOT_TOKEN = "8846850825:AAFNUneuiSG_EPlvcs1MC5Z7uz1cfphZj-Q"
TG_CHANNEL = "oqivaqotaril"
YT_CHANNEL_URL = "https://youtube.com/@islamicummah571?si=cdnypvM7njA3knKB"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

user_langs = {}
verified_users = set()
click_timers = {}
user_links = {}
users_db = set()

TEXTS = {
    'uz': {
        'welcome': "👋 **Xush kelibsiz!**\n\nMen **YouTube, Instagram, TikTok va Facebook**-dan video va audiolarni yuklab beruvchi botman.\n\nMenga video havolasini yuboring!",
        'select_lang': "🌐 **Iltimos, muloqot tilini tanlang:**",
        'lang_changed': "✅ **Til o'zgartirildi!**",
        'sub_required': "⚠️ **Botdan foydalanish uchun kanallarimizga obuna bo'ling!**",
        'btn_tg': "1️⃣ Telegram Kanal",
        'btn_yt': "2️⃣ YouTube Kanal",
        'btn_verify': "✅ Obunani Tasdiqlash",
        'timer_wait': "⏳ Kamida 4 soniya kuting!",
        'checking_link': "🔍 **Video tekshirilmoqda...**",
        'select_quality': "🎬 **Formatni tanlang:**",
        'downloading': "🔄 **Media yuklanmoqda...**",
        'sending': "🚀 **Yuborilmoqda...**",
        'success': "✨ **Muvaffaqiyatli yuklab berildi!**",
        'error_link': "❌ Iltimos, to'g'ri havola yuboring!",
        'error_download': "❌ **Yuklashda xatolik:** Platforma botni bloklagan bo'lishi mumkin yoki fayl juda katta.",
        'stats': "📊 Jami foydalanuvchilar: **{}**",
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

@bot.message_handler(commands=['start', 'lang'])
def start_handler(message):
    user_id = message.from_user.id
    users_db.add(user_id)
    if str(user_id) not in user_langs:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="setlang_uz"))
        bot.reply_to(message, TEXTS['uz']['select_lang'], reply_markup=markup)
    else:
        bot.reply_to(message, get_txt(user_id, 'welcome'), reply_markup=main_menu_keyboard(user_id))

@bot.callback_query_handler(func=lambda call: call.data.startswith("setlang_"))
def set_language_callback(call):
    user_id = call.from_user.id
    user_langs[str(user_id)] = call.data.replace("setlang_", "")
    bot.answer_callback_query(call.id, get_txt(user_id, 'lang_changed'))
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    bot.send_message(call.message.chat.id, get_txt(user_id, 'welcome'), reply_markup=main_menu_keyboard(user_id))

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
    bot.answer_callback_query(call.id, "✅ OK")
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    
    if url: fetch_and_show_formats(call.message.chat.id, user_id, url)

def fetch_and_show_formats(chat_id, user_id, url):
    msg = bot.send_message(chat_id, get_txt(user_id, 'checking_link'))
    
    # Blokirovkani aylanib o'tish sozlamalari (User-Agent bilan)
    ydl_opts = {
        'quiet': True, 
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("📹 Video (MP4)", callback_data="dl_video"),
                InlineKeyboardButton("🎵 Audio (MP3)", callback_data="dl_audio")
            )
            bot.delete_message(chat_id, msg.message_id)
            bot.send_message(chat_id, f"🎬 **{info.get('title', 'Media')}**\n\n{get_txt(user_id, 'select_quality')}", reply_markup=markup)
    except Exception as e:
        bot.edit_message_text(get_txt(user_id, 'error_download'), chat_id, msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("dl_"))
def download_selected_format(call):
    user_id = call.from_user.id
    url = user_links.get(str(user_id))
    fmt = call.data.replace("dl_", "")
    
    if not url: return
    bot.answer_callback_query(call.id, "🔄...")
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    
    download_and_send(call.message.chat.id, url, user_id, fmt)

@bot.message_handler(func=lambda message: True)
def message_handler(message):
    user_id = message.from_user.id
    users_db.add(user_id)
    text = message.text.strip()

    if text in [TEXTS[l]['btn_menu_lang'] for l in TEXTS if 'btn_menu_lang' in TEXTS[l]]:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="setlang_uz"))
        bot.reply_to(message, get_txt(user_id, 'select_lang'), reply_markup=markup)
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

def download_and_send(chat_id, url, user_id, fmt):
    status_msg = bot.send_message(chat_id, get_txt(user_id, 'downloading'))
    out_template = f"downloads/{user_id}_{int(time.time())}.%(ext)s"
    
    # Eng barqaror format kombinatsiyasi
    ydl_opts = {
        'outtmpl': out_template,
        'quiet': True,
        'max_filesize': 49 * 1024 * 1024,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
    }
    
    if fmt == "audio":
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}]
    else:
        ydl_opts['format'] = 'best[ext=mp4]/best'

    filename = None
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if fmt == "audio" and not filename.endswith(".mp3"):
                filename = os.path.splitext(filename)[0] + ".mp3"
            
        bot.edit_message_text(get_txt(user_id, 'sending'), chat_id, status_msg.message_id)
        
        with open(filename, 'rb') as file_data:
            if fmt == "audio":
                bot.send_audio(chat_id=chat_id, audio=file_data, caption=get_txt(user_id, 'success'))
            else:
                bot.send_video(chat_id=chat_id, video=file_data, caption=get_txt(user_id, 'success'))
            
        bot.delete_message(chat_id, status_msg.message_id)
        
    except Exception as e:
        bot.edit_message_text(get_txt(user_id, 'error_download'), chat_id, status_msg.message_id)
    finally:
        if filename and os.path.exists(filename):
            os.remove(filename)

if __name__ == "__main__":
    def run_dummy_server():
        PORT = int(os.environ.get("PORT", 8080))
        Handler = http.server.SimpleHTTPRequestHandler
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", PORT), Handler) as httpd: httpd.serve_forever()

    threading.Thread(target=run_dummy_server, daemon=True).start()
    bot.infinity_polling(timeout=10, long_polling_timeout=5)


