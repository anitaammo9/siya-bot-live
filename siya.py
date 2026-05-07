import telebot
from flask import Flask
from threading import Thread
import pymongo
from telebot import types
from datetime import datetime
import pytz

# --- 1. IST TIME & SERVER ---
app = Flask('')
@app.route('/')
def home(): return "SIYA DIGITAL IS LIVE!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

def get_now():
    return datetime.now(pytz.timezone('Asia/Kolkata'))

# --- 2. CONFIG ---
API_TOKEN = '8321892139:AAE722Hd-ZQWnkjh71ugnb19fdDxKzQMpqc' # यहाँ टोकन
CLUSTER_URL = 'mongodb+srv://Siya999:<db_password>@cluster0.b7sbepj.mongodb.net/?appName=Cluster0' # यहाँ मोंगो लिंक
ADMIN_ID = 5042331374
WA_NUMBER = "918766363760"

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

# --- 3. HOME & START ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.chat.id
    user = get_user(uid)
    if user.get('blocked'): return
    
    now = get_now().strftime("%H:%M")
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for m, t in MARKET_TIMINGS.items():
        status = "🟢 ON" if now < t['close'] else "🔴 LOCK"
        markup.add(types.InlineKeyboardButton(f"{status} {m} (बंद: {t['close']})", callback_data=f"mkt_{m}"))
    
    markup.row(types.InlineKeyboardButton("👤 WALLET / PROFILE", callback_data="u_prof"))
    bot.send_message(uid, f"💰 **SIYA DIGITAL**\n\n💵 Deposit: ₹{user['deposit']}\n🏆 Winning: ₹{user['winning']}\n🕒 Time: {now}", reply_markup=markup)

# --- 4. ADVANCED BETTING INTERFACE ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('mkt_'))
def bet_type_menu(call):
    m = call.data.split('_')[1]
    now = get_now().strftime("%H:%M")
    if now >= MARKET_TIMINGS[m]['close']:
        bot.answer_callback_query(call.id, "❌ यह मार्केट बंद हो गया है!", show_alert=True)
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🎯 SINGLE ANK", callback_data=f"btn_{m}_SINGLE"),
        types.InlineKeyboardButton("👫 JODI", callback_data=f"btn_{m}_JODI"),
        types.InlineKeyboardButton("📖 PANNA", callback_data=f"btn_{m}_PANNA"),
        types.InlineKeyboardButton("🏠 HOME", callback_data="back_home")
    )
    bot.edit_message_text(f"🎰 **{m}**\nगेम टाइप चुनें:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('btn_'))
def handle_bet_selection(call):
    _, m, gt = call.data.split('_')
    if gt == "SINGLE":
        markup = types.InlineKeyboardMarkup(row_width=5)
        btns = [types.InlineKeyboardButton(str(i), callback_data=f"sel_{m}_{gt}_{i}") for i in range(10)]
        markup.add(*btns)
        markup.add(types.InlineKeyboardButton("🔙 BACK", callback_data=f"mkt_{m}"),
                   types.InlineKeyboardButton("🏠 HOME", callback_data="back_home"))
        bot.edit_message_text("🔢 अंक चुनें:", call.message.chat.id, call.message.message_id, reply_markup=markup)
    else:
        msg = bot.send_message(call.message.chat.id, f"📝 **{gt}** के लिए लिखें (उदा: 12=50, 45=100):")
        bot.register_next_step_handler(msg, lambda m_obj: save_multi_bet(m_obj, m, gt))

@bot.callback_query_handler(func=lambda call: call.data.startswith('sel_'))
def single_amt_input(call):
    _, m, gt, num = call.data.split('_')
    msg = bot.send_message(call.message.chat.id, f"💰 अंक **{num}** पर कितनी राशि लगानी है?")
    bot.register_next_step_handler(msg, lambda m_obj: save_single_bet(m_obj, m, gt, num))

# --- 5. SAVING LOGIC (DEPOSIT ONLY) ---
def save_single_bet(message, m, gt, num):
    uid = message.chat.id
    try:
        amt = int(message.text)
        user = get_user(uid)
        if user['deposit'] < amt:
            bot.send_message(uid, "❌ बैलेंस कम है!"); return
        
        users_col.update_one({'_id': uid}, {'$inc': {'deposit': -amt}})
        bets_col.insert_one({'uid': uid, 'market': m, 'type': gt, 'num': num, 'amt': amt, 'date': get_now().strftime("%Y-%m-%d")})
        
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("➕ और दांव लगायें", callback_data=f"btn_{m}_{gt}"),
                                                 types.InlineKeyboardButton("🏠 HOME", callback_data="back_home"))
        bot.send_message(uid, f"✅ सफल! ₹{amt} कटे।", reply_markup=markup)
    except: bot.send_message(uid, "❌ सिर्फ नंबर लिखें।")

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
            bets_col.insert_one({'uid': uid, 'market': market, 'type': gtype, 'num': n.strip(), 'amt': int(a.strip()), 'date': get_now().strftime("%Y-%m-%d")})
        bot.send_message(uid, f"✅ कुल ₹{total} के दांव लग गए!")
    except: bot.send_message(uid, "❌ फॉर्मेट गलत है (उदा: 12=50)")

# --- 6. WALLET & BACK ---
@bot.callback_query_handler(func=lambda call: call.data == "u_prof")
def profile(call):
    uid = call.message.chat.id
    user = get_user(uid)
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_wd = types.InlineKeyboardButton("💸 WITHDRAW", callback_data="req_wd") if user['winning'] >= 500 else types.InlineKeyboardButton("🔒 MIN ₹500", callback_data="low")
    markup.add(btn_wd, types.InlineKeyboardButton("➕ ADD COINS", url=f"https://wa.me/{WA_NUMBER}"))
    markup.add(types.InlineKeyboardButton("🏠 HOME", callback_data="back_home"))
    bot.edit_message_text(f"👤 **WALLET**\n💵 Deposit: ₹{user['deposit']}\n🏆 Winning: ₹{user['winning']}", uid, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "back_home")
def b_home(call): start(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "low")
def low_msg(call): bot.answer_callback_query(call.id, "❌ कम से कम ₹500 विनिंग चाहिए!", show_alert=True)

if __name__ == "__main__":
    print("========================================")
    print("   SIYA DIGITAL BOT IS NOW LIVE!        ")
    print("========================================")
    
    # सर्वर को अलग धागे (Thread) में चलाएं
    t = Thread(target=run)
    t.start()
    
    # बॉट को मुख्य धागे में चलाएं
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
    
    
