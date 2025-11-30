import telebot
import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# =======================
# BOT CONFIG
# =======================
BOT_TOKEN = "8595068165:AAEjQjRKNbjq98R0LOunyVpvRIz64NaLLp4"  # Replace with your bot token
TMDB_API = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiI5MDA2NzMyMGExMTc4NDdmNTJkNTM1OGI0OGZmMzg1NSIsIm5iZiI6MTc2NDM3OTk4MS4xMTIsInN1YiI6IjY5MmE0ZDRkODhiMTBjMGNiMTN"         # Replace with your TMDb API key
UPI_ID = "6205228690@ybl"
ADMIN_ID = 6336582923                   # Your Telegram ID
BOT_USERNAME = "MahfuzX_AutoBot"      # Example: EarnXProBot
BOT_NAME = "EarnX Pro Bot"
# =======================

bot = telebot.TeleBot(BOT_TOKEN)

# Temporary database (replace with persistent DB in production)
users = {}
balance = {}
referrals = {}
withdraw_requests = {}
quiz_sessions = {}  # {user_id: {"category": ..., "questions": [...], "current": 0, "score": 0}}

WELCOME_TEXT = f"""
✨ *Welcome to {BOT_NAME}* ✨

🎁 Earn Rewards  
🎬 Download Movies  
📝 Take Quiz  
👥 Refer & Earn  
💳 UPI Withdraw  

Use the buttons below ↓
"""

# -------------------------
# QUIZ QUESTIONS (PLACEHOLDER)
# -------------------------
quiz_questions = {
    "General Knowledge": [
        {"question": "What is the capital of France?", "options": ["OPTION1", "OPTION2", "OPTION3", "OPTION4"], "answer": 0},
        {"question": "Which planet is known as the Red Planet?", "options": ["OPTION1", "OPTION2", "OPTION3", "OPTION4"], "answer": 1},
        {"question": "What is the largest ocean on Earth?", "options": ["OPTION1", "OPTION2", "OPTION3", "OPTION4"], "answer": 2}
    ],
    "Science": [
        {"question": "What is the chemical symbol for water?", "options": ["OPTION1", "OPTION2", "OPTION3", "OPTION4"], "answer": 0},
        {"question": "Which gas do plants absorb from the atmosphere?", "options": ["OPTION1", "OPTION2", "OPTION3", "OPTION4"], "answer": 1},
        {"question": "What force keeps us on the ground?", "options": ["OPTION1", "OPTION2", "OPTION3", "OPTION4"], "answer": 2}
    ],
    "History": [
        {"question": "Who was the first President of the United States?", "options": ["OPTION1", "OPTION2", "OPTION3", "OPTION4"], "answer": 0},
        {"question": "In which year did World War II end?", "options": ["OPTION1", "OPTION2", "OPTION3", "OPTION4"], "answer": 1},
        {"question": "Who discovered America?", "options": ["OPTION1", "OPTION2", "OPTION3", "OPTION4"], "answer": 2}
    ]
}

# -------------------------
# START COMMAND
# -------------------------
@bot.message_handler(commands=["start"])
def start(message):
    uid = message.chat.id

    # Register new user
    if uid not in users:
        users[uid] = True
        balance[uid] = 10  # signup bonus
        referrals[uid] = 0

    # Handle referral
    if " " in message.text:
        ref = message.text.split(" ")[1]
        if ref.isdigit() and int(ref) != uid:
            ref = int(ref)
            if ref in balance:
                balance[ref] += 5
                referrals[ref] += 1

    menu = InlineKeyboardMarkup()
    menu.row(
        InlineKeyboardButton("🎬 Movie Search", callback_data="movie"),
        InlineKeyboardButton("💰 Earn Money", callback_data="earn")
    )
    menu.row(
        InlineKeyboardButton("📤 Withdraw", callback_data="withdraw"),
        InlineKeyboardButton("👤 Profile", callback_data="profile")
    )
    menu.row(
        InlineKeyboardButton("📝 Quiz", callback_data="quiz")
    )

    bot.send_message(uid, WELCOME_TEXT, parse_mode="Markdown", reply_markup=menu)

