#!/usr/bin/env python3
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import config
from utils import setup_logging

setup_logging(config.LOG_LEVEL)
logger = logging.getLogger(__name__)

async def start(update, context):
    await update.message.reply_text("✅ Алекс работает!")

async def echo(update, context):
    await update.message.reply_text(f"Вы написали: {update.message.text}")

def main():
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    print("✅ Бот запущен в минимальном режиме")
    app.run_polling()

if __name__ == "__main__":
    main()
