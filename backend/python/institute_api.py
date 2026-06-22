from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from backend.database.database import SessionLocal
from backend.database.models import Institute
from backend.database.models import (
    Teacher,
    Student,
    Department,
    Subject,
    TeacherDepartmentSubject
)

router = APIRouter()


# DATABASE SESSION
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# REGISTER INSTITUTE
@router.post("/institute/register")
def register_institute(
    institute_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    institute_code: str = Form(...)
):

    db: Session = SessionLocal()

    # CHECK EMAIL
    existing_email = db.query(Institute).filter(Institute.email == email).first()

    if existing_email:
        db.close()
        return HTMLResponse("<h2>Email already exists</h2>")

    # CHECK CODE
    existing_code = db.query(Institute).filter(Institute.institute_code == institute_code).first()

    if existing_code:
        db.close()
        return HTMLResponse("<h2>Institute code already exists</h2>")

    # CREATE NEW INSTITUTE
    new_institute = Institute(
        institute_name=institute_name,
        email=email,
        password=password,
        institute_code=institute_code
    )

    db.add(new_institute)
    db.commit()

    db.close()
    return HTMLResponse("<h2>Institute Registered Successfully</h2>")


# LOGIN
@router.post("/institute/login")
def login_institute(
    email: str = Form(...),
    password: str = Form(...)
):

    db: Session = SessionLocal()

    institute = db.query(Institute).filter(
        Institute.email == email,
        Institute.password == password
    ).first()

    if not institute:
        db.close()
        return HTMLResponse("<h2>Invalid Email or Password</h2>")

    db.close()
    return HTMLResponse(
        """
        <script>
            window.location.href='/institute/dashboard';
        </script>
        """
    )

@router.get("/institute/pending/teachers")
def pending_teachers():

    db: Session = SessionLocal()

    teachers = db.query(Teacher).filter(
        Teacher.status == "pending"
    ).all()

    result = """
    <html>
    <head>
        <title>Teachers</title>
    </head>

    <body>

    <h1>Teachers</h1>
    <p>
        <a href="/institute/dashboard">
            ← Back to Dashboard
        </a>
    </p>

<hr>
    <div style="margin-bottom:20px;">

        <a href="/institute/approved/teachers">
            Existing
        </a>

        |

        <a href="/institute/pending/teachers">
            Approval List
        </a>

    </div>

    <h2>Teacher Approval List</h2>

    <input
        type="text"
        id="teacherSearch"
        placeholder="Search Teacher..."
        onkeyup="searchTeachers()"
    >

    <br><br>
    """

    for teacher in teachers:

        result += f"""
        <div id="teacher-{teacher.id}" 
             style="margin-bottom:20px; border:1px solid black; padding:10px; width:300px;">

            <p><b>Name:</b> {teacher.name}</p>

            <p><b>Email:</b> {teacher.email}</p>

            <button onclick="approveTeacher({teacher.id})">
                Approve
            </button>

        </div>
        """

    result += """

    <script>
    function searchTeachers() {

        let input = document.getElementById(
            "teacherSearch"
        ).value.toLowerCase();

        let teachers = document.querySelectorAll(
            "[id^='teacher-']"
        );

        teachers.forEach(teacher => {

            let text = teacher.innerText.toLowerCase();

            if(text.includes(input)) {
                teacher.style.display = "block";
            }
            else {
                teacher.style.display = "none";
            }

        });

    }

    async function approveTeacher(teacherId) {

        let confirmAction = confirm(
            "Are you sure you want to approve this teacher?"
        );

        if (!confirmAction) {
            return;
        }

        let response = await fetch(
            `/institute/approve/teacher/${teacherId}`
        );

        let data = await response.text();

        // REMOVE ENTRY FROM PAGE
        document.getElementById(
            `teacher-${teacherId}`
        ).remove();

        alert("Teacher Approved Successfully");

    }

    </script>

    </body>
    </html>
    """

    db.close()
    return HTMLResponse(result)

