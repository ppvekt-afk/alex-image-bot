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
from amazon_skill import AmazonListingGenerator

setup_logging(config.LOG_LEVEL)
logger = logging.getLogger(__name__)

image_gen = ImageGenerator(config.SD_API_URL, config.SD_API_KEY)
amazon_gen = AmazonListingGenerator()
active_amazon_listings = {}
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
        "🎨 БРЕНД-КИТ\n"
        "/brandkit название | индустрия\n"
        "/generate_brand_images\n\n"
        "📦 AMAZON LISTING (НОВЫЙ!)\n"
        "/amazon название | категория | особенности | покупатель\n"
        "/generate_amazon_listing\n\n"
        "Пример Amazon:\n"
        "/amazon Термокружка | Kitchen & Dining | герметичная, сохраняет тепло | офисные работники"
    )

async def help_command(update, context):
    await update.message.reply_text(
        "Команды Алекса:\n\n"
        "/image текст - создать изображение\n"
        "/ppt тема - создать презентацию\n"
        "/brandkit название | индустрия - создать бренд-кит\n"
        "/generate_brand_images - сгенерировать визуалы бренда\n"
        "/amazon название | категория | особенности - создать Amazon листинг\n"
        "/generate_amazon_listing - сгенерировать 4 изображения для Amazon\n"
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
            caption=f"✅ Готово: {prompt[:150]}"
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
        await update.message.reply_document(document=InputFile(f, filename=filename), caption=f"📊 Презентация: {topic}")
    
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
        f"Отправьте /generate_brand_images"
    )

async def generate_brand_images_command(update, context):
    user_id = update.effective_user.id
    if user_id not in active_brand_kits:
        await update.message.reply_text("Сначала создайте бренд-кит: /brandkit название | индустрия")
        return
    
    data = active_brand_kits[user_id]
    brand_name = data["brand_name"]
    industry = data["industry"]
    
    await update.message.reply_text(f"🎨 Создаю визуалы для {brand_name}...")
    
    prompts = {
        "logo": f"Minimalist logo for '{brand_name}', {industry} brand, clean vector-style on white background",
        "moodboard": f"Brand moodboard for {brand_name}, {industry}, show color palette and lifestyle images",
        "pattern": f"Seamless brand pattern for {brand_name}, {industry}, subtle and modern"
    }
    
    for name, prompt in prompts.items():
        img_bytes, error = await image_gen.generate(prompt, None)
        if img_bytes:
            await update.message.reply_photo(
                photo=InputFile(BytesIO(img_bytes), filename=f"{brand_name}_{name}.png"),
                caption=f"{name.upper()} для {brand_name}"
            )
    
    await update.message.reply_text(f"✅ Бренд-кит для {brand_name} готов!")

async def amazon_command(update, context):
    args = " ".join(context.args) if context.args else ""
    
    if not args:
        await update.message.reply_text(
            "📦 Amazon Product Listing\n\n"
            "Формат: /amazon название | категория | особенности | покупатель\n\n"
            "Пример:\n"
            "/amazon Термокружка 500мл | Kitchen & Dining | герметичная крышка, сохраняет тепло 12ч | офисные работники\n\n"
            "Затем /generate_amazon_listing"
        )
        return
    
    parts = [p.strip() for p in args.split("|")]
    if len(parts) < 3:
        await update.message.reply_text("Используйте: название | категория | особенности | покупатель")
        return
    
    product_name = parts[0]
    product_category = parts[1]
    key_features = parts[2]
    target_buyer = parts[3] if len(parts) > 3 else "general consumer"
    
    listing = amazon_gen.create_listing(product_name, product_category, key_features, target_buyer)
    
    prompts = {
        "hero": amazon_gen.generate_hero_prompt(product_name),
        "lifestyle": amazon_gen.generate_lifestyle_prompt(product_name, product_category, target_buyer),
        "infographic": amazon_gen.generate_infographic_prompt(product_name, listing["key_features"]),
        "detail": amazon_gen.generate_detail_prompt(product_name)
    }
    
    active_amazon_listings[update.effective_user.id] = {
        "listing": listing,
        "prompts": prompts
    }
    
    output = amazon_gen.format_output(listing, prompts)
    await update.message.reply_text(output)

async def generate_amazon_listing_command(update, context):
    user_id = update.effective_user.id
    if user_id not in active_amazon_listings:
        await update.message.reply_text("Сначала создайте Amazon listing: /amazon название | категория | особенности")
        return
    
    data = active_amazon_listings[user_id]
    listing = data["listing"]
    prompts = data["prompts"]
    
    await update.message.reply_text(f"📦 Создаю 4 изображения для {listing['product_name']}...")
    
    # Hero
    img_bytes, error = await image_gen.generate(prompts["hero"], None)
    if img_bytes:
        await update.message.reply_photo(
            photo=InputFile(BytesIO(img_bytes), filename="amazon_hero.png"),
            caption=f"1/4 HERO IMAGE\n{listing['product_name']}\nБелый фон для главного фото"
        )
    
    # Lifestyle
    img_bytes, error = await image_gen.generate(prompts["lifestyle"], None)
    if img_bytes:
        await update.message.reply_photo(
            photo=InputFile(BytesIO(img_bytes), filename="amazon_lifestyle.png"),
            caption=f"2/4 LIFESTYLE\n{listing['product_name']} в использовании"
        )
    
    # Infographic
    img_bytes, error = await image_gen.generate(prompts["infographic"], None)
    if img_bytes:
        await update.message.reply_photo(
            photo=InputFile(BytesIO(img_bytes), filename="amazon_infographic.png"),
            caption=f"3/4 INFOGRAPHIC\nКлючевые особенности продукта"
        )
    
    # Detail
    img_bytes, error = await image_gen.generate(prompts["detail"], None)
    if img_bytes:
        await update.message.reply_photo(
            photo=InputFile(BytesIO(img_bytes), filename="amazon_detail.png"),
            caption=f"4/4 DETAIL CLOSEUP\nКачество материалов"
        )
    
    await update.message.reply_text(f"✅ Amazon листинг для {listing['product_name']} готов!")

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
    app.add_handler(CommandHandler("brandkit", brandkit_command))
    app.add_handler(CommandHandler("generate_brand_images", generate_brand_images_command))
    app.add_handler(CommandHandler("amazon", amazon_command))
    app.add_handler(CommandHandler("generate_amazon_listing", generate_amazon_listing_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("=" * 60)
    print("АЛЕКС АРТ-ДИРЕКТОР - С НАВЫКОМ AMAZON LISTING")
    print("=" * 60)
    print("✅ Генерация изображений")
    print("✅ Презентации")
    print("✅ Бренд-кит")
    print("✅ Amazon Product Listing (НОВЫЙ!)")
    print("=" * 60)
    print("\nНовые команды:")
    print("  /amazon товар | категория | особенности | покупатель")
    print("  /generate_amazon_listing")
    print("\nПример:")
    print("  /amazon Термокружка | Kitchen & Dining | герметичная, сохраняет тепло | офисные работники")
    print("\n" + "=" * 60)
    
    app.run_polling()

if __name__ == "__main__":
    main()
