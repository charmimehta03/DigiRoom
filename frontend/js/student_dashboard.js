const params =
    new URLSearchParams(
        window.location.search
    );

const studentId =
    params.get("id");



/* -------------------------
   LIVE LECTURES
-------------------------- */

fetch(
    `/api/student/live-lectures?student_id=${studentId}`
)
.then(response => response.json())
.then(lectures => {

    const tbody =
        document.getElementById(
            "liveLectureTable"
        );

    tbody.innerHTML = "";

    if(lectures.length === 0)
    {
        tbody.innerHTML = `
        <tr>
            <td colspan="4">
                No Live Lectures
            </td>
        </tr>
        `;
        return;
    }

    lectures.forEach(lecture => {

        tbody.innerHTML += `

        <tr>

            <td>${lecture.title}</td>

            <td>${lecture.date}</td>

            <td>${lecture.time}</td>

            <td>

                <button
                    onclick="
                        joinLecture(
                            ${lecture.id}
                        )
                    "
                >
                    Join
                </button>

            </td>

        </tr>

        `;

    });

});


function joinLecture(
    lectureId
)
{
    window.location.href =
    `/student/live-lecture?lecture_id=${lectureId}&student_id=${studentId}`;
}



/* -------------------------
   ANALYTICS
-------------------------- */

fetch(
    `/api/student/analytics?student_id=${studentId}`
)
.then(response => response.json())
.then(data => {

    document.getElementById(
        "totalLectures"
    ).innerText =
        data.total_lectures;

    document.getElementById(
        "attendedLectures"
    ).innerText =
        data.attended_lectures;

    document.getElementById(
        "attendancePercent"
    ).innerText =
        data.attendance_percentage + "%";

    document.getElementById(
        "averageMinutes"
    ).innerText =
        data.average_minutes;

    const labels =
        data.graph_data.map(
            x => x.lecture
        );

    const values =
        data.graph_data.map(
            x => x.minutes
        );

    new Chart(

    document.getElementById(
        "attendanceChart"
    ),

    {

        type:"bar",

        data:{

            labels:labels,

            datasets:[

                {

                    label:"Minutes Attended",

                    data:values,

                    backgroundColor:
                        "rgba(91,91,214,0.8)",

                    borderRadius:8

                }

            ]

        },

        options:{

            responsive:true,

            maintainAspectRatio:false,

            plugins:{

                legend:{
                    labels:{
                        color:"#F0F2FF"
                    }
                }
            },

            scales:{

                x:{
                    ticks:{
                        color:"#8892B0"
                    },

                    grid:{
                        color:"rgba(255,255,255,0.05)"
                    }
                },

                y:{
                    ticks:{
                        color:"#8892B0"
                    },

                    grid:{
                        color:"rgba(255,255,255,0.05)"
                    }
                }

            }

        }

    }

);

});