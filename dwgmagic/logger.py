"""Logging utilities that honour runtime settings."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from dwgmagic.settings import Settings


@dataclass(slots=True)
class LoggerFactory:
    """Creates loggers scoped to a project run."""

    settings: Settings

    def _log_directory(self) -> Path:
        log_dir = self.settings.project_root / self.settings.log_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    def create(self, name: str) -> logging.Logger:
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, self.settings.log_level))

        log_dir = self._log_directory()
        log_path = log_dir / f"{name}.log"

        if not any(isinstance(handler, logging.FileHandler) and handler.baseFilename == str(log_path) for handler in logger.handlers):
            handler = logging.FileHandler(log_path, encoding=self.settings.log_encoding)
            handler.setLevel(getattr(logging, self.settings.log_level))
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger


__all__ = ["LoggerFactory"]

