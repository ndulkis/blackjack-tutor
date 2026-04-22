from __future__ import annotations

import logging
import logging.handlers

from util.paths import data_dir


def setup_logging(debug: bool = False) -> None:
    """Configure rotating file handler + console handler under ~/.blackjack_tutor/app.log."""
    level = logging.DEBUG if debug else logging.INFO
    log_path = data_dir() / "app.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        handlers=[file_handler, logging.StreamHandler()],
        force=True,
    )
