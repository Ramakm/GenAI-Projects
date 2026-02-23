"""
yolo_detector.py — YOLOv11 wrapper for person detection.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from ultralytics import YOLO

PERSON_CLASS_ID = 0


@dataclass
class Detection:
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float
    class_id: int

    @property
    def centroid(self) -> tuple[int, int]:
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    @property
    def center_bottom(self) -> tuple[int, int]:
        """Bottom-center of bounding box — closest to ground plane."""
        return ((self.x1 + self.x2) // 2, self.y2)


class YOLODetector:
    def __init__(self, model_name: str = "yolo11n", confidence: float = 0.5):
        self.confidence = confidence
        self._model = YOLO(f"{model_name}.pt")

    def detect_persons(self, frame: np.ndarray) -> list[Detection]:
        results = self._model(frame, conf=self.confidence, classes=[PERSON_CLASS_ID], verbose=False)
        detections: list[Detection] = []

        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                cls_id = int(box.cls[0])
                if cls_id != PERSON_CLASS_ID:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                detections.append(Detection(x1=x1, y1=y1, x2=x2, y2=y2, confidence=conf, class_id=cls_id))

        return detections

    def draw_detections(self, frame: np.ndarray, detections: list[Detection]) -> np.ndarray:
        for det in detections:
            cv2.rectangle(frame, (det.x1, det.y1), (det.x2, det.y2), (0, 255, 0), 2)
            label = f"Person {det.confidence:.2f}"
            label_y = det.y1 - 8 if det.y1 - 8 > 8 else det.y1 + 18
            cv2.putText(frame, label, (det.x1, label_y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
            cx, cy = det.center_bottom
            cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)
        return frame
