import os
import threading
import requests
import telebot
from telebot.types import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
from fuzzywuzzy import process
from flask import Flask
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv()
API_TOKEN        = os.getenv("API_TOKEN")
ADMIN_ID         = int(os.getenv("ADMIN_ID"))
MONGO_URI        = os.getenv("MONGO_URI")
OMDB_API_KEY     = os.getenv("OMDB_API_KEY")
MOVIE_CHANNEL_ID = int(os.getenv("MOVIE_CHANNEL_ID"))
LOG_CHANNEL_ID   = int(os.getenv("LOG_CHANNEL_ID"))

# === Initialize Bot, DB, Flask ===
bot = telebot.TeleBot(API_TOKEN)
client = MongoClient(MONGO_URI)
db = client['moviebot']
col = db['movies']
app = Flask(__name__)

# === Utility: Fetch metadata from OMDB ===
def fetch_metadata(title):
    try:
        resp = requests.get(
            f"http://www.omdbapi.com/", params={"t": title, "apikey": OMDB_API_KEY}
        )
        data = resp.json()
        return {
            "rating": data.get("imdbRating", "N/A"),
            "genre": data.get("Genre", ""),
            "poster": data.get("Poster", None)
        }
    except:
        return {"rating": "N/A", "genre": "", "poster": None}

# === Inline Search Handler ===
@bot.inline_handler(lambda query: True)
def inline_search(inline_query):
    q = inline_query.query.strip().lower()
    if not q:
        return
    # Fuzzy match top 5
    all_names = [doc['name'] for doc in col.find()]
    matches = process.extract(q, all_names, limit=5)
    results = []
    for name, score in matches:
        if score < 50:
            continue
        doc = col.find_one({'name': name})
        meta = fetch_metadata(name)
        title = doc['name'].title()
        description = f"{doc['year']} | IMDb: {meta['rating']} | {meta['genre']}"
        content = InputTextMessageContent(f"/watch {title}")
        button = InlineKeyboardButton("Get Movie", callback_data=f"WATCH|{name}")
        markup = InlineKeyboardMarkup().add(button)
        result = InlineQueryResultArticle(
            id=name,
            title=title,
            description=description,
            input_message_content=content,
            reply_markup=markup
        )
        results.append(result)
    bot.answer_inline_query(inline_query.id, results)

# === /watch Command or Callback ===
@bot.message_handler(commands=['watch'])
def watch_cmd(msg):
    name = msg.text.split(' ',1)[1].strip().lower()
    send_movie_or_suggest(msg.chat.id, name)

@bot.callback_query_handler(func=lambda c: c.data.startswith('WATCH|'))
def callback_watch(call):
    _, name = call.data.split('|',1)
    send_movie_or_suggest(call.message.chat.id, name)

# === Send movie or suggestions ===
def send_movie_or_suggest(chat_id, name):
    doc = col.find_one({'name': {'$regex': f'^{name}$'}})
    if doc:
        bot.forward_message(chat_id, doc['chat_id'], doc['message_id'])
    else:
        # Suggest top 3
        all_names = [d['name'] for d in col.find()]
        suggestions = process.extract(name, all_names, limit=3)
        text = "❌ Movie not found. Did you mean?\n"
        for s, _ in suggestions:
            text += f"• {s.title()}\n"
        bot.send_message(chat_id, text)

# === Auto-add Handler (Movie Channel) ===
@bot.message_handler(content_types=['document', 'video', 'audio'])
def auto_add(m):
    if m.chat.id != MOVIE_CHANNEL_ID:
        return
    caption = m.caption or ''
    if '|' not in caption:
        return
    name, year = [p.strip() for p in caption.split('|',1)]
    # Prevent duplicates
    if col.find_one({'chat_id': MOVIE_CHANNEL_ID, 'message_id': m.message_id}):
        return
    col.insert_one({
        'name': name.lower(), 'year': year,
        'chat_id': MOVIE_CHANNEL_ID, 'message_id': m.message_id
    })
    bot.send_message(LOG_CHANNEL_ID, f"✅ Added: *{name}* ({year})", parse_mode='Markdown')

# === /delmovie Command ===
@bot.message_handler(commands=['delmovie'])
def delete_movie(msg):
    if msg.from_user.id != ADMIN_ID:
        return bot.reply_to(msg, "⛔ Not authorized.")
    name = msg.text.split(' ',1)[1].strip().lower()
    doc = col.find_one({'name': name})
    if not doc:
        return bot.reply_to(msg, "❌ Movie not found.")
    col.delete_one({'_id': doc['_id']})
    try: bot.delete_message(doc['chat_id'], doc['message_id'])
    except: pass
    bot.send_message(LOG_CHANNEL_ID, f"🗑️ Deleted: *{name.title()}*", parse_mode='Markdown')
    bot.reply_to(msg, f"🗑️ Movie *{name.title()}* deleted.")

# === Flask Healthcheck ===
@app.route('/')
def health(): return 'OK'

# === Run ===
def run():
    bot.infinity_polling()
    
if __name__ == '__main__':
    # Start bot and Flask
    threading.Thread(target=run).start()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT',8000)))
