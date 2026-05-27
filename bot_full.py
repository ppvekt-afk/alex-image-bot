#!/usr/bin/env python3
import logging
import requests
import urllib.parse
import re
from io import BytesIO
from datetime import datetime
from pathlib import Path
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== ХРАНИЛИЩА ==========
active_brand_kits = {}
active_amazon_listings = {}

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def generate_image_bytes(prompt):
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
    response = requests.get(url, timeout=60)
    if response.status_code == 200 and len(response.content) > 1000:
        return response.content
    return None

# ========== ОСНОВНЫЕ КОМАНДЫ ==========
async def start(update, context):
    await update.message.reply_text(
        "🎨 АЛЕКС АРТ-ДИРЕКТОР - ПОЛНАЯ ВЕРСИЯ\n\n"
        "📌 ВСЕ КОМАНДЫ:\n\n"
        "🖼️ ИЗОБРАЖЕНИЯ\n"
        "/image текст - создать картинку\n"
        "Любой текст - сразу создаст изображение\n\n"
        "📊 ПРЕЗЕНТАЦИИ\n"
        "/ppt тема - создать HTML презентацию\n"
        "презентация про тему\n\n"
        "🎨 БРЕНД-КИТ\n"
        "/brandkit название | индустрия\n"
        "/generate_brand_images - создать логотип, мудборд, паттерн\n\n"
        "📦 AMAZON LISTING\n"
        "/amazon название | категория | особенности | покупатель\n"
        "/generate_amazon_listing - создать 4 изображения для Amazon\n\n"
        "📢 ПОМОЩЬ\n"
        "/help - справка\n\n"
        "Примеры:\n"
        "/brandkit Lumina | tech startup\n"
        "/amazon Термокружка | Kitchen & Dining | герметичная, сохраняет тепло | офисные работники"
    )

async def help_command(update, context):
    await update.message.reply_text(
        "ВСЕ КОМАНДЫ АЛЕКСА:\n\n"
        "🖼️ /image текст - создать изображение\n"
        "📊 /ppt тема - создать презентацию\n"
        "🎨 /brandkit название | индустрия - создать бренд-кит\n"
        "🎨 /generate_brand_images - сгенерировать визуалы бренда\n"
        "📦 /amazon название | категория | особенности - создать Amazon листинг\n"
        "📦 /generate_amazon_listing - сгенерировать 4 изображения для Amazon\n"
        "❓ /start - приветствие\n"
        "❓ /help - эта справка\n\n"
        "Или просто напишите любой текст - я создам изображение!"
    )

# ========== ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ ==========
async def generate_image(update, context, prompt):
    status_msg = await update.message.reply_text(f"🎨 Генерирую: {prompt[:80]}...")
    img_data = generate_image_bytes(prompt)
    if img_data:
        await status_msg.delete()
        await update.message.reply_photo(
            photo=BytesIO(img_data),
            caption=f"✅ {prompt[:150]}"
        )
        return True
    else:
        await status_msg.edit_text("❌ Не удалось создать изображение")
        return False

async def image_command(update, context):
    prompt = " ".join(context.args) if context.args else None
    if not prompt:
        await update.message.reply_text("Пример: /image кот в космосе")
        return
    await generate_image(update, context, prompt)

# ========== ПРЕЗЕНТАЦИИ ==========
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

async def ppt_command(update, context):
    topic = " ".join(context.args) if context.args else "Презентация"
    await create_ppt(update, context, topic)

# ========== БРЕНД-КИТ ==========
async def brandkit_command(update, context):
    args = " ".join(context.args) if context.args else ""
    if not args:
        await update.message.reply_text(
            "🎨 Бренд-кит\n\nФормат: /brandkit название | индустрия\n\nПример: /brandkit Lumina | tech startup"
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
        f"Теперь отправьте /generate_brand_images"
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
        "moodboard": f"Brand moodboard for {brand_name}, {industry}, show 5 color palette swatches and lifestyle images",
        "pattern": f"Seamless brand pattern for {brand_name}, {industry}, subtle and modern, tileable"
    }
    
    for name, prompt in prompts.items():
        img_data = generate_image_bytes(prompt)
        if img_data:
            await update.message.reply_photo(
                photo=BytesIO(img_data),
                caption=f"{name.upper()} для бренда {brand_name}"
            )
    
    await update.message.reply_text(f"✅ Бренд-кит для {brand_name} готов!")

