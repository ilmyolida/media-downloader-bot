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

# Foydalanuvchilar ma'lumotlarini saqlash
user_langs = {}    # user_id -> 'uz', 'ru', 'en', 'tr', 'ar'
click_timers = {}  # user_id -> timestamp
user_links = {}    # user_id -> url
users_db = set()   # Unikal foydalanuvchilar bazasi

# --- MULTI-LANGUAGE (TILLAR LUG'ATI) ---
TEXTS = {
    'uz': {
        'welcome': "👋 **Xush kelibsiz!**\n\nMen **YouTube, Instagram, TikTok va Facebook**-dan videolarni bepul va tez yuklab beruvchi botman.\n\nMenga shunchaki video havolasini (link) yuboring!",
        'select_lang': "🌐 **Iltimos, muloqot tilini tanlang / Пожалуйста, выберите язык:**",
        'lang_changed': "✅ **Til o'zgartirildi!**",
        'sub_required': "⚠️ **Botdan foydalanish uchun kanallarimizga obuna bo'lishingiz shart!**\n\nA'zo bo'lgach, **Obunani Tasdiqlash** tugmasini bosing.",
        'btn_tg': "1️⃣ Telegram Kanal",
        'btn_yt': "2️⃣ YouTube Kanal",
        'btn_verify': "✅ Obunani Tasdiqlash",
        'timer_wait': "⏳ Obuna bo'lish uchun kanallarga o'ting va kamida 4 soniya kuting!",
        'downloading': "🔄 **Video yuklanmoqda...**\nIltimos, biroz kuting.",
        'sending': "🚀 **Video jo'natilmoqda...**",
        'success': "✨ **Video muvaffaqiyatli yuklab berildi!**\n\n🕊 @oqivaqotaril loyihasi.",
        'error_link': "❌ Iltimos, faqat to'g'ri YouTube, Instagram, TikTok yoki Facebook havolasini yuboring!",
        'error_download': "❌ **Xatolik:** Video juda katta bo'lishi mumkin yoki havola noto'g'ri.",
        'stats': "📊 **Bot Statistikasi:**\n\n👥 Jami foydalanuvchilar: **{}** ta",
        'btn_menu_lang': "🌐 Tilni o'zgartirish",
        'btn_menu_stats': "📊 Statistika",
        'btn_menu_help': "ℹ️ Yordam"
    },
    'ru': {
        'welcome': "👋 **Добро пожаловать!**\n\nЯ бот для бесплатной и быстрой загрузки видео с **YouTube, Instagram, TikTok и Facebook**.\n\nПросто отправьте мне ссылку на видео!",
        'select_lang': "🌐 **Пожалуйста, выберите язык:**",
        'lang_changed': "✅ **Язык успешно изменен!**",
        'sub_required': "⚠️ **Для использования бота необходимо подписаться на наши каналы!**\n\nПосле подписки нажмите **Проверить подписку**.",
        'btn_tg': "1️⃣ Telegram Канал",
        'btn_yt': "2️⃣ YouTube Канал",
        'btn_verify': "✅ Проверить подписку",
        'timer_wait': "⏳ Перейдите на каналы и подождите не менее 4 секунд!",
        'downloading': "🔄 **Видео скачивается...**\nПожалуйста, подождите.",
        'sending': "🚀 **Отправка видео...**",
        'success': "✨ **Видео успешно загружено!**\n\n🕊 Проект @oqivaqotaril.",
        'error_link': "❌ Пожалуйста, отправьте корректную ссылку на YouTube, Instagram, TikTok или Facebook!",
        'error_download': "❌ **Ошибка:** Видео слишком большое или ссылка недействительна.",
        'stats': "📊 **Статистика бота:**\n\n👥 Всего пользователей: **{}**",
        'btn_menu_lang': "🌐 Сменить язык",
        'btn_menu_stats': "📊 Статистика",
        'btn_menu_help': "ℹ️ Помощь"
    },
    'en': {
        'welcome': "👋 **Welcome!**\n\nI am a bot to download videos from **YouTube, Instagram, TikTok, and Facebook** for free and fast.\n\nJust send me the video link!",
        'select_lang': "🌐 **Please select a language:**",
        'lang_changed': "✅ **Language changed!**",
        'sub_required': "⚠️ **You must subscribe to our channels to use the bot!**\n\nAfter subscribing, click **Verify Subscription**.",
        'btn_tg': "1️⃣ Telegram Channel",
        'btn_yt': "2️⃣ YouTube Channel",
        'btn_verify': "✅ Verify Subscription",
        'timer_wait': "⏳ Please visit the channels and wait at least 4 seconds!",
        'downloading': "🔄 **Downloading video...**\nPlease wait.",
        'sending': "🚀 **Sending video...**",
        'success': "✨ **Video successfully downloaded!**\n\n🕊 @oqivaqotaril project.",
        'error_link': "❌ Please send a valid YouTube, Instagram, TikTok, or Facebook link!",
        'error_download': "❌ **Error:** Video might be too large or the link is invalid.",
        'stats': "📊 **Bot Statistics:**\n\n👥 Total users: **{}**",
        'btn_menu_lang': "🌐 Change Language",
        'btn_menu_stats': "📊 Statistics",
        'btn_menu_help': "ℹ️ Help"
    },
    'tr': {
        'welcome': "👋 **Hoş geldiniz!**\n\n**YouTube, Instagram, TikTok ve Facebook**'tan ücretsiz ve hızlı video indiren bir botum.\n\nBana sadece video bağlantısını gönderin!",
        'select_lang': "🌐 **Lütfen bir dil seçin:**",
        'lang_changed': "✅ **Dil değiştirildi!**",
        'sub_required': "⚠️ **Botu kullanmak için kanallarımıza abone olmalısınız!**\n\nAbone olduktan sonra **Aboneliği Doğrula** butonuna basın.",
        'btn_tg': "1️⃣ Telegram Kanalı",
        'btn_yt': "2️⃣ YouTube Kanalı",
        'btn_verify': "✅ Aboneliği Doğrula",
        'timer_wait': "⏳ Lütfen kanalları ziyaret edin ve en az 4 saniye bekleyin!",
        'downloading': "🔄 **Video indiriliyor...**\nLütfen bekleyin.",
        'sending': "🚀 **Video gönderiliyor...**",
        'success': "✨ **Video başarıyla indirildi!**\n\n🕊 @oqivaqotaril projesi.",
        'error_link': "❌ Lütfen geçerli bir YouTube, Instagram, TikTok veya Facebook bağlantısı gönderin!",
        'error_download': "❌ **Hata:** Video çok büyük olabilir veya bağlantı geçersiz.",
        'stats': "📊 **Bot İstatistikleri:**\n\n👥 Toplam kullanıcı: **{}**",
        'btn_menu_lang': "🌐 Dili Değiştir",
        'btn_menu_stats': "📊 İstatistikler",
        'btn_menu_help': "ℹ️ Yardım"
    },
    'ar': {
        'welcome': "👋 **أهلاً بك!**\n\nأنا بوت لتنزيل الفيديوهات من **YouTube و Instagram و TikTok و Facebook** مجانًا وبسرعة.\n\nفقط أرسل لي رابط الفيديو!",
        'select_lang': "🌐 **الرجاء اختيار اللغة:**",
        'lang_changed': "✅ **تم تغيير اللغة!**",
        'sub_required': "⚠️ **يجب عليك الاشتراك في قنواتنا لاستخدام البوت!**\n\nبعد الاشتراك، اضغط على **تأكيد الاشتراك**.",
        'btn_tg': "1️⃣ قناة التليجرام",
        'btn_yt': "2️⃣ قناة اليوتيوب",
        'btn_verify': "✅ تأكيد الاشتراك",
        'timer_wait': "⏳ يرجى الانتقال إلى القنوات والانتظار 4 ثوانٍ على الأقل!",
        'downloading': "🔄 **جاري تحميل الفيديو...**\nيرجى الانتظار.",
        'sending': "🚀 **جاري إرسال الفيديو...**",
        'success': "✨ **تم تحميل الفيديو بنجاح!**\n\n🕊 مشروع @oqivaqotaril.",
        'error_link': "❌ يرجى إرسال رابط صحيح من YouTube أو Instagram أو TikTok أو Facebook!",
        'error_download': "❌ **خطأ:** قد يكون الفيديو كبيرًا جدًا أو الرابط غير صالحة.",
        'stats': "📊 **إحصائيات البوت:**\n\n👥 إجمالي المستخدمين: **{}**",
        'btn_menu_lang': "🌐 تغيير اللغة",
        'btn_menu_stats': "📊 الإحصائيات",
        'btn_menu_help': "ℹ️ المساعدة"
    }
}

