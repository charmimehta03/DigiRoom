"""
Analytics Storage System
------------------------
Persists a per-lecture analytics.json snapshot to:

    uploads/analytics/lecture_<id>_<title>/analytics.json

This is a *supplementary* on-disk record (human readable / exportable)
that mirrors what's in the database. The database (LectureAnalytics,
LectureAttendance, LectureChatMessage, LecturePollAnswer) remains the
source of truth used by the API; this file is rebuilt from the DB
whenever analytics changes (during lecture, on student leave, on
lecture completion).
"""

import os
import json
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ANALYTICS_DIR = os.path.join(BASE_DIR, "uploads", "analytics")


def _safe_title(title: str) -> str:
    title = title or "lecture"
    title = re.sub(r"[^a-zA-Z0-9_-]+", "_", title.strip())
    return title[:50] if title else "lecture"


def lecture_analytics_dir(lecture_id: int, title: str) -> str:
    folder = f"lecture_{lecture_id}_{_safe_title(title)}"
    path = os.path.join(ANALYTICS_DIR, folder)
    os.makedirs(path, exist_ok=True)
    return path


def write_lecture_analytics(lecture_id: int, title: str, payload: dict):
    """Overwrite the analytics.json snapshot for a lecture."""
    path = lecture_analytics_dir(lecture_id, title)
    file_path = os.path.join(path, "analytics.json")

    payload["last_updated"] = datetime.utcnow().isoformat()

    with open(file_path, "w") as f:
        json.dump(payload, f, indent=2, default=str)

    return file_path


def read_lecture_analytics(lecture_id: int, title: str):
    path = lecture_analytics_dir(lecture_id, title)
    file_path = os.path.join(path, "analytics.json")

    if not os.path.exists(file_path):
        return None

    with open(file_path, "r") as f:
        return json.load(f)
