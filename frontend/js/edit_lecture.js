const params = new URLSearchParams(
    window.location.search
);

const lectureId = params.get("id");

const teacherId = params.get(
    "teacher_id"
);

let lectureData = null;


/* LOAD LECTURE */

fetch(
    `/api/teacher/lecture/${lectureId}`
)
.then(response => response.json())
.then(data => {
    if(data.ppt_name)
        {
            document.getElementById(
                "current-ppt"
            ).innerHTML =

            `
                <b>Current PPT:</b>

                ${data.ppt_name}
            `;
        }
    lectureData = data;

    document.getElementById(
        "title"
    ).value =
        data.title;

    document.getElementById(
        "year"
    ).value =
        data.year;

    document.getElementById(
        "semester"
    ).value =
        data.semester;

    document.getElementById(
        "division"
    ).value =
        data.division;

    document.getElementById(
        "scheduled_date"
    ).value =
        data.scheduled_date;

    document.getElementById(
        "scheduled_time"
    ).value =
        data.scheduled_time;

    document.getElementById(
        "description"
    ).value =
        data.description || "";

    loadSubjects();
});


/* LOAD SUBJECTS */

function loadSubjects()
{
    fetch(
        `/api/teacher/subjects?teacher_id=${teacherId}`
    )
    .then(response => response.json())
    .then(subjects => {

        const dropdown =
            document.getElementById(
                "subject"
            );

        dropdown.innerHTML =
            `<option value="">
                Select Subject
            </option>`;

        subjects.forEach(subject => {

            dropdown.innerHTML += `
                <option value="${subject.id}">
                    ${subject.name}
                </option>
            `;
        });

        if (lectureData)
        {
            dropdown.value =
                lectureData.subject_id;
        }
    });
}


/* UPDATE LECTURE */

document
.getElementById("lecture-form")
.addEventListener(
    "submit",
    async function(e)
    {
        e.preventDefault();

        const formData =
            new FormData();

        formData.append(
            "title",
            document.getElementById(
                "title"
            ).value
        );

        formData.append(
            "subject_id",
            document.getElementById(
                "subject"
            ).value
        );

        formData.append(
            "year",
            document.getElementById(
                "year"
            ).value
        );

        formData.append(
            "semester",
            document.getElementById(
                "semester"
            ).value
        );

        formData.append(
            "division",
            document.getElementById(
                "division"
            ).value
        );

        formData.append(
            "scheduled_date",
            document.getElementById(
                "scheduled_date"
            ).value
        );

        formData.append(
            "scheduled_time",
            document.getElementById(
                "scheduled_time"
            ).value
        );

        formData.append(
            "description",
            document.getElementById(
                "description"
            ).value
        );
        const pptFile =
    document.getElementById(
        "ppt_file"
    ).files[0];

        if(pptFile)
        {
            formData.append(
                "ppt_file",
                pptFile
            );
        }

        const response =
            await fetch(
                `/api/teacher/update-lecture/${lectureId}`,
                {
                    method: "PUT",
                    body: formData
                }
            );

        const result =
            await response.json();

        alert(
            result.message
        );

        window.location.href =
            `/teacher/dashboard?id=${teacherId}`;
    }
);