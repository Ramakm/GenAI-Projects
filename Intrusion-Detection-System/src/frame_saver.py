"""
frame_saver.py — Save alert frames organized by zone name and date/time.
"""

from __future__ import annotations

import os
from datetime import datetime

import cv2
import numpy as np


class FrameSaver:
    def __init__(self, base_dir: str = "./frames"):
        self._base_dir = base_dir

    def save_frame(self, frame: np.ndarray, zone_name: str) -> str:
        """
        Saves frame to: frames/{zone_name}/{YYYY-MM-DD}/{HH-MM-SS_ms}.jpg
        Returns the absolute file path.
        """
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H-%M-%S_") + f"{now.microsecond // 1000:03d}"

        save_dir = os.path.join(self._base_dir, zone_name, date_str)
        os.makedirs(save_dir, exist_ok=True)

        file_path = os.path.join(save_dir, f"{time_str}.jpg")
        cv2.imwrite(file_path, frame)
        return os.path.abspath(file_path)
