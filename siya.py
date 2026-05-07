import telebot
import os
import time
from threading import Thread
from flask import Flask
from datetime import datetime
import pytz
from pymongo import MongoClient

# --- अपनी डिटेल्स यहाँ भरें ---
# 1. अपना नया टोकन यहाँ डालें
API_TOKEN = '8321892139:AAHO4ddIOAf6tR2HqbAWZcuTpLZVzlSChw8' 

# 2. यहाँ <db_password> को हटाकर अपना असली पासवर्ड लिखें (निशान < > भी हटा देना)
CLUSTER_URL = 'mongodb+srv://Siya999:Atypn7702P@cluster0.b7sbepj.mongodb.net/?appName=Cluster0' 

# 3. अपनी 10 अंकों की टेलीग्राम ID यहाँ लिखें
ADMIN_ID = 5042331374  

bot = telebot.TeleBot(API_TOKEN, threaded=False)
app = Flask(__name__)

@app.route('/')
def home():
    return "SIYA BOT IS ONLINE"

def run():
    app.run(host='0.0.0.0', port=8080)

# पुराने झगड़े (Webhook) खत्म करना
bot.remove_webhook()
time.sleep(2)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_name = message.from_user.first_name
    bot.reply_to(message, f"👋 नमस्ते {user_name}! सिया बॉट अब ऑनलाइन है।")

if __name__ == "__main__":
    # Flask सर्वर शुरू करें
    t = Thread(target=run)
    t.daemon = True
    t.start()
    
    print("SIYA BOT IS STARTING...")
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        print(f"Error: {e}")
        
