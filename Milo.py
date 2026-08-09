import os
import json
import time
import threading
from flask import Flask
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

TOKEN = "8952913458:AAEIrQqsi7MQ-1YmQZCJGYqTdj-RCswzi14"
ADMIN_USERNAME = "Mustafazx10"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

BANNED_WORDS_FILE = "banned_words.json"
BANNED_USERS_FILE = "banned_users.json"
WARNINGS_FILE = "warnings.json"

user_states = {}

def load_data(filename, default):
    try:
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return default

def save_data(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except:
        pass

banned_words = load_data(BANNED_WORDS_FILE, [])
banned_users = load_data(BANNED_USERS_FILE, [])
warnings = load_data(WARNINGS_FILE, {})

def is_admin(message):
    if message.from_user.username and message.from_user.username.lower() == ADMIN_USERNAME.lower():
        return True
    return False

@bot.message_handler(commands=["start"])
def start_command(message):
    if not is_admin(message):
        return

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("➕ إضافة كلمات محظورة (بأسطر)", callback_data="add_word"))
    markup.add(InlineKeyboardButton("🚫 حظر مستخدم", callback_data="ban_user"))
    markup.add(InlineKeyboardButton("✅ إلغاء حظر مستخدم", callback_data="unban_user"))
    markup.add(InlineKeyboardButton("📋 عرض الإعدادات", callback_data="show_settings"))

    bot.send_message(
        message.chat.id,
        "أهلاً بك يا مصطفى. هذه لوحة التحكم الخاصة ببوت الحماية:",
        reply_markup=markup,
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if not call.from_user.username or call.from_user.username.lower() != ADMIN_USERNAME.lower():
        bot.answer_callback_query(call.id, "هذه الأزرار لمالك البوت فقط.", show_alert=True)
        return

    user_id = call.from_user.id

    if call.data == "add_word":
        user_states[user_id] = "WAITING_FOR_BAD_WORD"
        bot.send_message(
            call.message.chat.id,
            "أرسل الكلمات المحظورة الآن. يمكنك إرسال عدة كلمات بحيث يكون كل كلمة في سطر مستقل.",
        )

    elif call.data == "ban_user":
        user_states[user_id] = "WAITING_FOR_BAN_USER"
        bot.send_message(call.message.chat.id, "أرسل معرف المستخدم (User ID) أو اليوزرنيم لحظره:")

    elif call.data == "unban_user":
        user_states[user_id] = "WAITING_FOR_UNBAN_USER"
        bot.send_message(call.message.chat.id, "أرسل المعرف أو اليوزرنيم لإلغاء حظره:")

    elif call.data == "show_settings":
        words_count = len(banned_words)
        banned_count = len(banned_users)
        text = f"📊 حالة النظام:\n\n- الكلمات المحظورة: {words_count}\n- المستخدمين المحظورين: {banned_count}"
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="back"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "back":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("➕ إضافة كلمات محظورة (بأسطر)", callback_data="add_word"))
        markup.add(InlineKeyboardButton("🚫 حظر مستخدم", callback_data="ban_user"))
        markup.add(InlineKeyboardButton("✅ إلغاء حظر مستخدم", callback_data="unban_user"))
        markup.add(InlineKeyboardButton("📋 عرض الإعدادات", callback_data="show_settings"))
        bot.edit_message_text("لوحة التحكم الرئيسية:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.message_handler(func=lambda message: True, content_types=["text"])
def handle_all_messages(message):
    user = message.from_user
    user_id = user.id
    text = message.text

    if user_id in user_states and user.username and user.username.lower() == ADMIN_USERNAME.lower():
        state = user_states[user_id]
        if state == "WAITING_FOR_BAD_WORD":
            lines = text.split("\n")
            added_count = 0
            for line in lines:
                word = line.strip().lower()
                if word and word not in banned_words:
                    banned_words.append(word)
                    added_count += 1
            save_data(BANNED_WORDS_FILE, banned_words)
            bot.reply_to(message, f"تمت إضافة {added_count} كلمة بنجاح.")
            del user_states[user_id]
            return

        elif state == "WAITING_FOR_BAN_USER":
            target = text.strip()
            if target not in banned_users:
                banned_users.append(target)
                save_data(BANNED_USERS_FILE, banned_users)
                bot.reply_to(message, f"تم حظر {target} بنجاح.")
            del user_states[user_id]
            return

        elif state == "WAITING_FOR_UNBAN_USER":
            target = text.strip()
            if target in banned_users:
                banned_users.remove(target)
                save_data(BANNED_USERS_FILE, banned_users)
                bot.reply_to(message, f"تم إلغاء حظر {target}.")
            del user_states[user_id]
            return

    if user.username and user.username.lower() == ADMIN_USERNAME.lower():
        return

    if str(user_id) in banned_users or (user.username and user.username in banned_users):
        try:
            bot.ban_chat_member(message.chat.id, user_id)
            bot.delete_message(message.chat.id, message.message_id)
        except:
            pass
        return

    text_lower = text.lower()
    for b_word in banned_words:
        if b_word in text_lower:
            try:
                bot.delete_message(message.chat.id, message.message_id)
            except:
                pass
            return

@app.route("/")
def home():
    return "Bot is running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    t = threading.Thread(target=lambda: bot.infinity_polling(skip_pending=True))
    t.daemon = True
    t.start()
    run_flask()
