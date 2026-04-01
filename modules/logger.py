"""
Sistema de logging centralizado para Inna.
Escribe simultáneamente a consola y a data/inna.log.
"""
import logging
import sys
from pathlib import Path

Path("data").mkdir(exist_ok=True)

_fmt = logging.Formatter(
    fmt="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

_file_handler = logging.FileHandler("data/inna.log", encoding="utf-8")
_file_handler.setFormatter(_fmt)
_file_handler.setLevel(logging.DEBUG)

_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setFormatter(_fmt)
_console_handler.setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """
    Retorna un logger configurado con handlers de archivo y consola.

    Uso:
        from modules.logger import get_logger
        log = get_logger(__name__)
        log.info("Mensaje")
        log.error("Error: %s", e)
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        logger.addHandler(_file_handler)
        logger.addHandler(_console_handler)
        logger.propagate = False
    return logger
