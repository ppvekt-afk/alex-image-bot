#!/usr/bin/env python3
import logging
import requests
import urllib.parse
import re
from io import BytesIO
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import config
from utils import setup_logging

setup_logging(config.LOG_LEVEL)
logger = logging.getLogger(__name__)

BOT_USERNAME = "photo_al_bot"
BOT_NAME = "Алекс"

MODE_IMAGE = "image"
MODE_CHAT = "chat"
user_modes = {}

def generate_image_bytes(prompt):
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
    response = requests.get(url, timeout=60)
    if response.status_code == 200 and len(response.content) > 1000:
        return response.content
    return None

def is_addressed_to_me(update: Update) -> bool:
    if not update.message:
        return False
    text = update.message.text or ""
    if f"@{BOT_USERNAME}" in text or "алекс" in text.lower():
        return True
    if update.message.chat.type == "private":
        return True
    return False

def should_generate_image(text: str) -> bool:
    keywords = ["нарисуй", "создай изображение", "картинку", "draw", "generate", "логотип", "лого"]
    return any(k in text.lower() for k in keywords)

async def start(update: Update, context):
    if not is_addressed_to_me(update):
        return
    await update.message.reply_text(
        f"🎨 Алекс здесь! Я умею генерировать изображения и отвечать на вопросы.\n\n"
        f"Примеры:\n"
        f"• Алекс, нарисуй кота\n"
        f"• Алекс, что думаешь о дизайне?\n"
        f"• @{BOT_USERNAME} помоги с композицией"
    )

async def handle_message(update: Update, context):
    if not update.message or not update.message.text:
        return
    if not is_addressed_to_me(update):
        return
    
    user_id = update.effective_user.id
    text = update.message.text
    text = re.sub(f"@{BOT_USERNAME}", "", text, flags=re.IGNORECASE)
    text = re.sub(r'\bалекс\b', "", text, flags=re.IGNORECASE)
    text = text.strip()
    
    if not text:
        await update.message.reply_text("Слушаю! Что нужно сделать?")
        return
    
    if should_generate_image(text):
        status = await update.message.reply_text(f"🎨 Генерирую: {text[:80]}...")
        img = generate_image_bytes(text)
        if img:
            await status.delete()
            await update.message.reply_photo(photo=BytesIO(img), caption=f"✅ {text[:150]}")
        else:
            await status.edit_text("❌ Не удалось создать изображение")
    else:
        await update.message.reply_text(
            "Чтобы сгенерировать изображение, напиши: 'Алекс, нарисуй ...'\n"
            "Или задай вопрос о дизайне, искусстве, трендах."
        )

def main():
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("АЛЕКС ЗАПУЩЕН")
    app.run_polling(allowed_updates=["message"])

if __name__ == "__main__":
    main()
