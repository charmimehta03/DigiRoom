from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from backend.database.database import SessionLocal
from backend.database.models import (
    Student,
    Institute,
    Lecture,
    LectureAttendance,
    Subject,
    LectureMaterial,
    LectureDocument,
    LectureRecording
)

from datetime import datetime

from fastapi.responses import FileResponse

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
    semester: str = Form(...),
    division: str = Form(...),
    institute_code: str = Form(...)
):

    db: Session = SessionLocal()

    # CHECK INSTITUTE
    institute = db.query(Institute).filter(
        Institute.institute_code == institute_code
    ).first()

    if not institute:
        db.close()
        return HTMLResponse("<h2>Invalid Institute Code</h2>")

    # CHECK EMAIL
    existing_email = db.query(Student).filter(
        Student.email == email
    ).first()

    if existing_email:
        db.close()
        return HTMLResponse("<h2>Email already exists</h2>")

    # CHECK ROLL NUMBER
    existing_roll = db.query(Student).filter(
        Student.roll_number == roll_number
    ).first()

    if existing_roll:
        db.close()
        return HTMLResponse("<h2>Roll Number already exists</h2>")

    # CREATE STUDENT
    new_student = Student(
        full_name=full_name,
        email=email,
        password=password,
        roll_number=roll_number,
        course=course,
        year=year,
        semester=semester,
        division=division,
        institute_code=institute_code,
        status="pending"
    )

    db.add(new_student)
    db.commit()

    db.close()
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
        db.close()
        return HTMLResponse("<h2>Invalid Email or Password</h2>")

    # APPROVAL CHECK
    if student.status != "approved":
        db.close()
        return HTMLResponse(
            "<h2>Your account is waiting for institute approval</h2>"
        )

    # SUCCESS LOGIN
    db.close()
    return HTMLResponse(
        f"""
        <script>
            window.location.href='/student/dashboard?id={student.id}';
        </script>
        """
    )

@router.post(
    "/api/student/join-lecture/{lecture_id}"
)
def join_lecture(
    lecture_id: int,
    student_id: int = Form(...)
):

    db: Session = SessionLocal()

    lecture = db.query(
        Lecture
    ).filter(
        Lecture.id == lecture_id
    ).first()

    if not lecture:
        db.close()
        return {
            "message":
            "Lecture not found"
        }

    student = db.query(
        Student
    ).filter(
        Student.id == student_id
    ).first()

    if not student:
        db.close()
        return {
            "message":
            "Student not found"
        }

    if lecture.status != "live":
        db.close()
        return {
            "message":
            "Lecture is not live"
        }

    if student.year != lecture.year:
        db.close()
        return {
            "message":
            "You are not assigned to this year"
        }

    if student.division != lecture.division:
        db.close()
        return {
            "message":
            "You are not assigned to this division"
        }

    attendance = db.query(
        LectureAttendance
    ).filter(
        LectureAttendance.lecture_id == lecture_id,
        LectureAttendance.student_id == student_id,
        LectureAttendance.left_at == None
    ).first()

    if attendance:
        db.close()
        return {
            "message":
            "Already joined"
        }

    attendance = LectureAttendance(

        lecture_id=lecture_id,

        student_id=student_id

    )

    db.add(attendance)

    db.commit()

    db.close()
    return {
        "message":
        "Joined lecture successfully"
    }

@router.put(
    "/api/student/leave-lecture/{lecture_id}"
)
def leave_lecture(
    lecture_id: int,
    student_id: int = Form(...)
):

    db: Session = SessionLocal()

    attendance = db.query(
        LectureAttendance
    ).filter(
        LectureAttendance.lecture_id == lecture_id,
        LectureAttendance.student_id == student_id,
        LectureAttendance.left_at == None
    ).first()

    if not attendance:
        db.close()
        return {
            "message":
            "Attendance not found"
        }

    attendance.left_at = datetime.utcnow()

    duration = (
        attendance.left_at -
        attendance.joined_at
    )

    attendance.total_minutes += int(
        duration.total_seconds() / 60
    )

    db.commit()

    db.close()
    return {
        "message":
        "Lecture exited"
    }

