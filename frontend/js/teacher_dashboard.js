const params = new URLSearchParams(
    window.location.search
);

const teacherId = params.get("id");

fetch(
    `/api/teacher/dashboard?teacher_id=${teacherId}`
)
.then(response => response.json())
.then(data => {

    document.getElementById(
        "teacher-name"
    ).innerText =
        "Welcome, " + data.teacher_name;

    document.getElementById(
        "assigned-subjects"
    ).innerText =
        data.assigned_subjects;

    document.getElementById(
        "total-lectures"
    ).innerText =
        data.total_lectures;

    document.getElementById(
        "lectures-week"
    ).innerText =
        data.lectures_this_week;

    document.getElementById(
        "attendance"
    ).innerText =
        data.average_attendance + "%";

    document.getElementById(
        "attention"
    ).innerText =
        data.average_attention + "%";

    document.getElementById(
        "students"
    ).innerText =
        data.total_students;
});

fetch(
    `/api/teacher/upcoming-lectures?teacher_id=${teacherId}`
)
.then(response => response.json())
.then(lectures => {

    const tbody =
        document.getElementById(
            "lecture-table-body"
        );

    tbody.innerHTML = "";

    if (lectures.length === 0) {

        tbody.innerHTML = `
            <tr>
                <td colspan="5">
                    No upcoming lectures found
                </td>
            </tr>
        `;

        return;
    }

    lectures.forEach(lecture => {

        tbody.innerHTML += `
            <tr>

                <td>${lecture.date}</td>

                <td>${lecture.time}</td>

                <td>${lecture.title}</td>

                <td>${lecture.subject}</td>

                <td>

                    <button
                        class="table-btn edit"
                        onclick="editLecture(${lecture.id})">
                        Edit
                    </button>

                    <button
                        class="table-btn postpone"
                        onclick="postponeLecture(
                                ${lecture.id},
                                '${lecture.date}',
                                '${lecture.time}'
                            )">
                        Postpone
                    </button>

                    <button
                        class="table-btn delete"
                        onclick="deleteLecture(${lecture.id})">
                        Delete
                    </button>

                    ${
                        lecture.status === "live"
                        ?
                        `
                        <button
                            class="table-btn start"
                            onclick="joinLecture(${lecture.id})">
                            Join Again
                        </button>

                        <button
                            class="table-btn complete"
                            onclick="completeLecture(${lecture.id})">
                            Complete
                        </button>
                        `
                        :
                        `
                        <button
                            class="table-btn start"
                            onclick="startLecture(${lecture.id})">
                            Start
                        </button>
                        `
                    }

                </td>

            </tr>
        `;
    });

});

async function deleteLecture(lectureId)
{
    const confirmDelete = confirm(
        "Are you sure you want to delete this lecture?"
    );

    if (!confirmDelete)
    {
        return;
    }

    const response = await fetch(
        `/api/teacher/delete-lecture/${lectureId}`,
        {
            method: "DELETE"
        }
    );

    const result = await response.json();

    alert(result.message);

    location.reload();
}


let selectedLectureId = null;

function postponeLecture(
    id,
    currentDate,
    currentTime
)
{
    selectedLectureId = id;

    document.getElementById(
        "newDate"
    ).value = currentDate;

    document.getElementById(
        "newTime"
    ).value = currentTime;

    document.getElementById(
        "postponeModal"
    ).style.display = "flex";
}

function closePostponeModal()
{
    document.getElementById(
        "postponeModal"
    ).style.display = "none";
}

async function savePostpone()
{
    const newDate =
        document.getElementById(
            "newDate"
        ).value;

    const newTime =
        document.getElementById(
            "newTime"
        ).value;

    if (!newDate || !newTime)
    {
        alert(
            "Please select date and time"
        );

        return;
    }

    const formData =
        new FormData();

    formData.append(
        "scheduled_date",
        newDate
    );

    formData.append(
        "scheduled_time",
        newTime
    );

    const response =
        await fetch(
            `/api/teacher/postpone-lecture/${selectedLectureId}`,
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

    closePostponeModal();

    location.reload();
}

function editLecture(id)
{
    window.location.href =
        `/teacher/edit-lecture?id=${id}&teacher_id=${teacherId}`;
}


async function startLecture(
    lectureId
)
{
    const response =
        await fetch(
            `/api/teacher/start-lecture/${lectureId}`,
            {
                method: "PUT"
            }
        );

    const result =
        await response.json();

    alert(
        result.message
    );

    window.location.href =
        `/teacher/live-lecture?id=${lectureId}`;
}

function joinLecture(
    lectureId
)
{
    window.location.href =
        `/teacher/live-lecture?id=${lectureId}`;
}

async function completeLecture(
    lectureId
)
{
    const confirmComplete =
        confirm(
            "Mark lecture as completed?"
        );

    if(!confirmComplete)
    {
        return;
    }

    const response =
        await fetch(
            `/api/teacher/complete-lecture/${lectureId}`,
            {
                method: "PUT"
            }
        );

    const result =
        await response.json();

    alert(
        result.message
    );

    location.reload();
}