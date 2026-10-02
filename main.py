import telebot
from telebot import types
import requests
import re
import time
import threading

# 🔑 आपकी मुख्य सीक्रेट चाबियाँ (Keys)
BOT_TOKEN = "8927629267:AAGsrRFrhWitPBhMhfuGcUHAmDF1YcfKe3Q"
PLISIO_API_KEY = "h0DlhP76M_Cr3ASwrwUCj7KT1BzLHqHNK5U7rNlhk--QEamFC0cKNtPJwpbm8AIS"

bot = telebot.TeleBot(BOT_TOKEN)

# ⚙️ बिज़नेस सेटिंग्स और रूल्स
COMMISSION_RATE = 0.10  # 10% एडमिन कमीशन
MIN_DEPOSIT = 500       # ₹500 न्यूनतम डिपॉजिट नियम
ALERT_TIME = 35 * 60    # 35 मिनट (पहला चेतावनी अलर्ट)
CANCEL_TIME = 50 * 60   # 50 मिनट (ऑटो-कैंसिलेशन टाइमआउट - नो रिफंड)

# 🗄️ डेटाबेस सिमुलेशन (मेमरी में सुरक्षित)
wallets = {}       # {user_id: {"available": 0, "hold": 0, "username": ""}}
active_bets = {}   # {message_id: {"amount": 0, "user_id": 0, "username": ""}}
tables = {}        # {table_id: {"p1": id, "p2": id, "amount": 0, "status": "Live", "time": 0}}
table_counter = 100

# 🤬 गाली-गलौज और ग्रुप बदनामी रोकने के लिए अपशब्दों का फ़िल्टर
BAD_WORDS = ["चोर", "chor", "fraud", "फ्रॉड", "कमीने", "gali", "गाली"]

# 1️⃣ अपशब्द और गाली-गलौज ऑटो-डिलीट फ़िल्टर (100% माहौल सुरक्षित)
@bot.message_handler(func=lambda message: any(word in message.text.lower() for word in BAD_WORDS))
def filter_bad_words(message):
    try:
        bot.delete_message(message.chat.id, message.message_id)
        counsel_text = (
            f"नमस्ते भाई! 🙏\n\nखेल में हार और जीत एक ही सिक्के के दो पहलू हैं। "
            f"आपस में आपसी भाईचारा बनाए रखें। हमारी हाथ जोड़कर विनती है कि किसी भी प्रकार की बहस या गलत शब्दों का प्रयोग न करें। "
            f"आइए, विवाद को भूलकर प्यार से खेलते हैं। ऑल द बेस्ट! 👍"
        )
        bot.send_message(message.from_user.id, counsel_text)
    except Exception as e:
        print(f"Error filtering text: {e}")