# Foydalanuvchi tilini olish funksiyasi (Standard: O'zbekcha)
def get_txt(user_id, key):
    lang = user_langs.get(str(user_id), 'uz')
    return TEXTS[lang].get(key, TEXTS['uz'][key])

# Asosiy Menyu Tugmalari (Reply Keyboard)
def main_menu_keyboard(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    lang_btn = KeyboardButton(get_txt(user_id, 'btn_menu_lang'))
    stats_btn = KeyboardButton(get_txt(user_id, 'btn_menu_stats'))
    help_btn = KeyboardButton(get_txt(user_id, 'btn_menu_help'))
    markup.row(lang_btn, stats_btn)
    markup.row(help_btn)
    return markup

# Tilni tanlash inline keyboardi
def language_inline_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="setlang_uz"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="setlang_ru")
    )
    markup.add(
        InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"),
        InlineKeyboardButton("🇹🇷 Türkçe", callback_data="setlang_tr")
    )
    markup.add(InlineKeyboardButton("🇸🇦 العربية", callback_data="setlang_ar"))
    return markup

# --- START BUYRUG'I ---
@bot.message_handler(commands=['start', 'lang'])
def start_handler(message):
    user_id = message.from_user.id
    users_db.add(user_id)
    
    # Agar foydalanuvchi tilni hali tanlamagan bo'lsa
    if str(user_id) not in user_langs:
        bot.reply_to(message, TEXTS['uz']['select_lang'], reply_markup=language_inline_keyboard())
    else:
        bot.reply_to(
            message, 
            get_txt(user_id, 'welcome'), 
            reply_markup=main_menu_keyboard(user_id)
        )