# ========== AMAZON LISTING ==========
async def amazon_command(update, context):
    args = " ".join(context.args) if context.args else ""
    if not args:
        await update.message.reply_text(
            "📦 Amazon Product Listing\n\n"
            "Формат: /amazon название | категория | особенности | покупатель\n\n"
            "Пример: /amazon Термокружка | Kitchen & Dining | герметичная крышка, сохраняет тепло | офисные работники"
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
    
    active_amazon_listings[update.effective_user.id] = {
        "product_name": product_name,
        "product_category": product_category,
        "key_features": key_features,
        "target_buyer": target_buyer
    }
    
    features_list = ", ".join([f.strip() for f in key_features.split(",")])
    
    await update.message.reply_text(
        f"✅ Amazon листинг создан!\n\n"
        f"Продукт: {product_name}\n"
        f"Категория: {product_category}\n"
        f"Особенности: {features_list}\n"
        f"Аудитория: {target_buyer}\n\n"
        f"Отправьте /generate_amazon_listing для создания 4 изображений"
    )

async def generate_amazon_listing_command(update, context):
    user_id = update.effective_user.id
    if user_id not in active_amazon_listings:
        await update.message.reply_text("Сначала создайте Amazon листинг: /amazon название | категория | особенности")
        return
    
    data = active_amazon_listings[user_id]
    product_name = data["product_name"]
    product_category = data["product_category"]
    key_features = data["key_features"]
    target_buyer = data["target_buyer"]
    
    features_list = [f.strip() for f in key_features.split(",")]
    features_text = ", ".join(features_list[:3])
    
    await update.message.reply_text(f"📦 Создаю 4 изображения для {product_name}...")
    
    prompts = {
        "hero": f"Professional Amazon main listing hero image of {product_name}. Pure white background, product centered, soft studio lighting, no shadows, commercial product photography",
        "lifestyle": f"Amazon lifestyle image of {product_name} being used by {target_buyer} in natural setting. {product_category} product in real-life context, warm lighting",
        "infographic": f"Amazon product infographic for {product_name}. Shows product with callout arrows highlighting: {features_text}. Clean white background, professional typography",
        "detail": f"Extreme closeup macro product detail shot of {product_name}, focus on premium materials and texture, studio lighting, white background"
    }
    
    # Hero
    img_data = generate_image_bytes(prompts["hero"])
    if img_data:
        await update.message.reply_photo(photo=BytesIO(img_data), caption=f"1/4 HERO IMAGE\n{product_name}\nБелый фон для главного фото Amazon")
    
    # Lifestyle
    img_data = generate_image_bytes(prompts["lifestyle"])
    if img_data:
        await update.message.reply_photo(photo=BytesIO(img_data), caption=f"2/4 LIFESTYLE\n{product_name} в использовании")
    
    # Infographic
    img_data = generate_image_bytes(prompts["infographic"])
    if img_data:
        await update.message.reply_photo(photo=BytesIO(img_data), caption=f"3/4 INFOGRAPHIC\nКлючевые особенности: {features_text}")
    
    # Detail
    img_data = generate_image_bytes(prompts["detail"])
    if img_data:
        await update.message.reply_photo(photo=BytesIO(img_data), caption=f"4/4 DETAIL CLOSEUP\nКачество материалов")
    
    await update.message.reply_text(
        f"✅ Amazon листинг для {product_name} готов!\n\n"
        f"📋 Порядок загрузки на Amazon:\n"
        f"1. Hero image (главное фото)\n"
        f"2. Lifestyle shot\n"
        f"3. Infographic\n"
        f"4. Detail closeup"
    )

# ========== ОБРАБОТЧИК СООБЩЕНИЙ ==========
async def handle_message(update, context):
    text = update.message.text.strip()
    if not text or text.startswith("/"):
        return
    
    lower = text.lower()
    
    if "презентац" in lower:
        topic = re.sub(r'(презентация|создай|про|на тему)', '', lower).strip()
        await create_ppt(update, context, topic or "Презентация")
    else:
        await generate_image(update, context, text)

# ========== ЗАПУСК ==========
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
    print("АЛЕКС АРТ-ДИРЕКТОР - ПОЛНАЯ ВЕРСИЯ")
    print("=" * 60)
    print("✅ Генерация изображений")
    print("✅ Презентации")
    print("✅ Бренд-кит (логотип, мудборд, паттерн)")
    print("✅ Amazon Product Listing (4 изображения)")
    print("=" * 60)
    print("\nДоступные команды:")
    print("  /image кот в космосе")
    print("  /ppt нейросети")
    print("  /brandkit Lumina | tech startup")
    print("  /generate_brand_images")
    print("  /amazon Термокружка | Kitchen & Dining | герметичная | офисные работники")
    print("  /generate_amazon_listing")
    print("\n" + "=" * 60)
    
    app.run_polling()

if __name__ == "__main__":
    main()
