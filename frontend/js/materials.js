function showSection(section)
{
    document.getElementById(
        "presentations-section"
    ).style.display = "none";

    document.getElementById(
        "documents-section"
    ).style.display = "none";

    document.getElementById(
        "recordings-section"
    ).style.display = "none";

    document.getElementById(
        section + "-section"
    ).style.display = "block";
}

const params = new URLSearchParams(
    window.location.search
);

const teacherId = params.get("id");

/* LOAD LECTURES */

fetch(
    `/api/teacher/lectures?teacher_id=${teacherId}`
)
.then(response => response.json())
.then(lectures => {

    const dropdown =
        document.getElementById(
            "lecture"
        );

    lectures.forEach(lecture => {

        dropdown.innerHTML += `
            <option value="${lecture.id}">
                ${lecture.title}
            </option>
        `;
    });

});


/* LOAD DOCUMENTS */

loadDocuments();
loadPresentations();
loadRecordings();

function loadRecordings()
{
    fetch(
        `/api/teacher/recordings?teacher_id=${teacherId}`
    )
    .then(response => response.json())
    .then(recordings => {

        const tbody =
            document.getElementById(
                "recordings-table"
            );

        tbody.innerHTML = "";

        recordings.forEach(recording => {

            tbody.innerHTML += `

                <tr>

                    <td>
                        ${recording.date}
                    </td>

                    <td>
                        ${recording.lecture}
                    </td>

                    <td>
                        ${recording.subject}
                    </td>

                    <td>
                        ${recording.duration} min
                    </td>

                    <td>
                        ${recording.attendance}%
                    </td>

                    <td>
                        ${recording.attention}%
                    </td>

                    <td>

                        <a
                            href="/api/teacher/download-recording/${recording.id}"
                            target="_blank"
                        >
                            Download
                        </a>

                        <button
                            onclick="
                                deleteRecording(
                                    ${recording.id}
                                )
                            "
                        >
                            Delete
                        </button>

                    </td>

                </tr>

            `;
        });

    });
}

async function deleteRecording(
    recordingId
)
{
    const confirmDelete =
        confirm(
            "Delete recording?"
        );

    if(!confirmDelete)
    {
        return;
    }

    const response =
        await fetch(
            `/api/teacher/delete-recording/${recordingId}`,
            {
                method: "DELETE"
            }
        );

    const result =
        await response.json();

    alert(
        result.message
    );

    loadRecordings();
}


function loadDocuments()
{
    fetch(
        `/api/teacher/documents?teacher_id=${teacherId}`
    )
    .then(response => response.json())
    .then(documents => {

        const tbody =
            document.getElementById(
                "documents-table"
            );

        tbody.innerHTML = "";

        documents.forEach(doc => {

            tbody.innerHTML += `

                <tr>

                    <td>
                        ${doc.date}
                    </td>

                    <td>
                        ${doc.lecture}
                    </td>

                    <td>
                        ${doc.subject}
                    </td>

                    <td>
                        ${doc.file_name}
                    </td>

                    <td>
                        ${doc.file_type}
                    </td>

                    <td>

                        <a
                            href="/api/teacher/download-document/${doc.id}"
                            target="_blank"
                        >
                            Download
                        </a>

                        <button
                            onclick="deleteDocument(${doc.id})"
                        >
                            Delete
                        </button>

                    </td>

                </tr>

            `;
        });

    });
}


/* UPLOAD DOCUMENT */

document
.getElementById(
    "upload-form"
)
.addEventListener(
    "submit",
    async function(e)
    {

        e.preventDefault();

        const file =
            document.getElementById(
                "document"
            ).files[0];

        if (!file)
        {
            alert(
                "Please select a file"
            );

            return;
        }

        const formData =
            new FormData();

        formData.append(
            "lecture_id",
            document.getElementById(
                "lecture"
            ).value
        );

        formData.append(
            "document",
            file
        );

        const response =
            await fetch(
                "/api/teacher/upload-document",
                {
                    method: "POST",
                    body: formData
                }
            );

        const result =
            await response.json();

        alert(
            result.message
        );

        loadDocuments();

        document.getElementById(
            "upload-form"
        ).reset();

    }
);


/* DELETE DOCUMENT */

async function deleteDocument(
    documentId
)
{
    const confirmDelete =
        confirm(
            "Delete document?"
        );

    if (!confirmDelete)
    {
        return;
    }

    const response =
        await fetch(
            `/api/teacher/delete-document/${documentId}`,
            {
                method: "DELETE"
            }
        );

    const result =
        await response.json();

    alert(
        result.message
    );

    loadDocuments();
}


function loadPresentations()
{
    fetch(
        `/api/teacher/presentations?teacher_id=${teacherId}`
    )
    .then(response => response.json())
    .then(presentations => {

        const tbody =
            document.getElementById(
                "presentations-table"
            );

        tbody.innerHTML = "";

        presentations.forEach(ppt => {

            tbody.innerHTML += `

                <tr>

                    <td>
                        ${ppt.date}
                    </td>

                    <td>
                        ${ppt.lecture}
                    </td>

                    <td>
                        ${ppt.subject}
                    </td>

                    <td>
                        ${ppt.file_name}
                    </td>

                    <td>

                        <a
                            href="/api/teacher/download-presentation/${ppt.id}"
                            target="_blank"
                        >
                            Download
                        </a>

                        <button
                            onclick="deletePresentation(${ppt.id})"
                        >
                            Delete
                        </button>

                    </td>

                </tr>

            `;
        });

    });
}

async function deletePresentation(
    materialId
)
{
    const confirmDelete =
        confirm(
            "Delete presentation?"
        );

    if(!confirmDelete)
    {
        return;
    }

    const response =
        await fetch(
            `/api/teacher/delete-presentation/${materialId}`,
            {
                method: "DELETE"
            }
        );

    const result =
        await response.json();

    alert(
        result.message
    );

    loadPresentations();
}   

showSection(
    "presentations"
);


document
.getElementById("search")
.addEventListener(
    "keyup",
    function()
    {
        const value =
            this.value.toLowerCase();

        const visibleTable =
            document.querySelector(
                "#presentations-section[style*='block'] tbody, " +
                "#documents-section[style*='block'] tbody, " +
                "#recordings-section[style*='block'] tbody"
            );

        if(!visibleTable)
        {
            return;
        }

        const rows =
            visibleTable.querySelectorAll(
                "tr"
            );

        rows.forEach(row => {

            const text =
                row.innerText
                .toLowerCase();

            row.style.display =
                text.includes(value)
                ? ""
                : "none";

        });
    }
);