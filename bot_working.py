#!/usr/bin/env python3
import logging
import requests
from io import BytesIO
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context):
    await update.message.reply_text(
        "🎨 Алекс Арт-директор\n\n"
        "Команды:\n"
        "/image текст - создать изображение\n"
        "/start - приветствие\n"
        "/help - помощь\n\n"
        "Просто напишите любой текст - я создам картинку"
    )

async def help_command(update: Update, context):
    await update.message.reply_text(
        "Отправьте любой текст, и я сгенерирую изображение.\n"
        "Например: 'кот в космосе'"
    )

async def generate_image(update, context, prompt):
    status_msg = await update.message.reply_text(f"🎨 Генерирую: {prompt[:80]}...")
    
    import urllib.parse
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
    
    try:
        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            img_data = response.content
            if len(img_data) > 1000:
                await status_msg.delete()
                await update.message.reply_photo(
                    photo=BytesIO(img_data),
                    caption=f"✅ {prompt[:150]}"
                )
                return True
            else:
                await status_msg.edit_text("❌ Не удалось создать изображение")
                return False
        else:
            await status_msg.edit_text(f"❌ Ошибка API: {response.status_code}")
            return False
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка: {e}")
        return False

async def handle_message(update: Update, context):
    text = update.message.text.strip()
    if text.startswith("/"):
        return
    await generate_image(update, context, text)

async def image_command(update: Update, context):
    prompt = " ".join(context.args) if context.args else None
    if not prompt:
        await update.message.reply_text("Пример: /image кот в космосе")
        return
    await generate_image(update, context, prompt)

def main():
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("image", image_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("=" * 50)
    print("АЛЕКС АРТ-ДИРЕКТОР ЗАПУЩЕН")
    print("=" * 50)
    print("✅ Генерация изображений через Pollinations.ai")
    print("=" * 50)
    
    app.run_polling()

if __name__ == "__main__":
    main()
