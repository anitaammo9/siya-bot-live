import telebot
from telebot import types
import sqlite3
from datetime import datetime
import time
import threading

# --- 1. SETUP ---
API_TOKEN = '8321892139:AAEOdZkUBb1crv5q6vODP04Cngu8YfX82Y8'  # अपना टोकन यहाँ डालें
ADMIN_ID = 5042331374             
WA_NUMBER = "918766363760"        
bot = telebot.TeleBot(API_TOKEN)

# भाव और मंडी टाइमिंग
MARKET_TIMINGS = {
    'BAHUBALI': {'open_off': '09:15', 'close_off': '13:15'},
    'PUSHPA':   {'open_off': '15:15', 'close_off': '18:15'},
    'KGF':      {'open_off': '19:45', 'close_off': '00:00'}
}

# 220 पन्ना चार्ट
MASTER_PANNA_CHART = {
    '1': ['137', '128', '146', '236', '245', '290', '380', '470', '489', '560', '678', '579', '119', '155', '227', '335', '344', '399', '588', '669', '777', '100'],
    '2': ['129', '138', '147', '156', '237', '246', '345', '390', '480', '570', '589', '679', '110', '228', '255', '336', '499', '660', '688', '778', '200', '444'],
    '3': ['120', '139', '148', '157', '238', '247', '256', '346', '490', '580', '670', '689', '166', '229', '337', '355', '445', '599', '779', '788', '300', '111'],
    '4': ['130', '149', '158', '167', '239', '248', '257', '347', '356', '590', '680', '789', '112', '220', '266', '338', '446', '455', '699', '770', '400', '888'],
    '5': ['140', '159', '168', '230', '249', '258', '267', '348', '357', '456', '690', '780', '113', '122', '177', '339', '366', '447', '799', '889', '500', '555'],
    '6': ['123', '150', '169', '178', '240', '259', '268', '349', '358', '367', '457', '790', '114', '277', '330', '448', '466', '556', '880', '899', '600', '222'],
    '7': ['124', '160', '179', '250', '269', '278', '340', '359', '368', '458', '467', '890', '115', '133', '188', '223', '377', '449', '557', '566', '700', '999'],
    '8': ['125', '134', '170', '189', '260', '279', '350', '369', '378', '459', '468', '567', '116', '224', '233', '288', '440', '477', '558', '990', '800', '666'],
    '9': ['126', '135', '180', '234', '270', '289', '360', '379', '450', '469', '478', '568', '117', '144', '199', '225', '388', '559', '577', '667', '900', '333'],
    '0': ['127', '136', '145', '190', '235', '280', '370', '389', '460', '479', '569', '578', '118', '226', '244', '299', '334', '488', '668', '677', '000', '550']
}

# --- 2. DATABASE FUNCTIONS ---
def get_db():
    conn = sqlite3.connect('siya.db', check_same_thread=False)
    conn.execute('PRAGMA journal_mode=WAL;')
    return conn

def init_db():
    conn = get_db(); c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (uid INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)')
    c.execute('CREATE TABLE IF NOT EXISTS bets (uid INTEGER, market TEXT, session TEXT, type TEXT, number TEXT, amount INTEGER, date TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS results (market TEXT, session TEXT, ank TEXT, panna TEXT, date TEXT, status TEXT DEFAULT "PENDING", PRIMARY KEY(market, session, date))')
    conn.commit(); conn.close()

def update_bal(uid, amt):
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (uid, balance) VALUES (?, 0)", (uid,))
    c.execute("UPDATE users SET balance = balance + ? WHERE uid=?", (amt, uid))
    conn.commit(); conn.close()

def get_bal(uid):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE uid=?", (uid,))
    res = c.fetchone(); conn.close()
    return res[0] if res else 0

init_db()
user_temp = {}

# --- 3. AUTO-SCHEDULER & WINNERS ---
def process_winners(market, session, ank, panna):
    conn = get_db(); c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    res_msg = f"🏆 **{market} ({session}) RESULT**\n━━━━━━━━━━━━━━━\n🔢 **{panna}-{ank}**\n━━━━━━━━━━━━━━━\n💰 SIYA DIGITAL"
    
    c.execute("SELECT uid FROM users")
    for u in c.fetchall():
        try: bot.send_message(u[0], res_msg)
        except: pass

    c.execute("SELECT uid, type, number, amount FROM bets WHERE market=? AND session=? AND date=?", (market, session, today))
    bets = c.fetchall()
    for b in bets:
        uid, t, num, amt = b
        win = 0
        if t == "SINGLE" and num == str(ank): win = amt * 9
        elif t == "PANNA" and num == str(panna): win = amt * 140
        elif t == "JODI" and session == "CLOSE":
            c.execute("SELECT ank FROM results WHERE market=? AND session='OPEN' AND date=?", (market, today))
            op_res = c.fetchone()
            if op_res and num == (str(op_res[0]) + str(ank)): win = amt * 90
            
        if win > 0:
            update_bal(uid, win)
            try: bot.send_message(uid, f"🎊 **CONGRATS!** जीत गए! ₹{win} वॉलेट में जोड़ दिए गए।")
            except: pass
            
    c.execute("UPDATE results SET status='SENT' WHERE market=? AND session=? AND date=?", (market, session, today))
    conn.commit(); conn.close()

