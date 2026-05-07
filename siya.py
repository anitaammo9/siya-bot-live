import telebot
from flask import Flask
from threading import Thread
import pymongo
from telebot import types
from datetime import datetime
import pytz # भारतीय समय के लिए

# --- 1. SERVER & IST TIME SETUP ---
app = Flask('')
@app.route('/')
def home(): return "SIYA DIGITAL IS LIVE!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

def get_ist_time():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).strftime("%H:%M")

# --- 2. CONFIGURATION ---
API_TOKEN = '8321892139:AAEOdZkUBb1crv5q6vODP04Cngu8YfX82Y8' # अपना टोकन यहाँ डालें
ADMIN_ID = 5042331374 
WA_NUMBER = "918766363760" 
CLUSTER_URL = 'mongodb+srv://Siya999:<db_password>@cluster0.b7sbepj.mongodb.net/?appName=Cluster0' # मोंगो लिंक यहाँ डालें

bot = telebot.TeleBot(API_TOKEN)
db = pymongo.MongoClient(CLUSTER_URL)['SiyaBotDB']
users_col, bets_col = db['users'], db['bets']

MARKET_TIMINGS = {
    'BAHUBALI': {'close': '13:15'}, 
    'PUSHPA': {'close': '18:15'}, 
    'KGF': {'close': '00:00'}
}

def get_user(uid):
    user = users_col.find_one({'_id': uid})
    if not user:
        user = {'_id': uid, 'deposit': 0, 'winning': 0, 'blocked': False}
        users_col.insert_one(user)
    return user

# --- 3. START & HOME ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.chat.id
    user = get_user(uid)
    if user.get('blocked'): return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    now = get_ist_time() # अब यह भारत का समय दिखाएगा
    
    for m, t in MARKET_TIMINGS.items():
        icon = "🟢 ON" if now < t['close'] else "🔴 LOCK"
        markup.add(types.InlineKeyboardButton(f"{icon} {m} (Ends: {t['close']})", callback_data=f"mkt_{m}"))
    
    markup.row(types.InlineKeyboardButton("👤 WALLET / PROFILE", callback_data="u_prof"))
    bot.send_message(uid, f"💰 **SIYA DIGITAL**\n💵 Deposit: ₹{user['deposit']}\n🏆 Winning: ₹{user['winning']}\n🕒 Time: {now}", reply_markup=markup)

# --- 4. BETTING & BUTTONS ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('mkt_'))
def bet_type_menu(call):
    m = call.data.split('_')[1]
    now = get_ist_time()
    if now >= MARKET_TIMINGS[m]['close']:
        bot.answer_callback_query(call.id, "❌ मार्केट लॉक हो चुका है!", show_alert=True)
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🎯 SINGLE ANK", callback_data=f"list_{m}_SINGLE"),
        types.InlineKeyboardButton("👫 JODI", callback_data=f"list_{m}_JODI"),
        types.InlineKeyboardButton("📖 PANNA", callback_data=f"list_{m}_PANNA"),
        types.InlineKeyboardButton("🏠 HOME", callback_data="back_home")
    )
    bot.edit_message_text(f"🎰 **{m}** - गेम चुनें:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('list_'))
def show_numbers(call):
    _, m, gt = call.data.split('_')
    if gt == "SINGLE":
        markup = types.InlineKeyboardMarkup(row_width=5)
        btns = [types.InlineKeyboardButton(str(i), callback_data=f"sel_{m}_{gt}_{i}") for i in range(10)]
        markup.add(*btns)
        markup.add(types.InlineKeyboardButton("🔙 BACK", callback_data=f"mkt_{m}"),
                   types.InlineKeyboardButton("🏠 HOME", callback_data="back_home"))
        bot.edit_message_text("🔢 अंक चुनें:", call.message.chat.id, call.message.message_id, reply_markup=markup)
    else:
        bot.send_message(call.message.chat.id, f"📝 **{gt}** नंबर और अमाउंट लिखें (उदा: 12=50):")

@bot.callback_query_handler(func=lambda call: call.data == "back_home")
def b_home(call): start(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "u_prof")
def profile(call):
    uid = call.message.chat.id
    user = get_user(uid)
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("➕ ADD COINS", url=f"https://wa.me/{WA_NUMBER}"),
               types.InlineKeyboardButton("🏠 HOME", callback_data="back_home"))
    bot.edit_message_text(f"👤 **WALLET**\n💵 Deposit: ₹{user['deposit']}\n🏆 Winning: ₹{user['winning']}", uid, call.message.message_id, reply_markup=markup)

# --- 5. BOOT ---
if __name__ == "__main__":
    print("========================================")
    print("   SIYA DIGITAL BOT IS NOW LIVE!        ")
    print("========================================")
    keep_alive()
    bot.infinity_polling()
    
