from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from backend.database.database import SessionLocal
from backend.database.models import Student, Institute

router = APIRouter()


# STUDENT REGISTRATION
@router.post("/student/register")
def register_student(
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    roll_number: str = Form(...),
    course: str = Form(...),
    year: str = Form(...),
    division: str = Form(...),
    institute_code: str = Form(...)
):

    db: Session = SessionLocal()

    # CHECK INSTITUTE
    institute = db.query(Institute).filter(
        Institute.institute_code == institute_code
    ).first()

    if not institute:
        return HTMLResponse("<h2>Invalid Institute Code</h2>")

    # CHECK EMAIL
    existing_email = db.query(Student).filter(
        Student.email == email
    ).first()

    if existing_email:
        return HTMLResponse("<h2>Email already exists</h2>")

    # CHECK ROLL NUMBER
    existing_roll = db.query(Student).filter(
        Student.roll_number == roll_number
    ).first()

    if existing_roll:
        return HTMLResponse("<h2>Roll Number already exists</h2>")

    # CREATE STUDENT
    new_student = Student(
        full_name=full_name,
        email=email,
        password=password,
        roll_number=roll_number,
        course=course,
        year=year,
        division=division,
        institute_code=institute_code,
        status="pending"
    )

    db.add(new_student)
    db.commit()

    return HTMLResponse(
        "<h2>Student Registered Successfully. Waiting for Approval.</h2>"
    )


# STUDENT LOGIN
@router.post("/student/login")
def login_student(
    email: str = Form(...),
    password: str = Form(...)
):

    db: Session = SessionLocal()

    student = db.query(Student).filter(
        Student.email == email,
        Student.password == password
    ).first()

    # INVALID LOGIN
    if not student:
        return HTMLResponse("<h2>Invalid Email or Password</h2>")

    # APPROVAL CHECK
    if student.status != "approved":
        return HTMLResponse(
            "<h2>Your account is waiting for institute approval</h2>"
        )

    # SUCCESS LOGIN
    return HTMLResponse(
        """
        <script>
            window.location.href='/student/dashboard';
        </script>
        """
    )