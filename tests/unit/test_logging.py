import logging

from lisa_api.logging import configure_logging


def test_configure_logging_create_log_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    configure_logging()

    logger = logging.getLogger("test_logger")
    logger.info("Test log message")

    log_file = tmp_path / "logs" / "lisa-api.log"

    assert log_file.exists()
    assert "Test log message" in log_file.read_text()