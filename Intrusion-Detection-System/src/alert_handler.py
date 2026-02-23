"""
alert_handler.py — Cooldown-aware alert orchestration (email + desktop).
"""

from __future__ import annotations

import logging
import time

import numpy as np

from config import AlertConfig, SMTPConfig
from src.email_alert import EmailAlert
from src.desktop_notification import DesktopNotification
from src.frame_saver import FrameSaver

logger = logging.getLogger(__name__)


class AlertCooldown:
    def __init__(self, cooldown_seconds: int):
        self._cooldown = cooldown_seconds
        self._last_alert: dict[str, float] = {}

    def is_cooldown_active(self, zone_name: str) -> bool:
        last = self._last_alert.get(zone_name, 0.0)
        return (time.monotonic() - last) < self._cooldown

    def reset_cooldown(self, zone_name: str) -> None:
        self._last_alert[zone_name] = time.monotonic()


class AlertHandler:
    def __init__(self, smtp_config: SMTPConfig, alert_config: AlertConfig):
        self._alert_cfg = alert_config
        self._cooldown = AlertCooldown(alert_config.cooldown_seconds)
        self._frame_saver = FrameSaver()

        self._email = EmailAlert(smtp_config) if alert_config.email_enabled else None
        self._desktop = DesktopNotification() if alert_config.desktop_enabled else None

    def trigger_intrusion_alert(
        self,
        zone_name: str,
        person_count: int,
        frame: np.ndarray,
    ) -> bool:
        """
        Checks cooldown, saves frame, then dispatches email + desktop alerts.
        Returns True if alert was actually sent (not suppressed by cooldown).
        """
        if self._cooldown.is_cooldown_active(zone_name):
            logger.debug("Cooldown active for zone '%s' — alert suppressed.", zone_name)
            return False

        # Save frame first so we can attach it to the email
        frame_path = self._frame_saver.save_frame(frame, zone_name)
        logger.info("Intrusion frame saved: %s", frame_path)

        subject = f"[IDS ALERT] Intrusion in {zone_name}"
        body = (
            f"Intrusion detected in restricted zone: {zone_name}\n"
            f"Person count: {person_count}\n"
            f"Captured frame: {frame_path}"
        )

        if self._email:
            self._email.send_alert(subject, body, image_path=frame_path)

        if self._desktop:
            self._desktop.notify(
                title=subject,
                message=f"{person_count} person(s) detected in {zone_name}",
            )

        self._cooldown.reset_cooldown(zone_name)
        return True
