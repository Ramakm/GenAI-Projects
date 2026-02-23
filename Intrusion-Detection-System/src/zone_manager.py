"""
zone_manager.py — Polygon zone definitions and intrusion checking.
"""

from __future__ import annotations

import cv2
import numpy as np

from src.yolo_detector import Detection


class PolygonZone:
    def __init__(self, points: np.ndarray, name: str):
        self.points = points.reshape((-1, 1, 2)).astype(np.int32)
        self.name = name

    def is_point_inside(self, point: tuple[int, int]) -> bool:
        result = cv2.pointPolygonTest(self.points, (float(point[0]), float(point[1])), measureDist=False)
        return result >= 0

    def is_center_bottom_inside(self, detection: Detection) -> bool:
        return self.is_point_inside(detection.center_bottom)

    def draw_zone(self, frame: np.ndarray, color: tuple[int, int, int] = (0, 255, 0), thickness: int = 2) -> None:
        cv2.polylines(frame, [self.points], isClosed=True, color=color, thickness=thickness)
        # Label at top-left of zone bounding rect
        x, y, w, h = cv2.boundingRect(self.points)
        cv2.putText(frame, self.name, (x, y - 8 if y > 20 else y + 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Semi-transparent fill
        overlay = frame.copy()
        cv2.fillPoly(overlay, [self.points], color)
        cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)


class ZoneManager:
    def __init__(self):
        self._zones: list[PolygonZone] = []

    def add_zone(self, points: np.ndarray, name: str | None = None) -> PolygonZone:
        zone_name = name or f"Zone-{len(self._zones) + 1}"
        zone = PolygonZone(points, zone_name)
        self._zones.append(zone)
        return zone

    @property
    def zones(self) -> list[PolygonZone]:
        return self._zones

    def check_intrusion(self, detection: Detection) -> list[str]:
        """Returns list of zone names where this detection's feet fall inside."""
        return [zone.name for zone in self._zones if zone.is_center_bottom_inside(detection)]
