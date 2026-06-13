from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from backend.python.dashboard_api import router as dashboard_router
from fastapi import FastAPI
from backend.database.database import engine
from backend.database import models
from backend.python.institute_api import router as institute_router
from backend.python.teacher_api import router as teacher_router
from backend.python.student_api import router as student_router
from backend.python.teacher_assignment_api import router as teacher_assignment_router
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Include API routes
app.include_router(dashboard_router)
app.include_router(institute_router)
app.include_router(teacher_router)
app.include_router(student_router)
app.include_router(teacher_assignment_router)
# Serve frontend files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
def home():
    return {"message": "DigiRoom Backend Running"}