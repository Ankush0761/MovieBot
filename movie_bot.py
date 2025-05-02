from flask import Flask
import threading, os
import telebot
from pymongo import MongoClient

# === CONFIGURATION ===
API_TOKEN = '7702090142:AAF0Ji1ERwbT3bwE5PPiu33zSUlh-P2UHpk'
ADMIN_ID = 8075098988
MONGO_URI = 'mongodb+srv://deybarun176:JNIj1Yy45xOzx4Av@barun.7t6nu9s.mongodb.net/?retryWrites=true&w=majority&appName=Barun'

# === TELEGRAM BOT SETUP ===
bot = telebot.TeleBot(API_TOKEN)
client = MongoClient(MONGO_URI)
db = client['moviebot']
collection = db['movies']

# === /start COMMAND ===
@bot.message_handler(commands=['start'])
def start_handler(message):
    welcome_text = (
        "👋 Welcome to the Movie Bot!\n\n"
        "🎥 Search any movie:\n"
        "`/search Movie Name`\n\n"
        "🎬 Add a movie (admin only):\n"
        "`/addmovie Name | Year | Link`\n\n"
        "🍿 Enjoy!"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown')

# === Robust /addmovie COMMAND ===
@bot.message_handler(commands=['addmovie'])
def add_movie(message):
    if message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, "⛔ You are not authorized to add movies.")

    text = message.text
    if not text.startswith('/addmovie '):
        return bot.reply_to(message, "⚠️ Usage: /addmovie Movie Name | Year | Link")

    args = text[len('/addmovie '):]
    parts = [p.strip() for p in args.split('|')]

    if len(parts) != 3:
        return bot.reply_to(message, "⚠️ Usage: /addmovie Movie Name | Year | Link")

    name, year, link = parts
    try:
        collection.insert_one({
            'name': name.lower(),
            'year': year,
            'link': link
        })
        bot.reply_to(message, f"✅ Added: *{name}* ({year})", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Error adding movie:\n```\n{e}\n```", parse_mode='Markdown')

# === /delmovie COMMAND ===
@bot.message_handler(commands=['delmovie'])
def del_movie(message):
    if message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, "⛔ You are not authorized to delete movies.")
    try:
        name = message.text.split(' ', 1)[1].strip().lower()
        result = collection.delete_one({'name': name})
        if result.deleted_count:
            bot.reply_to(message, f"✅ Deleted: {name.title()}")
        else:
            bot.reply_to(message, "❌ Movie not found.")
    except:
        bot.reply_to(message, "⚠️ Usage: /delmovie Movie Name")

# === /search COMMAND ===
@bot.message_handler(commands=['search'])
def search_movie(message):
    try:
        name = message.text.split(' ', 1)[1].strip().lower()
        movie = collection.find_one({'name': {'$regex': name}})
        if movie:
            reply = (
                f"🎬 *{movie['name'].title()}* ({movie['year']})\n"
                f"👉 [Download Link]({movie['link']})"
            )
            bot.send_message(message.chat.id, reply, parse_mode='Markdown')
        else:
            bot.reply_to(message, "❌ Movie not found.")
    except:
        bot.reply_to(message, "⚠️ Usage: /search Movie Name")

# === FLASK HEALTHCHECK ===
app = Flask(__name__)
@app.route('/')
def health():
    return 'OK'

# === RUN BOT POLLING IN BACKGROUND + FLASK ===
def run_bot():
    bot.polling()

if __name__ == '__main__':
    # 1) Start bot polling in a separate thread
    threading.Thread(target=run_bot).start()
    # 2) Start Flask web server for Koyeb healthchecks
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
