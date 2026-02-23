"""
pipeline.py — Main detection loop: reads frames, runs YOLO, checks zones, fires alerts.
"""

from __future__ import annotations

import logging

import cv2
import numpy as np

from src.video_source import VideoSource
from src.yolo_detector import YOLODetector, Detection
from src.zone_manager import ZoneManager
from src.alert_handler import AlertHandler

logger = logging.getLogger(__name__)

# Zone colours
COLOR_CLEAR = (0, 220, 0)       # green — no intrusion
COLOR_INTRUDED = (0, 0, 220)    # red — intrusion active


class IntrusionDetectionPipeline:
    def __init__(
        self,
        video_source: VideoSource,
        detector: YOLODetector,
        zone_manager: ZoneManager,
        alert_handler: AlertHandler,
    ):
        self._source = video_source
        self._detector = detector
        self._zones = zone_manager
        self._alerts = alert_handler
        self._frame_count = 0

    def process_frame(self, frame: np.ndarray) -> dict:
        """
        Runs detection + zone check + alert on a single frame.
        Returns a result dict with detections and intruded zones.
        """
        detections: list[Detection] = self._detector.detect_persons(frame)
        intruded_zones: set[str] = set()

        for det in detections:
            violated = self._zones.check_intrusion(det)
            intruded_zones.update(violated)

        # Fire alerts per intruded zone
        for zone_name in intruded_zones:
            person_count = len(detections)
            self._alerts.trigger_intrusion_alert(zone_name, person_count, frame)

        return {
            "detections": detections,
            "intruded_zones": intruded_zones,
            "person_count": len(detections),
        }

    def _annotate_frame(self, frame: np.ndarray, result: dict) -> np.ndarray:
        display = frame.copy()

        # Draw zones with colour indicating state
        intruded = result["intruded_zones"]
        for zone in self._zones.zones:
            color = COLOR_INTRUDED if zone.name in intruded else COLOR_CLEAR
            zone.draw_zone(display, color)

        # Draw person bounding boxes
        self._detector.draw_detections(display, result["detections"])

        # HUD overlay
        hud_lines = [
            f"Frame: {self._frame_count}",
            f"Persons: {result['person_count']}",
            f"Zones active: {len(self._zones.zones)}",
        ]
        if intruded:
            hud_lines.append(f"INTRUSION: {', '.join(sorted(intruded))}")

        for i, line in enumerate(hud_lines):
            color = (0, 0, 255) if "INTRUSION" in line else (255, 255, 255)
            cv2.putText(display, line, (10, 28 + i * 26),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

        return display

    def run(self, show_video: bool = True) -> None:
        logger.info("Pipeline started. Press 'q' to quit.")

        try:
            while self._source.is_open():
                ok, frame = self._source.read_frame()
                if not ok or frame is None:
                    logger.info("End of video stream.")
                    break

                self._frame_count += 1
                result = self.process_frame(frame)

                if show_video:
                    display = self._annotate_frame(frame, result)
                    cv2.imshow("Intrusion Detection System", display)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord("q"):
                        logger.info("Quit key pressed.")
                        break

        except KeyboardInterrupt:
            logger.info("Interrupted by user (Ctrl+C).")

        finally:
            self._source.release()
            cv2.destroyAllWindows()
            logger.info("Pipeline stopped. Total frames processed: %d", self._frame_count)
