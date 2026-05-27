import logging
import re
from io import BytesIO
from datetime import datetime
from pathlib import Path
from telegram import Update, InputFile
from telegram.ext import ContextTypes
from image_generator import ImageGenerator
from prompt_enhancer import PromptEnhancer
from memory_manager import MemoryManager
from cache_skill import ImageCache
from poster_skill import MagazinePoster

logger = logging.getLogger(__name__)

STYLES = {"реализм":"","аниме":"","акварель":"","пиксель-арт":"","масло":"","карандаш":"","фэнтези":"","киберпанк":"","космос":"","природа":"","портрет":""}

memory = MemoryManager()
cache = None
poster_maker = MagazinePoster()

async def set_cache(c):
    global cache
    cache = c

async def start(update, context):
    await update.message.reply_text(
        "🎨 *Алекс Арт-директор*\n\n"
        "Я умею:\n"
        "• 🖼️ Генерировать изображения\n"
        "• 📊 Создавать презентации\n"
        "• 📰 Создавать журнальные постеры\n\n"
        "*Команды:*\n"
        "/start - приветствие\n"
        "/help - помощь\n"
        "/poster [тема] - журнальный постер\n"
        "/magazine [тема] - редакционный плакат\n"
        "/image [описание] - сгенерировать картинку\n"
        "/ppt [тема] - презентация\n\n"
        "*Примеры:*\n"
        "• кот в космосе\n"
        "• /poster искусственный интеллект\n"
        "• /magazine дизайн\n"
        "• презентация про ИИ",
        parse_mode="Markdown"
    )

async def help_command(update, context):
    await update.message.reply_text(
        "🆘 *Помощь*\n\n"
        "📰 *Журнальные постеры:*\n"
        "/poster [тема] - создать постер в стиле газеты\n"
        "/magazine [тема] - редакционный плакат\n\n"
        "🖼️ *Изображения:*\n"
        "Напишите любой текст - я сгенерирую картинку\n"
        "/image [описание] - альтернативный способ\n\n"
        "📊 *Презентации:*\n"
        "/ppt [тема] - создать презентацию\n"
        "презентация про [тема]\n\n"
        "✨ *Совет:* Чем подробнее описание, тем лучше результат!",
        parse_mode="Markdown"
    )

async def poster_command(update, context):
    topic = " ".join(context.args) if context.args else "creative work"
    status_msg = await update.message.reply_text(f"📰 Создаю журнальный постер: *{topic[:50]}*...", parse_mode="Markdown")
    
    html_content = poster_maker.create_poster(topic)
    filename = f"poster_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    with open(filename, 'rb') as f:
        await update.message.reply_document(
            document=InputFile(f, filename=filename),
            caption=f"📰 *Editorial Poster*\n\n🎨 Тема: {topic}\n📄 Формат: HTML (откройте в браузере)\n✨ Стиль: Newsprint / Magazine",
            parse_mode="Markdown"
        )
    
    Path(filename).unlink(missing_ok=True)
    await status_msg.delete()

async def generate_image(update, context, prompt):
    from image_generator import ImageGenerator
    from config import config
    image_gen = ImageGenerator(config.SD_API_URL, config.SD_API_KEY)
    
    status_msg = await update.message.reply_text(f"🎨 Генерирую: *{prompt[:80]}*...", parse_mode="Markdown")
    
    img_bytes, error = await image_gen.generate(prompt, None)
    
    if img_bytes:
        await status_msg.delete()
        await update.message.reply_photo(
            photo=InputFile(BytesIO(img_bytes), filename="art.png"),
            caption=f"✅ *Изображение готово*\n📝 Запрос: {prompt[:150]}",
            parse_mode="Markdown"
        )
        return True
    else:
        await status_msg.edit_text(f"❌ *Ошибка:* {error}", parse_mode="Markdown")
        return False

