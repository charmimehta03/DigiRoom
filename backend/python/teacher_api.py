from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from backend.database.database import SessionLocal
from backend.database.models import Teacher, Institute

router = APIRouter()


@router.post("/teacher/register")
def register_teacher(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    institute_code: str = Form(...)
):

    db: Session = SessionLocal()

    # CHECK INSTITUTE CODE
    institute = db.query(Institute).filter(
        Institute.institute_code == institute_code
    ).first()

    if not institute:
        return HTMLResponse("<h2>Invalid Institute Code</h2>")

    # CHECK EMAIL
    existing_teacher = db.query(Teacher).filter(
        Teacher.email == email
    ).first()

    if existing_teacher:
        return HTMLResponse("<h2>Email already exists</h2>")

    # CREATE TEACHER
    new_teacher = Teacher(
        name=name,
        email=email,
        password=password,
        institute_code=institute_code,
        status="pending"
    )

    db.add(new_teacher)
    db.commit()

    return HTMLResponse(
        "<h2>Registration Successful. Waiting for Institute Approval.</h2>"
    )


@router.post("/teacher/login")
def login_teacher(
    email: str = Form(...),
    password: str = Form(...)
):

    db: Session = SessionLocal()

    teacher = db.query(Teacher).filter(
        Teacher.email == email,
        Teacher.password == password
    ).first()

    # INVALID LOGIN
    if not teacher:
        return HTMLResponse("<h2>Invalid Email or Password</h2>")

    # CHECK APPROVAL
    if teacher.status != "approved":
        return HTMLResponse(
            "<h2>Your account is waiting for institute approval</h2>"
        )

    # SUCCESS LOGIN
    return HTMLResponse(
        """
        <script>
            window.location.href='/teacher/dashboard';
        </script>
        """
    )