# 2️⃣ ऑटोमैटिक क्रिप्टो गेटवे डिपॉजिट (UPI से पेमेंट)
@bot.message_handler(commands=['deposit'])
def process_deposit(message):
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ **गलत फॉर्मेट!** कृपया राशि इस प्रकार लिखें: `/deposit 500`", parse_mode="Markdown")
        return
        
    try:
        amount = int(args[1])
    except ValueError:
        bot.reply_to(message, "❌ अमाउंट केवल नंबर में होना चाहिए।")
        return

    # ₹500 न्यूनतम डिपॉजिट का कड़ा नियम
    if amount < MIN_DEPOSIT:
        bot.reply_to(message, f"❌ **नियम अलर्ट:** ग्रुप की सुरक्षा और गेटवे फीस के कारण न्यूनतम डिपॉजिट ₹{MIN_DEPOSIT} होना आवश्यक है।")
        return

    bot.reply_to(message, "⏳ आपका सुरक्षित पेमेंट लिंक तैयार किया जा रहा है, कृपया प्रतीक्षा करें...")

    # Plisio API के ज़रिए UPI/Crypto इनवॉइस लिंक बनाना
    try:
        payload = {
            'api_key': PLISIO_API_KEY,
            'currency': 'USDT',
            'order_number': f"DEP_{user_id}_{int(time.time())}",
            'order_name': f"Wallet Deposit for {username}",
            'amount': str(amount / 88.0), # रुपयों को रफली क्रिप्टो डॉलर में बदलना
            'source_currency': 'INR',
            'source_amount': str(amount),
            'callback_url': 'https://google.com' # डेमो हेतु
        }
        response = requests.get('https://plisio.net', params=payload).json()
        
        if response.get('status') == 'success':
            pay_url = response['data']['invoice_url']
            
            # खिलाड़ी को सीक्रेट पेमेंट लिंक बटन के साथ भेजना
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(text="💳 PhonePe/GPay से पेमेंट करें", url=pay_url))
            
            bot.send_message(user_id, f"🎯 **डिपॉजिट ऑर्डर:** ₹{amount}\n\nनीचे दिए गए बटन पर क्लिक करके 100% सुरक्षित भुगतान करें। भुगतान सफल होते ही बैलेंस अपने आप लोड हो जाएगा।", reply_markup=markup)
            
            # डेमो सिमुलेशन: चूंकि वेबहुक लाइव नहीं है, 5 सेकंड में बैलेंस लोड करना
            def demo_load():
                time.sleep(5)
                if user_id not in wallets: wallets[user_id] = {"available": 0, "hold": 0, "username": username}
                wallets[user_id]["available"] += amount
                bot.send_message(user_id, f"✅ **पेमेंट कन्फर्म!** आपके वॉलेट में ₹{amount} जोड़ दिए गए हैं।\nकुल बैलेंस: ₹{wallets[user_id]['available']}")
            threading.Thread(target=demo_load).start()
            
        else:
            bot.reply_to(message, "❌ गेटवे सर्वर व्यस्त है। कृपया कुछ देर बाद प्रयास करें।")
    except Exception as e:
        bot.reply_to(message, "❌ गेटवे कनेक्ट करने में त्रुटि आई है।")

# 3️⃣ बैट डिटेक्ट करना (ग्रुप में राशि लिखना)
@bot.message_handler(func=lambda message: message.chat.type in ['group', 'supergroup'] and any(char.isdigit() for char in message.text))
def detect_bet(message):
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    
    # पेंडिंग टेबल लॉक चेक (पुरानी टेबल होने पर नई बैट ब्लॉक)
    for t_id, t_data in tables.items():
        if (t_data["p1"] == user_id or t_data["p2"] == user_id) and t_data["status"] == "Live":
            bot.reply_to(message, f"❌ {username}, कृपया पहले अपनी पेंडिंग टेबल #{t_id} का परिणाम क्लियर करें।")
            return

    numbers = [int(s) for s in re.findall(r'\b\d+\b', message.text)]
    if not numbers: return
    bet_amount = numbers[0]

    # मल्टी-टेबल रिस्क बैलेंस चेक
    user_bal = wallets.get(user_id, {"available": 0})["available"]
    if user_bal < bet_amount: return # बैलेंस कम होने पर अनदेखा करें

    active_bets[message.message_id] = {"amount": bet_amount, "user_id": user_id, "username": username}

