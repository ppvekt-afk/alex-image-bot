import logging
import os
import re
import tempfile
from telegram import Update, Voice
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Инициализация модели SpeechBrain
asr_model = None

def init_asr():
    global asr_model
    try:
        from speechbrain.inference.ASR import EncoderDecoderASR
        asr_model = EncoderDecoderASR.from_hparams(
            source="speechbrain/asr-crdnn-rnnlm-librispeech",
            savedir="pretrained_models/asr",
            run_opts={"device": "cpu"}
        )
        logger.info("ASR model loaded")
    except Exception as e:
        logger.warning(f"ASR not available: {e}")

async def download_voice(bot, file_id: str) -> str:
    try:
        file = await bot.get_file(file_id)
        voice_path = tempfile.gettempdir() + f"/voice_{file_id}.ogg"
        await file.download_to_drive(voice_path)
        return voice_path
    except Exception as e:
        logger.error(f"Download error: {e}")
        return None

async def transcribe_voice(file_path: str) -> str:
    global asr_model
    if not asr_model:
        return None
    try:
        transcript = asr_model.transcribe_file(file_path)
        return transcript.strip()
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return None

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not asr_model:
        await update.message.reply_text("🎤 Голосовые сообщения временно недоступны.")
        return
    
    status_msg = await update.message.reply_text("🎤 Распознаю голос...")
    
    voice: Voice = update.message.voice
    voice_path = await download_voice(context.bot, voice.file_id)
    
    if not voice_path:
        await status_msg.edit_text("❌ Не удалось загрузить голосовое сообщение.")
        return
    
    transcript = await transcribe_voice(voice_path)
    
    if transcript:
        await status_msg.edit_text(f"📝 Распознано: {transcript}\n\n💬 Отвечаю...")
        
        from config import config
        import requests
        
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
                await status_msg.edit_text(f"📝 Распознано: {transcript}\n\n🧠 {ai_response}")
            else:
                await status_msg.edit_text(f"📝 Распознано: {transcript}\n\nИзвини, ошибка API.")
        except Exception as e:
            logger.error(f"OpenRouter error: {e}")
            await status_msg.edit_text(f"📝 Распознано: {transcript}\n\nИзвини, ошибка связи.")
        
        os.unlink(voice_path)
    else:
        await status_msg.edit_text("❌ Не удалось распознать речь. Попробуйте говорить чётче.")

init_asr()
