import telebot
from flask import Flask
from threading import Thread
import pymongo
from telebot import types
from datetime import datetime
import time
import threading

# --- 1. SERVER SETUP ---
app = Flask('')
@app.route('/')
def home(): return "SIYA DIGITAL PRO IS ALIVE!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. CONFIGURATION (यहाँ अपनी डिटेल्स भरें) ---
API_TOKEN = '8321892139:AAEOdZkUBb1crv5q6vODP04Cngu8YfX82Y8' # अपना टोकन यहाँ डालें
ADMIN_ID = 5042331374 
WA_NUMBER = "918766363760" 
CLUSTER_URL = 'mongodb+srv://Siya999:<db_password>@cluster0.b7sbepj.mongodb.net/?appName=Cluster0' # अपनी MongoDB लिंक यहाँ डालें

bot = telebot.TeleBot(API_TOKEN)
client = pymongo.MongoClient(CLUSTER_URL)
db = client['SiyaBotDB']
users_col = db['users']
bets_col = db['bets']

MARKET_TIMINGS = {
    'BAHUBALI': {'close': '13:15'}, 
    'PUSHPA': {'close': '18:15'}, 
    'KGF': {'close': '00:00'}
}

# --- 3. DATABASE FUNCTIONS ---
def get_user(uid):
    user = users_col.find_one({'_id': uid})
    if not user:
        user = {'_id': uid, 'deposit': 0, 'winning': 0, 'blocked': False}
        users_col.insert_one(user)
    return user

# --- 4. START & HOME ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.chat.id
    user = get_user(uid)
    if user.get('blocked'):
        bot.send_message(uid, "❌ आप ब्लॉक हैं।")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    now = datetime.now().strftime("%H:%M")
    for m, t in MARKET_TIMINGS.items():
        icon = "🟢 ON" if now < t['close'] else "🔴 LOCK"
        markup.add(types.InlineKeyboardButton(f"{icon} {m}", callback_data=f"mkt_{m}"))
    
    markup.row(types.InlineKeyboardButton("👤 WALLET / PROFILE", callback_data="u_prof"))
    msg = f"💰 **SIYA DIGITAL**\n\n💵 Deposit: ₹{user['deposit']}\n🏆 Winning: ₹{user['winning']}\n━━━━━━━━━━━━━━\n💸 Total: ₹{user['deposit'] + user['winning']}"
    bot.send_message(uid, msg, reply_markup=markup)

# --- 5. MULTIPLE CHOICE BETTING ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('mkt_'))
def bet_type_menu(call):
    m = call.data.split('_')[1]
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
        msg = bot.send_message(call.message.chat.id, f"📝 **{gt}** के लिए नंबर और अमाउंट लिखें (उदा: `12=50, 45=100`):")
        bot.register_next_step_handler(msg, lambda m_obj: save_multi_bet(m_obj, m, gt))

@bot.callback_query_handler(func=lambda call: call.data.startswith('sel_'))
def single_bet_amt(call):
    _, m, gt, num = call.data.split('_')
    msg = bot.send_message(call.message.chat.id, f"💰 अंक **{num}** पर कितनी राशि लगानी है?")
    bot.register_next_step_handler(msg, lambda m_obj: save_single_bet(m_obj, m, gt, num))

def save_single_bet(message, m, gt, num):
    try:
        amt = int(message.text)
        uid = message.chat.id
        user = get_user(uid)
        if user['deposit'] < amt:
            bot.send_message(uid, "❌ डिपॉजिट बैलेंस कम है!"); return
        
        users_col.update_one({'_id': uid}, {'$inc': {'deposit': -amt}})
        bets_col.insert_one({'uid': uid, 'market': m, 'type': gt, 'num': num, 'amt': amt, 'date': datetime.now().strftime("%Y-%m-%d")})
        
        markup = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("➕ और दांव लगायें", callback_data=f"list_{m}_{gt}"),
            types.InlineKeyboardButton("🏠 HOME", callback_data="back_home")
        )
        bot.send_message(uid, f"✅ दांव सफल! ₹{amt} डिपॉजिट से कटे।", reply_markup=markup)
    except: bot.send_message(message.chat.id, "❌ गलत अमाउंट!")

def save_multi_bet(message, market, gtype):
    uid = message.chat.id
    user = get_user(uid)
    try:
        parts = message.text.split(',')
        total = 0
        for p in parts: total += int(p.split('=')[1].strip())
        if user['deposit'] < total:
            bot.send_message(uid, "❌ बैलेंस कम है!"); return
        
        users_col.update_one({'_id': uid}, {'$inc': {'deposit': -total}})
        for p in parts:
            n, a = p.split('=')
            bets_col.insert_one({'uid': uid, 'market': market, 'type': gtype, 'num': n.strip(), 'amt': int(a.strip()), 'date': datetime.now().strftime("%Y-%m-%d")})
        
        bot.send_message(uid, f"✅ दांव सफल! कुल ₹{total} डिपॉजिट से कटे।")
    except: bot.send_message(uid, "❌ फॉर्मेट गलत है (उदा: 12=50)")

# --- 6. WALLET & BACK ---
@bot.callback_query_handler(func=lambda call: call.data == "u_prof")
def profile(call):
    uid = call.message.chat.id
    user = get_user(uid)
    markup = types.InlineKeyboardMarkup(row_width=2)
    wa_link = f"https://wa.me/{WA_NUMBER}?text=ID:{uid}%20Deposit"
    btn_wd = types.InlineKeyboardButton("💸 WITHDRAWAL", callback_data="req_wd") if user['winning'] >= 500 else types.InlineKeyboardButton("🔒 WITHDRAW (Min 500)", callback_data="low")
    markup.add(btn_wd, types.InlineKeyboardButton("➕ ADD COINS", url=wa_link),
               types.InlineKeyboardButton("🏠 HOME", callback_data="back_home"))
    bot.edit_message_text(f"👤 **WALLET**\n🆔 ID: `{uid}`\n💵 Deposit: ₹{user['deposit']}\n🏆 Winning: ₹{user['winning']}", uid, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "back_home")
def b_home(call): start(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "low")
def low_msg(call): bot.answer_callback_query(call.id, "❌ ₹500 विनिंग चाहिए!", show_alert=True)

# --- 7. FINAL BOOT ---
if __name__ == "__main__":
    print("========================================")
    print("   SIYA DIGITAL BOT IS NOW LIVE!        ")
    print("========================================")
    keep_alive()
    bot.infinity_polling()
    
