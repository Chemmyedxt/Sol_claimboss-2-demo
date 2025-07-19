import json, os, requests
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATA_FILE = "wallets.json"
MINED_FILE = "mined.json"

# Storage Setup
for file in [DATA_FILE, MINED_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)

def load_json(path): return json.load(open(path))
def save_json(path, data): json.dump(data, open(path, "w"), indent=2)

def is_valid_wallet(addr):
    return len(addr) in range(32, 45) and addr.isalnum()

# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    wallets = load_json(DATA_FILE)
    if user_id in wallets:
        await update.message.reply_text(f"✅ Already registered: {wallets[user_id]['wallet']}")
    else:
        await update.message.reply_text("👋 Welcome! Send your Solana wallet address to get started.")
        context.user_data['awaiting_wallet'] = True

async def handle_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()
    if context.user_data.get("awaiting_wallet"):
        if is_valid_wallet(text):
            wallets = load_json(DATA_FILE)
            wallets[user_id] = {"wallet": text, "joined": datetime.utcnow().isoformat()}
            save_json(DATA_FILE, wallets)
            await update.message.reply_text("✅ Wallet saved! Use /farm")
        else:
            await update.message.reply_text("❌ Invalid Solana wallet.")
        context.user_data['awaiting_wallet'] = False

async def setwallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['awaiting_wallet'] = True
    await update.message.reply_text("Send your new Solana wallet:")

# 🔥 Real Airdrop Fetch
def get_sol_mints(wallet):
    url = f"https://api.solana.fm/v0/accounts/{wallet}/tokens?limit=20&offset=0"
    headers = {'accept': 'application/json'}
    r = requests.get(url, headers=headers)
    if r.status_code != 200: return []
    data = r.json()
    results = []
    for t in data.get("tokens", []):
        if t.get("isAirdrop", False) or t.get("token", {}).get("mintAuthority"):
            symbol = t["token"].get("symbol", "???")
            results.append(f"{symbol} - {t['amountReadable']} {symbol}")
    return results[:5]

async def farm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    wallets = load_json(DATA_FILE)
    mined = load_json(MINED_FILE)

    if user_id not in wallets:
        await update.message.reply_text("❌ Set wallet with /start")
        return

    wallet = wallets[user_id]['wallet']
    mints = get_sol_mints(wallet)

    if not mints:
        await update.message.reply_text("😐 No airdrops or new tokens found.")
        return

    mined[user_id] = {
        "wallet": wallet,
        "claims": len(mints),
        "tokens": mints,
        "last_claim": datetime.utcnow().isoformat(),
        "usd_total": round(len(mints) * 0.9, 2)
    }
    save_json(MINED_FILE, mined)
    await update.message.reply_text(f"✅ Detected {len(mints)} tokens!\nUse /report")

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    mined = load_json(MINED_FILE)
    if user_id not in mined:
        await update.message.reply_text("❌ Nothing claimed yet.")
        return
    d = mined[user_id]
    token_list = "\n".join(f"- {t}" for t in d['tokens'])
    await update.message.reply_text(f"""📊 Dashboard:
👛 {d['wallet']}
🪙 Claims: {d['claims']}
🧾 Last: {d['last_claim']}
💰 Est. Total: ${d['usd_total']}
🔹 Tokens:
{token_list}
""")

# Bot Init
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("setwallet", setwallet))
app.add_handler(CommandHandler("farm", farm))
app.add_handler(CommandHandler("report", report))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wallet))

if __name__ == '__main__':
    print("Bot running...")
    app.run_polling()
