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

# Xotira va ma'lumotlar bazasi
user_langs = {}      # user_id -> lang
verified_users = set() # Bir marta obuna bo'lgan foydalanuvchilar IDsi
click_timers = {}    # user_id -> time
user_links = {}      # user_id -> link
users_db = set()     # Unikal foydalanuvchilar

# --- MULTI-LANGUAGE DICTIONARY ---
TEXTS = {
    'uz': {
        'welcome': "👋 **Xush kelibsiz!**\n\nMen **YouTube, Instagram, TikTok va Facebook**-dan video va audiolarni yuqori sifatda yuklab beraman.\n\nMenga shunchaki media havolasini (link) yuboring!",
        'select_lang': "🌐 **Iltimos, muloqot tilini tanlang / Пожалуйста, выберите язык:**",
        'lang_changed': "✅ **Til o'zgartirildi!**",
        'sub_required': "⚠️ **Botdan foydalanish uchun bir marta kanallarimizga obuna bo'ling!**\n\nA'zo bo'lgach, **Obunani Tasdiqlash** tugmasini bosing.",
        'btn_tg': "1️⃣ Telegram Kanal",
        'btn_yt': "2️⃣ YouTube Kanal",
        'btn_verify': "✅ Obunani Tasdiqlash",
        'timer_wait': "⏳ Obuna bo'lish uchun kanallarga o'ting va kamida 4 soniya kuting!",
        'select_format': "🎬 **Formatni tanlang:**\nNima shaklida yuklab olishni xohlaysiz?",
        'btn_mp4': "📹 Video (MP4)",
        'btn_mp3': "🎵 Audio (MP3)",
        'downloading': "🔄 **Media yuklanmoqda...**\nIltimos, biroz kuting.",
        'sending': "🚀 **Fayl yuborilmoqda...**",
        'success': "✨ **Muvaffaqiyatli yuklab berildi!**\n\n🕊 @oqivaqotaril loyihasi.",
        'error_link': "❌ Iltimos, faqat to'g'ri YouTube, Instagram, TikTok yoki Facebook havolasini yuboring!",
        'error_download': "❌ **Xatolik:** Video o'lchami o'ta katta (50MB dan ortiq) yoki havola yopiq profildan.",
        'stats': "📊 **Bot Statistikasi:**\n\n👥 Jami foydalanuvchilar: **{}** ta",
        'btn_menu_lang': "🌐 Tilni o'zgartirish",
        'btn_menu_stats': "📊 Statistika",
        'btn_menu_help': "ℹ️ Yordam"
    },
    'ru': {
        'welcome': "👋 **Добро пожаловать!**\n\nЯ скачиваю видео и аудио с **YouTube, Instagram, TikTok и Facebook** в высоком качестве.\n\nПросто отправьте мне ссылку!",
        'select_lang': "🌐 **Пожалуйста, выберите язык:**",
        'lang_changed': "✅ **Язык успешно изменен!**",
        'sub_required': "⚠️ **Подпишитесь на наши каналы один раз для доступа к боту!**",
        'btn_tg': "1️⃣ Telegram Канал",
        'btn_yt': "2️⃣ YouTube Канал",
        'btn_verify': "✅ Проверить подписку",
        'timer_wait': "⏳ Перейдите на каналы и подождите не менее 4 секунд!",
        'select_format': "🎬 **Выберите формат:**\nВ каком формате вы хотите скачать?",
        'btn_mp4': "📹 Видео (MP4)",
        'btn_mp3': "🎵 Аудио (MP3)",
        'downloading': "🔄 **Медиа скачивается...**\nПожалуйста, подождите.",
        'sending': "🚀 **Отправка файла...**",
        'success': "✨ **Успешно загружено!**\n\n🕊 Проект @oqivaqotaril.",
        'error_link': "❌ Отправьте корректную ссылку на YouTube, Instagram, TikTok или Facebook!",
        'error_download': "❌ **Ошибка:** Файл слишком большой (более 50 МБ) или ссылка недоступна.",
        'stats': "📊 **Статистика бота:**\n\n👥 Всего пользователей: **{}**",
        'btn_menu_lang': "🌐 Сменить язык",
        'btn_menu_stats': "📊 Статистика",
        'btn_menu_help': "ℹ️ Помощь"
    }
}

def get_txt(user_id, key):
    lang = user_langs.get(str(user_id), 'uz')
    return TEXTS.get(lang, TEXTS['uz']).get(key, TEXTS['uz'][key])

