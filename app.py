import logging
import os
import random
import sqlite3
import threading
import requests
from flask import Flask, render_template_string, request, redirect, url_for
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from telegram.request import HTTPXRequest

# ================= CONFIGURATION =================
BOT_TOKEN = os.getenv("BOT_TOKEN", "9222785063:AAHTUbRGRlH_F9gqzh-IZEhe-i_beVuqejg")    
ADMIN_ID = int(os.getenv("ADMIN_ID", "7351717426"))                                     
TELEGRAM_BOT_LINK = "https://t.me/Oroluckylotterybot"
SETTINGS = {
    "ticket_price": "100 Birr",
    "telebirr": "0912345678 (Maqaa Keessan)",
    "cbe": "1000123456789 (Maqaa Keessan)",
    "min_ticket": 1000,
    "max_ticket": 9999
}
# =================================================

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
NAME, ACCOUNT_TYPE, PAYMENT_METHOD, PAYMENT_PROOF = range(4)

def init_db():
    conn = sqlite3.connect("oro_lucky.db", timeout=30.0)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            account_type TEXT,
            payment_method TEXT,
            payment_proof TEXT,
            lottery_number INTEGER UNIQUE,
            status TEXT DEFAULT 'PENDING'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS winners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            full_name TEXT,
            lottery_number INTEGER,
            round_name TEXT,
            won_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def send_telegram_message(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print("Telegram Send Error:", e)

app_flask = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Oro Lucky - Admin Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; margin: 0; padding: 15px; color: #f8fafc; }
        .container { max-width: 600px; margin: auto; background: #1e293b; padding: 25px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }
        .header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; border-bottom: 2px solid #334155; padding-bottom: 10px; }
        .header h2 { font-size: 22px; margin: 0; color: #38bdf8; }
        .nav-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px; }
        .nav-btn { background: #334155; border: none; padding: 12px; border-radius: 10px; font-weight: bold; color: #f8fafc; cursor: pointer; text-align: center; font-size: 13px; text-decoration: none; display: block; transition: 0.2s; }
        .nav-btn:hover { background: #0284c7; }
        h3 { font-size: 16px; margin-top: 20px; color: #94a3b8; }
        .card { background: #0f172a; border: 1px solid #334155; padding: 15px; margin-bottom: 12px; border-radius: 12px; }
        .stat { font-size: 26px; font-weight: bold; color: #38bdf8; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #334155; padding: 10px; text-align: left; font-size: 12px; }
        th { background: #1e293b; color: #38bdf8; }
        input { width: 100%; padding: 10px; margin: 6px 0 12px 0; background: #0f172a; border: 1px solid #334155; color: white; border-radius: 8px; box-sizing: border-box; }
        button.submit-btn { background: #10b981; color: white; border: none; padding: 12px; border-radius: 8px; font-weight: bold; cursor: pointer; width: 100%; font-size: 14px; }
        button.submit-btn:hover { background: #059669; }
        .action-btn { padding: 5px 10px; border-radius: 6px; text-decoration: none; font-size: 11px; font-weight: bold; color: white; display: inline-block; margin: 2px; }
        .approve { background: #10b981; }
        .reject { background: #ef4444; }
        .reset-btn { background: #f59e0b; color: white; border: none; padding: 10px; border-radius: 8px; font-weight: bold; cursor: pointer; width: 100%; margin-top: 10px; font-size: 14px; }
        .reset-btn:hover { background: #d97706; }
        .back-btn { display: inline-block; margin-bottom: 15px; background: #2563eb; color: white; padding: 8px 14px; border-radius: 8px; text-decoration: none; font-size: 13px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        {% if view == 'home' %}
            <div class="header">
                <h2>🍀 Oro Lucky Admin</h2>
            </div>
            <div class="nav-grid">
                <a href="/" class="nav-btn">📊 Dashboard</a>
                <a href="/records" class="nav-btn">📁 Records</a>
                <a href="/tickets" class="nav-btn">🎟️ Ticket & Approval</a>
                <a href="/settings" class="nav-btn">⚙️ Settings</a>
                <a href="/reports" class="nav-btn">🏆 Draw Simulator</a>
                <a href="{{ bot_link }}" target="_blank" class="nav-btn">🤖 Telegram Bot</a>
            </div>

            <h3>Summary of the record</h3>
            <div class="card">
                <div>Gatii Tikkeetii Carraa (Price)</div>
                <div class="stat" style="color: #fbbf24;">{{ settings.ticket_price }}</div>
            </div>
            <div class="card">
                <div>General records</div>
                <div class="stat">{{ total_users }}</div>
            </div>
            <div class="card">
                <div>Pending Confirmation</div>
                <div class="stat" style="color: #f59e0b;">{{ pending_users }}</div>
            </div>
            <div class="card">
                <div>Approved Records</div>
                <div class="stat" style="color: #10b981;">{{ approved_users }}</div>
            </div>

        {% elif view == 'records' %}
            <a href="/" class="back-btn">⬅️ Deebi'i</a>
            <h2>📁 Records of the General</h2>
            <table>
                <tr><th>Maqaa</th><th>Account</th><th>Payment</th><th>Status</th></tr>
                {% for u in users %}
                <tr><td>{{ u[1] }}</td><td>{{ u[2] }}</td><td>{{ u[3] }}</td><td><b>{{ u[5] }}</b></td></tr>
                {% endfor %}
            </table>

        {% elif view == 'tickets' %}
            <a href="/" class="back-btn">⬅️ Deebi'i</a>
            <h2>🎟️ Ticket Records & Approval Panel</h2>
            <table>
                <tr><th>Maqaa</th><th>Status</th><th>Carraa / TxID</th><th>Action</th></tr>
                {% for u in users %}
                <tr>
                    <td>{{ u[1] }}</td>
                    <td><b>{{ u[5] }}</b></td>
                    <td>{{ u[4] if u[4] else '-' }}</td>
                    <td>
                        <a href="/approve/{{ u[0] }}" class="action-btn approve">Approve</a>
                        <a href="/reject/{{ u[0] }}" class="action-btn reject">Reject</a>
                    </td>
                </tr>
                {% endfor %}
            </table>

        {% elif view == 'settings' %}
            <a href="/" class="back-btn">⬅️ Deebi'i</a>
            <h2>⚙️ Accounts & Lottery Range Settings</h2>
            <form method="POST" action="/update_settings">
                <label>Gatii Tikkeetii (Ticket Price):</label>
                <input type="text" name="ticket_price" value="{{ settings.ticket_price }}" required>
                
                <label>Telebirr Account & Name:</label>
                <input type="text" name="telebirr" value="{{ settings.telebirr }}" required>
                
                <label>CBE Account & Name:</label>
                <input type="text" name="cbe" value="{{ settings.cbe }}" required>
                
                <label>Min Ticket Number:</label>
                <input type="number" name="min_ticket" value="{{ settings.min_ticket }}" required>
                
                <label>Max Ticket Number:</label>
                <input type="number" name="max_ticket" value="{{ settings.max_ticket }}" required>
                
                <button type="submit" class="submit-btn">Save Settings</button>
            </form>

        {% elif view == 'reports' %}
            <a href="/" class="back-btn">⬅️ Deebi'i</a>
            <h2>📊 Reports & Draw Simulator</h2>
            <form method="POST" action="/run_draw">
                <label>Marsaa Carraa (Round Name):</label>
                <input type="text" name="round_name" value="Marsaa 1ffaa" required>
                <button type="submit" class="submit-btn">Run Draw & Announce Winner</button>
            </form>
            
            <form method="POST" action="/reset_new_round" onsubmit="return confirm('Carraan haaraan fi galmeen haaraan haala kanaan eegala. Dhugaa ni barbaaddaa?');">
                <button type="submit" class="reset-btn">🔄 Galmee Haaraa & Marsaa Haaraa Eegalsiisi (Reset Round)</button>
            </form>

            {% if winners_list %}
                <h3 style="color: #38bdf8; margin-top: 20px;">🏆 Mo'atoota Kanaan Dura Bahes:</h3>
                <table>
                    <tr><th>Marsaa</th><th>Maqaa</th><th>Carraa</th><th>Yeroo</th></tr>
                    {% for w in winners_list %}
                    <tr><td>{{ w[3] }}</td><td>{{ w[1] }}</td><td><b>{{ w[2] }}</b></td><td>{{ w[4] }}</td></tr>
                    {% endfor %}
                </table>
            {% else %}
                <p style="margin-top: 15px; color: #94a3b8; font-size: 13px;">Ammaaf mo'ataan bahe hin jiru.</p>
            {% endif %}
        {% endif %}
    </div>
</body>
</html>
"""

@app_flask.route('/')
def dashboard():
    conn = sqlite3.connect("oro_lucky.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'PENDING'")
    pending_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'APPROVED'")
    approved_users = cursor.fetchone()[0]
    conn.close()
    return render_template_string(HTML_TEMPLATE, view='home', total_users=total_users, pending_users=pending_users, approved_users=approved_users, bot_link=TELEGRAM_BOT_LINK, settings=SETTINGS)

@app_flask.route('/records')
def records():
    conn = sqlite3.connect("oro_lucky.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, full_name, account_type, payment_method, lottery_number, status FROM users")
    users = cursor.fetchall()
    conn.close()
    return render_template_string(HTML_TEMPLATE, view='records', users=users)

@app_flask.route('/tickets')
def tickets():
    conn = sqlite3.connect("oro_lucky.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, full_name, account_type, payment_method, payment_proof, status FROM users")
    users = cursor.fetchall()
    conn.close()
    return render_template_string(HTML_TEMPLATE, view='tickets', users=users)

@app_flask.route('/settings')
def settings_page():
    return render_template_string(HTML_TEMPLATE, view='settings', settings=SETTINGS)

@app_flask.route('/update_settings', methods=['POST'])
def update_settings():
    SETTINGS['ticket_price'] = request.form.get('ticket_price')
    SETTINGS['telebirr'] = request.form.get('telebirr')
    SETTINGS['cbe'] = request.form.get('cbe')
    SETTINGS['min_ticket'] = int(request.form.get('min_ticket'))
    SETTINGS['max_ticket'] = int(request.form.get('max_ticket'))
    return redirect(url_for('dashboard'))

@app_flask.route('/approve/<int:user_id>')
def web_approve(user_id):
    conn = sqlite3.connect("oro_lucky.db")
    cursor = conn.cursor()
    cursor.execute("SELECT lottery_number FROM users WHERE user_id = ? AND lottery_number IS NOT NULL", (user_id,))
    existing = cursor.fetchone()
    
    if existing:
        cursor.execute("UPDATE users SET status = 'APPROVED' WHERE user_id = ?", (user_id,))
    else:
        cursor.execute("SELECT lottery_number FROM users WHERE lottery_number IS NOT NULL")
        used = set(r[0] for r in cursor.fetchall())
        avail = list(set(range(SETTINGS['min_ticket'], SETTINGS['max_ticket'] + 1)) - used)
        if avail:
            l_num = random.choice(avail)
            cursor.execute("UPDATE users SET status = 'APPROVED', lottery_number = ? WHERE user_id = ?", (l_num, user_id))
    conn.commit()
    conn.close()
    return redirect(url_for('tickets'))

@app_flask.route('/reject/<int:user_id>')
def web_reject(user_id):
    conn = sqlite3.connect("oro_lucky.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status = 'REJECTED', lottery_number = NULL WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('tickets'))

@app_flask.route('/reports')
def reports():
    conn = sqlite3.connect("oro_lucky.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, full_name, lottery_number, round_name, won_at FROM winners ORDER BY id DESC")
    winners_list = cursor.fetchall()
    conn.close()
    return render_template_string(HTML_TEMPLATE, view='reports', winners_list=winners_list)

@app_flask.route('/run_draw', methods=['POST'])
def run_draw():
    round_name = request.form.get('round_name')
    conn = sqlite3.connect("oro_lucky.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, full_name, lottery_number FROM users WHERE status = 'APPROVED' AND user_id NOT IN (SELECT user_id FROM winners WHERE round_name = ?)", (round_name,))
    users = cursor.fetchall()
    
    if users:
        winner = random.choice(users)
        w_id, w_name, w_num = winner[0], winner[1], winner[2]
        try:
            cursor.execute("INSERT INTO winners (user_id, full_name, lottery_number, round_name) VALUES (?, ?, ?, ?)", 
                           (w_id, w_name, w_num, round_name))
            conn.commit()
            
            announcement_text = (
                f"🏆 **HUBIIRSAA MO'ATAALOTTERY!** 🏆\n\n"
                f"📌 **Marsaa:** {round_name}\n"
                f"👤 **Maqaa Mo'ataa:** {w_name}\n"
                f"🎟️ **Lakkoofsa Carraa:** `{w_num}`\n\n"
                f"🎉 Baga gammaddan!"
            )
            
            send_telegram_message(ADMIN_ID, announcement_text)
            
            cursor.execute("SELECT user_id FROM users")
            all_users = cursor.fetchall()
            for u_row in all_users:
                send_telegram_message(u_row[0], announcement_text)

        except Exception as e:
            print("Draw Error:", e)
    conn.close()
    return redirect(url_for('reports'))

@app_flask.route('/reset_new_round', methods=['POST'])
def reset_new_round():
    conn = sqlite3.connect("oro_lucky.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users")
    cursor.execute("DELETE FROM winners")
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

def run_flask():
    app_flask.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("📝 Galmee Jalqabi")],
        [KeyboardButton("👤 Galmee koo"), KeyboardButton("📋 Haala galmee")],
        [KeyboardButton("ℹ️ Gargaarsa")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    conn = sqlite3.connect("oro_lucky.db")
    cursor = conn.cursor()
    cursor.execute("SELECT status, lottery_number FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        status, l_num = row
        if status == 'APPROVED':
            await update.message.reply_text(f"⚠️ Ati duraanuu galmoofteetta!\n🎟️ Lakkoofsi Carraa Keetii: **{l_num}**", parse_mode="Markdown", reply_markup=get_main_keyboard())
            return ConversationHandler.END
        elif status == 'PENDING':
            await update.message.reply_text("⏳ Galmeen kee ammaan tti Admin irraa mirkaneessaa (Pending) jira.", reply_markup=get_main_keyboard())
            return ConversationHandler.END

    await update.message.reply_text(f"🍀 **Baga gara Oro Lucky Bot tti Nagaan Dhuftan!**\n\n💰 Gatiin Tikkeetii Carraa: *{SETTINGS['ticket_price']}*\nMoo'ataa ta'uuf **Maqaa Keessan Guutuu** barreessaa:", reply_markup=get_main_keyboard(), parse_mode="Markdown")
    return NAME

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ Galmee eegaluuf '📝 Galmee Jalqabi' tuqi.", reply_markup=get_main_keyboard())

async def my_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect("oro_lucky.db")
    cursor = conn.cursor()
    cursor.execute("SELECT full_name, account_type, payment_method, lottery_number, status FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        await update.message.reply_text("⚠️ Ati kanaan dura hin galmoofne.", reply_markup=get_main_keyboard())
        return
    await update.message.reply_text(f"👤 Maqaa: {row[0]}\nAccount: {row[1]}\nStatus: {row[4]}\nCarraa: {row[3] if row[3] else 'Pending'}", reply_markup=get_main_keyboard())

async def rules_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📋 Namni tokko carraa tokko qofa argata.", reply_markup=get_main_keyboard())

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['full_name'] = update.message.text
    keyboard = [[InlineKeyboardButton("Standard 💳", callback_data="Standard")], [InlineKeyboardButton("Premium 🌟", callback_data="Premium")], [InlineKeyboardButton("VIP 👑", callback_data="VIP")]]
    await update.message.reply_text("Account keessanii filadhaa:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ACCOUNT_TYPE

async def select_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['account_type'] = query.data
    keyboard = [[InlineKeyboardButton("📱 Telebirr", callback_data="Telebirr")], [InlineKeyboardButton("🏦 CBE", callback_data="CBE")]]
    await query.edit_message_text(f"Mala kaffaltii filadhaa (Gatiin: {SETTINGS['ticket_price']}):\n📱 Telebirr: `{SETTINGS['telebirr']}`\n🏦 CBE: `{SETTINGS['cbe']}`", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return PAYMENT_METHOD

async def select_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['payment_method'] = query.data
    await query.edit_message_text("Ragaa kaffaltii (Transaction ID) asitti ergaa:")
    return PAYMENT_PROOF

async def get_payment_proof(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    data = context.user_data
    conn = sqlite3.connect("oro_lucky.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (user_id, full_name, account_type, payment_method, payment_proof, status) VALUES (?, ?, ?, ?, ?, 'PENDING')",
                       (user.id, data['full_name'], data['account_type'], data['payment_method'], update.message.text))
        conn.commit()
    except:
        conn.close()
        await update.message.reply_text("⚠️ Ati duraanuu galmoofteetta!", reply_markup=get_main_keyboard())
        return ConversationHandler.END
    conn.close()

    await update.message.reply_text("✅ Ragaan kee ergameera! Dashboard irratti ni mul'ata.", reply_markup=get_main_keyboard())
    
    admin_markup = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user.id}"), InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user.id}")]])
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"📋 Galmee Haaraa:\nMaqaa: {data['full_name']}\nID: {user.id}\nTxID: {update.message.text}", reply_markup=admin_markup)
    return ConversationHandler.END

async def admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("❌ Eeyyama hin qabdu!", show_alert=True)
        return
    await query.answer()
    action, user_id_str = query.data.split("_")
    target_id = int(user_id_str)

    conn = sqlite3.connect("oro_lucky.db")
    cursor = conn.cursor()
    if action == "approve":
        cursor.execute("SELECT lottery_number FROM users WHERE lottery_number IS NOT NULL")
        used = set(r[0] for r in cursor.fetchall())
        avail = list(set(range(SETTINGS['min_ticket'], SETTINGS['max_ticket'] + 1)) - used)
        if not avail:
            await query.edit_message_text("⚠️ Lakkoofsi carraa dhumateera!")
            conn.close()
            return
        l_num = random.choice(avail)
        cursor.execute("UPDATE users SET status = 'APPROVED', lottery_number = ? WHERE user_id = ?", (l_num, target_id))
        conn.commit()
        await context.bot.send_message(chat_id=target_id, text=f"🎉 Galmeen kee mirkanaa'eera!\n🎟️ Lakkoofsi Carraa: {l_num}", reply_markup=get_main_keyboard())
        await query.edit_message_text(f"✅ Approved! Lakkoofsi {l_num} kennameera.")
    else:
        cursor.execute("UPDATE users SET status = 'REJECTED' WHERE user_id = ?", (target_id,))
        conn.commit()
        await context.bot.send_message(chat_id=target_id, text="❌ Galmeen kee fudhatama dhabe.", reply_markup=get_main_keyboard())
        await query.edit_message_text("❌ Rejected.")
    conn.close()

def main():
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
    print("🌐 Web Dashboard running on http://127.0.0.1:5000")

    request = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0)
    app = Application.builder().token(BOT_TOKEN).request(request).build()
    
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start), MessageHandler(filters.Regex("^📝 Galmee Jalqabi$"), start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            ACCOUNT_TYPE: [CallbackQueryHandler(select_account, pattern="^(Standard|Premium|VIP)$")],
            PAYMENT_METHOD: [CallbackQueryHandler(select_payment_method, pattern="^(Telebirr|CBE)$")],
            PAYMENT_PROOF: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_payment_proof)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)]
    )
    
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.Regex("^👤 Galmee koo$"), my_status))
    app.add_handler(MessageHandler(filters.Regex("^📋 Haala galmee$"), rules_info))
    app.add_handler(MessageHandler(filters.Regex("^ℹ️ Gargaarsa$"), help_command))
    app.add_handler(CallbackQueryHandler(admin_decision, pattern="^(approve|reject)_"))

    print("🤖 Telegram Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
