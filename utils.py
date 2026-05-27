import logging
import os
from datetime import datetime
def setup_logging(log_level: str = "INFO"):
    os.makedirs("logs", exist_ok=True)
    os.makedirs("images", exist_ok=True)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f"logs/bot_{datetime.now().strftime('%Y%m%d')}.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    error_handler = logging.FileHandler("logs/errors.log", encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    logging.getLogger().addHandler(error_handler)
