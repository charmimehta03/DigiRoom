import os
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from backend.python.dashboard_api import router as dashboard_router
from fastapi import FastAPI
from backend.database.database import engine

from backend.python.live_lecture_api import (
    sio,
    socket_app,
    router as live_lecture_router
)

from backend.database import models
from backend.python.institute_api import router as institute_router
from backend.python.teacher_api import router as teacher_router
from backend.python.student_api import router as student_router
from backend.python.teacher_assignment_api import router as teacher_assignment_router
from backend.python.analytics_api import router as analytics_router

# ── Recording system (existing) ───────────────────────────
from backend.python.recording_api import router as recording_router

# ── Recording viewer (NEW) ────────────────────────────────
from backend.python.recording_viewer_api import router as recording_viewer_router

# Folders that are git-ignored must exist on a fresh server
for _d in ("uploads/recordings", "uploads/analytics", "uploads/materials"):
    os.makedirs(_d, exist_ok=True)

models.Base.metadata.create_all(bind=engine)

# Seed departments / subjects on a fresh (empty) database
def _seed_if_empty():
    from backend.database.database import SessionLocal
    db = SessionLocal()
    try:
        empty = db.query(models.Department).first() is None
    finally:
        db.close()
    if empty:
        try:
            import backend.database.seed_data  # noqa: F401  (runs on import)
        except Exception as e:
            print("Seeding skipped:", e)

_seed_if_empty()

app = FastAPI()

# ── Include API routes ────────────────────────────────────

app.include_router(dashboard_router)
app.include_router(institute_router)
app.include_router(teacher_router)
app.include_router(teacher_assignment_router)
app.include_router(live_lecture_router)
app.include_router(analytics_router)
app.include_router(recording_router)

# ── Recording viewer router BEFORE student_router ─────────
# This ensures /api/student/materials (with lecture_id param) and
# /teacher/view-recording / /student/view-recording page routes
# are handled by the new router first.
app.include_router(recording_viewer_router)

# ── Student router (must come AFTER recording_viewer_router) ─
app.include_router(student_router)

# ── Static files ──────────────────────────────────────────
app.mount(
    "/static",
    StaticFiles(directory="frontend"),
    name="static"
)

# ── Uploaded files (recordings served via /uploads/…) ─────
app.mount(
    "/uploads",
    StaticFiles(directory="uploads"),
    name="uploads"
)

app.mount(
    "/socket.io",
    socket_app
)

@app.get("/")
def home():
    return RedirectResponse(url="/static/html/common/index.html")


@app.get("/health")
def health():
    return {"status": "ok"}
