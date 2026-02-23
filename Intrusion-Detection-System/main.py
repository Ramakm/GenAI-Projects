"""
main.py — Entry point for the Intrusion Detection System.

Usage:
    python main.py --source webcam
    python main.py --source video --file path/to/video.mp4
    python main.py --source webcam --no-display
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

import cv2

# Ensure project root is on PYTHONPATH when run directly
sys.path.insert(0, os.path.dirname(__file__))

from config import ConfigManager
from src.video_source import VideoSource, SourceType
from src.yolo_detector import YOLODetector
from src.zone_drawer import ZoneDrawer
from src.zone_manager import ZoneManager
from src.alert_handler import AlertHandler
from src.pipeline import IntrusionDetectionPipeline


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(os.path.join("logs", "ids.log"), mode="a"),
        ],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Intrusion Detection System (YOLOv11)")
    parser.add_argument(
        "--source",
        choices=["webcam", "video"],
        default="webcam",
        help="Input source: webcam or video file",
    )
    parser.add_argument(
        "--file",
        default=None,
        help="Path to video file (required when --source video)",
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Run headless (no OpenCV display window)",
    )
    return parser.parse_args()


def capture_snapshot(source: VideoSource) -> "cv2.Mat | None":
    """Read a single frame to use as the canvas for zone drawing."""
    ok, frame = source.read_frame()
    if not ok or frame is None:
        logging.error("Could not read a frame from the source for zone drawing.")
        return None
    return frame


def interactive_zone_setup(snapshot: "cv2.Mat") -> ZoneManager:
    zone_manager = ZoneManager()
    zone_index = 1

    print("\n--- Zone Setup ---")
    print("Draw restricted zones interactively.")
    print("  Left-click : add vertex")
    print("  SPACE      : close & confirm polygon")
    print("  R          : reset current polygon")
    print("  ESC        : cancel current polygon\n")

    while True:
        zone_name = input(f"Enter name for zone {zone_index} (or press Enter for 'Zone-{zone_index}'): ").strip()
        if not zone_name:
            zone_name = f"Zone-{zone_index}"

        drawer = ZoneDrawer(snapshot)
        points = drawer.draw()

        if points is None:
            print(f"Zone '{zone_name}' cancelled or invalid.")
        else:
            zone_manager.add_zone(points, zone_name)
            print(f"Zone '{zone_name}' added with {len(points)} vertices.")
            zone_index += 1

        add_another = input("Add another zone? [y/N]: ").strip().lower()
        if add_another != "y":
            break

    if not zone_manager.zones:
        print("No zones defined. Exiting.")
        sys.exit(0)

    print(f"\n{len(zone_manager.zones)} zone(s) defined. Starting detection...\n")
    return zone_manager


def main() -> None:
    args = parse_args()

    # Load config
    cfg = ConfigManager.load_from_env()

    # Ensure log/frame directories exist
    os.makedirs("logs", exist_ok=True)
    os.makedirs("frames", exist_ok=True)

    setup_logging(cfg.log_level)
    logger = logging.getLogger(__name__)

    # Determine source
    if args.source == "webcam":
        source_type = SourceType.WEBCAM
        file_path = None
    else:
        source_type = SourceType.VIDEO_FILE
        file_path = args.file or cfg.camera.video_file_path
        if not file_path:
            logger.error("--file is required when using --source video")
            sys.exit(1)

    logger.info("Initialising video source: %s", source_type.value)
    video_source = VideoSource(source_type, camera_index=cfg.camera.index, file_path=file_path)

    logger.info("Loading YOLO model: %s", cfg.yolo.model_name)
    detector = YOLODetector(model_name=cfg.yolo.model_name, confidence=cfg.yolo.confidence)

    # Zone setup — grab one frame as canvas
    print("Capturing frame for zone drawing...")
    snapshot = capture_snapshot(video_source)
    if snapshot is None:
        sys.exit(1)

    zone_manager = interactive_zone_setup(snapshot)

    alert_handler = AlertHandler(smtp_config=cfg.smtp, alert_config=cfg.alert)

    pipeline = IntrusionDetectionPipeline(
        video_source=video_source,
        detector=detector,
        zone_manager=zone_manager,
        alert_handler=alert_handler,
    )

    show_video = not args.no_display
    pipeline.run(show_video=show_video)


if __name__ == "__main__":
    main()
