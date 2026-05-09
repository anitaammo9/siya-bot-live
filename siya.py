import telebot
from telebot import types
import time
from datetime import datetime
from threading import Thread
from flask import Flask
from pymongo import MongoClient

# --- अपनी डिटेल्स यहाँ भरें ---
API_TOKEN = '8321892139:AAFgXCnc_IISY1-LYy-Ih8EhPxQhygg7cMg' 
CLUSTER_URL = 'mongodb+srv://Siya999:Atypn7702P@cluster0.b7sbepj.mongodb.net/?appName=Cluster0' 
ADMIN_ID = 5042331374
WA_LINK = "https://wa.me/message/ZPLNFOZFRXWKP1"

bot = telebot.TeleBot(API_TOKEN, threaded=False)
app = Flask(__name__)

client = MongoClient(CLUSTER_URL)
db = client['matka_empire_db']
users_col = db['users']
bets_col = db['bets']
results_col = db['results'] # चार्ट के लिए

# --- मार्केट टाइमिंग (यहाँ से टाइम बदलें) ---
MARKET_TIME = {
    "BAHUBALI": {"open": "13:30", "close": "15:30"},
    "KGF": {"open": "18:30", "close": "20:30"}
}

def is_market_open(m_name):
    now = datetime.now().strftime("%H:%M")
    return now < MARKET_TIME[m_name]['close']

@app.route('/')
def home(): return "SYSTEM ONLINE"

def run(): app.run(host='0.0.0.0', port=8080)

# --- पन्ना चेक करने वाला लॉजिक (बढ़ते क्रम) ---
def validate_panna(p):
    if len(p) != 3 or not p.isdigit(): return False
    # अंकों को लिस्ट में लेकर सॉर्ट करना
    sorted_p = "".join(sorted(p))
    return sorted_p == p

# --- कीबोर्ड्स ---
def main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("👤 My Profile", callback_data="profile"),
               types.InlineKeyboardButton("🎮 Play Game", callback_data="play"),
               types.InlineKeyboardButton("📊 View Chart", callback_data="view_chart"),
               types.InlineKeyboardButton("📞 Contact", url=WA_LINK))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if not users_col.find_one({"user_id": uid}):
        users_col.insert_one({"user_id": uid, "name": message.from_user.first_name, "deposit": 0, "winning": 0, "block": False})
    bot.send_message(uid, "👑 *सिया गेम्स* में आपका स्वागत है!", parse_mode="Markdown", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    uid = call.from_user.id
    data = call.data.split("_")

    if data[0] == "main_menu":
        bot.edit_message_text("मुख्य मेनू चुनें:", uid, call.message.message_id, reply_markup=main_menu())

    elif data[0] == "play":
        mk = types.InlineKeyboardMarkup(row_width=1)
        for m in ["BAHUBALI", "KGF"]:
            status = "🟢" if is_market_open(m) else "🔴"
            mk.add(types.InlineKeyboardButton(f"{status} {m} ({MARKET_TIME[m]['open']} - {MARKET_TIME[m]['close']})", callback_data=f"m_{m}"))
        mk.add(types.InlineKeyboardButton("🔙 Back", callback_data="main_menu"))
        bot.edit_message_text("📈 मार्केट चुनें:", uid, call.message.message_id, reply_markup=mk)

    elif data[0] == "m":
        m = data[1]
        if not is_market_open(m):
            bot.answer_callback_query(call.id, "❌ यह मार्केट अभी बंद है!", show_alert=True)
            return
        mk = types.InlineKeyboardMarkup(row_width=2)
        mk.add(types.InlineKeyboardButton("☀️ OPEN", callback_data=f"type_{m}_OPEN"),
               types.InlineKeyboardButton("🌙 CLOSE", callback_data=f"type_{m}_CLOSE"),
               types.InlineKeyboardButton("🔙 Back", callback_data="play"))
        bot.edit_message_text(f"🎰 {m} - अपना मोड चुनें:", uid, call.message.message_id, reply_markup=mk)

    elif data[0] == "type":
        m, mode = data[1], data[2]
        mk = types.InlineKeyboardMarkup(row_width=2)
        # Single और Jodi के लिए बटन सिस्टम (जैसा आपने कहा था)
        mk.add(types.InlineKeyboardButton("Single (1:9)", callback_data=f"list_{m}_{mode}_S"),
               types.InlineKeyboardButton("Jodi (1:90)", callback_data=f"list_{m}_{mode}_J"),
               types.InlineKeyboardButton("Panna (1:120)", callback_data=f"list_{m}_{mode}_P"),
               types.InlineKeyboardButton("🔙 Back", callback_data=f"m_{m}"))
        bot.edit_message_text("गेम टाइप चुनें:", uid, call.message.message_id, reply_markup=mk)

    elif data[0] == "list":
        m, mode, g = data[1], data[2], data[3]
        if g == "P":
            msg = bot.send_message(uid, "⌨️ पन्ना टाइप करें (जैसे: 123, 259):\n*नोट: अंक बढ़ते क्रम में होने चाहिए।*")
            bot.register_next_step_handler(msg, process_panna, m, mode)
        else:
            # यहाँ Single (0-9) और Jodi (0-99) के बटन आएंगे (पिछले कोड की तरह)
            bot.send_message(uid, f"नंबर चुनने के लिए तैयार... (Single/Jodi Buttons)")

    elif data[0] == "view_chart":
        # मोंगोडीबी से चार्ट दिखाना
        history = results_col.find().sort("_id", -1).limit(10)
        text = "📊 **रिजल्ट चार्ट (Last 10)**\n━━━━━━━━━━━━━━\n"
        for r in history:
            text += f"📅 {r['date']} | {r['market']} | {r['res']}\n"
        bot.send_message(uid, text, parse_mode="Markdown", reply_markup=main_menu())

# --- पन्ना प्रोसेसिंग ---
def process_panna(message, m, mode):
    p = message.text.strip()
    if validate_panna(p):
        msg = bot.send_message(message.from_user.id, f"✅ पन्ना {p} सही है।\nकितने रुपये लगाने हैं?")
        bot.register_next_step_handler(msg, finalize_bet, m, mode, "P", p)
    else:
        bot.send_message(message.from_user.id, "❌ गलत पन्ना! पन्ना 3 अंकों का और बढ़ते क्रम (जैसे 123) में होना चाहिए।", reply_markup=main_menu())

def finalize_bet(message, m, mode, g, num):
    # (यहाँ वही बैलेंस काटने और बेट सेव करने वाला लॉजिक रहेगा)
    pass

if __name__ == "__main__":
    Thread(target=run).start()
    bot.remove_webhook()
    time.sleep(1)
    print("EMPIRE BOT IS READY!")
    bot.infinity_polling(skip_pending=True)
                              
