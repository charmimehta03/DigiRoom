from fastapi import APIRouter, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from backend.database.database import SessionLocal
from backend.database.models import Teacher, Institute
from fastapi import Query
from backend.database.models import (
    Teacher,
    TeacherDepartmentSubject,
    Lecture,
    Subject,
    LectureMaterial,
    LectureDocument,
    LectureRecording,
    LectureAttendance
)

import os
import shutil

from fastapi.responses import FileResponse


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
        db.close()
        return HTMLResponse("<h2>Invalid Institute Code</h2>")

    # CHECK EMAIL
    existing_teacher = db.query(Teacher).filter(
        Teacher.email == email
    ).first()

    if existing_teacher:
        db.close()
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

    db.close()
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
        db.close()
        return HTMLResponse("<h2>Invalid Email or Password</h2>")

    # CHECK APPROVAL
    if teacher.status != "approved":
        db.close()
        return HTMLResponse(
            "<h2>Your account is waiting for institute approval</h2>"
        )

    # SUCCESS LOGIN
    db.close()
    return HTMLResponse(
        f"""
        <script>
            window.location.href='/teacher/dashboard?id={teacher.id}';
        </script>
        """
    )


@router.get("/api/teacher/dashboard")
def teacher_dashboard_data(
    teacher_id: int = Query(...)
):

    db: Session = SessionLocal()

    teacher = db.query(Teacher).filter(
        Teacher.id == teacher_id
    ).first()

    if not teacher:
        db.close()
        return {
            "error": "Teacher not found"
        }

    assigned_subjects = db.query(
        TeacherDepartmentSubject
    ).filter(
        TeacherDepartmentSubject.teacher_id == teacher_id
    ).count()

    total_lectures = db.query(
        Lecture
    ).filter(
        Lecture.teacher_id == teacher_id
    ).count()
    week_ago = datetime.utcnow() - timedelta(days=7)

    lectures_this_week = db.query(
        Lecture
    ).filter(
        Lecture.teacher_id == teacher_id,
        Lecture.created_at >= week_ago
    ).count()

    from backend.database.models import (
        LectureAttendance as _LectureAttendance,
        LectureAnalytics as _LectureAnalytics,
        Student as _Student
    )

    teacher_lectures = db.query(Lecture).filter(
        Lecture.teacher_id == teacher_id
    ).all()
    lecture_ids = [l.id for l in teacher_lectures]

    total_students = 0
    seen_divisions = set()
    for lec in teacher_lectures:
        key = (lec.year, lec.division)
        if key in seen_divisions:
            continue
        seen_divisions.add(key)
        total_students += db.query(_Student).filter(
            _Student.year == lec.year,
            _Student.division == lec.division,
            _Student.institute_code == teacher.institute_code
        ).count()

    average_attendance = 0
    if lecture_ids:
        attendance_counts = []
        for lec in teacher_lectures:
            present = db.query(_LectureAttendance).filter(
                _LectureAttendance.lecture_id == lec.id
            ).count()
            eligible = db.query(_Student).filter(
                _Student.year == lec.year,
                _Student.division == lec.division,
                _Student.institute_code == teacher.institute_code
            ).count()
            if eligible > 0:
                attendance_counts.append((present / eligible) * 100)
        average_attendance = (
            round(sum(attendance_counts) / len(attendance_counts))
            if attendance_counts else 0
        )

    average_attention = 0
    if lecture_ids:
        analytics_rows = db.query(_LectureAnalytics).filter(
            _LectureAnalytics.lecture_id.in_(lecture_ids)
        ).all()
        average_attention = (
            round(sum(r.attention_percentage for r in analytics_rows) / len(analytics_rows))
            if analytics_rows else 0
        )

    db.close()
    return {

        "teacher_name":
            teacher.name,

        "assigned_subjects":
            assigned_subjects,

        "total_lectures":
            total_lectures,

        "lectures_this_week":
            lectures_this_week,

        "average_attendance":
            average_attendance,

        "average_attention":
            average_attention,

        "total_students":
            total_students
    }

