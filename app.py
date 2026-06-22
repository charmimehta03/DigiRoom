from fastapi import FastAPI
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

models.Base.metadata.create_all(bind=engine)

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
    return {"message": "DigiRoom Backend Running"}
