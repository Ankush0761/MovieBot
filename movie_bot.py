import telebot
from pymongo import MongoClient

# === CONFIGURATION ===
API_TOKEN = '7702090142:AAF0Ji1ERwbT3bwE5PPiu33zSUlh-P2UHpk'  # Your bot token
ADMIN_ID = 8075098988                                          # Your Telegram user ID
MONGO_URI = 'mongodb+srv://deybarun176:JNIj1Yy45xOzx4Av@barun.7t6nu9s.mongodb.net/?retryWrites=true&w=majority&appName=Barun'

# === SETUP ===
bot = telebot.TeleBot(API_TOKEN)
client = MongoClient(MONGO_URI)
db = client['moviebot']
collection = db['movies']

# === /start COMMAND ===
@bot.message_handler(commands=['start'])
def start_handler(message):
    welcome_text = (
        "👋 Welcome to the Movie Bot!\n\n"
        "🎥 Search any movie using:\n"
        "`/search Movie Name`\n\n"
        "Example: `/search Animal`\n\n"
        "Enjoy your movies 🍿"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown')

# === /addmovie COMMAND ===
@bot.message_handler(commands=['addmovie'])
def add_movie(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ You are not authorized to add movies.")
        return

    try:
        parts = message.text.split('|')
        name = parts[0].split(' ', 1)[1].strip()
        year = parts[1].strip()
        link = parts[2].strip()

        movie = {'name': name.lower(), 'year': year, 'link': link}
        collection.insert_one(movie)
        bot.reply_to(message, f"✅ Added: {name} ({year})")
    except:
        bot.reply_to(message, "⚠️ Usage:\n`/addmovie Movie Name | Year | Link`", parse_mode='Markdown')

# === /delmovie COMMAND ===
@bot.message_handler(commands=['delmovie'])
def del_movie(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ You are not authorized to delete movies.")
        return

    try:
        name = message.text.split(' ', 1)[1].strip().lower()
        result = collection.delete_one({'name': name})
        if result.deleted_count:
            bot.reply_to(message, f"✅ Deleted: {name.title()}")
        else:
            bot.reply_to(message, "❌ Movie not found.")
    except:
        bot.reply_to(message, "⚠️ Usage:\n`/delmovie Movie Name`", parse_mode='Markdown')

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
        bot.reply_to(message, "⚠️ Usage:\n`/search Movie Name`", parse_mode='Markdown')

# === POLLING ===
bot.polling()