@router.get("/api/teacher/upcoming-lectures")
def upcoming_lectures(
    teacher_id: int
):

    db: Session = SessionLocal()

    lectures = db.query(
        Lecture
    ).filter(
        Lecture.teacher_id == teacher_id,
        Lecture.status != "completed"
    ).all()

    data = []

    for lecture in lectures:

        subject = db.query(Subject).filter(
            Subject.id == lecture.subject_id
        ).first()

        data.append({

            "id": lecture.id,

            "date": lecture.scheduled_date,

            "time": lecture.scheduled_time,

            "title": lecture.title,

            "subject":
                subject.subject_name
                if subject else "Unknown",

            "status": lecture.status

        })

    db.close()
    return data

# @router.get("/teacher/schedule-lecture")
# def schedule_lecture():
#     return FileResponse(
#         os.path.join(
#             HTML_DIR,
#             "teacher",
#             "schedule_lecture.html"
#         )
#     )

@router.get("/api/teacher/subjects")
def get_teacher_subjects(
    teacher_id: int
):

    db: Session = SessionLocal()

    assignments = db.query(
        TeacherDepartmentSubject
    ).filter(
        TeacherDepartmentSubject.teacher_id == teacher_id
    ).all()

    subjects = []

    for assignment in assignments:

        subject = db.query(
            Subject
        ).filter(
            Subject.id == assignment.subject_id
        ).first()

        if subject:

            subjects.append({

                "id": subject.id,

                "name": subject.subject_name

            })

    db.close()
    return subjects

@router.post("/api/teacher/create-lecture")
def create_lecture(

    teacher_id: int = Form(...),

    title: str = Form(...),

    subject_id: int = Form(...),

    year: str = Form(...),

    semester: str = Form(...),

    division: str = Form(...),

    scheduled_date: str = Form(...),

    scheduled_time: str = Form(...),

    description: str = Form(""),

    ppt_file: UploadFile = File(None)
):

    db: Session = SessionLocal()

    lecture = Lecture(

        teacher_id=teacher_id,

        subject_id=subject_id,

        title=title,

        year=year,

        semester=semester,

        division=division,

        scheduled_date=scheduled_date,

        scheduled_time=scheduled_time,

        description=description,

        status="scheduled"

    )

    db.add(lecture)

    db.commit()
    db.refresh(lecture)
    safe_title = (
        lecture.title
        .replace(" ", "_")
        .replace("/", "_")
    )

    folder_name = (
        f"lecture_{lecture.id}_{safe_title}"
    )

    upload_dir = os.path.join(
        "uploads",
        "materials",
        "presentations",
        folder_name
    )

    documents_dir = os.path.join(
        "uploads",
        "materials",
        "documents",
        folder_name
    )

    os.makedirs(
        upload_dir,
        exist_ok=True
    )

    os.makedirs(
        documents_dir,
        exist_ok=True
    )
    if ppt_file:    

        file_extension = os.path.splitext(
            ppt_file.filename
        )[1].lower()

        if file_extension not in [
            ".ppt",
            ".pptx"
        ]:

            db.close()
            return {
                "message":
                "Only PPT and PPTX files are allowed"
            }

        file_path = os.path.join(
            upload_dir,
            ppt_file.filename
        )

        with open(
            file_path,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                ppt_file.file,
                buffer
            )

        material = LectureMaterial(

            lecture_id=lecture.id,

            title="Presentation",

            file_name=ppt_file.filename,

            file_path=file_path

        )

        db.add(material)

        db.commit()

    db.close()
    return {
        "message": "Lecture Scheduled Successfully"
    }


@router.get("/api/teacher/lecture-history")
def lecture_history(
    teacher_id: int
):

    db: Session = SessionLocal()

    lectures = db.query(
        Lecture
    ).filter(
        Lecture.teacher_id == teacher_id
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

            "date":
                lecture.scheduled_date,

            "time":
                lecture.scheduled_time,

            "title":
                lecture.title,

            "subject":
                subject.subject_name
                if subject else "Unknown",

            "status":
                lecture.status

        })

    db.close()
    return data



