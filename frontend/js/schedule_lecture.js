const params = new URLSearchParams(
    window.location.search
);

const teacherId = params.get("id");

/* LOAD SUBJECTS */

fetch(
    `/api/teacher/subjects?teacher_id=${teacherId}`
)
.then(response => response.json())
.then(subjects => {

    const dropdown =
        document.getElementById("subject");

    subjects.forEach(subject => {

        dropdown.innerHTML += `
            <option value="${subject.id}">
                ${subject.name}
            </option>
        `;
    });

});


/* SAVE LECTURE */

document
.getElementById("lecture-form")
.addEventListener("submit", async function(e){

    e.preventDefault();

    const formData = new FormData();

    formData.append(
        "teacher_id",
        teacherId
    );

    formData.append(
        "title",
        document.getElementById("title").value
    );

    formData.append(
        "subject_id",
        document.getElementById("subject").value
    );

    formData.append(
        "year",
        document.getElementById("year").value
    );

    formData.append(
        "semester",
        document.getElementById("semester").value
    );

    formData.append(
        "division",
        document.getElementById("division").value
    );

    formData.append(
        "scheduled_date",
        document.getElementById("scheduled_date").value
    );

    formData.append(
        "scheduled_time",
        document.getElementById("scheduled_time").value
    );

    formData.append(
        "description",
        document.getElementById("description").value
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
    const response = await fetch(
        "/api/teacher/create-lecture",
        {
            method: "POST",
            body: formData
        }
    );

    const result =
        await response.json();

    alert(result.message);

    window.location.href =
        "/teacher/dashboard?id=" +
        teacherId;

});