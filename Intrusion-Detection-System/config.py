"""
config.py — Load environment variables and expose typed configuration dataclasses.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class SMTPConfig:
    host: str
    port: int
    user: str
    password: str
    recipient: str


@dataclass
class CameraConfig:
    index: int
    video_file_path: str | None


@dataclass
class YOLOConfig:
    model_name: str
    confidence: float


@dataclass
class AlertConfig:
    cooldown_seconds: int
    email_enabled: bool
    desktop_enabled: bool


@dataclass
class SystemConfig:
    smtp: SMTPConfig
    camera: CameraConfig
    yolo: YOLOConfig
    alert: AlertConfig
    log_level: str


class ConfigManager:
    @staticmethod
    def load_from_env() -> SystemConfig:
        smtp = SMTPConfig(
            host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
            port=int(os.getenv("SMTP_PORT", "587")),
            user=os.getenv("SMTP_USER", ""),
            password=os.getenv("SMTP_PASSWORD", ""),
            recipient=os.getenv("ALERT_EMAIL_TO", ""),
        )

        camera = CameraConfig(
            index=int(os.getenv("CAMERA_INDEX", "0")),
            video_file_path=os.getenv("VIDEO_FILE_PATH", None),
        )

        yolo = YOLOConfig(
            model_name=os.getenv("YOLO_MODEL", "yolo11n"),
            confidence=float(os.getenv("YOLO_CONFIDENCE", "0.5")),
        )

        alert = AlertConfig(
            cooldown_seconds=int(os.getenv("ALERT_COOLDOWN_SECONDS", "30")),
            email_enabled=os.getenv("EMAIL_ALERTS_ENABLED", "true").lower() == "true",
            desktop_enabled=os.getenv("DESKTOP_ALERTS_ENABLED", "true").lower() == "true",
        )

        return SystemConfig(
            smtp=smtp,
            camera=camera,
            yolo=yolo,
            alert=alert,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
