"""
Bot Telegram per aggiungere il codice referral Amazon ai link condivisi.

Requisiti:
    pip install python-telegram-bot==21.9

Configurazione:
    Imposta le variabili d'ambiente:
        BOT_TOKEN  = token fornito da @BotFather
        AMAZON_TAG = il tuo Associates tag (es. "marcosbox-21")
"""

import os
import re
import logging
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ─── CONFIGURAZIONE ──────────────────────────────────────────────────────────

BOT_TOKEN  = os.environ.get("BOT_TOKEN")
AMAZON_TAG = os.environ.get("AMAZON_TAG")

# ─── LOGGING ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── DOMINI AMAZON SUPPORTATI ────────────────────────────────────────────────

AMAZON_DOMAINS = {
    "amazon.it", "amazon.com", "amazon.co.uk", "amazon.de",
    "amazon.fr", "amazon.es", "amazon.nl", "amazon.pl",
    "amazon.se", "amazon.co.jp", "amazon.ca", "amazon.com.au",
    "amzn.to", "amzn.eu",
}

URL_REGEX = re.compile(r"https?://\S+", re.IGNORECASE)

# ─── FUNZIONI ────────────────────────────────────────────────────────────────

def is_amazon_url(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower().removeprefix("www.")
        return host in AMAZON_DOMAINS
    except Exception:
        return False


def add_tag(url: str) -> str:
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    params["tag"] = [AMAZON_TAG]
    new_query = urlencode({k: v[0] for k, v in sorted(params.items())})
    return urlunparse(parsed._replace(query=new_query))


def process_text(text: str) -> tuple[str, int]:
    links = URL_REGEX.findall(text)
    modified = text
    count = 0
    for link in links:
        if is_amazon_url(link):
            modified = modified.replace(link, add_tag(link))
            count += 1
    return modified, count

# ─── HANDLER ─────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Ciao! Sono il bot di Marco's Box per i link referral Amazon!\n\n"
        "📌 Come funziono:\n"
        "• Inviami uno o più link Amazon\n"
        "• Ti rispondo con gli stessi link con il codice referral aggiunto\n\n"
        "🔗 Aggiungimi a un gruppo: intervengo solo quando trovo link Amazon.\n\n"
        "Usa /help per maggiori informazioni."
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "ℹ️ Come usare il bot\n\n"
        "Inviami un messaggio con un link Amazon, anche in mezzo al testo.\n\n"
        "Esempi di link supportati:\n"
        "• https://www.amazon.it/dp/B09XXXXX\n"
        "• https://amzn.to/XXXXX\n"
        "• https://www.amazon.com/dp/B09XXXXX\n\n"
        "Il tag referral viene aggiunto o sovrascritto automaticamente."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    modified_text, count = process_text(update.message.text)

    if count == 0:
        if update.message.chat.type == "private":
            await update.message.reply_text(
                "❌ Nessun link Amazon trovato.\n"
                "Inviami un link che inizi con https://www.amazon.* o https://amzn.to/"
            )
        return

    await update.message.reply_text(
        f"🛒 {count} link Amazon con referral:\n\n{modified_text}",
        disable_web_page_preview=True,
    )
    logger.info("Processati %d link per utente %s", count, update.effective_user.id)

# ─── MAIN ────────────────────────────────────────────────────────────────────

def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("Variabile d'ambiente BOT_TOKEN non impostata!")
    if not AMAZON_TAG:
        raise RuntimeError("Variabile d'ambiente AMAZON_TAG non impostata!")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot avviato. In attesa di messaggi…")
    app.run_polling()


if __name__ == "__main__":
    main()
