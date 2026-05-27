import os
import tempfile
import asyncio
import logging
from pathlib import Path
from io import BytesIO
import aiohttp

logger = logging.getLogger(__name__)

class VoiceProcessor:
    def __init__(self):
        self.asr_model = None
        self.tts_client = None
        self._initialized = False
    
    async def initialize(self):
        try:
            import torch
            from speechbrain.inference.ASR import EncoderDecoderASR
            self.asr_model = EncoderDecoderASR.from_hparams(
                source="speechbrain/asr-crdnn-rnnlm-librispeech",
                savedir="pretrained_models/asr",
                run_opts={"device": "cpu"}
            )
            logger.info("✅ ASR модель загружена")
        except Exception as e:
            logger.warning(f"ASR модель не загружена: {e}")
        
        self._initialized = True
    
    async def transcribe_voice(self, voice_file_path: str) -> str:
        if not self.asr_model:
            return None
        try:
            transcript = self.asr_model.transcribe_file(voice_file_path)
            return transcript.strip()
        except Exception as e:
            logger.error(f"Ошибка распознавания: {e}")
            return None
    
    async def download_voice_file(self, bot, file_id: str) -> str:
        try:
            file = await bot.get_file(file_id)
            temp_dir = tempfile.gettempdir()
            voice_path = Path(temp_dir) / f"voice_{file_id}.ogg"
            await file.download_to_drive(voice_path)
            return str(voice_path)
        except Exception as e:
            logger.error(f"Ошибка скачивания: {e}")
            return None
    
    async def text_to_speech(self, text: str, output_path: str = None) -> bytes:
        try:
            import torch
            from speechbrain.inference.TTS import Tacotron2
            from speechbrain.inference.vocoders import HIFIGAN
            
            tts_model = Tacotron2.from_hparams(
                source="speechbrain/tts-tacotron2-ljspeech",
                savedir="pretrained_models/tts"
            )
            vocoder = HIFIGAN.from_hparams(
                source="speechbrain/tts-hifigan-ljspeech",
                savedir="pretrained_models/vocoder"
            )
            
            mel_output, mel_length, alignment = tts_model.encode_text(text)
            waveforms = vocoder.decode_batch(mel_output)
            
            import torchaudio
            if output_path:
                torchaudio.save(output_path, waveforms.squeeze(1), 22050)
            
            from io import BytesIO
            buffer = BytesIO()
            torchaudio.save(buffer, waveforms.squeeze(1), 22050, format="wav")
            return buffer.getvalue()
        except Exception as e:
            logger.error(f"TTS ошибка: {e}")
            return None
    
    def is_available(self) -> bool:
        return self.asr_model is not None

voice_processor = VoiceProcessor()