@router.get("/institute/pending/students")
def pending_students():

    db: Session = SessionLocal()

    students = db.query(Student).filter(
        Student.status == "pending"
    ).all()

    result = """
    <html>
    <head>
        <title>Students</title>
    </head>

    <body>

    <h1>Students</h1>
    <p>
        <a href="/institute/dashboard">
            ← Back to Dashboard
        </a>
    </p>

    <hr>
    <div style="margin-bottom:20px;">

        <a href="/institute/approved/students">
            Existing
        </a>

        |

        <a href="/institute/pending/students">
            Approval List
        </a>

    </div>

    <h2>Student Approval List</h2>
    <input
        type="text"
        id="studentSearch"
        placeholder="Search Student..."
        onkeyup="searchStudents()"
    >

    <br><br>
    """

    for student in students:

        result += f"""
        <div id="student-{student.id}" 
             style="margin-bottom:20px; border:1px solid black; padding:10px; width:300px;">

            <p><b>Name:</b> {student.full_name}</p>

            <p><b>Email:</b> {student.email}</p>

            <p><b>Roll Number:</b> {student.roll_number}</p>

            <button onclick="approveStudent({student.id})">
                Approve
            </button>

        </div>
        """

    result += """

    <script>
    function searchStudents() {

        let input = document.getElementById(
            "studentSearch"
        ).value.toLowerCase();

        let students = document.querySelectorAll(
            "[id^='student-']"
        );

        students.forEach(student => {

            let text = student.innerText.toLowerCase();

            if(text.includes(input)) {
                student.style.display = "block";
            }
            else {
                student.style.display = "none";
            }

        });

    }
    async function approveStudent(studentId) {

        let confirmAction = confirm(
            "Are you sure you want to approve this student?"
        );

        if (!confirmAction) {
            return;
        }

        let response = await fetch(
            `/institute/approve/student/${studentId}`
        );

        let data = await response.text();

        // REMOVE ENTRY
        document.getElementById(
            `student-${studentId}`
        ).remove();

        alert("Student Approved Successfully");

    }

    </script>

    </body>
    </html>
    """

    db.close()
    return HTMLResponse(result)


@router.get("/institute/approve/teacher/{teacher_id}")
def approve_teacher(teacher_id: int):

    db: Session = SessionLocal()

    teacher = db.query(Teacher).filter(
        Teacher.id == teacher_id
    ).first()

    if not teacher:
        db.close()
        return HTMLResponse("<h2>Teacher Not Found</h2>")

    teacher.status = "approved"

    db.commit()

    db.close()
    return {"message": "Teacher Approved Successfully"}

@router.get("/institute/approve/student/{student_id}")
def approve_student(student_id: int):

    db: Session = SessionLocal()

    student = db.query(Student).filter(
        Student.id == student_id
    ).first()

    if not student:
        db.close()
        return HTMLResponse("<h2>Student Not Found</h2>")

    student.status = "approved"

    db.commit()

    db.close()
    return {"message": "Student Approved Successfully"}


@router.get("/institute/approved/teachers")
def approved_teachers():

    db: Session = SessionLocal()

    teachers = db.query(Teacher).filter(
        Teacher.status == "approved"
    ).all()

    result = """
    <html>
    <head>
        <title>Teachers</title>
    </head>

    <body>

    <h1>Teachers</h1>
    
    <p>
        <a href="/institute/dashboard">
            ← Back to Dashboard
        </a>
    </p>

    <hr>
    <div style="margin-bottom:20px;">

        <a href="/institute/approved/teachers">
            Existing
        </a>

        |

        <a href="/institute/pending/teachers">
            Approval List
        </a>

    </div>

    <h2>Existing Teachers</h2>

    <input
        type="text"
        id="approvedTeacherSearch"
        placeholder="Search Teacher..."
        onkeyup="searchApprovedTeachers()"
    >

    <br><br>
    """

    if not teachers:
        result += "<h3>No Approved Teachers</h3>"

    for teacher in teachers:

        result += f"""
        <div class="teacher-card" onclick="window.location.href='/institute/teacher/{teacher.id}'" style="
            margin-bottom:20px;
            border:1px solid green;
            padding:10px;
            width:500px;
        ">

            <p><b>Name:</b> {teacher.name}</p>

            <p><b>Email:</b> {teacher.email}</p>

            <p><b>Status:</b> {teacher.status}</p>
            <p>
                <button
                    onclick="event.stopPropagation(); removeTeacher({teacher.id})"
                    style="margin-top:10px;"
                >
                    Remove Teacher
                </button>
            </p>
            <p>
                <a href='/institute/assign/teacher/{teacher.id}' onclick="event.stopPropagation();">
                    Assign Department & Subject
                </a>
            </p>

            <hr>

            <h3>Assigned Subjects</h3>
        """

        assignments = db.query(
            TeacherDepartmentSubject
        ).filter(
            TeacherDepartmentSubject.teacher_id == teacher.id
        ).all()

        if not assignments:

            result += "<p>No Subjects Assigned</p>"

        else:

            for assignment in assignments:

                department = db.query(Department).filter(
                    Department.id == assignment.department_id
                ).first()

                subject = db.query(Subject).filter(
                    Subject.id == assignment.subject_id
                ).first()

                result += f"""
                <div id='assignment-{assignment.id}'
                     style='margin-bottom:10px;'>

                    <b>{department.department_name}</b> :
                    {subject.subject_name}

                    <button
                        onclick='event.stopPropagation(); removeAssignment({assignment.id})'
                        style='margin-left:10px;'
                    >
                        Remove
                    </button>

                </div>
                """

        result += "</div>"

    result += """

    <script>
    function searchApprovedTeachers() {

        let input = document.getElementById(
            "approvedTeacherSearch"
        ).value.toLowerCase();

        let teachers = document.querySelectorAll(
            ".teacher-card"
        );

        teachers.forEach(teacher => {

            let text = teacher.innerText.toLowerCase();

            if(text.includes(input)) {
                teacher.style.display = "block";
            }
            else {
                teacher.style.display = "none";
            }

        });

    }
    async function removeAssignment(assignmentId) {

        let confirmAction = confirm(
            "Are you sure you want to remove this subject?"
        );

        if(!confirmAction) {
            return;
        }

        let response = await fetch(
            `/institute/remove-assignment/${assignmentId}`
        );

        let data = await response.json();

        alert(data.message);

        location.reload();

    }

    async function removeTeacher(teacherId) {

        let confirmAction = confirm(
            "Are you sure you want to remove this teacher?"
        );

        if(!confirmAction){
            return;
        }

        let response = await fetch(
            `/institute/remove-teacher/${teacherId}`
        );

        let data = await response.json();

        alert(data.message);

        location.reload();
    }

    </script>

    </body>
    </html>
    """

    db.close()
    return HTMLResponse(result)

