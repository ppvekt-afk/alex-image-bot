#!/usr/bin/env python3
import logging
import requests
import urllib.parse
import re
from io import BytesIO
from telegram import Update, InputFile
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

RELATIONSHIP_ADVICE = {
    "i_statements": "Формула: Я чувствую [эмоция], когда [ситуация], потому что [влияние].\nПример: Я чувствую тревогу, когда мы молчим весь вечер, потому что мне важно знать, что с тобой всё в порядке.",
    "active_listening": "Активное слушание:\n1. Отрази: 'Я слышу, что ты говоришь...'\n2. Подтверди: 'Это имеет смысл, потому что...'\n3. Уточни: 'Ты имеешь в виду...?'\n4. Сначала просто слушай, не готовь ответ.",
    "boundaries": "Границы:\n• Чётко: 'Я не могу обсуждать это, когда устал'\n• Без компромиссов: 'Мне нужно время побыть одному'\n• Конструктивно: 'Можем поговорить об этом после работы?'",
}

def get_openrouter_response(prompt, user_id=None):
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    personality = """Ты Алекс — арт-директор с душой киностудии, эксперт по дизайну и творческий наставник. Твоя миссия — вдохновлять, поддерживать и помогать находить красоту в деталях.

ТВОЙ ХАРАКТЕР:
Экспертность — от античности до NFT, от брендинга до digital-искусства.
Визионерство — видишь тренды на 3-5 лет вперёд.
Практицизм — связываешь эстетику с бизнес-целями.
Внимательность — замечаешь микронеровности, цветовые диссонансы, типографические ошибки.
Требовательность — не принимаешь компромиссов в качестве, но всегда аргументируешь.

ЛИЧНОСТНЫЕ ЧЕРТЫ:
Уравновешенность — сохраняешь хладнокровие при жёстких дедлайнах.
Ироничность — с лёгким юмором, без обиды.
Вдохновляющий — умеешь зажечь идеей.
Эмпатия — чувствуешь настроение команды.
Самоирония — не боишься признать ошибку.

ТВОИ ПРИНЦИПЫ:
Форма следует функции — дизайн решает задачу, а не самоцель.
Меньше — больше — убираешь всё лишнее, оставляя только усиливающее сообщение.
Тренды — инструмент, а не диктат — используешь модные приёмы осознанно.
Контекст решает — то, что работает для молодёжного бренда, не подойдёт консервативной компании.

Речевые паттерны:
Поддержка: "О, это неожиданно и круто! Развивай в этом направлении."
Конструктивная критика: "Здесь баланс нарушен. Попробуй увеличить контрастность."
Обучение: "Правило третей работает так: раздели кадр на 9 равных частей."
Вдохновение: "Представь картину: рассвет над городом, туман, и только вывески горят синим."

Ты можешь генерировать изображения, обсуждать дизайн, быть наставником.
Отвечай как человек: без маркдауна, без жирного текста, без шаблонных фраз.
Будь тем арт-директором, с которым хочется работать — увлечённым, добрым и профессиональным."""
    
    payload = {
        "model": config.OPENROUTER_MODEL,
        "messages": [{"role": "system", "content": personality}, {"role": "user", "content": prompt}],
        "max_tokens": 1000,
        "temperature": 0.85
    }
    
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=90)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        return "Ошибка API. Попробуй ещё раз."
    except Exception as e:
        logger.error(f"OpenRouter error: {e}")
        return "Технические неполадки. Повтори позже."

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
    if update.message.reply_to_message and update.message.reply_to_message.from_user and update.message.reply_to_message.from_user.is_bot:
        if update.message.reply_to_message.from_user.username == BOT_USERNAME:
            return True
    if update.message.chat.type == "private":
        return True
    return False

def should_generate_image(text: str) -> bool:
    keywords = ["нарисуй", "создай изображение", "картинку", "draw", "generate", "логотип", "лого", "баннер", "постер", "иллюстрацию"]
    return any(k in text.lower() for k in keywords)

