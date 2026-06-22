"""
recording_viewer_api.py
=======================
Adds to DigiRoom:

  Page routes (HTML delivery):
    GET /teacher/view-recording         → teacher view_recording.html
    GET /student/view-recording         → student view_recording.html

  Data API:
    GET /api/student/materials-by-lecture   — materials for a single lecture
                                             (used by both viewer pages)

  Extended recording list:
    GET /api/teacher/lecture-history-with-recordings
        — lecture history rows enriched with has_recording flag
        (optional convenience; the JS can also call /api/recording/info per row)
"""

import os
from fastapi import APIRouter, Query
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from backend.database.database import SessionLocal
from backend.database.models import (
    Student,
    Lecture,
    Subject,
    LectureMaterial,
    LectureDocument,
    LectureRecording,
    LectureAttendance
)

router = APIRouter()

# ── HTML directory ────────────────────────────────────────
BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
HTML_DIR = os.path.join(BASE_DIR, "frontend", "html")


# =========================================================
# PAGE ROUTES
# =========================================================

@router.get("/teacher/view-recording")
def teacher_view_recording_page():
    """Serve teacher recording viewer page."""
    return FileResponse(
        os.path.join(HTML_DIR, "teacher", "view_recording.html")
    )


@router.get("/student/view-recording")
def student_view_recording_page():
    """Serve student recording viewer page."""
    return FileResponse(
        os.path.join(HTML_DIR, "student", "view_recording.html")
    )


# =========================================================
# MATERIALS BY LECTURE  (used by viewer JS for both roles)
# =========================================================

@router.get("/api/student/materials")
def student_materials_by_lecture(
    lecture_id: int = Query(None),
    student_id: int = Query(None)
):
    """
    Return presentations and documents for a specific lecture.

    If lecture_id is provided, returns materials for that lecture only.
    Student eligibility is enforced when student_id is also provided:
      lecture.year == student.year AND lecture.division == student.division

    This endpoint intentionally reuses the path /api/student/materials
    so the existing student materials page (which does NOT pass lecture_id)
    continues to work unmodified — the student_api.py handler is
    REPLACED by this one which handles both cases.

    IMPORTANT: Update app.py to use recording_viewer_router BEFORE
    student_router so this route takes precedence, OR rename the existing
    endpoint in student_api.py.  See integration notes below.
    """
    db: Session = SessionLocal()
    try:
        # ── Case 1: Per-lecture lookup (viewer pages) ─────────
        if lecture_id is not None:
            lecture = db.query(Lecture).filter(
                Lecture.id == lecture_id
            ).first()

            if not lecture:
                return JSONResponse(
                    status_code=404,
                    content={"error": "Lecture not found"}
                )

            # Student eligibility check
            if student_id is not None:
                student = db.query(Student).filter(
                    Student.id == student_id
                ).first()

                if not student:
                    return JSONResponse(
                        status_code=403,
                        content={"error": "Student not found"}
                    )

                if (lecture.year != student.year or
                        lecture.division != student.division):
                    return JSONResponse(
                        status_code=403,
                        content={"error": "Not authorised for this lecture"}
                    )

            presentations = db.query(LectureMaterial).filter(
                LectureMaterial.lecture_id == lecture_id
            ).all()

            documents = db.query(LectureDocument).filter(
                LectureDocument.lecture_id == lecture_id
            ).all()

            return {
                "presentations": [
                    {"id": p.id, "file_name": p.file_name}
                    for p in presentations
                ],
                "documents": [
                    {"id": d.id, "file_name": d.file_name}
                    for d in documents
                ]
            }

        # ── Case 2: All-lectures lookup (existing materials page) ─
        if student_id is None:
            return JSONResponse(
                status_code=400,
                content={"error": "Provide student_id or lecture_id"}
            )

        student = db.query(Student).filter(
            Student.id == student_id
        ).first()

        if not student:
            return []

        lectures = db.query(Lecture).filter(
            Lecture.status == "completed",
            Lecture.year == student.year,
            Lecture.division == student.division
        ).all()

        data = []

        for lec in lectures:
            subject = db.query(Subject).filter(
                Subject.id == lec.subject_id
            ).first()

            presos = db.query(LectureMaterial).filter(
                LectureMaterial.lecture_id == lec.id
            ).all()
            docs = db.query(LectureDocument).filter(
                LectureDocument.lecture_id == lec.id
            ).all()
            recs = db.query(LectureRecording).filter(
                LectureRecording.lecture_id == lec.id
            ).all()

            for p in presos:
                data.append({
                    "type": "Presentation",
                    "id": p.id,
                    "lecture": lec.title,
                    "subject": subject.subject_name if subject else "",
                    "file_name": p.file_name
                })
            for d in docs:
                data.append({
                    "type": "Document",
                    "id": d.id,
                    "lecture": lec.title,
                    "subject": subject.subject_name if subject else "",
                    "file_name": d.file_name
                })
            for r in recs:
                data.append({
                    "type": "Recording",
                    "id": r.id,
                    "lecture": lec.title,
                    "subject": subject.subject_name if subject else "",
                    "file_name": "Lecture Recording"
                })

        return data

    finally:
        db.close()
