import logging
from logging.handlers import RotatingFileHandler
from utils.config_manager import DATA_DIR

def setup_logging():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(DATA_DIR / "application.log", maxBytes=2000000, backupCount=3, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[handler], format="%(asctime)s %(levelname)s %(message)s")