@router.get("/institute/approved/students")
def approved_students():

    db: Session = SessionLocal()

    students = db.query(Student).filter(
        Student.status == "approved"
    ).all()

    result = """
    <html>
    <head>
        <title>Students</title>
    </head>

    <body>

    <h1>Students</h1>
    <p>
        <a href="/institute/dashboard">
            ← Back to Dashboard
        </a>
    </p>

    <hr>
    <div style="margin-bottom:20px;">

        <a href="/institute/approved/students">
            Existing
        </a>

        |

        <a href="/institute/pending/students">
            Approval List
        </a>

    </div>

    <h2>Existing Students</h2>

    <input
        type="text"
        id="approvedStudentSearch"
        placeholder="Search Student..."
        onkeyup="searchApprovedStudents()"
    >

    <br><br>
    """

    if not students:
        result += "<h3>No Approved Students</h3>"

    for student in students:

        result += f"""
        <div class="student-card" onclick="window.location.href='/institute/student/{student.id}'" style="
            margin-bottom:20px;
            border:1px solid green;
            padding:10px;
            width:300px;
        ">

            <p><b>Name:</b> {student.full_name}</p>

            <p><b>Email:</b> {student.email}</p>

            <p><b>Roll Number:</b> {student.roll_number}</p>

            <p><b>Status:</b> {student.status}</p>
            
            <p>
                <button
                    onclick="event.stopPropagation(); removeStudent({student.id})"
                    style="margin-top:10px;"
                >
                    Remove Student
                </button>
            </p>

        </div>
        """

    result += """

    <script>
    function searchApprovedStudents() {

        let input = document.getElementById(
            "approvedStudentSearch"
        ).value.toLowerCase();

        let students = document.querySelectorAll(
            ".student-card"
        );

        students.forEach(student => {

            let text = student.innerText.toLowerCase();

            if(text.includes(input)) {
                student.style.display = "block";
            }
            else {
                student.style.display = "none";
            }

        });

    }

    async function removeStudent(studentId) {

        let confirmAction = confirm(
            "Are you sure you want to remove this student?"
        );

        if(!confirmAction){
            return;
        }

        let response = await fetch(
            `/institute/remove-student/${studentId}`
        );

        let data = await response.json();

        alert(data.message);

        location.reload();
    }

    </script>

    </body>
    </html>
    """

    db.close()
    return HTMLResponse(result)

@router.get("/institute/remove-assignment/{assignment_id}")
def remove_assignment(assignment_id: int):

    db: Session = SessionLocal()

    assignment = db.query(
        TeacherDepartmentSubject
    ).filter(
        TeacherDepartmentSubject.id == assignment_id
    ).first()

    if not assignment:
        db.close()
        return {"message": "Assignment Not Found"}

    db.delete(assignment)

    db.commit()

    db.close()
    return {"message": "Assignment Removed Successfully"}

@router.get("/institute/remove-student/{student_id}")
def remove_student(student_id: int):

    db: Session = SessionLocal()

    student = db.query(Student).filter(
        Student.id == student_id
    ).first()

    if not student:
        db.close()
        return {"message": "Student Not Found"}

    db.delete(student)

    db.commit()

    db.close()
    return {"message": "Student Removed Successfully"}


