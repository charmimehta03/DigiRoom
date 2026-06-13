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