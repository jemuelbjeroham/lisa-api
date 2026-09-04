import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "lisa-api.log"

def configure_logging() -> None:
    LOG_DIR.mkdir(exist_ok=True)

    console_handler = logging.StreamHandler()

    file_handler = RotatingFileHandler(
        filename=LOG_FILE,
        maxBytes=20 * 1024 * 1024,
        backupCount=10,
    )

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    console_handler.setLevel(logging.INFO)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.DEBUG)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logging.getLogger("urllib3").setLevel(logging.WARNING)
