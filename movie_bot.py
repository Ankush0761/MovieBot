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
        "Enjoy your movies 🍿"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown')

# === /addmovie COMMAND ===
@bot.message_handler(commands=['addmovie'])
def add_movie(message):
    if message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, "⛔ Not authorized.")
    try:
        parts = message.text.split('|')
        name = parts[0].split(' ', 1)[1].strip()
        year = parts[1].strip()
        link = parts[2].strip()
        collection.insert_one({'name': name.lower(), 'year': year, 'link': link})
        bot.reply_to(message, f"✅ Added: {name} ({year})")
    except:
        bot.reply_to(message, "⚠️ Use: /addmovie Name | Year | Link")

# === /delmovie COMMAND ===
@bot.message_handler(commands=['delmovie'])
def del_movie(message):
    if message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, "⛔ Not authorized.")
    try:
        name = message.text.split(' ', 1)[1].strip().lower()
        result = collection.delete_one({'name': name})
        bot.reply_to(message, "✅ Deleted." if result.deleted_count else "❌ Not found.")
    except:
        bot.reply_to(message, "⚠️ Use: /delmovie Name")

# === /search COMMAND ===
@bot.message_handler(commands=['search'])
def search_movie(message):
    try:
        name = message.text.split(' ', 1)[1].strip().lower()
        movie = collection.find_one({'name': {'$regex': name}})
        if movie:
            reply = f"🎬 *{movie['name'].title()}* ({movie['year']})\n👉 [Download Link]({movie['link']})"
            bot.send_message(message.chat.id, reply, parse_mode='Markdown')
        else:
            bot.reply_to(message, "❌ Movie not found.")
    except:
        bot.reply_to(message, "⚠️ Use: /search Name")

# === FLASK HEALTHCHECK ===
app = Flask(__name__)
@app.route('/')
def health():
    return 'OK'

# === RUN BOT IN THREAD + FLASK ===
def run_bot():
    bot.polling()

if __name__ == '__main__':
    threading.Thread(target=run_bot).start()
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