async def create_ppt(update, context, topic):
    status_msg = await update.message.reply_text(f"📊 Создаю презентацию: *{topic[:80]}*...", parse_mode="Markdown")
    
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
<div class="slide"><h1>📊 {topic}</h1><p>Содержание презентации</p></div>
</body>
</html>'''
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    with open(filename, 'rb') as f:
        await update.message.reply_document(document=InputFile(f, filename=filename), caption=f"🎨 *Презентация: {topic}*", parse_mode="Markdown")
    
    Path(filename).unlink(missing_ok=True)
    await status_msg.delete()

async def handle_message(update, context):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if not text:
        return
    
    lower_text = text.lower()
    
    if "magazine" in lower_text or "poster" in lower_text or "газет" in lower_text or "журнальн" in lower_text or "плакат" in lower_text:
        topic = re.sub(r'(magazine|poster|газета|журнал|плакат|создай|сделай|постер)', '', lower_text).strip()
        if not topic or len(topic) < 2:
            topic = "creativity"
        await poster_command(update, context)
    elif "презентац" in lower_text or text.startswith("/ppt"):
        topic = re.sub(r'(презентация|создай|/ppt|про|на тему)', '', lower_text).strip()
        if not topic or len(topic) < 2:
            topic = "Презентация"
        await create_ppt(update, context, topic)
    elif text.startswith("/image"):
        prompt = text[6:].strip()
        if not prompt:
            await update.message.reply_text("❌ Укажите описание после команды /image")
            return
        await generate_image(update, context, prompt)
    else:
        await generate_image(update, context, text)

async def styles_command(update, context):
    await update.message.reply_text("Стили: " + ", ".join(STYLES.keys()))

async def new_command(update, context):
    await update.message.reply_text("Опишите изображение или презентацию")

async def memory_command(update, context):
    await update.message.reply_text("📊 Функция памяти в разработке")

async def forget_command(update, context):
    await update.message.reply_text("🗑️ Данные очищены")

async def history_command(update, context):
    await update.message.reply_text("📖 История пока не сохраняется")

async def stats_command(update, context):
    await update.message.reply_text("📊 Статистика: бот работает")

from campaign_skill import ImageCampaign
campaign = ImageCampaign()
active_campaigns = {}

async def campaign_command(update, context):
    args = " ".join(context.args) if context.args else ""
    
    if not args:
        await update.message.reply_text(
            "📊 *Image Campaign*\n\n"
            "Создайте рекламную кампанию изображений!\n\n"
            "*Формат:*\n"
            "/campaign продукт | аудитория | соотношение | количество\n\n"
            "*Пример:*\n"
            `/campaign кофе | молодые профессионалы | 1:1 | 3`\n\n"
            "*Соотношения:* 1:1, 16:9, 9:16, 4:3\n"
            "*Количество:* 1-5",
            parse_mode="Markdown"
        )
        return
    
    parts = args.split("|")
    if len(parts) < 2:
        await update.message.reply_text("❌ Используйте формат: /campaign продукт | аудитория | соотношение | количество")
        return
    
    product = parts[0].strip()
    audience = parts[1].strip()
    aspect_ratio = parts[2].strip() if len(parts) > 2 else "1:1"
    count = int(parts[3].strip()) if len(parts) > 3 and parts[3].strip().isdigit() else 3
    
    valid_ratios = ["1:1", "16:9", "9:16", "4:3"]
    if aspect_ratio not in valid_ratios:
        aspect_ratio = "1:1"
    
    if count < 1:
        count = 1
    if count > 5:
        count = 5
    
    status_msg = await update.message.reply_text("📊 Создаю бриф кампании...")
    
    brief = campaign.create_brief(product, audience, aspect_ratio, count)
    prompts = campaign.generate_prompts(brief)
    campaign_file = campaign.save_campaign(brief, prompts)
    
    active_campaigns[update.effective_user.id] = {
        "brief": brief,
        "prompts": prompts,
        "file": campaign_file
    }
    
    output = campaign.format_output(brief, prompts)
    await status_msg.edit_text(output, parse_mode="Markdown")

async def generate_campaign_command(update, context):
    user_id = update.effective_user.id
    
    if user_id not in active_campaigns:
        await update.message.reply_text("❌ Сначала создайте кампанию: /campaign продукт | аудитория")
        return
    
    campaign_data = active_campaigns[user_id]
    prompts = campaign_data["prompts"]
    brief = campaign_data["brief"]
    
    status_msg = await update.message.reply_text(f"🎨 Генерирую {len(prompts)} изображений для кампании...")
    
    from image_generator import ImageGenerator
    from config import config
    image_gen = ImageGenerator(config.SD_API_URL, config.SD_API_KEY)
    
    generated = []
    failed = []
    
    for i, p in enumerate(prompts, 1):
        await status_msg.edit_text(f"🎨 Генерация {i}/{len(prompts)}: {p['name']}...")
        
        img_bytes, error = await image_gen.generate(p["prompt"], None)
        
        if img_bytes:
            from io import BytesIO
            from telegram import InputFile
            filename = f"campaign_{p['name'].replace(' ', '_')}.png"
            await update.message.reply_photo(
                photo=InputFile(BytesIO(img_bytes), filename=filename),
                caption=f"*{p['name']}*\n{p['prompt'][:80]}...\n🎨 Стиль: {p['style']}",
                parse_mode="Markdown"
            )
            generated.append(p["name"])
        else:
            failed.append(p["name"])
    
    await status_msg.delete()
    
    summary = f"✅ *Кампания завершена!*\n\n"
    summary += f"📦 Продукт: {brief['product']}\n"
    summary += f"👥 Аудитория: {brief['audience']}\n"
    summary += f"✅ Успешно: {len(generated)}\n"
    if failed:
        summary += f"❌ Не удалось: {', '.join(failed)}\n"
    
    await update.message.reply_text(summary, parse_mode="Markdown")

from brand_kit_skill import BrandKitGenerator
brand_kit_gen = BrandKitGenerator()
active_brand_kits = {}

async def brandkit_command(update, context):
    args = " ".join(context.args) if context.args else ""
    
    if not args:
        await update.message.reply_text(
            "🎨 *Brand Kit Generator*\n\n"
            "Создайте полный бренд-кит!\n\n"
            "*Формат:*\n"
            "/brandkit название | индустрия | характер | цветовые предпочтения\n\n"
            "*Пример:*\n"
            "/brandkit Эко-кофе | кофейня | natural, organic, warm | earthy greens\n\n"
            "*Характер (3-5 слов):*\n"
            "luxury, elegant, modern, tech, natural, bold, youthful, minimal",
            parse_mode="Markdown"
        )
        return
    
    parts = [p.strip() for p in args.split("|")]
    if len(parts) < 2:
        await update.message.reply_text("❌ Используйте: название | индустрия | характер | цветовое предпочтение")
        return
    
    brand_name = parts[0]
    industry = parts[1]
    personality = parts[2] if len(parts) > 2 else "modern, trustworthy, approachable"
    color_preference = parts[3] if len(parts) > 3 else ""
    
    status_msg = await update.message.reply_text(f"🎨 Создаю бренд-кит для {brand_name}...")
    
    brand_kit = brand_kit_gen.create_brand_kit(brand_name, industry, personality, color_preference)
    logo_prompts = brand_kit_gen.generate_logo_prompts(brand_name, industry, personality, color_preference)
    moodboard_prompt = brand_kit_gen.generate_moodboard_prompt(brand_name, industry, personality, color_preference)
    pattern_prompt = brand_kit_gen.generate_pattern_prompt(brand_name, industry, personality, color_preference)
    
    kit_file = brand_kit_gen.save_brand_kit(brand_kit, logo_prompts, moodboard_prompt, pattern_prompt)
    
    active_brand_kits[update.effective_user.id] = {
        "brand_kit": brand_kit,
        "logo_prompts": logo_prompts,
        "moodboard_prompt": moodboard_prompt,
        "pattern_prompt": pattern_prompt,
        "file": kit_file
    }
    
    output = brand_kit_gen.format_output(brand_kit, logo_prompts, moodboard_prompt, pattern_prompt)
    await status_msg.edit_text(output, parse_mode="Markdown")

async def generate_brand_images_command(update, context):
    user_id = update.effective_user.id
    
    if user_id not in active_brand_kits:
        await update.message.reply_text("❌ Сначала создайте бренд-кит: /brandkit название | индустрия | характер")
        return
    
    data = active_brand_kits[user_id]
    brand_kit = data["brand_kit"]
    logo_prompts = data["logo_prompts"]
    moodboard_prompt = data["moodboard_prompt"]
    pattern_prompt = data["pattern_prompt"]
    
    await update.message.reply_text(
        f"🎨 *Генерация визуальных assets для {brand_kit['brand_name']}*\n\n"
        f"Создаю 4 элемента:\n"
        f"1. Логотип A (словесный)\n"
        f"2. Логотип B (иконка + слово)\n"
        f"3. Мудборд с палитрой\n"
        f"4. Паттерн/текстура\n\n"
        f"🔄 Генерация началась...",
        parse_mode="Markdown"
    )
    
    from image_generator import ImageGenerator
    from config import config
    image_gen = ImageGenerator(config.SD_API_URL, config.SD_API_KEY)
    
    assets = []
    
    for name, prompt in logo_prompts.items():
        status_msg = await update.message.reply_text(f"🎨 Генерирую {name}...")
        img_bytes, error = await image_gen.generate(prompt, None)
        if img_bytes:
            filename = f"{brand_kit['brand_name'].replace(' ', '_')}_{name}.png"
            await update.message.reply_photo(
                photo=InputFile(BytesIO(img_bytes), filename=filename),
                caption=f"*{name.upper()}* для {brand_kit['brand_name']}\n{prompt[:100]}...",
                parse_mode="Markdown"
            )
            assets.append(name)
        await status_msg.delete()
    
    status_msg = await update.message.reply_text("🎨 Генерирую мудборд...")
    img_bytes, error = await image_gen.generate(moodboard_prompt, None)
    if img_bytes:
        await update.message.reply_photo(
            photo=InputFile(BytesIO(img_bytes), filename=f"{brand_kit['brand_name'].replace(' ', '_')}_moodboard.png"),
            caption=f"*Moodboard* для {brand_kit['brand_name']}\nЦветовая палитра и вдохновение",
            parse_mode="Markdown"
        )
        assets.append("moodboard")
    await status_msg.delete()
    
    status_msg = await update.message.reply_text("🎨 Генерирую паттерн...")
    img_bytes, error = await image_gen.generate(pattern_prompt, None)
    if img_bytes:
        await update.message.reply_photo(
            photo=InputFile(BytesIO(img_bytes), filename=f"{brand_kit['brand_name'].replace(' ', '_')}_pattern.png"),
            caption=f"*Pattern* для {brand_kit['brand_name']}\nФирменный орнамент",
            parse_mode="Markdown"
        )
        assets.append("pattern")
    await status_msg.delete()
    
    colors = brand_kit_gen.get_color_palette(brand_kit["personality"])
    typography = brand_kit_gen.get_typography_pairing(brand_kit["personality"])
    
    summary = f"✅ *Бренд-кит {brand_kit['brand_name']} завершён!*\n\n"
    summary += f"🎨 *Цветовая палитра:*\n"
    for role, hex_code in colors.items():
        summary += f"• {role}: `{hex_code}`\n"
    summary += f"\n📝 *Шрифты:* {typography['heading']} + {typography['body']}\n"
    summary += f"\n✨ Сгенерировано: {', '.join(assets)}"
    
    await update.message.reply_text(summary, parse_mode="Markdown")

from amazon_skill import AmazonListingGenerator
amazon_gen = AmazonListingGenerator()
active_amazon_listings = {}

async def amazon_command(update, context):
    args = " ".join(context.args) if context.args else ""
    
    if not args:
        await update.message.reply_text(
            "📦 Amazon Product Listing\n\n"
            "Создайте полный набор изображений для Amazon!\n\n"
            "Формат:\n"
            "/amazon название | категория | особенности | покупатель\n\n"
            "Пример:\n"
            "/amazon Термокружка 500мл | Kitchen & Dining | герметичная крышка, сохраняет тепло 12ч, BPA-free | офисные работники\n\n"
            "Затем /generate_amazon_listing - создать 4 изображения"
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
    
    listing_file = amazon_gen.save_listing(listing, prompts)
    
    active_amazon_listings[update.effective_user.id] = {
        "listing": listing,
        "prompts": prompts,
        "file": listing_file
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
    
    await update.message.reply_text(
        f"📦 Создаю 4 изображения для {listing['product_name']}...\n\n"
        f"🖼️ 1/4 Hero image (белый фон)\n"
        f"🖼️ 2/4 Lifestyle shot\n"
        f"🖼️ 3/4 Feature infographic\n"
        f"🖼️ 4/4 Closeup detail\n\n"
        f"🔄 Генерация началась..."
    )
    
    from image_generator import ImageGenerator
    from config import config
    image_gen = ImageGenerator(config.SD_API_URL, config.SD_API_KEY)
    
    # Hero image
    img_bytes, error = await image_gen.generate(prompts["hero"], None)
    if img_bytes:
        await update.message.reply_photo(
            photo=InputFile(BytesIO(img_bytes), filename="amazon_hero.png"),
            caption=f"📷 HERO IMAGE\n{listing['product_name']}\nЧистый белый фон для главного фото Amazon"
        )
    
    # Lifestyle
    img_bytes, error = await image_gen.generate(prompts["lifestyle"], None)
    if img_bytes:
        await update.message.reply_photo(
            photo=InputFile(BytesIO(img_bytes), filename="amazon_lifestyle.png"),
            caption=f"🏠 LIFESTYLE\n{listing['product_name']} в использовании\nАудитория: {listing['target_buyer']}"
        )
    
    # Infographic
    img_bytes, error = await image_gen.generate(prompts["infographic"], None)
    if img_bytes:
        features_text = ", ".join(listing["key_features"][:3])
        await update.message.reply_photo(
            photo=InputFile(BytesIO(img_bytes), filename="amazon_infographic.png"),
            caption=f"📊 INFOGRAPHIC\nКлючевые особенности: {features_text}"
        )
    
    # Detail
    img_bytes, error = await image_gen.generate(prompts["detail"], None)
    if img_bytes:
        await update.message.reply_photo(
            photo=InputFile(BytesIO(img_bytes), filename="amazon_detail.png"),
            caption=f"🔍 CLOSEUP DETAIL\nКачество материалов и текстура"
        )
    
    await update.message.reply_text(
        f"✅ Amazon листинг для {listing['product_name']} готов!\n\n"
        f"📋 Рекомендации:\n"
        f"• Hero image - главное фото Amazon (требует белый фон)\n"
        f"• Lifestyle - показывает продукт в использовании\n"
        f"• Infographic - преимущества с подписями\n"
        f"• Detail - качество материалов крупным планом\n\n"
        f"💡 Загрузите в порядке: hero -> lifestyle -> infographic -> detail"
    )