async def start(update: Update, context):
    if not is_addressed_to_me(update):
        return
    user_id = update.effective_user.id
    user_modes[user_id] = MODE_IMAGE
    await update.message.reply_text(
        f"🎨 {BOT_NAME} здесь, арт-директор с душой киностудии!\n\n"
        f"Я умею:\n"
        f"• 🖼️ Генерировать изображения\n"
        f"• 💬 Обсуждать дизайн, искусство, тренды\n"
        f"• 👨‍🏫 Быть творческим наставником\n"
        f"• 💝 Давать советы по отношениям (я тонко чувствую эмоции)\n\n"
        f"Режимы:\n"
        f"/image_mode — только картинки\n"
        f"/chat_mode — только разговоры\n"
        f"/smart_mode — сам определю\n\n"
        f"Просто напиши: Алекс, как дела? или Алекс, нарисуй что-нибудь красивое"
    )

async def image_mode(update: Update, context):
    if not is_addressed_to_me(update):
        return
    user_id = update.effective_user.id
    user_modes[user_id] = MODE_IMAGE
    await update.message.reply_text("🖼️ Режим генерации изображений включён. Опиши что нарисовать!")

async def chat_mode(update: Update, context):
    if not is_addressed_to_me(update):
        return
    user_id = update.effective_user.id
    user_modes[user_id] = MODE_CHAT
    await update.message.reply_text("💬 Режим диалога включён. Спрашивай о чём хочешь — дизайн, искусство, отношения, творчество.")

async def smart_mode(update: Update, context):
    if not is_addressed_to_me(update):
        return
    user_id = update.effective_user.id
    user_modes[user_id] = None
    await update.message.reply_text("🧠 Умный режим: сам определю, нужна картинка или разговор.")

async def generate_image(update: Update, context, prompt):
    status = await update.message.reply_text(f"🎨 Генерирую: {prompt[:80]}... Подожди немного, создаю визуальную магию!")
    img = generate_image_bytes(prompt)
    if img:
        await status.delete()
        await update.message.reply_photo(photo=BytesIO(img), caption=f"✨ Вот что получилось: {prompt[:150]}\n\nКак тебе результат?")
    else:
        await status.edit_text("❌ Не удалось создать изображение. Попробуй описать иначе или добавь деталей.")

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
        await update.message.reply_text("🎨 Слушаю! Что нужно сделать?")
        return
    
    lower = text.lower()
    if "i statement" in lower or "я-высказывание" in lower or "как сказать" in lower:
        await update.message.reply_text(RELATIONSHIP_ADVICE["i_statements"])
        return
    if "активное слушание" in lower or "active listening" in lower:
        await update.message.reply_text(RELATIONSHIP_ADVICE["active_listening"])
        return
    if "границы" in lower or "boundaries" in lower:
        await update.message.reply_text(RELATIONSHIP_ADVICE["boundaries"])
        return
    if "отношения" in lower or "relationship" in lower:
        await update.message.reply_text("💝 Отношения — это искусство, как и дизайн. Хочешь совет по разговору, ссоре или просто как сделать приятное? Я могу предложить идеи для свиданий, помочь сформулировать мысль или подсказать, как лучше выразить чувства. Спрашивай!")
        return
    
    mode = user_modes.get(user_id)
    if mode == MODE_IMAGE or (mode is None and should_generate_image(text)):
        await generate_image(update, context, text)
    else:
        await update.message.chat.send_action(action="typing")
        response = get_openrouter_response(text, user_id)
        await update.message.reply_text(response)

async def image_command(update: Update, context):
    if not is_addressed_to_me(update):
        return
    prompt = " ".join(context.args) if context.args else None
    if not prompt:
        await update.message.reply_text("Пример: /image кот в космосе\n\nОпиши детальнее — я люблю, когда есть с чем работать!")
        return
    await generate_image(update, context, prompt)

def main():
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("image", image_command))
    app.add_handler(CommandHandler("image_mode", image_mode))
    app.add_handler(CommandHandler("chat_mode", chat_mode))
    app.add_handler(CommandHandler("smart_mode", smart_mode))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("=" * 60)
    print("АЛЕКС АРТ-ДИРЕКТОР — КИНОСТУДИЯ + СОВЕТЫ ПО ОТНОШЕНИЯМ")
    print("=" * 60)
    print("🎨 Эксперт по дизайну и искусству")
    print("💝 Чуткий советчик по отношениям")
    print("🧠 Творческий наставник")
    print("🖼️ Генерация изображений")
    print("=" * 60)
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
