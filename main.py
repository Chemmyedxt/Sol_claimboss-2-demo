import json
import os
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Config
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATA_FILE = "wallets.json"
MINED_FILE = "mined.json"

# Init storage
for file in [DATA_FILE, MINED_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)

# Load/save helpers
def load_wallets():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_wallets(w):
    with open(DATA_FILE, "w") as f:
        json.dump(w, f, indent=2)

def load_mined():
    with open(MINED_FILE, "r") as f:
        return json.load(f)

def save_mined(m):
    with open(MINED_FILE, "w") as f:
        json.dump(m, f, indent=2)

# Validate Solana wallet
def is_valid_wallet(addr):
    return len(addr) in range(32, 45) and addr.isalnum()

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    wallets = load_wallets()

    if user_id in wallets:
        await update.message.reply_text(f"✅ Already setup. Wallet: {wallets[user_id]['wallet']}\nUse /farm.")
    else:
        await update.message.reply_text("👋 Welcome! Send me your Solana wallet address to continue.")
        context.user_data['awaiting_wallet'] = True

async def handle_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()

    if context.user_data.get("awaiting_wallet"):
        if is_valid_wallet(text):
            wallets = load_wallets()
            wallets[user_id] = {
                "wallet": text,
                "joined": datetime.utcnow().isoformat()
            }
            save_wallets(wallets)
            context.user_data['awaiting_wallet'] = False
            await update.message.reply_text("✅ Wallet saved! Use /farm.")
        else:
            await update.message.reply_text("❌ Invalid Solana address. Try again.")

async def setwallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['awaiting_wallet'] = True
    await update.message.reply_text("Send your new Solana wallet.")

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    wallets = load_wallets()
    mined = load_mined()

    if user_id not in wallets:
        await update.message.reply_text("❌ Set wallet first using /start.")
        return

    w = wallets[user_id]['wallet']
    stats = mined.get(user_id, {"claims": 0, "tokens": [], "last_claim": "-", "usd_total": 0})
    token_list = "\n".join([f"- {t}" for t in stats["tokens"]]) or "- None"

    msg = f"""📊 Dashboard
👛 Wallet: {w}
🪙 Claims: {stats['claims']}
🧾 Last: {stats['last_claim']}
💰 Total: ${stats['usd_total']}
🔹 Tokens:
{token_list}
"""
    await update.message.reply_text(msg)

async def farm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    wallets = load_wallets()
    mined = load_mined()

    if user_id not in wallets:
        await update.message.reply_text("❌ Set wallet first with /start.")
        return

    now = datetime.utcnow().isoformat()
    demo_tokens = ["0.0005 SOL (~$0.9)", "0.3 HULK (~$1.8)"]

    stats = mined.get(user_id, {"claims": 0, "tokens": [], "last_claim": "-", "usd_total": 0})
    stats["claims"] += len(demo_tokens)
    stats["tokens"].extend(demo_tokens)
    stats["last_claim"] = now
    stats["usd_total"] += 2.7
    mined[user_id] = stats
    save_mined(mined)

    await update.message.reply_text(f"✅ You farmed {len(demo_tokens)} tokens!\nUse /report to view them.")

# Telegram bot setup
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("setwallet", setwallet))
app.add_handler(CommandHandler("report", report))
app.add_handler(CommandHandler("farm", farm))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wallet))

if __name__ == '__main__':
    print(\"Bot running...\")
    app.run_polling()
