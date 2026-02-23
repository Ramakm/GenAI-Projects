"""
video_source.py — Abstracts webcam and video file input via cv2.VideoCapture.
"""

from __future__ import annotations

from enum import Enum

import cv2
import numpy as np


class SourceType(Enum):
    WEBCAM = "webcam"
    VIDEO_FILE = "video_file"


class VideoSource:
    def __init__(self, source_type: SourceType, camera_index: int = 0, file_path: str | None = None):
        self.source_type = source_type

        if source_type == SourceType.WEBCAM:
            self._cap = cv2.VideoCapture(camera_index)
        elif source_type == SourceType.VIDEO_FILE:
            if not file_path:
                raise ValueError("file_path must be provided for VIDEO_FILE source")
            self._cap = cv2.VideoCapture(file_path)
        else:
            raise ValueError(f"Unknown source type: {source_type}")

        if not self._cap.isOpened():
            raise RuntimeError(f"Failed to open video source: {source_type.value}")

    def read_frame(self) -> tuple[bool, np.ndarray | None]:
        ret, frame = self._cap.read()
        if not ret:
            return False, None
        return True, frame

    def is_open(self) -> bool:
        return self._cap.isOpened()

    def get_fps(self) -> float:
        fps = self._cap.get(cv2.CAP_PROP_FPS)
        return fps if fps > 0 else 30.0

    def release(self) -> None:
        self._cap.release()
