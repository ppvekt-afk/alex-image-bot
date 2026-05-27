import logging
import os
from aiogram import Router, F
from aiogram.types import Message, Voice, FSInputFile
from aiogram.enums import ChatAction

from app.voice_processor import voice_processor

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.voice)
async def handle_voice_message(message: Message):
    user_id = message.from_user.id
    user_text = message.caption or ""
    
    if not voice_processor.is_available():
        await message.answer(
            "🎤 Голосовые сообщения временно недоступны.\nПожалуйста, напишите текстом."
        )
        return
    
    status_msg = await message.answer("🎤 Распознаю голосовое сообщение...")
    
    voice: Voice = message.voice
    voice_path = await voice_processor.download_voice_file(message.bot, voice.file_id)
    
    if not voice_path:
        await status_msg.edit_text("❌ Не удалось загрузить голосовое сообщение.")
        return
    
    transcript = await voice_processor.transcribe_voice(voice_path)
    
    if transcript:
        await status_msg.edit_text(f"📝 Распознанный текст:\n{transcript}\n\n💬 Обрабатываю...")
        
        from config import config
        import requests
        import re
        
        headers = {
            "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        personality = """Ты Алекс — арт-директор. Отвечай как человек: коротко, по делу, с душой."""
        
        payload = {
            "model": config.OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": personality},
                {"role": "user", "content": transcript}
            ],
            "max_tokens": 500,
            "temperature": 0.7
        }
        
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            if response.status_code == 200:
                ai_response = response.json()["choices"][0]["message"]["content"]
                ai_response = re.sub(r'\*\*(.+?)\*\*', r'\1', ai_response)
                await status_msg.edit_text(f"📝 Распознано: {transcript}\n\n🧠 Ответ: {ai_response}")
            else:
                await status_msg.edit_text(f"📝 Распознано: {transcript}\n\nИзвини, не могу ответить.")
        except Exception as e:
            logger.error(f"OpenRouter error: {e}")
            await status_msg.edit_text(f"📝 Распознано: {transcript}\n\nИзвини, ошибка связи.")
        
        os.unlink(voice_path)
    else:
        await status_msg.edit_text("❌ Не удалось распознать речь. Попробуйте говорить чётче.")
    
    await message.bot.send_chat_action(message.chat.id, ChatAction.CANCEL)

@router.message(F.text & (F.text.lower().contains("озвучь") | F.text.lower().contains("скажи")))
async def handle_text_to_speech(message: Message):
    text = message.text
    text = re.sub(r'(озвучь|скажи|прочитай|озвучка)', '', text, flags=re.IGNORECASE).strip()
    
    if not text:
        await message.answer("Что озвучить? Напиши текст после команды.")
        return
    
    status_msg = await message.answer("🎵 Озвучиваю текст...")
    
    audio_data = await voice_processor.text_to_speech(text)
    
    if audio_data:
        from io import BytesIO
        audio_file = BytesIO(audio_data)
        audio_file.name = "speech.wav"
        await message.reply_voice(voice=audio_file)
        await status_msg.delete()
    else:
        await status_msg.edit_text("❌ Не удалось озвучить текст.")
cd ~/alex_art_bot && cat > voice_handlers.py << 'EOF'
import logging
import os
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from voice_processor import voice_processor

async def handle_voice_message(update: Update, context):
    user_id = update.effective_user.id
    
    if not voice_processor.is_available():
        await update.message.reply_text("🎤 Голосовые сообщения временно недоступны.")
        return
    
    status_msg = await update.message.reply_text("🎤 Распознаю голос...")
    
    voice_path = await voice_processor.download_voice_file(context.bot, update.message.voice.file_id)
    
    if not voice_path:
        await status_msg.edit_text("❌ Не удалось загрузить.")
        return
    
    transcript = await voice_processor.transcribe_voice(voice_path)
    
    if transcript:
        import requests
        from config import config
        
        headers = {"Authorization": f"Bearer {config.OPENROUTER_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": config.OPENROUTER_MODEL, "messages": [{"role": "user", "content": transcript}], "max_tokens": 500}
        
        try:
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                ai_response = response.json()["choices"][0]["message"]["content"]
                ai_response = re.sub(r'\*\*(.+?)\*\*', r'\1', ai_response)
                await status_msg.edit_text(f"📝 Распознано: {transcript}\n\n🧠 {ai_response}")
            else:
                await status_msg.edit_text(f"📝 Распознано: {transcript}\n\nИзвини, ошибка.")
        except Exception as e:
            await status_msg.edit_text(f"📝 Распознано: {transcript}\n\nОшибка связи.")
        
        os.unlink(voice_path)
    else:
        await status_msg.edit_text("❌ Не удалось распознать речь.")
