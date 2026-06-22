from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from .database import Base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class Institute(Base):
    __tablename__ = "institutes"

    id = Column(Integer, primary_key=True, index=True)
    institute_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    institute_code = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)

    email = Column(String, unique=True, nullable=False)

    password = Column(String, nullable=False)

    institute_code = Column(String, nullable=False)

    status = Column(String, default="pending")

    created_at = Column(DateTime, default=datetime.utcnow)



class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)

    full_name = Column(String, nullable=False)

    email = Column(String, unique=True, nullable=False)

    password = Column(String, nullable=False)

    roll_number = Column(String, unique=True, nullable=False)

    course = Column(String, nullable=False)

    year = Column(String, nullable=False)

    division = Column(String, nullable=False)

    institute_code = Column(String, nullable=False)

    status = Column(String, default="pending")

    created_at = Column(DateTime, default=datetime.utcnow)
    
    semester = Column(String, nullable=False)



class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)

    department_name = Column(String, unique=True, nullable=False)


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)

    subject_name = Column(String, nullable=False)

    department_id = Column(Integer, ForeignKey("departments.id"))


class TeacherDepartmentSubject(Base):
    __tablename__ = "teacher_department_subject"

    id = Column(Integer, primary_key=True, index=True)

    teacher_id = Column(Integer, ForeignKey("teachers.id"))

    department_id = Column(Integer, ForeignKey("departments.id"))

    subject_id = Column(Integer, ForeignKey("subjects.id"))


class SubjectSemesterYear(Base):
    __tablename__ = "subject_semester_year"

    id = Column(Integer, primary_key=True, index=True)

    subject_id = Column(Integer, ForeignKey("subjects.id"))

    year = Column(String, nullable=False)

    semester = Column(String, nullable=False)

class Lecture(Base):
    __tablename__ = "lectures"

    id = Column(Integer, primary_key=True)

    teacher_id = Column(
        Integer,
        ForeignKey("teachers.id")
    )

    subject_id = Column(
        Integer,
        ForeignKey("subjects.id")
    )

    title = Column(String)

    year = Column(String)

    semester = Column(String)

    division = Column(String)

    scheduled_date = Column(String)

    scheduled_time = Column(String)

    description = Column(String)

    actual_start = Column(DateTime)

    actual_end = Column(DateTime)

    status = Column(
        String,
        default="scheduled"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
    teacher = relationship("Teacher")
    
    subject = relationship("Subject")

class LectureMaterial(Base):
    __tablename__ = "lecture_materials"

    id = Column(Integer, primary_key=True)

    lecture_id = Column(
        Integer,
        ForeignKey("lectures.id")
    )

    title = Column(String)

    file_name = Column(String)

    file_path = Column(String)

    uploaded_at = Column(
        DateTime,
        default=datetime.utcnow
    )

# =========================================================
# MODIFIED: LectureRecording
# Added: marker_path, file_size, duration_seconds
# All existing columns unchanged.
# =========================================================
class LectureRecording(Base):
    __tablename__ = "lecture_recordings"

    id = Column(Integer, primary_key=True)

    lecture_id = Column(
        Integer,
        ForeignKey("lectures.id")
    )

    recording_path = Column(String)

    total_students = Column(Integer)

    students_present = Column(Integer)

    attendance_percentage = Column(Integer)

    average_attention = Column(Integer)

    duration_minutes = Column(Integer)

    # ── NEW COLUMNS (nullable, backward-compatible) ───────
    marker_path = Column(String, nullable=True)        # path to markers.json
    file_size = Column(Integer, nullable=True)         # bytes of .webm file
    duration_seconds = Column(Integer, nullable=True)  # recording length in seconds
    # ── END NEW COLUMNS ───────────────────────────────────

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class LectureDocument(Base):
    __tablename__ = "lecture_documents"

    id = Column(
        Integer,
        primary_key=True
    )

    lecture_id = Column(
        Integer,
        ForeignKey("lectures.id")
    )

    file_name = Column(String)

    file_path = Column(String)

    uploaded_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class LectureAttendance(Base):
    __tablename__ = "lecture_attendance"

    id = Column(
        Integer,
        primary_key=True
    )

    lecture_id = Column(
        Integer,
        ForeignKey("lectures.id")
    )

    student_id = Column(
        Integer,
        ForeignKey("students.id")
    )

    joined_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    left_at = Column(
        DateTime
    )

    total_minutes = Column(
        Integer,
        default=0
    )


# =========================================================
# LIVE LECTURE ADDITIONS (NEW TABLES ONLY)
# Nothing above this line was modified.
# =========================================================

class LectureChatMessage(Base):
    __tablename__ = "lecture_chat_messages"

    id = Column(Integer, primary_key=True, index=True)

    lecture_id = Column(Integer, ForeignKey("lectures.id"))

    sender_type = Column(String)   # "teacher" or "student"

    sender_id = Column(Integer)    # teacher_id or student_id

    sender_name = Column(String)

    message = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)


class LecturePoll(Base):
    __tablename__ = "lecture_polls"

    id = Column(Integer, primary_key=True, index=True)

    lecture_id = Column(Integer, ForeignKey("lectures.id"))

    question = Column(String)

    option_a = Column(String)
    option_b = Column(String)
    option_c = Column(String, nullable=True)
    option_d = Column(String, nullable=True)

    status = Column(String, default="open")   # "open" or "closed"

    created_at = Column(DateTime, default=datetime.utcnow)

    correct_option = Column(String, nullable=True)   # "A"/"B"/"C"/"D" or NULL


# =========================================================
# ANALYTICS ADDITIONS (NEW TABLE ONLY)
# Nothing above this line was modified.
# =========================================================

class LectureAnalytics(Base):
    __tablename__ = "lecture_analytics"

    id = Column(Integer, primary_key=True, index=True)

    lecture_id = Column(Integer, ForeignKey("lectures.id"))
    student_id = Column(Integer, ForeignKey("students.id"))

    attention_percentage = Column(Integer, default=0)
    focus_time_seconds = Column(Integer, default=0)
    away_time_seconds = Column(Integer, default=0)
    samples_count = Column(Integer, default=0)
    attention_sum = Column(Integer, default=0)

    face_present = Column(String, default="unknown")

    face_present_count = Column(Integer, default=0)
    face_missing_count = Column(Integer, default=0)

    started_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow)


class LecturePollAnswer(Base):
    __tablename__ = "lecture_poll_answers"

    id = Column(Integer, primary_key=True, index=True)

    poll_id = Column(Integer, ForeignKey("lecture_polls.id"))

    student_id = Column(Integer, ForeignKey("students.id"))

    selected_option = Column(String)   # "A" / "B" / "C" / "D"

    created_at = Column(DateTime, default=datetime.utcnow)

    is_correct = Column(String, nullable=True)   # "correct" / "incorrect" / NULL