# 4️⃣ रिप्लाई/टैग करने पर मैच फिक्स करना और बोर्ड जारी करना (पहले आओ पहले पाओ)
@bot.message_handler(func=lambda message: message.reply_to_message is not None)
def match_bet(message):
    global table_counter
    p2_id = message.from_user.id
    p2_username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    reply_msg_id = message.reply_to_message.message_id

    if reply_msg_id not in active_bets: return

    bet_data = active_bets[reply_msg_id]
    p1_id = bet_data["user_id"]
    p1_username = bet_data["username"]
    bet_amount = bet_data["amount"]

    if p1_id == p2_id: return

    p2_bal = wallets.get(p2_id, {"available": 0})["available"]
    if p2_bal < bet_amount:
        bot.reply_to(message, f"❌ {p2_username}, आपके पास पर्याप्त बैलेंस नहीं है।")
        return

    del active_bets[reply_msg_id] # मैच लॉक
    table_counter += 1
    current_table = table_counter

    # फंड होल्ड पर डालना
    wallets[p1_id]["available"] -= bet_amount
    wallets[p1_id]["hold"] += bet_amount
    wallets[p2_id]["available"] -= bet_amount
    wallets[p2_id]["hold"] += bet_amount

    tables[current_table] = {
        "p1": p1_id, "p1_name": p1_username,
        "p2": p2_id, "p2_name": p2_username,
        "amount": bet_amount, "status": "Live", "time": time.time()
    }

    board_text = (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎲 **टेबल नंबर: #{current_table}**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 **बैट अमाउंट:** ₹{bet_amount}/- Full\n"
        f"🔥 **स्थिति:** 🟢 मैच चालू है (Live)\n\n"
        f"👥 **खिलाड़ी:**\n"
        f"1️⃣ प्लेयर 1: {p1_username}\n"
        f"2️⃣ प्लेयर 2: {p2_username}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👉 *दोनों भाई आपस में रूम कोड शेयर करके गेम शुरू करें। मैच खत्म होने पर विजेता `/win {current_table}` लिखकर स्क्रीनशॉट डालें।* \n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    bot.send_message(message.chat.id, board_text)
    threading.Thread(target=table_timer_check, args=(current_table, message.chat.id)).start()

# 5️⃣ 35 मिनट अलर्ट और 50 मिनट ऑटो-कैंसिलेशन पॉलिसी
def table_timer_check(table_id, chat_id):
    time.sleep(ALERT_TIME)
    if table_id in tables and tables[table_id]["status"] == "Live":
        t = tables[table_id]
        bot.send_message(chat_id, f"⚠️ **अलर्ट टेबल #{table_id}:** {t['p1_name']} और {t['p2_name']}, मैच को 35 मिनट हो चुके हैं! कृपया 15 मिनट में रिस्पॉन्स दें।")
        
        time.sleep(CANCEL_TIME - ALERT_TIME)
        if table_id in tables and tables[table_id]["status"] == "Live":
            t = tables[table_id]
            p1_id, p2_id, amt = t["p1"], t["p2"], t["amount"]
            
            # रिफंड
            wallets[p1_id]["hold"] -= amt
            wallets[p1_id]["available"] += amt
            wallets[p2_id]["hold"] -= amt
            wallets[p2_id]["available"] += amt
            
            tables[table_id]["status"] = "Auto-Cancelled"
            bot.send_message(chat_id, f"❌ **टेबल #{table_id} ऑटो-कैंसिल:** 50 मिनट तक कोई रिस्पॉन्स न मिलने पर टेबल रद्द कर दी गई है। अमाउंट रिफंड कर दिया गया है, अब कोई सुनवाई नहीं होगी।")

# 6️⃣ विनर डिक्लेरेशन और 10% कमीशन काटना
@bot.message_handler(commands=['win'])
def claim_win(message):
    args = message.text.split()
    if len(args) < 2: return
    
    table_id = int(args[1])
    if table_id not in tables or tables[table_id]["status"] != "Live": return
    
    t = tables[table_id]
    winner_id = message.from_user.id
    
    if winner_id not in [t["p1"], t["p2"]]: return
    
    loser_id = t["p2"] if winner_id == t["p1"] else t["p1"]
    amt = t["amount"]
    
    # 10% एडमिन कमीशन काटकर विनर को क्रेडिट करना
    net_win = int(amt * (1 - COMMISSION_RATE))
    total_credit = amt + net_win # खुद का ₹500 + विरोधी का ₹450 प्रॉफिट
    
    wallets[winner_id]["hold"] -= amt
    wallets[winner_id]["available"] += total_credit
    wallets[loser_id]["hold"] -= amt
    
    tables[table_id]["status"] = "Cleared"
    bot.reply_to(message, f"🏆 **मैच क्लियर!** टेबल #{table_id} के विजेता को ₹{total_credit} ट्रांसफर कर दिए गए हैं (10% कमीशन काटकर)।")

bot.polling(none_stop=True)
