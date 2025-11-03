"""Logging utilities that honour runtime settings."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple

from dwgmagic.settings import Settings


@dataclass(slots=True)
class LoggerFactory:
    """Creates loggers scoped to a project run."""

    settings: Settings
    extra_handlers: Tuple[logging.Handler, ...] = field(default_factory=tuple)

    def with_handlers(self, *handlers: logging.Handler) -> "LoggerFactory":
        """Return a new factory that attaches additional handlers."""

        existing = list(self.extra_handlers)
        for handler in handlers:
            if handler not in existing:
                existing.append(handler)
        return LoggerFactory(self.settings, tuple(existing))

    def _log_directory(self) -> Path:
        log_dir = self.settings.project_root / self.settings.log_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    def create(self, name: str) -> logging.Logger:
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, self.settings.log_level))

        log_dir = self._log_directory()
        log_path = log_dir / f"{name}.log"

        if not any(
            isinstance(handler, logging.FileHandler) and handler.baseFilename == str(log_path)
            for handler in logger.handlers
        ):
            handler = logging.FileHandler(log_path, encoding=self.settings.log_encoding)
            handler.setLevel(getattr(logging, self.settings.log_level))
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        for handler in self.extra_handlers:
            if handler not in logger.handlers:
                logger.addHandler(handler)

        logger.propagate = False
        return logger


__all__ = ["LoggerFactory"]