@router.get(
    "/api/student/live-lectures"
)
def get_live_lectures(
    student_id: int
):

    db: Session = SessionLocal()

    student = db.query(
        Student
    ).filter(
        Student.id == student_id
    ).first()

    if not student:
        db.close()
        return []

    lectures = db.query(
        Lecture
    ).filter(
        Lecture.status == "live",
        Lecture.year == student.year,
        Lecture.division == student.division
    ).all()

    data = []

    for lecture in lectures:

        data.append({

            "id":
                lecture.id,

            "title":
                lecture.title,

            "date":
                lecture.scheduled_date,

            "time":
                lecture.scheduled_time

        })

    db.close()
    return data


@router.get(
    "/api/student/scheduled-lectures"
)
def scheduled_lectures(
    student_id: int
):

    db: Session = SessionLocal()

    student = db.query(
        Student
    ).filter(
        Student.id == student_id
    ).first()

    if not student:

        db.close()
        return []

    lectures = db.query(
        Lecture
    ).filter(
        Lecture.status == "scheduled",
        Lecture.year == student.year,
        Lecture.division == student.division
    ).all()

    data = []

    for lecture in lectures:

        subject = db.query(
            Subject
        ).filter(
            Subject.id == lecture.subject_id
        ).first()

        data.append({

            "id": lecture.id,

            "title": lecture.title,

            "date": lecture.scheduled_date,

            "time": lecture.scheduled_time,

            "subject":
                subject.subject_name
                if subject else ""

        })

    db.close()

    return data

@router.get(
    "/api/student/lecture-history"
)
def student_lecture_history(
    student_id: int
):

    db: Session = SessionLocal()

    student = db.query(
        Student
    ).filter(
        Student.id == student_id
    ).first()

    if not student:

        db.close()
        return []

    lectures = db.query(
        Lecture
    ).filter(
        Lecture.status == "completed",
        Lecture.year == student.year,
        Lecture.division == student.division
    ).all()

    data = []

    for lecture in lectures:

        subject = db.query(
            Subject
        ).filter(
            Subject.id == lecture.subject_id
        ).first()

        attendance = db.query(
            LectureAttendance
        ).filter(
            LectureAttendance.lecture_id == lecture.id,
            LectureAttendance.student_id == student.id
        ).all()

        total_minutes = sum(
            a.total_minutes
            for a in attendance
        )

        data.append({

            "id": lecture.id,

            "title": lecture.title,

            "date": lecture.scheduled_date,

            "time": lecture.scheduled_time,

            "subject":
                subject.subject_name
                if subject else "",

            "minutes":
                total_minutes

        })

    db.close()

    return data

# NOTE: /api/student/materials is now handled by recording_viewer_api.py
# which supports both ?student_id= (all lectures) and ?lecture_id= (per-lecture viewer).
# This function is intentionally removed to avoid route duplication.
# The new handler is fully backward-compatible with the original student_id-only call.

