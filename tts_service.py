import logging
import os
from io import BytesIO
from google.cloud import texttospeech

logger = logging.getLogger(__name__)

class TTSService:
    def __init__(self):
        self.client = None
        self._initialized = False
    
    def initialize(self):
        try:
            self.client = texttospeech.TextToSpeechClient()
            self._initialized = True
            logger.info("✅ TTS клиент готов")
        except Exception as e:
            logger.warning(f"TTS недоступен: {e}")
    
    def synthesize_speech(self, text: str) -> bytes:
        if not self._initialized:
            return None
        try:
            synthesis_input = texttospeech.SynthesisInput(text=text[:500])
            voice = texttospeech.VoiceSelectionParams(
                language_code="ru-RU",
                name="ru-RU-Wavenet-D",
                ssml_gender=texttospeech.SsmlVoiceGender.MALE
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.OGG_OPUS,
                speaking_rate=0.95
            )
            
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            return response.audio_content
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None

tts_service = TTSService()
