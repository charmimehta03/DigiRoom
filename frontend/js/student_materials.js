const params =
    new URLSearchParams(
        window.location.search
    );

const studentId =
    params.get("id");

fetch(
    `/api/student/materials?student_id=${studentId}`
)
.then(response => response.json())
.then(data => {

    const tbody =
        document.getElementById(
            "materialsTable"
        );

    tbody.innerHTML = "";

    if(data.length === 0)
    {
        tbody.innerHTML = `
        <tr>
            <td colspan="5">
                No Materials Available
            </td>
        </tr>
        `;
        return;
    }

    data.forEach(item => {

        let downloadLink = "#";

        if(item.type === "Presentation")
        {
            downloadLink =
            `/api/student/download-presentation/${item.id}`;
        }

        else if(item.type === "Document")
        {
            downloadLink =
            `/api/student/download-document/${item.id}`;
        }

        else if(item.type === "Recording")
        {
            downloadLink =
            `/api/student/download-recording/${item.id}`;
        }

        tbody.innerHTML += `

        <tr>

            <td>${item.type}</td>

            <td>${item.lecture}</td>

            <td>${item.subject}</td>

            <td>${item.file_name}</td>

            <td>

                <a
                    href="${downloadLink}"
                    target="_blank"
                >
                    Download
                </a>

            </td>

        </tr>

        `;

    });

});