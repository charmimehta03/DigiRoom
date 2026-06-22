const params =
    new URLSearchParams(
        window.location.search
    );

const studentId =
    params.get("id");

fetch(
    `/api/student/scheduled-lectures?student_id=${studentId}`
)
.then(response => response.json())
.then(data => {

    const tbody =
        document.getElementById(
            "scheduledTable"
        );

    tbody.innerHTML = "";

    data.forEach(item => {

        tbody.innerHTML += `

        <tr>

            <td>${item.title}</td>

            <td>${item.subject}</td>

            <td>${item.date}</td>

            <td>${item.time}</td>

        </tr>

        `;

    });

});