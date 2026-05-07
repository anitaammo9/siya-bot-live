import telebot
import os
import time
from threading import Thread
from flask import Flask
from datetime import datetime
import pytz
from pymongo import MongoClient

# --- अपनी डिटेल्स यहाँ भरें ---
API_TOKEN = '8321892139:AAHO4ddIOAf6tR2HqbAWZcuTpLZVzlSChw8' # BotFather से मिला नया टोकन
CLUSTER_URL = 'mongodb+srv://Siya999:<db_password>@cluster0.b7sbepj.mongodb.net/?appName=Cluster0' # मोंगोडीबी लिंक
ADMIN_ID = 5042331374  # अपनी असली टेलीग्राम ID यहाँ लिखें

bot = telebot.TeleBot(API_TOKEN, threaded=False)
app = Flask(__name__)

# मोंगोडीबी कनेक्शन
client = MongoClient(CLUSTER_URL)
db = client['siya_bot_db']
users_col = db['users']

@app.route('/')
def home():
    return "SIYA BOT IS LIVE WITH DATABASE"

def run():
    app.run(host='0.0.0.0', port=8080)

# पुराने झगड़े (Webhook) खत्म करना
bot.remove_webhook()
time.sleep(1)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    # डेटाबेस में यूजर को सेव करना
    if not users_col.find_one({"user_id": user_id}):
        users_col.insert_one({"user_id": user_id, "name": user_name, "joined_at": datetime.now()})

    IST = pytz.timezone('Asia/Kolkata')
    current_time = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')
    
    msg = f"👋 नमस्ते {user_name}!\n\n🕒 समय: {current_time}\n✅ बॉट अब मोंगोडीबी के साथ ऑनलाइन है।"
    
    # अगर आप (Admin) मैसेज करें तो अलग रिप्लाई आए
    if user_id == ADMIN_ID:
        msg += "\n\n👑 स्वागत है मालिक! आपकी आईडी पहचान ली गई है।"
        
    bot.reply_to(message, msg)

if __name__ == "__main__":
    print("SIYA BOT IS STARTING...")
    Thread(target=run).start()
    
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(5)
    
