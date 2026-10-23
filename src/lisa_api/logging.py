import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "lisa-api.log"

def configure_logging() -> None:
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )

    console_handler = logging.StreamHandler()
    handlers: list[logging.Handler] = [console_handler]

    log_file = os.getenv("LISA_LOG_FILE", str(LOG_FILE))
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            filename=log_path,
            maxBytes=20 * 1024 * 1024,
            backupCount=10,
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.DEBUG)

    for handler in handlers:
        root_logger.addHandler(handler)

    logging.getLogger("urllib3").setLevel(logging.WARNING)
