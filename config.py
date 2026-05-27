import os
from dotenv import load_dotenv
load_dotenv()
class Config:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    SD_API_URL = os.getenv("SD_API_URL", "https://image.pollinations.ai/prompt")
    SD_API_KEY = os.getenv("SD_API_KEY", "")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b:free")
    MAX_IMAGE_SIZE = int(os.getenv("MAX_IMAGE_SIZE", 1024))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    @classmethod
    def validate(cls):
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
config = Config()
