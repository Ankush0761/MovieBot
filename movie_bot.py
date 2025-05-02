from flask import Flask
import threading, os
import telebot
from pymongo import MongoClient

# === CONFIG ===
API_TOKEN        = '7702090142:AAF0Ji1ERwbT3bwE5PPiu33zSUlh-P2UHpk'
ADMIN_ID         = 8075098988
MONGO_URI        = 'mongodb+srv://deybarun176:JNIj1Yy45xOzx4Av@barun.7t6nu9s.mongodb.net/?retryWrites=true&w=majority&appName=Barun'
MOVIE_CHANNEL_ID = -1002605645508    # ← Your Movie Store channel ID
LOG_CHANNEL_ID   = -1002661190627    # ← Your Log channel ID

# === BOT & DB SETUP ===
bot    = telebot.TeleBot(API_TOKEN)
client = MongoClient(MONGO_URI)
db     = client['moviebot']
col    = db['movies']

# === /start COMMAND ===
@bot.message_handler(commands=['start'])
def start_handler(msg):
    text = (
        "👋 Welcome to MovieBot!\n\n"
        "🎥 Just type movie name to get it.\n"
    )
    bot.send_message(msg.chat.id, text, parse_mode='Markdown')

# === CHANNEL POST HANDLER FOR AUTO-ADDING ===
@bot.message_handler(func=lambda m: m.chat.id == MOVIE_CHANNEL_ID and (m.document or m.video or m.audio), content_types=['document', 'video', 'audio'])
def channel_store_movie(m):
    # Only process if caption provided
    if not m.caption or '|' not in m.caption:
        return
    # Parse caption
    parts = [p.strip() for p in m.caption.split('|', 1)]
    if len(parts) != 2:
        return
    name, year = parts
    # Save in DB
    col.insert_one({
        'name': name.lower(),
        'year': year,
        'chat_id': MOVIE_CHANNEL_ID,
        'message_id': m.message_id
    })
    # Log addition
    log = f"✅ New movie added: *{name}* ({year})"
    bot.send_message(LOG_CHANNEL_ID, log, parse_mode='Markdown')

# === /delmovie COMMAND ===
@bot.message_handler(commands=['delmovie'])
def del_movie(msg):
    if msg.from_user.id != ADMIN_ID:
        return bot.reply_to(msg, "⛔ You are not authorized.")
    name = msg.text.split(' ',1)[1].strip().lower()
    doc = col.find_one({'name': name})
    if not doc:
        return bot.reply_to(msg, "❌ Movie not found.")
    # Delete DB record
    col.delete_one({'_id': doc['_id']})
    # Optional: Delete from channel
    try:
        bot.delete_message(doc['chat_id'], doc['message_id'])
    except:
        pass
    # Log deletion
    bot.send_message(LOG_CHANNEL_ID, f"🗑️ Deleted: *{name.title()}*", parse_mode='Markdown')
    bot.reply_to(msg, f"🗑️ Movie *{name.title()}* deleted.", parse_mode='Markdown')

# === Direct Text Handler for Movie Name ===
@bot.message_handler(func=lambda m: True)
def handle_movie_name(m):
    name = m.text.strip().lower()
    doc = col.find_one({'name': {'$regex': f'^{name}$'}})
    if doc:
        bot.forward_message(m.chat.id, doc['chat_id'], doc['message_id'])
    else:
        bot.reply_to(m, "❌ Movie not found. Please type exact name.")

# === Flask Healthcheck ===
app = Flask(__name__)
@app.route('/')
def health():
    return 'OK'

# === Run Bot & Flask ===
def run_bot():
    bot.polling()

if __name__ == '__main__':
    threading.Thread(target=run_bot).start()
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