@router.delete("/api/teacher/delete-lecture/{lecture_id}")
def delete_lecture(
    lecture_id: int
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
    

    safe_title = (
        lecture.title
        .replace(" ", "_")
        .replace("/", "_")
    )

    folder_name = (
        f"lecture_{lecture.id}_{safe_title}"
    )

    presentation_folder = os.path.join(
        "uploads",
        "materials",
        "presentations",
        folder_name
    )

    documents_folder = os.path.join(
        "uploads",
        "materials",
        "documents",
        folder_name
    )

    if os.path.exists(
        presentation_folder
    ):
        shutil.rmtree(
            presentation_folder
        )

    if os.path.exists(
        documents_folder
    ):
        shutil.rmtree(
            documents_folder
        )

    materials = db.query(
        LectureMaterial
    ).filter(
        LectureMaterial.lecture_id == lecture.id
    ).all()

    for material in materials:
        db.delete(material)
    db.delete(lecture)

    db.commit()

    db.close()
    return {
        "message":
        "Lecture deleted successfully"
    }



@router.put("/api/teacher/postpone-lecture/{lecture_id}")
def postpone_lecture(
    lecture_id: int,
    scheduled_date: str = Form(...),
    scheduled_time: str = Form(...)
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
            "message": "Lecture not found"
        }

    lecture.scheduled_date = scheduled_date
    lecture.scheduled_time = scheduled_time

    db.commit()

    db.close()
    return {
        "message":
        "Lecture postponed successfully"
    }



@router.get("/api/teacher/lecture/{lecture_id}")
def get_lecture(
    lecture_id: int
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
            "error":
            "Lecture not found"
        }
    material = db.query(
        LectureMaterial
    ).filter(
        LectureMaterial.lecture_id == lecture.id
    ).first()
    db.close()
    return {

        "id":
            lecture.id,

        "title":
            lecture.title,

        "subject_id":
            lecture.subject_id,

        "year":
            lecture.year,

        "semester":
            lecture.semester,

        "division":
            lecture.division,

        "scheduled_date":
            lecture.scheduled_date,

        "scheduled_time":
            lecture.scheduled_time,

        "description":
            lecture.description,

        "ppt_name":
            material.file_name
            if material else "",

        "ppt_path":
            material.file_path
            if material else ""

    }

@router.put("/api/teacher/update-lecture/{lecture_id}")
def update_lecture(

    lecture_id: int,

    title: str = Form(...),

    subject_id: int = Form(...),

    year: str = Form(...),

    semester: str = Form(...),

    division: str = Form(...),

    scheduled_date: str = Form(...),

    scheduled_time: str = Form(...),

    description: str = Form(""),

    ppt_file: UploadFile = File(None)
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
    old_title = lecture.title

    old_folder = (
        f"lecture_{lecture.id}_"
        +
        old_title
        .replace(" ", "_")
        .replace("/", "_")
    )

    new_folder = (
        f"lecture_{lecture.id}_"
        +
        title
        .replace(" ", "_")
        .replace("/", "_")
    )

    lecture.title = title
    lecture.subject_id = subject_id
    lecture.year = year
    lecture.semester = semester
    lecture.division = division
    lecture.scheduled_date = scheduled_date
    lecture.scheduled_time = scheduled_time
    lecture.description = description
    old_presentation = os.path.join(
        "uploads",
        "materials",
        "presentations",
        old_folder
    )

    new_presentation = os.path.join(
        "uploads",
        "materials",
        "presentations",
        new_folder
    )

    if (
        os.path.exists(old_presentation)
        and
        old_folder != new_folder
    ):
        os.rename(
            old_presentation,
            new_presentation
        )
        material = db.query(
            LectureMaterial
        ).filter(
            LectureMaterial.lecture_id == lecture.id
        ).first()

        if material:

            material.file_path = (
                material.file_path.replace(
                    old_folder,
                    new_folder
                )
            )
    old_documents = os.path.join(
        "uploads",
        "materials",
        "documents",
        old_folder
    )

    new_documents = os.path.join(
        "uploads",
        "materials",
        "documents",
        new_folder
    )

    if (
        os.path.exists(old_documents)
        and
        old_folder != new_folder
    ):
        os.rename(
            old_documents,
            new_documents
        )
    if ppt_file:

        material = db.query(
            LectureMaterial
        ).filter(
            LectureMaterial.lecture_id == lecture.id
        ).first()

        presentation_folder = os.path.join(
            "uploads",
            "materials",
            "presentations",
            new_folder
        )

        os.makedirs(
            presentation_folder,
            exist_ok=True
        )

        if material:

            old_file = material.file_path

            if os.path.exists(old_file):

                os.remove(old_file)

        file_path = os.path.join(
            presentation_folder,
            ppt_file.filename
        )

        with open(
            file_path,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                ppt_file.file,
                buffer
            )

        if material:

            material.file_name = (
                ppt_file.filename
            )

            material.file_path = (
                file_path
            )

        else:

            material = LectureMaterial(

                lecture_id=lecture.id,

                title="Presentation",

                file_name=ppt_file.filename,

                file_path=file_path

            )

            db.add(material)
    db.commit()

    db.close()
    return {
        "message":
        "Lecture updated successfully"
    }

@router.get("/api/teacher/lectures")
def get_teacher_lectures(
    teacher_id: int
):

    db: Session = SessionLocal()

    lectures = db.query(
        Lecture
    ).filter(
        Lecture.teacher_id == teacher_id
    ).all()

    data = []

    for lecture in lectures:

        data.append({

            "id": lecture.id,

            "title": lecture.title

        })

    db.close()
    return data

@router.post("/api/teacher/upload-document")
def upload_document(

    lecture_id: int = Form(...),

    document: UploadFile = File(...)

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

    allowed_extensions = [
        ".pdf",
        ".doc",
        ".docx",
        ".zip",
        ".rar",
        ".ppt",
        ".pptx"
    ]

    extension = os.path.splitext(
        document.filename
    )[1].lower()

    if extension not in allowed_extensions:

        db.close()
        return {
            "message":
            "File type not allowed"
        }

    folder_name = (
        f"lecture_{lecture.id}_"
        +
        lecture.title
        .replace(" ", "_")
        .replace("/", "_")
    )

    documents_folder = os.path.join(

        "uploads",
        "materials",
        "documents",
        folder_name

    )

    os.makedirs(
        documents_folder,
        exist_ok=True
    )

    file_path = os.path.join(
        documents_folder,
        document.filename
    )

    with open(
        file_path,
        "wb"
    ) as buffer:

        shutil.copyfileobj(
            document.file,
            buffer
        )

    new_document = LectureDocument(

        lecture_id=lecture.id,

        file_name=document.filename,

        file_path=file_path

    )

    db.add(new_document)

    db.commit()

    db.close()
    return {
        "message":
        "Document uploaded successfully"
    }


@router.get("/api/teacher/documents")
def get_documents(
    teacher_id: int
):

    db: Session = SessionLocal()

    lectures = db.query(
        Lecture
    ).filter(
        Lecture.teacher_id == teacher_id
    ).all()

    data = []

    for lecture in lectures:

        subject = db.query(
            Subject
        ).filter(
            Subject.id == lecture.subject_id
        ).first()

        docs = db.query(
            LectureDocument
        ).filter(
            LectureDocument.lecture_id == lecture.id
        ).all()

        for doc in docs:

            data.append({

                "id":
                    doc.id,

                "date":
                    lecture.scheduled_date,

                "lecture":
                    lecture.title,

                "subject":
                    subject.subject_name
                    if subject else "",

                "file_name":
                    doc.file_name,

                "file_type":
                    doc.file_name.split(".")[-1]

            })

    db.close()
    return data

@router.delete(
    "/api/teacher/delete-document/{document_id}"
)
def delete_document(
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

    if os.path.exists(
        document.file_path
    ):
        os.remove(
            document.file_path
        )

    db.delete(document)

    db.commit()

    db.close()
    return {
        "message":
        "Document deleted"
    }


@router.get(
    "/api/teacher/download-document/{document_id}"
)
def download_document(
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

    file_path = document.file_path
    file_name = document.file_name

    db.close()
    return FileResponse(

        path=file_path,

        filename=file_name,

        media_type="application/octet-stream"

    )


@router.get("/api/teacher/presentations")
def get_presentations(
    teacher_id: int
):

    db: Session = SessionLocal()

    lectures = db.query(
        Lecture
    ).filter(
        Lecture.teacher_id == teacher_id
    ).all()

    data = []

    for lecture in lectures:

        presentation = db.query(
            LectureMaterial
        ).filter(
            LectureMaterial.lecture_id == lecture.id
        ).first()
        if presentation:

            subject = db.query(
                Subject
            ).filter(
                Subject.id == lecture.subject_id
            ).first()

            data.append({

                "id":
                    presentation.id,

                "date":
                    lecture.scheduled_date,

                "lecture":
                    lecture.title,

                "subject":
                    subject.subject_name
                    if subject else "",

                "file_name":
                    presentation.file_name

            })
    db.close()
    return data


@router.get(
    "/api/teacher/download-presentation/{material_id}"
)
def download_presentation(
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

    file_path = material.file_path
    file_name = material.file_name

    db.close()
    return FileResponse(

        path=file_path,

        filename=file_name,

        media_type="application/octet-stream"

    )



@router.delete(
    "/api/teacher/delete-presentation/{material_id}"
)
def delete_presentation(
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

    if os.path.exists(
        material.file_path
    ):
        os.remove(
            material.file_path
        )

    db.delete(material)

    db.commit()

    db.close()
    return {
        "message":
        "Presentation deleted"
    }


@router.get("/api/teacher/recordings")
def get_recordings(
    teacher_id: int
):

    db: Session = SessionLocal()

    lectures = db.query(
        Lecture
    ).filter(
        Lecture.teacher_id == teacher_id
    ).all()

    data = []

    for lecture in lectures:

        recording = db.query(
            LectureRecording
        ).filter(
            LectureRecording.lecture_id == lecture.id
        ).first()

        if recording:

            subject = db.query(
                Subject
            ).filter(
                Subject.id == lecture.subject_id
            ).first()

            data.append({

                    "id":
                        recording.id,

                    "date":
                        lecture.scheduled_date,

                    "lecture":
                        lecture.title,

                    "subject":
                        subject.subject_name
                        if subject else "",

                    "attendance":
                        recording.attendance_percentage,

                    "attention":
                        recording.average_attention,

                    "duration":
                        recording.duration_minutes,

                    "students":
                        recording.students_present

                })

    db.close()
    return data



@router.get(
    "/api/teacher/download-recording/{recording_id}"
)
def download_recording(
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

    recording_path = recording.recording_path

    db.close()
    return FileResponse(
        recording_path
    )




@router.delete(
    "/api/teacher/delete-recording/{recording_id}"
)
def delete_recording(
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

    if os.path.exists(
        recording.recording_path
    ):
        os.remove(
            recording.recording_path
        )

    db.delete(recording)

    db.commit()

    db.close()
    return {
        "message":
        "Recording deleted"
    }

@router.put(
    "/api/teacher/start-lecture/{lecture_id}"
)
def start_lecture(
    lecture_id: int
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

    lecture.status = "live"

    lecture.actual_start = (
        datetime.utcnow()
    )

    db.commit()

    db.close()
    return {
        "message":
        "Lecture started successfully"
    }


@router.get(
    "/api/teacher/live-lecture/{lecture_id}"
)
def get_live_lecture(
    lecture_id: int
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

    subject = db.query(
        Subject
    ).filter(
        Subject.id == lecture.subject_id
    ).first()

    material = db.query(
        LectureMaterial
    ).filter(
        LectureMaterial.lecture_id == lecture.id
    ).first()

    db.close()
    return {

        "id":
            lecture.id,

        "title":
            lecture.title,

        "subject":
            subject.subject_name
            if subject else "",

        "date":
            lecture.scheduled_date,

        "time":
            lecture.scheduled_time,

        "status":
            lecture.status,

        "presentation_id":
            material.id
            if material else None,

        "presentation_name":
            material.file_name
            if material else ""

    }

@router.put(
    "/api/teacher/complete-lecture/{lecture_id}"
)
def complete_lecture(
    lecture_id: int
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

    lecture.status = "completed"

    lecture.actual_end = (
        datetime.utcnow()
    )

    db.commit()

    try:
        from backend.python.analytics_api import _sync_lecture_analytics_file
        _sync_lecture_analytics_file(db, lecture)
    except Exception as e:
        print("Analytics sync on complete failed:", e)

    db.close()
    return {
        "message":
        "Lecture completed successfully"
    }


@router.get(
    "/api/teacher/live-count/{lecture_id}"
)
def live_count(
    lecture_id: int
):

    db: Session = SessionLocal()

    count = db.query(
        LectureAttendance
    ).filter(
        LectureAttendance.lecture_id == lecture_id,
        LectureAttendance.left_at == None
    ).count()

    db.close()
    return {
        "students":
        count
    }