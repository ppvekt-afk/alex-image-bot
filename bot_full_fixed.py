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

# Хранилища для временных данных
active_campaigns = {}
active_brand_kits = {}

async def start(update, context):
    await update.message.reply_text(
        "🎨 Алекс Арт-директор\n\n"
        "Доступные команды:\n\n"
        "🖼️ ИЗОБРАЖЕНИЯ\n"
        "/image описание\n"
        "Любой текст\n\n"
        "📊 ПРЕЗЕНТАЦИИ\n"
        "/ppt тема\n"
        "презентация про тему\n\n"
        "📢 КАМПАНИИ\n"
        "/campaign продукт | аудитория\n"
        "/generate_campaign\n\n"
        "🎨 БРЕНД-КИТ\n"
        "/brandkit название | индустрия\n"
        "/generate_brand_images\n\n"
        "Примеры:\n"
        "/brandkit Lumina | tech startup\n"
        "/campaign кофе | молодежь"
    )

async def help_command(update, context):
    await update.message.reply_text(
        "Команды Алекса:\n\n"
        "/image текст - создать изображение\n"
        "/ppt тема - создать презентацию\n"
        "/campaign продукт | аудитория - создать кампанию\n"
        "/generate_campaign - сгенерировать изображения кампании\n"
        "/brandkit название | индустрия - создать бренд-кит\n"
        "/generate_brand_images - сгенерировать визуалы бренда\n"
        "/start - приветствие\n"
        "/help - помощь"
    )

async def generate_image(update, context, prompt):
    status_msg = await update.message.reply_text(f"🎨 Генерирую: {prompt[:80]}...")
    img_bytes, error = await image_gen.generate(prompt, None)
    if img_bytes:
        await status_msg.delete()
        await update.message.reply_photo(
            photo=InputFile(BytesIO(img_bytes), filename="art.png"),
            caption=f"Готово: {prompt[:150]}"
        )
        return True
    else:
        await status_msg.edit_text(f"Ошибка: {error}")
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

async def campaign_command(update, context):
    args = " ".join(context.args) if context.args else ""
    if not args:
        await update.message.reply_text(
            "Формат: /campaign продукт | аудитория\n\n"
            "Пример: /campaign кофе | молодые профессионалы"
        )
        return
    
    parts = [p.strip() for p in args.split("|")]
    if len(parts) < 2:
        await update.message.reply_text("Используйте: продукт | аудитория")
        return
    
    product = parts[0]
    audience = parts[1]
    
    active_campaigns[update.effective_user.id] = {
        "product": product,
        "audience": audience
    }
    
    await update.message.reply_text(
        f"✅ Кампания создана!\n\n"
        f"Продукт: {product}\n"
        f"Аудитория: {audience}\n\n"
        f"Теперь отправьте /generate_campaign для создания 3 изображений"
    )

async def generate_campaign_command(update, context):
    user_id = update.effective_user.id
    if user_id not in active_campaigns:
        await update.message.reply_text("Сначала создайте кампанию: /campaign продукт | аудитория")
        return
    
    data = active_campaigns[user_id]
    product = data["product"]
    audience = data["audience"]
    
    await update.message.reply_text(f"🎨 Создаю 3 изображения для кампании {product}...")
    
    prompts = [
        f"Premium product photography of {product}, targeting {audience}, cinematic lighting",
        f"Lifestyle shot of people using {product}, {audience} demographic, natural lighting",
        f"Abstract artistic representation of {product}, modern design, bold colors"
    ]
    
    for i, prompt in enumerate(prompts, 1):
        img_bytes, error = await image_gen.generate(prompt, None)
        if img_bytes:
            await update.message.reply_photo(
                photo=InputFile(BytesIO(img_bytes), filename=f"campaign_{i}.png"),
                caption=f"Концепт {i}: {prompt[:80]}..."
            )
    
    await update.message.reply_text(f"✅ Кампания для {product} завершена!")

async def brandkit_command(update, context):
    args = " ".join(context.args) if context.args else ""
    if not args:
        await update.message.reply_text(
            "Формат: /brandkit название | индустрия\n\n"
            "Пример: /brandkit Lumina | tech startup"
        )
        return
    
    parts = [p.strip() for p in args.split("|")]
    if len(parts) < 2:
        await update.message.reply_text("Используйте: название | индустрия")
        return
    
    brand_name = parts[0]
    industry = parts[1]
    
    active_brand_kits[update.effective_user.id] = {
        "brand_name": brand_name,
        "industry": industry
    }
    
    await update.message.reply_text(
        f"✅ Бренд-кит создан!\n\n"
        f"Название: {brand_name}\n"
        f"Индустрия: {industry}\n\n"
        f"Теперь отправьте /generate_brand_images для создания визуалов бренда"
    )

async def generate_brand_images_command(update, context):
    user_id = update.effective_user.id
    if user_id not in active_brand_kits:
        await update.message.reply_text("Сначала создайте бренд-кит: /brandkit название | индустрия")
        return
    
    data = active_brand_kits[user_id]
    brand_name = data["brand_name"]
    industry = data["industry"]
    
    await update.message.reply_text(f"🎨 Создаю визуалы для бренда {brand_name}...")
    
    prompts = {
        "logo": f"Minimalist logo for '{brand_name}', {industry} brand, clean vector-style on white background",
        "moodboard": f"Brand moodboard for {brand_name}, {industry}, show color palette swatches and lifestyle images",
        "pattern": f"Seamless brand pattern for {brand_name}, {industry}, subtle and modern"
    }
    
    for name, prompt in prompts.items():
        img_bytes, error = await image_gen.generate(prompt, None)
        if img_bytes:
            await update.message.reply_photo(
                photo=InputFile(BytesIO(img_bytes), filename=f"{brand_name}_{name}.png"),
                caption=f"{name.upper()} для бренда {brand_name}"
            )
    
    await update.message.reply_text(
        f"✅ Бренд-кит для {brand_name} готов!\n\n"
        f"Цвета: подберите из moodboard\n"
        f"Шрифты: Montserrat для заголовков, Open Sans для текста"
    )

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
    app.add_handler(CommandHandler("campaign", campaign_command))
    app.add_handler(CommandHandler("generate_campaign", generate_campaign_command))
    app.add_handler(CommandHandler("brandkit", brandkit_command))
    app.add_handler(CommandHandler("generate_brand_images", generate_brand_images_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("=" * 60)
    print("АЛЕКС АРТ-ДИРЕКТОР - ПОЛНАЯ ВЕРСИЯ")
    print("=" * 60)
    print("✅ Генерация изображений")
    print("✅ Презентации")
    print("✅ Рекламные кампании")
    print("✅ Бренд-кит")
    print("=" * 60)
    print("\nКоманды:")
    print("  /brandkit Lumina | tech startup")
    print("  /generate_brand_images")
    print("  /campaign кофе | молодежь")
    print("  /generate_campaign")
    print("  /image кот в космосе")
    print("  /ppt нейросети")
    print("\n" + "=" * 60)
    
    app.run_polling()

if __name__ == "__main__":
    main()
