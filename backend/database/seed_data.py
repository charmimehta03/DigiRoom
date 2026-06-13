from backend.database.database import SessionLocal
from backend.database.models import (
    Department,
    Subject,
    SubjectSemesterYear
)

db = SessionLocal()

departments = [
    "Computer Engineering",
    "Information Technology",
    "Electronics Engineering",
    "Mechanical Engineering",
    "Civil Engineering"
]

saved_departments = {}

for dept_name in departments:

    existing = db.query(Department).filter(
        Department.department_name == dept_name
    ).first()

    if not existing:
        dept = Department(department_name=dept_name)

        db.add(dept)
        db.commit()
        db.refresh(dept)

        saved_departments[dept_name] = dept.id

    else:
        saved_departments[dept_name] = existing.id


subjects_data = {

    "Computer Engineering": [
        "Data Structures",
        "Algorithms",
        "Database Management",
        "Operating Systems",
        "Computer Networks",
        "Software Engineering",
        "Python Programming",
        "Java Programming",
        "Artificial Intelligence",
        "Machine Learning",
        "Cyber Security",
        "Cloud Computing",
        "Web Development",
        "Compiler Design",
        "Computer Graphics"
    ],

    "Information Technology": [
        "Information Security",
        "Web Technologies",
        "Data Mining",
        "Big Data Analytics",
        "Java",
        "Python",
        "Software Testing",
        "Mobile Computing",
        "Internet of Things",
        "Computer Organization",
        "Data Analytics",
        "Linux Administration",
        "DevOps",
        "Data Communication",
        "Project Management"
    ],

    "Electronics Engineering": [
        "Digital Electronics",
        "Analog Electronics",
        "Microprocessors",
        "Microcontrollers",
        "Signals and Systems",
        "Control Systems",
        "Embedded Systems",
        "Communication Engineering",
        "VLSI Design",
        "Power Electronics",
        "Electronic Devices",
        "Circuit Theory",
        "Industrial Electronics",
        "DSP",
        "Robotics"
    ],

    "Mechanical Engineering": [
        "Thermodynamics",
        "Fluid Mechanics",
        "Machine Design",
        "Manufacturing Process",
        "Heat Transfer",
        "Theory of Machines",
        "CAD CAM",
        "Industrial Engineering",
        "Strength of Materials",
        "Engineering Mechanics",
        "Automation",
        "Automobile Engineering",
        "Refrigeration and AC",
        "Metrology",
        "Welding Technology"
    ],

    "Civil Engineering": [
        "Structural Engineering",
        "Surveying",
        "Concrete Technology",
        "Transportation Engineering",
        "Environmental Engineering",
        "Geotechnical Engineering",
        "Hydraulics",
        "Building Construction",
        "Construction Management",
        "Water Resources",
        "Steel Structures",
        "Soil Mechanics",
        "Bridge Engineering",
        "Town Planning",
        "Irrigation Engineering"
    ]
}


for dept_name, subjects in subjects_data.items():

    dept_id = saved_departments[dept_name]

    for sub in subjects:

        existing_subject = db.query(Subject).filter(
            Subject.subject_name == sub,
            Subject.department_id == dept_id
        ).first()

        if not existing_subject:

            new_subject = Subject(
                subject_name=sub,
                department_id=dept_id
            )

            db.add(new_subject)

db.commit()

print("Departments and Subjects Added Successfully")


# ----------------------------------------
# SUBJECT SEMESTER YEAR MAPPING
# ----------------------------------------

all_subjects = db.query(Subject).all()

counter = 0

for subject in all_subjects:

    counter += 1

    # FIRST YEAR
    if counter % 4 == 1:
        year = "First Year"
        semester = "Sem 1"

    elif counter % 4 == 2:
        year = "First Year"
        semester = "Sem 2"

    # SECOND YEAR
    elif counter % 4 == 3:
        year = "Second Year"
        semester = "Sem 3"

    else:
        year = "Second Year"
        semester = "Sem 4"

    existing_mapping = db.query(
        SubjectSemesterYear
    ).filter(
        SubjectSemesterYear.subject_id == subject.id
    ).first()

    if not existing_mapping:

        mapping = SubjectSemesterYear(
            subject_id=subject.id,
            year=year,
            semester=semester
        )

        db.add(mapping)

db.commit()

print("Semester and Year Mapping Added Successfully")