from flask import Flask
import threading, os
import telebot
from pymongo import MongoClient

# === CONFIGURATION ===
API_TOKEN        = '7702090142:AAF0Ji1ERwbT3bwE5PPiu33zSUlh-P2UHpk'  # Your Bot Token
ADMIN_ID         = 8075098988                                   # Your Telegram User ID
MONGO_URI        = 'mongodb+srv://deybarun176:JNIj1Yy45xOzx4Av@barun.7t6nu9s.mongodb.net/?retryWrites=true&w=majority&appName=Barun'
MOVIE_CHANNEL_ID = -1002605645508    # Movie Store channel ID
LOG_CHANNEL_ID   = -1002661190627    # Log channel ID

# === SETUP ===
bot = telebot.TeleBot(API_TOKEN)
client = MongoClient(MONGO_URI)
db = client['moviebot']
col = db['movies']

# === /start COMMAND ===
@bot.message_handler(commands=['start'])
def handle_start(message):
    text = (
        "👋 Welcome to MovieBot!\n"
        "🎥 Just type the exact movie name to get the file."
    )
    bot.send_message(message.chat.id, text)

# === AUTO-ADD HANDLER FOR MOVIE CHANNEL ===
@bot.message_handler(content_types=['document', 'video', 'audio'])
def handle_channel_post(message):
    # Only process in Movie Store channel
    if message.chat.id != MOVIE_CHANNEL_ID:
        return
    caption = message.caption or ''
    if '|' not in caption:
        return
    name_part, year_part = [p.strip() for p in caption.split('|', 1)]
    if not name_part or not year_part:
        return
    name = name_part.lower()
    year = year_part
    # Avoid duplicates
    exists = col.find_one({'chat_id': MOVIE_CHANNEL_ID, 'message_id': message.message_id})
    if exists:
        return
    # Insert into DB
    col.insert_one({
        'name': name,
        'year': year,
        'chat_id': MOVIE_CHANNEL_ID,
        'message_id': message.message_id
    })
    # Log to Log Channel
    log_text = f"✅ New movie added: *{name_part}* ({year_part})"
    bot.send_message(LOG_CHANNEL_ID, log_text, parse_mode='Markdown')

# === /delmovie COMMAND ===
@bot.message_handler(commands=['delmovie'])
def handle_delmovie(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ You are not authorized to delete movies.")
        return
    parts = message.text.split(' ', 1)
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ Usage: /delmovie Movie Name")
        return
    name_query = parts[1].strip().lower()
    doc = col.find_one({'name': name_query})
    if not doc:
        bot.reply_to(message, "❌ Movie not found.")
        return
    # Delete DB record
    col.delete_one({'_id': doc['_id']})
    # Optionally delete from channel
    try:
        bot.delete_message(doc['chat_id'], doc['message_id'])
    except Exception:
        pass
    # Log deletion
    bot.send_message(LOG_CHANNEL_ID,
                     f"🗑️ Deleted: *{name_query.title()}*",
                     parse_mode='Markdown')
    bot.reply_to(message,
                 f"🗑️ Movie *{name_query.title()}* deleted.",
                 parse_mode='Markdown')

# === DIRECT TEXT HANDLER FOR MOVIE SEARCH ===
@bot.message_handler(func=lambda m: m.content_type == 'text' and not m.text.startswith('/'), content_types=['text'])
def handle_movie_search(message):
    name_query = message.text.strip().lower()
    doc = col.find_one({'name': name_query})
    if doc:
        bot.forward_message(message.chat.id, doc['chat_id'], doc['message_id'])
    else:
        bot.reply_to(message, "❌ Movie not found. Please type the exact name.")

# === FLASK HEALTHCHECK ===
app = Flask(__name__)
@app.route('/')
def health_check():
    return 'OK'

# === RUN BOT AND FLASK ===
def run_bot():
    bot.infinity_polling()

if __name__ == '__main__':
    # Start bot polling in a separate thread
    threading.Thread(target=run_bot).start()
    # Run Flask app for healthchecks
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
