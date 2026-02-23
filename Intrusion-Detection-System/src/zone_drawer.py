"""
zone_drawer.py — Interactive polygon zone drawing via OpenCV mouse callbacks.
"""

from __future__ import annotations

import cv2
import numpy as np

WINDOW_NAME = "Draw Zone — Left-click: add point | SPACE: close | R: reset | ESC: cancel"


class ZoneDrawer:
    def __init__(self, frame: np.ndarray):
        self._base_frame = frame.copy()
        self._points: list[tuple[int, int]] = []
        self._mouse_pos: tuple[int, int] = (0, 0)
        self._done = False
        self._cancelled = False

    def _mouse_callback(self, event: int, x: int, y: int, flags: int, param) -> None:
        self._mouse_pos = (x, y)
        if event == cv2.EVENT_LBUTTONDOWN:
            self._points.append((x, y))

    def _draw_preview(self) -> np.ndarray:
        preview = self._base_frame.copy()
        if len(self._points) > 1:
            cv2.polylines(preview, [np.array(self._points, dtype=np.int32)], isClosed=False, color=(0, 200, 255), thickness=2)
        if self._points:
            # Line from last point to current mouse
            cv2.line(preview, self._points[-1], self._mouse_pos, (0, 200, 255), 1)
            # Close preview line from mouse back to first point
            if len(self._points) >= 2:
                cv2.line(preview, self._mouse_pos, self._points[0], (0, 200, 255), 1)
        for pt in self._points:
            cv2.circle(preview, pt, 5, (0, 255, 255), -1)
        cv2.putText(preview, f"Points: {len(self._points)}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        return preview

    def draw(self) -> np.ndarray | None:
        """
        Opens an OpenCV window. Returns polygon points array or None if cancelled.
        Requires at least 3 points to form a valid polygon.
        """
        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(WINDOW_NAME, self._mouse_callback)

        while True:
            preview = self._draw_preview()
            cv2.imshow(WINDOW_NAME, preview)
            key = cv2.waitKey(20) & 0xFF

            if key == ord(" "):  # SPACE — close polygon
                if len(self._points) >= 3:
                    self._done = True
                    break
                else:
                    print("[ZoneDrawer] Need at least 3 points to close polygon.")

            elif key == ord("r") or key == ord("R"):  # Reset
                self._points.clear()

            elif key == 27:  # ESC — cancel
                self._cancelled = True
                break

        cv2.destroyWindow(WINDOW_NAME)

        if self._cancelled or len(self._points) < 3:
            return None

        return np.array(self._points, dtype=np.int32)
