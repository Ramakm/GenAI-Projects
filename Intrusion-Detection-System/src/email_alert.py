"""
email_alert.py — SMTP email alerts with optional image attachment.
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import SMTPConfig

logger = logging.getLogger(__name__)


class EmailAlert:
    def __init__(self, smtp_config: SMTPConfig):
        self._cfg = smtp_config

    def send_alert(self, subject: str, message: str, image_path: str | None = None) -> bool:
        if not self._cfg.user or not self._cfg.password:
            logger.warning("SMTP credentials not configured — skipping email alert.")
            return False

        try:
            msg = MIMEMultipart()
            msg["From"] = self._cfg.user
            msg["To"] = self._cfg.recipient
            msg["Subject"] = subject

            msg.attach(MIMEText(message, "plain"))

            if image_path:
                with open(image_path, "rb") as img_file:
                    img_data = img_file.read()
                image = MIMEImage(img_data, name="alert_frame.jpg")
                image.add_header("Content-Disposition", "attachment", filename="alert_frame.jpg")
                msg.attach(image)

            with smtplib.SMTP(self._cfg.host, self._cfg.port) as server:
                server.ehlo()
                server.starttls()
                server.login(self._cfg.user, self._cfg.password)
                server.sendmail(self._cfg.user, self._cfg.recipient, msg.as_string())

            logger.info("Email alert sent to %s", self._cfg.recipient)
            return True

        except Exception as exc:
            logger.error("Failed to send email alert: %s", exc)
            return False