def main_menu_keyboard(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    lang_btn = KeyboardButton(get_txt(user_id, 'btn_menu_lang'))
    stats_btn = KeyboardButton(get_txt(user_id, 'btn_menu_stats'))
    help_btn = KeyboardButton(get_txt(user_id, 'btn_menu_help'))
    markup.row(lang_btn, stats_btn)
    markup.row(help_btn)
    return markup

def language_inline_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="setlang_uz"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="setlang_ru")
    )
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
    lang_code = call.data.replace("setlang_", "")
    user_langs[str(user_id)] = lang_code
    
    bot.answer_callback_query(call.id, get_txt(user_id, 'lang_changed'))
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    bot.send_message(call.message.chat.id, get_txt(user_id, 'welcome'), reply_markup=main_menu_keyboard(user_id))

# --- OBUNA TASDIQLASH (BIR MARTA) ---
@bot.callback_query_handler(func=lambda call: call.data == "verify_sub")
def verify_callback(call):
    user_id = call.from_user.id
    url = user_links.get(str(user_id))
    
    current_time = time.time()
    start_time = click_timers.get(str(user_id), current_time)
    
    if (current_time - start_time) < 4.0:
        bot.answer_callback_query(call.id, get_txt(user_id, 'timer_wait'), show_alert=True)
        return

    # Foydalanuvchini doimiy ruxsat berilganlar ro'yxatiga qo'shamiz
    verified_users.add(user_id)
    bot.answer_callback_query(call.id, "✅ Rahmat! Endi bemalol foydalanishingiz mumkin.")
    
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
        
    if url:
        show_format_options(call.message.chat.id, user_id)

def show_format_options(chat_id, user_id):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(get_txt(user_id, 'btn_mp4'), callback_data="dl_mp4"),
        InlineKeyboardButton(get_txt(user_id, 'btn_mp3'), callback_data="dl_mp3")
    )
    bot.send_message(chat_id, get_txt(user_id, 'select_format'), reply_markup=markup)

# --- FORMAT TANLANGANDA (MP4 yoki MP3) ---
@bot.callback_query_handler(func=lambda call: call.data in ["dl_mp4", "dl_mp3"])
def download_choice_callback(call):
    user_id = call.from_user.id
    url = user_links.get(str(user_id))
    
    if not url:
        bot.answer_callback_query(call.id, "❌ Havola topilmadi, qaytadan yuboring!", show_alert=True)
        return

    is_audio = (call.data == "dl_mp3")
    bot.answer_callback_query(call.id, "🔄...")
    
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
        
    download_and_send_media(call.message.chat.id, url, user_id, is_audio)

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

    # Agar foydalanuvchi ilgarigi safar obuna bo'lgan bo'lsa - OBUNA SO'RAMAYDI!
    if user_id in verified_users:
        show_format_options(message.chat.id, user_id)
    else:
        click_timers[str(user_id)] = time.time()
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(get_txt(user_id, 'btn_tg'), url=f"https://t.me/{TG_CHANNEL}"))
        markup.add(InlineKeyboardButton(get_txt(user_id, 'btn_yt'), url=YT_CHANNEL_URL))
        markup.add(InlineKeyboardButton(get_txt(user_id, 'btn_verify'), callback_data="verify_sub"))
        
        bot.reply_to(message, get_txt(user_id, 'sub_required'), reply_markup=markup)

# --- MEDIA YUKLASH TIZIMI ---
def download_and_send_media(chat_id, url, user_id, is_audio=False):
    status_msg = bot.send_message(chat_id, get_txt(user_id, 'downloading'))
    
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
        
    out_template = f"downloads/{user_id}_{int(time.time())}.%(ext)s"
    
    # Optimizatsiyalashgan yt-dlp sozlamasi
    if is_audio:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': out_template,
            'max_filesize': 49 * 1024 * 1024,
            'quiet': True
        }
    else:
        ydl_opts = {
            'format': 'best[ext=mp4]/bestvideo+bestaudio/best',
            'outtmpl': out_template,
            'max_filesize': 49 * 1024 * 1024,
            'quiet': True
        }
    
    filename = None
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
        bot.edit_message_text(get_txt(user_id, 'sending'), chat_id, status_msg.message_id)
        
        with open(filename, 'rb') as file_data:
            if is_audio:
                bot.send_audio(chat_id=chat_id, audio=file_data, caption=get_txt(user_id, 'success'))
            else:
                bot.send_video(chat_id=chat_id, video=file_data, caption=get_txt(user_id, 'success'))
            
        bot.delete_message(chat_id, status_msg.message_id)
        
    except Exception as e:
        bot.edit_message_text(get_txt(user_id, 'error_download'), chat_id, status_msg.message_id)
    finally:
        if filename and os.path.exists(filename):
            os.remove(filename)

# --- BOTNI ISHGA TUSHIRISH ---
if __name__ == "__main__":
    def run_dummy_server():
        PORT = int(os.environ.get("PORT", 8080))
        Handler = http.server.SimpleHTTPRequestHandler
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            httpd.serve_forever()

    threading.Thread(target=run_dummy_server, daemon=True).start()
    print("🚀 Professional Bot Tayyor!")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

