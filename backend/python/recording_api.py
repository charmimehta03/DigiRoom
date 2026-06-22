"""
recording_api.py
================
REST endpoints for the DigiRoom recording + marker system.

Handles:
  POST /api/recording/start/{lecture_id}        — create DB record, return folder path
  POST /api/recording/upload/{lecture_id}        — receive final .webm blob from browser
  POST /api/recording/markers/{lecture_id}       — save markers.json
  GET  /api/recording/info/{lecture_id}          — retrieve recording metadata
  GET  /api/recording/list                       — list all recordings

Storage layout:
  uploads/recordings/lecture_<id>_<slug>/
      recording.webm
      markers.json

Only one recording per lecture_id is kept.
Uploading again overwrites the previous file (no duplicates).
"""

import os
import json
import re
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database.database import SessionLocal
from backend.database.models import LectureRecording, Lecture

router = APIRouter()

# =========================================================
# CONSTANTS
# =========================================================

RECORDINGS_ROOT = os.path.join("uploads", "recordings")


# =========================================================
# HELPERS
# =========================================================

def _slug(title: str) -> str:
    slug = title.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug[:40]


def _lecture_folder(lecture_id: int, title: str) -> str:
    folder_name = f"lecture_{lecture_id}_{_slug(title)}"
    folder_path = os.path.join(RECORDINGS_ROOT, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    return folder_path


def _get_db() -> Session:
    return SessionLocal()


def _get_lecture_or_404(db: Session, lecture_id: int) -> Lecture:
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")
    return lecture


# =========================================================
# SCHEMA
# =========================================================

class MarkerPayload(BaseModel):
    markers: list  # list of {"time": int, "title": str}


# =========================================================
# ENDPOINTS
# =========================================================

@router.post("/api/recording/start/{lecture_id}")
def recording_start(lecture_id: int):
    db = _get_db()
    try:
        lecture = _get_lecture_or_404(db, lecture_id)
        folder = _lecture_folder(lecture_id, lecture.title or str(lecture_id))

        rec = db.query(LectureRecording).filter(
            LectureRecording.lecture_id == lecture_id
        ).first()

        if not rec:
            rec = LectureRecording(lecture_id=lecture_id)
            db.add(rec)

        rec.recording_path = None
        rec.marker_path = None
        rec.file_size = None
        rec.duration_seconds = None
        db.commit()

        return {"status": "ready", "folder": folder}
    finally:
        db.close()


@router.post("/api/recording/upload/{lecture_id}")
async def recording_upload(lecture_id: int, file: UploadFile = File(...)):
    db = _get_db()
    try:
        lecture = _get_lecture_or_404(db, lecture_id)
        folder = _lecture_folder(lecture_id, lecture.title or str(lecture_id))

        webm_path = os.path.join(folder, "recording.webm")

        contents = await file.read()
        with open(webm_path, "wb") as f:
            f.write(contents)

        file_size = os.path.getsize(webm_path)

        rec = db.query(LectureRecording).filter(
            LectureRecording.lecture_id == lecture_id
        ).first()

        if not rec:
            rec = LectureRecording(lecture_id=lecture_id)
            db.add(rec)

        rec.recording_path = webm_path
        rec.file_size = file_size
        db.commit()

        return {
            "status": "saved",
            "path": webm_path,
            "size_bytes": file_size
        }
    finally:
        db.close()


@router.post("/api/recording/markers/{lecture_id}")
def save_markers(lecture_id: int, payload: MarkerPayload):
    db = _get_db()
    try:
        lecture = _get_lecture_or_404(db, lecture_id)
        folder = _lecture_folder(lecture_id, lecture.title or str(lecture_id))

        markers_path = os.path.join(folder, "markers.json")

        clean_markers = []
        for m in payload.markers:
            if not isinstance(m, dict):
                continue
            clean_markers.append({
                "time": int(m.get("time", 0)),
                "title": str(m.get("title", "Marker")).strip()[:120]
            })

        data = {"markers": clean_markers}

        with open(markers_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        rec = db.query(LectureRecording).filter(
            LectureRecording.lecture_id == lecture_id
        ).first()

        if not rec:
            rec = LectureRecording(lecture_id=lecture_id)
            db.add(rec)

        rec.marker_path = markers_path
        db.commit()

        return {"status": "saved", "marker_count": len(clean_markers)}
    finally:
        db.close()


@router.get("/api/recording/info/{lecture_id}")
def recording_info(lecture_id: int):
    db = _get_db()
    try:
        rec = db.query(LectureRecording).filter(
            LectureRecording.lecture_id == lecture_id
        ).first()

        if not rec or not rec.recording_path:
            return {"has_recording": False}

        markers = []
        if rec.marker_path and os.path.exists(rec.marker_path):
            try:
                with open(rec.marker_path, "r", encoding="utf-8") as f:
                    markers = json.load(f).get("markers", [])
            except Exception:
                markers = []

        return {
            "has_recording": True,
            "lecture_id": lecture_id,
            "recording_path": rec.recording_path,
            "file_size_bytes": rec.file_size,
            "duration_seconds": rec.duration_seconds,
            "marker_count": len(markers),
            "markers": markers,
            "created_at": rec.created_at.isoformat() if rec.created_at else None
        }
    finally:
        db.close()


@router.get("/api/recording/list")
def recording_list(teacher_id: int = None):
    db = _get_db()
    try:
        query = db.query(LectureRecording, Lecture).join(
            Lecture, LectureRecording.lecture_id == Lecture.id
        )

        if teacher_id:
            query = query.filter(Lecture.teacher_id == teacher_id)

        rows = query.order_by(LectureRecording.created_at.desc()).all()

        results = []
        for rec, lecture in rows:
            if not rec.recording_path:
                continue
            results.append({
                "lecture_id": lecture.id,
                "lecture_title": lecture.title,
                "recording_path": rec.recording_path,
                "file_size_bytes": rec.file_size,
                "duration_seconds": rec.duration_seconds,
                "created_at": rec.created_at.isoformat() if rec.created_at else None
            })

        return {"recordings": results, "count": len(results)}
    finally:
        db.close()
