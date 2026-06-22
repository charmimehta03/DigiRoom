from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse

from backend.database.database import SessionLocal

from backend.database.models import (
    Teacher,
    Department,
    Subject,
    TeacherDepartmentSubject
)

router = APIRouter()

@router.get("/institute/assign/teacher/{teacher_id}")
def assign_teacher_page(teacher_id: int):

    db = SessionLocal()

    teacher = db.query(Teacher).filter(
        Teacher.id == teacher_id
    ).first()

    departments = db.query(Department).all()

    department_options = ""

    for dept in departments:
        department_options += f"""
        <option value='{dept.id}'>
            {dept.department_name}
        </option>
        """

    subjects = db.query(Subject).all()

    subject_data = []

    for sub in subjects:

        subject_data.append({
            "id": sub.id,
            "name": sub.subject_name,
            "department_id": sub.department_id
        })

    html = f"""

    <html>
    <body>

    <h1>Assign Department & Subject</h1>

    <h3>Teacher: {teacher.name}</h3>

    <form action='/institute/assign/teacher' method='post'>

        <input type='hidden' name='teacher_id' value='{teacher.id}'>

        <label>Select Department</label>

        <br><br>

        <select id='department' name='department_id' onchange='loadSubjects()'>

            {department_options}

        </select>

        <br><br>

        <label>Select Subject</label>

        <br><br>

        <select id='subject' name='subject_id'>
        </select>

        <br><br>

        <button type='submit'>
            Assign
        </button>

    </form>

    <script>

        const subjects = {subject_data};

        function loadSubjects() {{

            const departmentId = document.getElementById(
                "department"
            ).value;

            const subjectDropdown = document.getElementById(
                "subject"
            );

            subjectDropdown.innerHTML = "";

            subjects.forEach(subject => {{

                if(subject.department_id == departmentId) {{

                    subjectDropdown.innerHTML += `
                        <option value="${{subject.id}}">
                            ${{subject.name}}
                        </option>
                    `;
                }}

            }});

        }}

        // LOAD INITIAL SUBJECTS
        loadSubjects();

    </script>

    </body>
    </html>

    """

    return HTMLResponse(html)

@router.post("/institute/assign/teacher")
def assign_teacher(
    teacher_id: int = Form(...),
    department_id: int = Form(...),
    subject_id: int = Form(...)
):

    db = SessionLocal()

    assignment = TeacherDepartmentSubject(
        teacher_id=teacher_id,
        department_id=department_id,
        subject_id=subject_id
    )

    db.add(assignment)

    db.commit()

    return HTMLResponse(
        """

        <script>

            alert("Teacher Assigned Successfully");

            window.location.href='/institute/approved/teachers';

        </script>

        """
    )