@router.get("/institute/remove-teacher/{teacher_id}")
def remove_teacher(teacher_id: int):

    db: Session = SessionLocal()

    teacher = db.query(Teacher).filter(
        Teacher.id == teacher_id
    ).first()

    if not teacher:
        db.close()
        return {"message": "Teacher Not Found"}

    assignments = db.query(
        TeacherDepartmentSubject
    ).filter(
        TeacherDepartmentSubject.teacher_id == teacher_id
    ).all()

    for assignment in assignments:
        db.delete(assignment)

    db.delete(teacher)

    db.commit()

    db.close()
    return {"message": "Teacher Removed Successfully"}

@router.get("/institute/teacher/{teacher_id}")
def teacher_details(teacher_id: int):

    db = SessionLocal()

    teacher = db.query(Teacher).filter(
        Teacher.id == teacher_id
    ).first()

    if not teacher:
        db.close()
        return HTMLResponse("<h1>Teacher Not Found</h1>")

    html = f"""

    <html>

    <body>

    <h1>Teacher Details</h1>

    <p>
        <a href="/institute/approved/teachers">
            ← Back
        </a>
    </p>

    <hr>

    <h2>{teacher.name}</h2>

    <p>Email: {teacher.email}</p>

    <h3>Assigned Subjects</h3>

    """

    assignments = db.query(
        TeacherDepartmentSubject
    ).filter(
        TeacherDepartmentSubject.teacher_id == teacher.id
    ).all()

    if not assignments:

        html += "<p>No Subjects Assigned</p>"

    else:

        for assignment in assignments:

            department = db.query(
                Department
            ).filter(
                Department.id == assignment.department_id
            ).first()

            subject = db.query(
                Subject
            ).filter(
                Subject.id == assignment.subject_id
            ).first()

            html += f"""
            <p>
                {department.department_name}
                :
                {subject.subject_name}
            </p>
            """

    html += """

    <hr>

    <h2>Statistics</h2>

    <p>Total Lectures Taken : 0</p>

    <p>Total Hours Taught : 0</p>

    <p>Average Students Present : 0</p>

    <p>Highest Attendance : 0</p>

    <p>Lowest Attendance : 0</p>

    <p>Total Students Taught : 0</p>

    <p>Average Student Attention : 0%</p>

    </body>

    </html>

    """

    db.close()
    return HTMLResponse(html)

@router.get("/institute/student/{student_id}")
def student_details(student_id: int):

    db = SessionLocal()

    student = db.query(Student).filter(
        Student.id == student_id
    ).first()

    if not student:
        db.close()
        return HTMLResponse("<h1>Student Not Found</h1>")

    html = f"""

    <html>

    <body>

    <h1>Student Details</h1>

    <p>
        <a href="/institute/approved/students">
            ← Back
        </a>
    </p>

    <hr>

    <h2>{student.full_name}</h2>

    <p>Email : {student.email}</p>

    <p>Roll Number : {student.roll_number}</p>

    <p>Course : {student.course}</p>

    <p>Year : {student.year}</p>

    <p>Division : {student.division}</p>

    <hr>

    <h2>Statistics</h2>

    <p>Attendance Percentage : 0%</p>

    <p>Total Lectures Attended : 0</p>

    <p>Lectures Missed : 0</p>

    <p>Average Attention Score : 0%</p>

    <p>Highest Attention Score : 0%</p>

    <p>Lowest Attention Score : 0%</p>

    <p>Average Session Duration : 0 Minutes</p>

    <p>Assignments Submitted : 0</p>

    <p>Assignments Pending : 0</p>

    <hr>

    <h2>AI Analytics</h2>

    <p>DBMS : 0%</p>

    <p>Operating Systems : 0%</p>

    <p>Computer Networks : 0%</p>

    </body>

    </html>

    """

    db.close()
    return HTMLResponse(html)

@router.get("/api/institute/dashboard")
def dashboard_data():

    db = SessionLocal()

    result = {
        "total_teachers": db.query(Teacher).count(),

        "approved_teachers": db.query(Teacher).filter(
            Teacher.status == "approved"
        ).count(),

        "pending_teachers": db.query(Teacher).filter(
            Teacher.status == "pending"
        ).count(),

        "total_students": db.query(Student).count(),

        "approved_students": db.query(Student).filter(
            Student.status == "approved"
        ).count(),

        "pending_students": db.query(Student).filter(
            Student.status == "pending"
        ).count(),

        "departments": db.query(Department).count(),

        "subjects": db.query(Subject).count()
    }

    db.close()
    return result