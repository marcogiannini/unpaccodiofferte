"""
Bot Telegram per aggiungere il codice referral Amazon ai link condivisi.

Requisiti:
    pip install python-telegram-bot==20.7

Configurazione:
    1. Crea un bot su Telegram tramite @BotFather e ottieni il TOKEN
    2. Imposta il tuo TAG referral Amazon in AMAZON_TAG
    3. Avvia il bot con: python amazon_referral_bot.py
"""

import os
import re
import logging
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ─── CONFIGURAZIONE ──────────────────────────────────────────────────────────

BOT_TOKEN = os.environ.get("BOT_TOKEN")       # Impostalo nelle variabili Railway
AMAZON_TAG = os.environ.get("AMAZON_TAG")     # Impostalo nelle variabili Railway

# ─── LOGGING ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── DOMINI AMAZON SUPPORTATI ────────────────────────────────────────────────

AMAZON_DOMAINS = {
    "amazon.it", "amazon.com", "amazon.co.uk", "amazon.de",
    "amazon.fr", "amazon.es", "amazon.nl", "amazon.pl",
    "amazon.se", "amazon.co.jp", "amazon.ca", "amazon.com.au",
    "amzn.to", "amzn.eu",                 # URL corti
}

# Regex per estrarre URL dal testo
URL_REGEX = re.compile(
    r"https?://[^\s<>\"\u201c\u201d\u2018\u2019\u300c\u300d\uff08\uff09\u3010\u3011\u0028\u0029]+",
    re.IGNORECASE,
)


def is_amazon_url(url: str) -> bool:
    """Controlla se l'URL appartiene ad Amazon."""
    try:
        host = urlparse(url).netloc.lower().lstrip("www.")
        return host in AMAZON_DOMAINS
    except Exception:
        return False


def add_referral_tag(url: str) -> str:
    """
    Aggiunge (o sovrascrive) il parametro tag=AMAZON_TAG all'URL.
    Gestisce sia i link brevi (amzn.to) che quelli completi.
    """
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)

    # Imposta / sovrascrive il tag referral
    params["tag"] = [AMAZON_TAG]

    # Ricostruisce la query string (sort per coerenza)
    new_query = urlencode(
        {k: v[0] for k, v in sorted(params.items())},
        doseq=False,
    )

    new_url = urlunparse(parsed._replace(query=new_query))
    return new_url


def process_text(text: str) -> tuple[str, int]:
    """
    Cerca tutti i link Amazon nel testo e aggiunge il tag referral.
    Restituisce (testo_modificato, numero_link_trovati).
    """
    found_links = URL_REGEX.findall(text)
    modified = text
    count = 0

    for link in found_links:
        if is_amazon_url(link):
            new_link = add_referral_tag(link)
            modified = modified.replace(link, new_link)
            count += 1

    return modified, count


# ─── HANDLER ─────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Messaggio di benvenuto."""
    await update.message.reply_text(
        "👋 Ciao! Sono il tuo bot per i link referral Amazon.\n\n"
        "📌 Come funziono:\n"
        "• Inviami un messaggio contenente uno o più link Amazon\n"
        "• Ti rispondo con gli stessi link, ma con il tuo codice referral aggiunto\n\n"
        "🔗 Puoi anche aggiungermi a un gruppo: leggo tutti i messaggi e rispondo "
        "solo quando trovo link Amazon.\n\n"
        "Usa /help per maggiori informazioni."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Messaggio di aiuto."""
    await update.message.reply_text(
        "ℹ️ *Come usare il bot*\n\n"
        "1\\. Inviami un link Amazon \\(anche all'interno di un testo\\)\n"
        "2\\. Il bot risponde con il link modificato\n\n"
        "*Esempi di link supportati:*\n"
        "• `https://www.amazon.it/dp/B09XXXXX`\n"
        "• `https://amzn.to/XXXXX` \\(link brevi\\)\n"
        "• `https://www.amazon.com/dp/B09XXXXX`\n\n"
        "Il tag referral viene aggiunto o sovrascritto automaticamente.",
        parse_mode="MarkdownV2",
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Elabora ogni messaggio in cerca di link Amazon."""
    if not update.message or not update.message.text:
        return

    text = update.message.text
    modified_text, count = process_text(text)

    if count == 0:
        # Nessun link Amazon trovato — silenzioso nei gruppi, risponde in privato
        if update.message.chat.type == "private":
            await update.message.reply_text(
                "❌ Nessun link Amazon trovato nel messaggio.\n"
                "Inviami un link che inizi con https://www.amazon.* oppure https://amzn.to/"
            )
        return

    plural = "link" if count == 1 else "link"
    caption = f"🛒 {count} {plural} Amazon con il tuo referral:\n\n{modified_text}"

    await update.message.reply_text(
        caption,
        disable_web_page_preview=True,
    )
    logger.info("Processati %d link Amazon per utente %s", count, update.effective_user.id)


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main() -> None:
    """Avvia il bot."""
    if not BOT_TOKEN:
        raise ValueError("⚠️  Variabile d'ambiente BOT_TOKEN non impostata!")
    if not AMAZON_TAG:
        raise ValueError("⚠️  Variabile d'ambiente AMAZON_TAG non impostata!")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot avviato. In attesa di messaggi…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