# --- TILNI O'ZGARTIRISH CALLBACK'I ---
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
        
    bot.send_message(
        call.message.chat.id,
        get_txt(user_id, 'welcome'),
        reply_markup=main_menu_keyboard(user_id)
    )

# --- TASDIQLASH TUGMASI (TAYMER) ---
@bot.callback_query_handler(func=lambda call: call.data == "verify_sub")
def verify_callback(call):
    user_id = call.from_user.id
    url = user_links.get(str(user_id))
    
    if not url:
        bot.answer_callback_query(call.id, "❌ Havola topilmadi!", show_alert=True)
        return
    
    current_time = time.time()
    start_time = click_timers.get(str(user_id), current_time)
    
    if (current_time - start_time) < 4.0:
        bot.answer_callback_query(call.id, get_txt(user_id, 'timer_wait'), show_alert=True)
        return

    bot.answer_callback_query(call.id, "✅ OK!")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    download_and_send_video(call.message, url, user_id)

# --- MATNLAR VA MENYU TUGMALARIGA ISHLOV BERISH ---
@bot.message_handler(func=lambda message: True)
def message_handler(message):
    user_id = message.from_user.id
    users_db.add(user_id)
    text = message.text.strip()

    # Menyu tugmalarini tekshirish
    if text in [TEXTS[l]['btn_menu_lang'] for l in TEXTS]:
        bot.reply_to(message, get_txt(user_id, 'select_lang'), reply_markup=language_inline_keyboard())
        return
        
    if text in [TEXTS[l]['btn_menu_stats'] for l in TEXTS]:
        bot.reply_to(message, get_txt(user_id, 'stats').format(len(users_db)))
        return
        
    if text in [TEXTS[l]['btn_menu_help'] for l in TEXTS]:
        bot.reply_to(message, get_txt(user_id, 'welcome'))
        return

    # Video Linkini tekshirish
    if not re.match(r'(https?://)?(www\.)?(youtube\.com|youtu\.be|instagram\.com|tiktok\.com|facebook\.com)/.+', text):
        bot.reply_to(message, get_txt(user_id, 'error_link'))
        return

    # Obuna taymerini va linkni saqlash
    click_timers[str(user_id)] = time.time()
    user_links[str(user_id)] = text

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(get_txt(user_id, 'btn_tg'), url=f"https://t.me/{TG_CHANNEL}"))
    markup.add(InlineKeyboardButton(get_txt(user_id, 'btn_yt'), url=YT_CHANNEL_URL))
    markup.add(InlineKeyboardButton(get_txt(user_id, 'btn_verify'), callback_data="verify_sub"))
    
    bot.reply_to(
        message,
        get_txt(user_id, 'sub_required'),
        reply_markup=markup
    )

# --- VIDEO YUKLASH FUNKSIYASI ---
def download_and_send_video(message, url, user_id):
    status_msg = bot.send_message(message.chat.id, get_txt(user_id, 'downloading'))
    
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
            
        bot.edit_message_text(get_txt(user_id, 'sending'), message.chat.id, status_msg.message_id)
        
        with open(filename, 'rb') as video_file:
            bot.send_video(
                chat_id=message.chat.id,
                video=video_file,
                caption=get_txt(user_id, 'success')
            )
            
        bot.delete_message(message.chat.id, status_msg.message_id)
        
    except Exception as e:
        bot.edit_message_text(get_txt(user_id, 'error_download'), message.chat.id, status_msg.message_id)
    finally:
        if filename and os.path.exists(filename):
            os.remove(filename)

# --- BOTNI ISHGA TUSHIRISH (RENDER PORT FIX BILAN) ---
if __name__ == "__main__":
    def run_dummy_server():
        PORT = int(os.environ.get("PORT", 8080))
        Handler = http.server.SimpleHTTPRequestHandler
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            httpd.serve_forever()

    threading.Thread(target=run_dummy_server, daemon=True).start()

    print("🚀 Professional Bot Ishga Tushdi!")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
                                  
