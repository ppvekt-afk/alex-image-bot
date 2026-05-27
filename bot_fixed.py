#!/usr/bin/env python3
import logging
import re
from io import BytesIO
from datetime import datetime
from pathlib import Path
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import config
from utils import setup_logging
from image_generator import ImageGenerator

setup_logging(config.LOG_LEVEL)
logger = logging.getLogger(__name__)

image_gen = ImageGenerator(config.SD_API_URL, config.SD_API_KEY)

async def start(update, context):
    await update.message.reply_text(
        "🎨 Алекс Арт-директор - Полная версия\n\n"
        "Доступные навыки:\n\n"
        "🖼️ Изображения\n"
        "• /image описание - генерация картинок\n"
        "• Любой текст - сразу создаст изображение\n\n"
        "📊 Презентации\n"
        "• /ppt тема - создать презентацию\n"
        "• презентация про тему\n\n"
        "📢 Рекламные кампании\n"
        "• /campaign продукт | аудитория | формат | кол-во\n"
        "• /generate_campaign - создать изображения\n\n"
        "🎨 Бренд-кит\n"
        "• /brandkit название | индустрия | характер | цвет\n"
        "• /generate_brand_images - создать визуалы\n\n"
        "Примеры:\n"
        "/brandkit Lumina | tech startup | modern | blue\n"
        "/campaign кофе | молодежь | 1:1 | 3"
    )

async def help_command(update, context):
    await update.message.reply_text(
        "Все команды Алекса:\n\n"
        "🎨 Бренд-кит:\n"
        "/brandkit название | индустрия | характер | цвет\n"
        "/generate_brand_images - создать визуалы бренда\n\n"
        "📢 Кампании:\n"
        "/campaign продукт | аудитория | формат | кол-во\n"
        "/generate_campaign - создать изображения\n\n"
        "🖼️ Изображения:\n"
        "/image описание\n"
        "Любой текст\n\n"
        "📊 Презентации:\n"
        "/ppt тема\n"
        "презентация про тему"
    )

async def generate_image(update, context, prompt):
    status_msg = await update.message.reply_text(f"🎨 Генерирую: {prompt[:80]}...")
    img_bytes, error = await image_gen.generate(prompt, None)
    if img_bytes:
        await status_msg.delete()
        await update.message.reply_photo(
            photo=InputFile(BytesIO(img_bytes), filename="art.png"),
            caption=f"✅ Готово\nЗапрос: {prompt[:150]}"
        )
        return True
    else:
        await status_msg.edit_text(f"❌ Ошибка: {error}")
        return False

async def create_ppt(update, context, topic):
    status_msg = await update.message.reply_text(f"📊 Создаю презентацию: {topic[:80]}...")
    filename = f"presentation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    
    html_content = f'''<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>{topic}</title>
<style>
body {{ margin:0; background:linear-gradient(135deg,#667eea,#764ba2); font-family:Arial; }}
.slide {{ min-height:100vh; display:flex; align-items:center; justify-content:center; flex-direction:column; text-align:center; color:white; padding:20px; }}
h1 {{ font-size:48px; }}
p {{ font-size:24px; }}
</style>
</head>
<body>
<div class="slide"><h1>📊 {topic}</h1><p>Презентация</p></div>
</body>
</html>'''
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    with open(filename, 'rb') as f:
        await update.message.reply_document(document=InputFile(f, filename=filename), caption=f"Презентация: {topic}")
    
    Path(filename).unlink(missing_ok=True)
    await status_msg.delete()

async def image_command(update, context):
    prompt = " ".join(context.args) if context.args else None
    if not prompt:
        await update.message.reply_text("Пример: /image кот в космосе")
        return
    await generate_image(update, context, prompt)

async def ppt_command(update, context):
    topic = " ".join(context.args) if context.args else "Презентация"
    await create_ppt(update, context, topic)

async def handle_message(update, context):
    text = update.message.text.strip()
    if not text:
        return
    lower = text.lower()
    
    if text.startswith("/"):
        return
    
    if "презентац" in lower:
        topic = re.sub(r'(презентация|создай|про|на тему)', '', lower).strip()
        await create_ppt(update, context, topic or "Презентация")
    else:
        await generate_image(update, context, text)

def main():
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("image", image_command))
    app.add_handler(CommandHandler("ppt", ppt_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("=" * 50)
    print("АЛЕКС АРТ-ДИРЕКТОР ЗАПУЩЕН")
    print("=" * 50)
    print("✅ Генерация изображений")
    print("✅ Презентации")
    print("=" * 50)
    print("\nКоманды:")
    print("  /image кот в космосе")
    print("  /ppt нейросети")
    print("  презентация про ИИ")
    print("\n" + "=" * 50)
    
    app.run_polling()

if __name__ == "__main__":
    main()
