"""
desktop_notification.py — Cross-platform desktop notifications via plyer.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class DesktopNotification:
    def __init__(self):
        self._available = True
        try:
            from plyer import notification as _n
            self._notifier = _n
        except ImportError:
            logger.warning("plyer not installed — desktop notifications disabled.")
            self._available = False

    def notify(self, title: str, message: str, timeout: int = 10) -> bool:
        if not self._available:
            return False
        try:
            self._notifier.notify(
                title=title,
                message=message,
                app_name="Intrusion Detection System",
                timeout=timeout,
            )
            return True
        except Exception as exc:
            logger.error("Desktop notification failed: %s", exc)
            return False