# -------------------------
# CALLBACK HANDLER
# -------------------------
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    cid = call.message.chat.id

    if call.data == "earn":
        ref_link = f"https://t.me/{BOT_USERNAME}?start={cid}"
        bot.send_message(cid, f"""
💰 *Earn Money*

Invite friends & earn instantly.

🔗 *Your Referral Link:*  
{ref_link}

👥 Referrals: {referrals.get(cid, 0)}
💵 Balance: ₹{balance.get(cid, 0)}
        """, parse_mode="Markdown")

    elif call.data == "profile":
        bot.send_message(cid, f"""
👤 *Profile*

Name: {call.from_user.first_name}
User ID: {cid}

💵 Balance: ₹{balance.get(cid, 0)}
👥 Referrals: {referrals.get(cid, 0)}
        """, parse_mode="Markdown")

    elif call.data == "withdraw":
        user_balance = balance.get(cid, 0)
        if user_balance < 30:
            bot.send_message(cid, f"❌ Minimum withdraw is ₹30.\nYour balance: ₹{user_balance}")
            return
        withdraw_requests[cid] = user_balance
        bot.send_message(cid, f"""
💳 *Withdraw Money*

Your request for ₹{user_balance} has been received.

📌 Please pay to the following UPI ID to confirm:
`{UPI_ID}`

✅ Once payment is done, admin will verify and mark as completed.
        """, parse_mode="Markdown")
        bot.send_message(ADMIN_ID, f"💳 Withdraw Request\nUser: {call.from_user.first_name} ({cid})\nAmount: ₹{user_balance}")

    elif call.data == "movie":
        bot.send_message(cid, "🎬 Send movie name:")
        bot.register_next_step_handler(call.message, movie_search)

    elif call.data == "quiz":
        # Show category options
        menu = InlineKeyboardMarkup()
        for cat in quiz_questions.keys():
            menu.add(InlineKeyboardButton(cat, callback_data=f"quiz_{cat}"))
        bot.send_message(cid, "📝 Choose a quiz category:", reply_markup=menu)

    elif call.data.startswith("quiz_"):
        category = call.data.split("_")[1]
        questions = quiz_questions.get(category, [])
        if not questions:
            bot.send_message(cid, "❌ No questions in this category yet.")
            return
        quiz_sessions[cid] = {"category": category, "questions": questions, "current": 0, "score": 0}
        send_quiz_question(cid)

# -------------------------
# SEND QUIZ QUESTION
# -------------------------
def send_quiz_question(user_id):
    session = quiz_sessions.get(user_id)
    if not session:
        return
    q_index = session["current"]
    questions = session["questions"]

    if q_index >= len(questions):
        # Quiz finished
        score = session["score"]
        bot.send_message(user_id, f"🎉 Quiz Completed!\nYour Score: {score}/{len(questions)}")
        # Optional: reward user balance
        balance[user_id] += score * 5  # 5₹ per correct answer
        bot.send_message(user_id, f"💰 {score*5}₹ added to your balance!")
        quiz_sessions.pop(user_id)
        return

    q = questions[q_index]
    menu = InlineKeyboardMarkup()
    for i, opt in enumerate(q["options"]):
        menu.add(InlineKeyboardButton(opt, callback_data=f"ans_{i}"))
    bot.send_message(user_id, f"Q{q_index+1}: {q['question']}", reply_markup=menu)

# -------------------------
# HANDLE QUIZ ANSWERS
# -------------------------
@bot.callback_query_handler(func=lambda call: call.data.startswith("ans_"))
def handle_answer(call):
    cid = call.message.chat.id
    session = quiz_sessions.get(cid)
    if not session:
        bot.answer_callback_query(call.id, "No active quiz.")
        return

    selected = int(call.data.split("_")[1])
    q_index = session["current"]
    question = session["questions"][q_index]

    if selected == question["answer"]:
        session["score"] += 1
        bot.answer_callback_query(call.id, "✅ Correct!")
    else:
        bot.answer_callback_query(call.id, "❌ Wrong!")

    session["current"] += 1
    send_quiz_question(cid)

# -------------------------
# MOVIE SEARCH
# -------------------------
def movie_search(message):
    query = message.text
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API}&query={query}"

    try:
        data = requests.get(url).json()
    except:
        bot.send_message(message.chat.id, "❌ Error fetching data from TMDb.")
        return

    if "results" not in data or len(data["results"]) == 0:
        bot.send_message(message.chat.id, "❌ Movie not found.")
        return

    movie = data["results"][0]
    title = movie["title"]
    desc = movie.get("overview", "No description available")

    bot.send_message(message.chat.id, f"""
🎬 *{title}*

📝 {desc[:200]}...

🔗 *Download Links:*  
• HD Print  

(Note: Real download links you must add manually)
    """, parse_mode="Markdown")

# -------------------------
# ADMIN COMMANDS
# -------------------------
@bot.message_handler(commands=["admin"])
def admin(message):
    if message.chat.id != ADMIN_ID:
        return

    panel = "🛠 Admin Panel\n\n"
    panel += "👥 Total Users: " + str(len(users)) + "\n"
    panel += "💳 Pending Withdraw Requests: " + str(len(withdraw_requests)) + "\n\n"
    panel += "Use /approve <user_id> to approve withdrawal."
    bot.send_message(ADMIN_ID, panel)

@bot.message_handler(commands=["approve"])
def approve_withdraw(message):
    if message.chat.id != ADMIN_ID:
        return
    try:
        uid = int(message.text.split()[1])
    except:
        bot.send_message(ADMIN_ID, "Usage: /approve <user_id>")
        return

    if uid in withdraw_requests:
        amt = withdraw_requests.pop(uid)
        balance[uid] -= amt
        bot.send_message(uid, f"✅ Your withdrawal of ₹{amt} has been approved by admin!")
        bot.send_message(ADMIN_ID, f"✅ Withdrawal approved for {uid}")
    else:
        bot.send_message(ADMIN_ID, "No pending withdraw request for this user.")

# -------------------------
# RUN BOT
# -------------------------
bot.infinity_polling()