@router.get(
    "/api/student/materials-legacy-removed"  # disabled
)
def student_materials(
    student_id: int
):

    db: Session = SessionLocal()

    student = db.query(
        Student
    ).filter(
        Student.id == student_id
    ).first()

    if not student:

        db.close()
        return []

    lectures = db.query(
        Lecture
    ).filter(
        Lecture.status == "completed",
        Lecture.year == student.year,
        Lecture.division == student.division
    ).all()

    data = []

    for lecture in lectures:

        subject = db.query(
            Subject
        ).filter(
            Subject.id == lecture.subject_id
        ).first()

        presentations = db.query(
            LectureMaterial
        ).filter(
            LectureMaterial.lecture_id == lecture.id
        ).all()

        documents = db.query(
            LectureDocument
        ).filter(
            LectureDocument.lecture_id == lecture.id
        ).all()
        recordings = db.query(
            LectureRecording
        ).filter(
            LectureRecording.lecture_id == lecture.id
        ).all()

        for ppt in presentations:

            data.append({

                "type": "Presentation",

                "id": ppt.id,

                "lecture": lecture.title,

                "subject":
                    subject.subject_name
                    if subject else "",

                "file_name":
                    ppt.file_name

            })

        for doc in documents:

            data.append({

                "type": "Document",

                "id": doc.id,

                "lecture": lecture.title,

                "subject":
                    subject.subject_name
                    if subject else "",

                "file_name":
                    doc.file_name

            })
        
        for recording in recordings:

            data.append({

                "type": "Recording",

                "id": recording.id,

                "lecture": lecture.title,

                "subject":
                    subject.subject_name
                    if subject else "",

                "file_name":
                    "Lecture Recording"

            })

    db.close()

    return data


@router.get(
    "/api/student/download-presentation/{material_id}"
)
def student_download_presentation(
    material_id: int
):

    db: Session = SessionLocal()

    material = db.query(
        LectureMaterial
    ).filter(
        LectureMaterial.id == material_id
    ).first()

    if not material:

        db.close()
        return {
            "message":
            "Presentation not found"
        }

    db.close()

    return FileResponse(
        path=material.file_path,
        filename=material.file_name,
        media_type="application/octet-stream"
    )


@router.get(
    "/api/student/download-document/{document_id}"
)
def student_download_document(
    document_id: int
):

    db: Session = SessionLocal()

    document = db.query(
        LectureDocument
    ).filter(
        LectureDocument.id == document_id
    ).first()

    if not document:

        db.close()
        return {
            "message":
            "Document not found"
        }

    db.close()

    return FileResponse(
        path=document.file_path,
        filename=document.file_name,
        media_type="application/octet-stream"
    )


@router.get(
    "/api/student/download-recording/{recording_id}"
)
def student_download_recording(
    recording_id: int
):

    db: Session = SessionLocal()

    recording = db.query(
        LectureRecording
    ).filter(
        LectureRecording.id == recording_id
    ).first()

    if not recording:

        db.close()

        return {
            "message":
            "Recording not found"
        }

    db.close()

    return FileResponse(
        path=recording.recording_path,
        filename="lecture_recording.mp4",
        media_type="video/mp4"
    )


@router.get(
    "/api/student/analytics"
)
def student_analytics(
    student_id: int
):

    db: Session = SessionLocal()

    student = db.query(
        Student
    ).filter(
        Student.id == student_id
    ).first()

    if not student:

        db.close()

        return {}

    total_lectures = db.query(
        Lecture
    ).filter(
        Lecture.status == "completed",
        Lecture.year == student.year,
        Lecture.division == student.division
    ).count()

    attendance_records = db.query(
        LectureAttendance
    ).filter(
        LectureAttendance.student_id == student.id
    ).all()

    attended_lectures = len(
        set(
            record.lecture_id
            for record in attendance_records
        )
    )

    total_minutes = sum(
        record.total_minutes
        for record in attendance_records
    )

    average_minutes = 0

    if attended_lectures > 0:

        average_minutes = round(
            total_minutes /
            attended_lectures,
            2
        )

    attendance_percentage = 0

    if total_lectures > 0:

        attendance_percentage = round(
            (
                attended_lectures /
                total_lectures
            ) * 100,
            2
        )

    graph_data = []

    for record in attendance_records:

        lecture = db.query(
            Lecture
        ).filter(
            Lecture.id == record.lecture_id
        ).first()

        if lecture:

            graph_data.append({

                "lecture":
                    lecture.title,

                "minutes":
                    record.total_minutes

            })

    db.close()

    return {

        "total_lectures":
            total_lectures,

        "attended_lectures":
            attended_lectures,

        "attendance_percentage":
            attendance_percentage,

        "average_minutes":
            average_minutes,

        "graph_data":
            graph_data

    }

