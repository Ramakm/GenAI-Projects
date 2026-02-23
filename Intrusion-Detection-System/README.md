# Intrusion Detection System (IDS)

Real-time intrusion detection using **YOLOv11** and **OpenCV**. Detects persons entering user-defined restricted polygon zones drawn interactively on live video. Triggers **email** and **desktop notifications** when intrusion is confirmed.

---

## Features

- YOLOv11 person detection (COCO class 0)
- Interactive polygon zone drawing with mouse
- Per-zone cooldown to prevent alert spam
- Email alerts with captured frame attachment (Gmail / any SMTP)
- Cross-platform desktop notifications via `plyer`
- Supports webcam and video file input

---

## Project Structure

```
Intrusion-Detection-System/
├── main.py                  # Entry point
├── config.py                # Environment-based configuration
├── requirements.txt
├── .env.example
├── logs/                    # Runtime logs (auto-created)
├── frames/                  # Alert frames (auto-created)
└── src/
    ├── video_source.py      # Webcam / video file abstraction
    ├── yolo_detector.py     # YOLOv11 person detection
    ├── zone_drawer.py       # Interactive polygon drawing
    ├── zone_manager.py      # Point-in-polygon zone logic
    ├── frame_saver.py       # Timestamped frame saving
    ├── email_alert.py       # SMTP email with attachment
    ├── desktop_notification.py  # plyer desktop alerts
    ├── alert_handler.py     # Cooldown + alert orchestration
    └── pipeline.py          # Main detection loop
```

---

## Setup

```bash
# 1. Clone / navigate to project
cd GenAI-Projects/Intrusion-Detection-System

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate      # macOS/Linux
# venv\Scripts\activate       # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your SMTP credentials and settings
```

---

## Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server hostname |
| `SMTP_PORT` | `587` | SMTP port (TLS) |
| `SMTP_USER` | — | Sender email address |
| `SMTP_PASSWORD` | — | App password (Gmail: generate in Google Account) |
| `ALERT_EMAIL_TO` | — | Recipient email address |
| `CAMERA_INDEX` | `0` | Webcam device index |
| `VIDEO_FILE_PATH` | — | Optional default video file path |
| `YOLO_MODEL` | `yolo11n` | Model variant (`yolo11n`, `yolo11s`, `yolo11m`, …) |
| `YOLO_CONFIDENCE` | `0.5` | Detection confidence threshold (0–1) |
| `ALERT_COOLDOWN_SECONDS` | `30` | Minimum seconds between alerts per zone |
| `EMAIL_ALERTS_ENABLED` | `true` | Enable/disable email alerts |
| `DESKTOP_ALERTS_ENABLED` | `true` | Enable/disable desktop notifications |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## Usage

### Webcam
```bash
python main.py --source webcam
```

### Video File
```bash
python main.py --source video --file path/to/video.mp4
```

### Headless (no display window)
```bash
python main.py --source webcam --no-display
```

---

## Zone Drawing Instructions

After launch, a frame from the video source is shown for zone drawing:

| Action | Effect |
|---|---|
| **Left-click** | Add a polygon vertex |
| **SPACE** | Close and confirm the polygon (min. 3 points) |
| **R** | Reset — clear all points and start over |
| **ESC** | Cancel current polygon |

After closing a zone, you will be prompted to add more zones or start detection.

---

## Detection Loop Controls

| Key | Action |
|---|---|
| `q` | Quit the detection loop |
| `Ctrl+C` | Graceful shutdown |

---

## Alert Behaviour

- **Green zone** — no intrusion detected
- **Red zone** — person's feet detected inside zone
- Alert fires once per zone per cooldown period
- Frame saved to `frames/{zone_name}/{YYYY-MM-DD}/{HH-MM-SS_ms}.jpg`
- Email sent with frame attached
- Desktop notification shown

---

## Gmail App Password Setup

1. Enable 2-Step Verification on your Google Account
2. Go to **Security → App passwords**
3. Generate a password for "Mail"
4. Use that 16-character password as `SMTP_PASSWORD`