def auto_scheduler():
    while True:
        try:
            now = datetime.now().strftime("%H:%M")
            today = datetime.now().strftime("%Y-%m-%d")
            conn = get_db(); c = conn.cursor()
            for m, t in MARKET_TIMINGS.items():
                for s in ["OPEN", "CLOSE"]:
                    off_time = t['open_off'] if s == "OPEN" else t['close_off']
                    if now >= off_time:
                        c.execute("SELECT ank, panna FROM results WHERE market=? AND session=? AND date=? AND status='PENDING'", (m, s, today))
                        res = c.fetchone()
                        if res: process_winners(m, s, res[0], res[1])
            conn.close()
        except: pass
        time.sleep(60)

threading.Thread(target=auto_scheduler, daemon=True).start()

# --- 4. ADMIN PANEL ---
@bot.message_handler(commands=['admin'])
def admin_menu(message):
    if message.from_user.id != ADMIN_ID: return
    markup = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("📊 LOAD CHECK", callback_data="adm_load"),
        types.InlineKeyboardButton("🏆 SET RESULT", callback_data="adm_res"))
    bot.send_message(ADMIN_ID, "🛠 **ADMIN PANEL**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "adm_load")
def load_check(call):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT market, type, number, SUM(amount) FROM bets WHERE date=? GROUP BY market, type, number", (today,))
    rows = c.fetchall(); conn.close()
    if not rows:
        bot.answer_callback_query(call.id, "आज कोई दांव नहीं लगा है।", show_alert=True); return
    txt = "📊 **LIVE LOAD CHECK**\n\n"
    for r in rows: txt += f"🔹 {r[0]} | {r[1]} | {r[2]} : ₹{r[3]}\n"
    bot.send_message(ADMIN_ID, txt)

@bot.callback_query_handler(func=lambda call: call.data == "adm_res")
def adm_res_mkt(call):
    markup = types.InlineKeyboardMarkup()
    for m in MARKET_TIMINGS:
        markup.add(types.InlineKeyboardButton(f"{m} OPEN", callback_data=f"r1_{m}_OPEN"),
                   types.InlineKeyboardButton(f"{m} CLOSE", callback_data=f"r1_{m}_CLOSE"))
    bot.edit_message_text("रिजल्ट मंडी चुनें:", ADMIN_ID, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('r1_'))
def adm_res_ank(call):
    _, m, s = call.data.split('_')
    markup = types.InlineKeyboardMarkup(row_width=5)
    for i in range(10): markup.add(types.InlineKeyboardButton(str(i), callback_data=f"r2_{m}_{s}_{i}"))
    bot.edit_message_text(f"🏆 {m} {s} अंक:", ADMIN_ID, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('r2_'))
def adm_res_panna(call):
    _, m, s, a = call.data.split('_')
    markup = types.InlineKeyboardMarkup(row_width=4)
    btns = [types.InlineKeyboardButton(p, callback_data=f"r3_{m}_{s}_{a}_{p}") for p in MASTER_PANNA_CHART[a]]
    markup.add(*btns)
    bot.edit_message_text(f"🏆 पन्ना चुनें:", ADMIN_ID, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('r3_'))
def adm_res_save(call):
    _, m, s, a, p = call.data.split('_')
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO results (market, session, ank, panna, date, status) VALUES (?,?,?,?,?, 'PENDING')", (m, s, a, p, today))
    conn.commit(); conn.close()
    bot.answer_callback_query(call.id, f"✅ {p}-{a} सेव!", show_alert=True)
    bot.send_message(ADMIN_ID, f"✅ {m} {s} का रिजल्ट सेव हो गया!")

@bot.message_handler(commands=['add'])
def admin_add(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        p = message.text.split()
        target, amt = int(p[1]), int(p[2])
        update_bal(target, amt)
        bot.send_message(ADMIN_ID, f"✅ ID {target} में ₹{amt} जुड़ गए।")
        bot.send_message(target, f"🎉 **पैसे जमा हो गए!**\n💰 ₹{amt} वॉलेट में जोड़ दिए गए हैं।\nकुल बैलेंस: ₹{get_bal(target)}")
    except: bot.reply_to(message, "उपयोग: `/add ID Amount`")

# --- 5. USER INTERFACE & GAME ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.chat.id
    update_bal(uid, 0)
    markup = types.InlineKeyboardMarkup(row_width=1)
    for m in MARKET_TIMINGS:
        icon = "🟢 ON" if datetime.now().strftime("%H:%M") < MARKET_TIMINGS[m]['close_off'] else "🔴 LOCK"
        markup.add(types.InlineKeyboardButton(f"{icon} {m}", callback_data=f"m_{m}"))
    markup.row(types.InlineKeyboardButton("👤 PROFILE", callback_data="u_prof"))
    bot.send_message(uid, f"💰 **SIYA DIGITAL**\nबैलेंस: ₹{get_bal(uid)}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "u_prof")
def profile(call):
    uid = call.message.chat.id
    wa = f"https://wa.me/{WA_NUMBER}?text=ID:{uid}%20AddPoints"
    markup = types.InlineKeyboardMarkup(row_width=2).add(
        types.InlineKeyboardButton("➕ ADD POINTS", url=wa),
        types.InlineKeyboardButton("💸 WITHDRAWAL", callback_data="u_withdraw"),
        types.InlineKeyboardButton("🔙 BACK", callback_data="home"))
    bot.edit_message_text(f"👤 **PROFILE**\n🆔 ID: `{uid}`\n💰 बैलेंस: ₹{get_bal(uid)}", uid, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "u_withdraw")
def withdraw_msg(call):
    uid = call.message.chat.id
    msg = (f"💸 **WITHDRAWAL REQUEST**\nनीचे दी गई जानकारी टाइप करके भेजें:\n\n🏦 **BANK DETAILS:**\n1. Name:\n2. Bank:\n3. Account:\n4. IFSC:\n\n🆔 **या UPI:**\n1. UPI ID:\n2. Mobile No:\n\n💰 **Amount:**")
    bot.send_message(uid, msg)
    bot.send_message(ADMIN_ID, f"🔔 **WITHDRAWAL ALERT!** ID `{uid}` ने विथड्रॉल माँगा है।")

@bot.callback_query_handler(func=lambda call: call.data.startswith('m_'))
def m_sel(call):
    m = call.data.split('_')[1]
    user_temp[call.message.chat.id] = {'market': m}
    markup = types.InlineKeyboardMarkup()
    now = datetime.now().strftime("%H:%M")
    if now < MARKET_TIMINGS[m]['open_off']: markup.add(types.InlineKeyboardButton("☀️ OPEN", callback_data="s_OPEN"))
    markup.add(types.InlineKeyboardButton("🌙 CLOSE", callback_data="s_CLOSE"))
    bot.edit_message_text(f"🎬 {m} - सेशन चुनें:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('s_'))
def s_sel(call):
    user_temp[call.message.chat.id]['session'] = call.data.split('_')[1]
    markup = types.InlineKeyboardMarkup(row_width=2).add(
        types.InlineKeyboardButton("🎯 SINGLE", callback_data="t_SINGLE"),
        types.InlineKeyboardButton("👫 JODI", callback_data="t_JODI"),
        types.InlineKeyboardButton("📖 PANNA", callback_data="t_PANNA"))
    bot.edit_message_text("गेम टाइप चुनें:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('t_'))
def t_sel(call):
    user_temp[call.message.chat.id]['type'] = call.data.split('_')[1]
    msg = bot.send_message(call.message.chat.id, "🔢 वो नंबर लिखें जिसपर दांव लगाना है:")
    bot.register_next_step_handler(msg, get_num)

def get_num(message):
    user_temp[message.chat.id]['num'] = message.text
    msg = bot.send_message(message.chat.id, "💰 कितनी राशि (Amount) लगानी है?")
    bot.register_next_step_handler(msg, bet_final)

def bet_final(message):
    uid = message.chat.id
    try:
        amt = int(message.text)
        if get_bal(uid) < amt:
            bot.send_message(uid, "❌ बैलेंस कम है!"); return
        update_bal(uid, -amt)
        d = user_temp[uid]
        today = datetime.now().strftime("%Y-%m-%d")
        conn = get_db(); c = conn.cursor()
        c.execute("INSERT INTO bets VALUES (?,?,?,?,?,?,?)", (uid, d['market'], d['session'], d['type'], d['num'], amt, today))
        conn.commit(); conn.close()
        bot.send_message(uid, f"✅ **दांव सफल!**\nमंडी: {d['market']}\nनंबर: {d['num']}\nराशि: ₹{amt}")
        bot.send_message(ADMIN_ID, f"📩 नया दांव: ID {uid} | {d['market']} | {d['num']} | ₹{amt}")
    except: bot.send_message(uid, "❌ गलत अमाउंट!")

@bot.callback_query_handler(func=lambda call: call.data == "home")
def home(call): start(call.message)

if __name__ == "__main__":
    print("========================================")
    print("   SIYA DIGITAL BOT IS NOW LIVE!        ")
    print("========================================")
    bot.infinity_polling()
