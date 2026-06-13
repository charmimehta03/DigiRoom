from fastapi import APIRouter
from fastapi.responses import FileResponse
import os

from fastapi.responses import HTMLResponse
from backend.database.database import SessionLocal
from backend.database.models import (
    Teacher,
    Student,
    Department,
    Subject
)

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HTML_DIR = os.path.join(BASE_DIR, "frontend", "html")


@router.get("/institute")
def institute_dashboard():
    return FileResponse(os.path.join(HTML_DIR, "institute", "dashboard.html"))


@router.get("/teacher")
def teacher_dashboard():
    return FileResponse(os.path.join(HTML_DIR, "teacher", "dashboard.html"))


@router.get("/student")
def student_dashboard():
    return FileResponse(os.path.join(HTML_DIR, "student", "dashboard.html"))


@router.get("/")
def index():
    return FileResponse(os.path.join(HTML_DIR, "common", "index.html"))


# Institute
@router.get("/institute/login")
def institute_login():
    return FileResponse(os.path.join(HTML_DIR, "institute", "login.html"))

@router.get("/institute/register")
def institute_register():
    return FileResponse(os.path.join(HTML_DIR, "institute", "register.html"))

@router.get("/institute/dashboard")
def institute_dashboard():
    return FileResponse(os.path.join(HTML_DIR, "institute", "dashboard.html"))


# Teacher
@router.get("/teacher/login")
def teacher_login():
    return FileResponse(os.path.join(HTML_DIR, "teacher", "login.html"))

@router.get("/teacher/dashboard")
def teacher_dashboard():
    return FileResponse(os.path.join(HTML_DIR, "teacher", "dashboard.html"))

@router.get("/teacher/register")
def teacher_register():
    return FileResponse(os.path.join(HTML_DIR, "teacher", "register.html"))

# Student
@router.get("/student/login")
def student_login():
    return FileResponse(os.path.join(HTML_DIR, "student", "login.html"))

@router.get("/student/dashboard")
def student_dashboard():
    return FileResponse(os.path.join(HTML_DIR, "student", "dashboard.html"))

@router.get("/student/register")
def student_register():
    return FileResponse(os.path.join(HTML_DIR, "student", "register.html"))


@router.get("/student/login")
def student_login():
    return FileResponse(os.path.join(HTML_DIR, "student", "login.html"))


@router.get("/student/dashboard")
def student_dashboard():
    return FileResponse(os.path.join(HTML_DIR, "student", "dashboard.html"))


