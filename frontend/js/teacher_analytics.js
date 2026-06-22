const params = new URLSearchParams(window.location.search);
const teacherId = params.get("id");

let charts = {};

function destroyChart(key) {
    if (charts[key]) {
        charts[key].destroy();
        charts[key] = null;
    }
}

function showView(name) {
    document.querySelectorAll(".analytics-view").forEach(v => v.style.display = "none");
    document.getElementById("view-" + name).style.display = "block";
}

function setBreadcrumb(crumbs) {
    const el = document.getElementById("breadcrumb");
    el.innerHTML = "";
    crumbs.forEach((c, i) => {
        const span = document.createElement("span");
        span.className = "crumb" + (i === crumbs.length - 1 ? " active" : "");
        span.innerText = c.label;
        if (i !== crumbs.length - 1) {
            span.onclick = c.onClick;
        }
        el.appendChild(span);
    });
}

/* ============================================================
   OVERVIEW
   ============================================================ */
async function loadOverview() {

    showView("overview");
    setBreadcrumb([{ label: "Overall Class Analytics" }]);

    const res = await fetch(`/api/teacher/analytics/overview?teacher_id=${teacherId}`);
    const data = await res.json();

    document.getElementById("ov-attendance").innerText = data.average_attendance + "%";
    document.getElementById("ov-attention").innerText = data.average_attention + "%";
    document.getElementById("ov-lectures").innerText = data.total_lectures;
    document.getElementById("ov-students").innerText = data.total_students;
    document.getElementById("ov-poll").innerText = data.average_poll_participation + "%";
    document.getElementById("ov-chat").innerText = data.average_chat_participation + "%";

    const lectures = data.lectures || [];

    destroyChart("bar");
    charts.bar = new Chart(document.getElementById("chartLectureBar"), {
        type: "bar",
        data: {
            labels: lectures.map(l => l.title || ("Lecture " + l.lecture_id)),
            datasets: [
                { label: "Attendance %", data: lectures.map(l => l.attendance_percentage), backgroundColor: "#2563eb" },
                { label: "Attention %", data: lectures.map(l => l.average_attention), backgroundColor: "#16a34a" }
            ]
        },
        options: { responsive: true, scales: { y: { beginAtZero: true, max: 100 } } }
    });

    destroyChart("pie");
    charts.pie = new Chart(document.getElementById("chartEngagementPie"), {
        type: "pie",
        data: {
            labels: ["Attendance", "Attention", "Poll Participation", "Chat Participation"],
            datasets: [{
                data: [
                    data.average_attendance,
                    data.average_attention,
                    data.average_poll_participation,
                    data.average_chat_participation
                ],
                backgroundColor: ["#2563eb", "#16a34a", "#f59e0b", "#dc2626"]
            }]
        }
    });

    const mostList = document.getElementById("most-active-list");
    mostList.innerHTML = "";
    (data.most_active_lectures || []).forEach(l => {
        mostList.innerHTML += `<li><span>${l.title || "Lecture " + l.lecture_id}</span><span>${l.activity_score}%</span></li>`;
    });

    const leastList = document.getElementById("least-active-list");
    leastList.innerHTML = "";
    (data.least_active_lectures || []).forEach(l => {
        leastList.innerHTML += `<li><span>${l.title || "Lecture " + l.lecture_id}</span><span>${l.activity_score}%</span></li>`;
    });

    const rows = document.getElementById("lecture-rows");
    rows.innerHTML = "";
    if (lectures.length === 0) {
        rows.innerHTML = `<tr><td colspan="6">No lecture data yet</td></tr>`;
    }
    lectures.forEach(l => {
        rows.innerHTML += `
            <tr>
                <td>${l.date || ""}</td>
                <td>${l.title || ""}</td>
                <td>${l.attendance_percentage}%</td>
                <td>${l.average_attention}%</td>
                <td>${l.status}</td>
                <td><button class="table-btn edit" onclick="loadLecture(${l.lecture_id})">View</button></td>
            </tr>
        `;
    });
}

/* ============================================================
   LECTURE DRILLDOWN
   ============================================================ */
async function loadLecture(lectureId) {

    showView("lecture");
    setBreadcrumb([
        { label: "Overall Class Analytics", onClick: loadOverview },
        { label: "Lecture" }
    ]);

    const res = await fetch(`/api/teacher/analytics/lecture/${lectureId}`);
    const data = await res.json();

    if (data.message) {
        alert(data.message);
        loadOverview();
        return;
    }

    const stats = data.lecture;

    document.getElementById("lecture-stats-grid").innerHTML = `
        <div class="stat-card"><h3>Attendance</h3><div class="stat-value">${stats.attendance_percentage}%</div></div>
        <div class="stat-card"><h3>Average Attention</h3><div class="stat-value">${stats.average_attention}%</div></div>
        <div class="stat-card"><h3>Students Present</h3><div class="stat-value">${stats.students_present}</div></div>
        <div class="stat-card"><h3>Duration</h3><div class="stat-value">${stats.duration_minutes}m</div></div>
        <div class="stat-card"><h3>Poll Participation</h3><div class="stat-value">${stats.poll_participation_percentage}%</div></div>
        <div class="stat-card"><h3>Chat Participation</h3><div class="stat-value">${stats.chat_participation_percentage}%</div></div>
    `;

    const students = data.students || [];

    destroyChart("studentAttention");
    charts.studentAttention = new Chart(document.getElementById("chartStudentAttention"), {
        type: "bar",
        data: {
            labels: students.map(s => s.name),
            datasets: [{ label: "Attention %", data: students.map(s => s.attention_percentage), backgroundColor: "#16a34a" }]
        },
        options: { responsive: true, scales: { y: { beginAtZero: true, max: 100 } } }
    });

    destroyChart("attendancePie");
    charts.attendancePie = new Chart(document.getElementById("chartAttendancePie"), {
        type: "pie",
        data: {
            labels: ["Present", "Absent"],
            datasets: [{
                data: [stats.students_present, Math.max(stats.total_students - stats.students_present, 0)],
                backgroundColor: ["#2563eb", "#e2e8f0"]
            }]
        }
    });

    const rows = document.getElementById("student-rows");
    rows.innerHTML = "";
    if (students.length === 0) {
        rows.innerHTML = `<tr><td colspan="6">No students attended this lecture</td></tr>`;
    }
    students.forEach(s => {
        rows.innerHTML += `
            <tr>
                <td>${s.name}</td>
                <td>${s.roll_number}</td>
                <td>${s.time_present_minutes}m</td>
                <td>${s.attention_percentage}%</td>
                <td>${s.chat_messages}</td>
                <td><button class="table-btn edit" onclick="loadStudent(${s.student_id})">View</button></td>
            </tr>
        `;
    });

    /* ---- Polls in this lecture (new) ---- */
    const polls = data.polls || [];
    const gradedPolls = polls.filter(p => p.has_correct_answer);

    const pollChartsWrap = document.getElementById("lecture-poll-charts");
    pollChartsWrap.style.display = gradedPolls.length > 0 ? "grid" : "none";

    if (gradedPolls.length > 0) {
        destroyChart("lecturePollAccuracy");
        charts.lecturePollAccuracy = new Chart(document.getElementById("chartLecturePollAccuracy"), {
            type: "bar",
            data: {
                labels: gradedPolls.map(p => p.question.length > 25 ? p.question.slice(0, 25) + "…" : p.question),
                datasets: [{ label: "Accuracy %", data: gradedPolls.map(p => p.accuracy_percentage), backgroundColor: "#16a34a" }]
            },
            options: { responsive: true, scales: { y: { beginAtZero: true, max: 100 } } }
        });

        destroyChart("lectureAccuracyTrend");
        charts.lectureAccuracyTrend = new Chart(document.getElementById("chartLectureAccuracyTrend"), {
            type: "line",
            data: {
                labels: gradedPolls.map((p, i) => "Poll " + (i + 1)),
                datasets: [{
                    label: "Class Accuracy %",
                    data: gradedPolls.map(p => p.accuracy_percentage),
                    borderColor: "#f59e0b",
                    backgroundColor: "rgba(245,158,11,0.15)",
                    fill: true,
                    tension: 0.3
                }]
            },
            options: { responsive: true, scales: { y: { beginAtZero: true, max: 100 } } }
        });
    }

    const pollRows = document.getElementById("lecture-poll-rows");
    pollRows.innerHTML = "";
    if (polls.length === 0) {
        pollRows.innerHTML = `<tr><td colspan="7">No polls created in this lecture</td></tr>`;
    }
    polls.forEach(p => {
        pollRows.innerHTML += `
            <tr>
                <td>${p.question}</td>
                <td>${p.has_correct_answer ? (p.correct_text || p.correct_option) : "—"}</td>
                <td>${p.total_responses}</td>
                <td>${p.has_correct_answer ? p.correct_responses : "—"}</td>
                <td>${p.has_correct_answer ? p.incorrect_responses : "—"}</td>
                <td>${p.skipped_count}</td>
                <td>${p.accuracy_percentage !== null ? p.accuracy_percentage + "%" : "—"}</td>
            </tr>
        `;
    });
}

/* ============================================================
   INDIVIDUAL STUDENT ANALYTICS
   ============================================================ */
async function loadStudent(studentId) {

    showView("student");
    setBreadcrumb([
        { label: "Overall Class Analytics", onClick: loadOverview },
        { label: "Student" }
    ]);

    const res = await fetch(`/api/teacher/analytics/student/${teacherId}/${studentId}`);
    const data = await res.json();

    if (data.message) {
        alert(data.message);
        loadOverview();
        return;
    }

    const d = data.student_details;
    const att = data.attendance_analytics;
    const attn = data.attention_analytics;
    const part = data.participation_analytics;
    const pollA = data.poll_analytics || {};
    const chatA = data.chat_analytics || {};
    const perf = data.performance || {};

    document.getElementById("student-header").innerHTML = `
        <h2>${d.name}</h2>
        <span>Roll No: ${d.roll_number}</span>
        <span>Department: ${d.department}</span>
        <span>Year: ${d.year}</span>
        <span>Semester: ${d.semester}</span>
        <span>Division: ${d.division}</span>
    `;

    document.getElementById("st-attendance").innerText = att.attendance_percentage + "%";
    document.getElementById("st-attended").innerText = att.attended_lectures + "/" + att.total_lectures;
    document.getElementById("st-time").innerText = att.time_present_minutes + "m";
    document.getElementById("st-attention").innerText = attn.average_attention + "%";
    document.getElementById("st-poll").innerText = part.poll_participation_percentage + "%";
    document.getElementById("st-chat").innerText = part.chat_messages;

    /* ---- Overall performance ---- */
    document.getElementById("perf-score").innerText = (perf.performance_percentage ?? 0) + "%";
    document.getElementById("perf-rank").innerText = perf.class_rank
        ? `#${perf.class_rank} of ${perf.class_size}`
        : "-";
    document.getElementById("perf-poll-accuracy").innerText = (pollA.poll_accuracy_percentage ?? 0) + "%";

    /* ---- Attention trend (existing chart, unchanged) ---- */
    const trend = attn.attention_trend || [];

    destroyChart("attentionTrend");
    charts.attentionTrend = new Chart(document.getElementById("chartAttentionTrend"), {
        type: "line",
        data: {
            labels: trend.map(t => t.title || t.date || ("Lecture " + t.lecture_id)),
            datasets: [{
                label: "Attention %",
                data: trend.map(t => t.attention_percentage === null ? 0 : t.attention_percentage),
                borderColor: "#2563eb",
                backgroundColor: "rgba(37,99,235,0.15)",
                fill: true,
                tension: 0.3
            }]
        },
        options: { responsive: true, scales: { y: { beginAtZero: true, max: 100 } } }
    });

    /* ---- Focus vs Away (existing chart, unchanged) ---- */
    destroyChart("focusAway");
    charts.focusAway = new Chart(document.getElementById("chartFocusAway"), {
        type: "pie",
        data: {
            labels: ["Focus Time", "Away Time"],
            datasets: [{
                data: [attn.focus_time_seconds, attn.away_time_seconds],
                backgroundColor: ["#16a34a", "#dc2626"]
            }]
        }
    });

    /* ---- Attendance breakdown pie (new) ---- */
    destroyChart("studentAttendancePie");
    charts.studentAttendancePie = new Chart(document.getElementById("chartStudentAttendancePie"), {
        type: "pie",
        data: {
            labels: ["Attended", "Missed"],
            datasets: [{
                data: [att.attended_lectures, Math.max(att.total_lectures - att.attended_lectures, 0)],
                backgroundColor: ["#2563eb", "#e2e8f0"]
            }]
        }
    });

    /* ---- Attendance per lecture bar (new) ---- */
    const attendanceTable = att.attendance_table || [];
    destroyChart("studentAttendanceBar");
    charts.studentAttendanceBar = new Chart(document.getElementById("chartStudentAttendanceBar"), {
        type: "bar",
        data: {
            labels: attendanceTable.map(r => r.title || ("Lecture " + r.lecture_id)),
            datasets: [{
                label: "Time Present (min)",
                data: attendanceTable.map(r => r.time_present_minutes),
                backgroundColor: attendanceTable.map(r => r.attended ? "#16a34a" : "#dc2626")
            }]
        },
        options: { responsive: true, scales: { y: { beginAtZero: true } } }
    });

    /* ---- Attendance detail table (new) ---- */
    const attRows = document.getElementById("attendance-detail-rows");
    attRows.innerHTML = "";
    if (attendanceTable.length === 0) {
        attRows.innerHTML = `<tr><td colspan="4">No lecture data yet</td></tr>`;
    }
    attendanceTable.forEach(r => {
        attRows.innerHTML += `
            <tr>
                <td>${r.date || ""}</td>
                <td>${r.title || ""}</td>
                <td>${r.attended ? "✓ Present" : "✗ Absent"}</td>
                <td>${r.time_present_minutes}m</td>
            </tr>
        `;
    });

    /* ---- Daily attention line (new) ---- */
    const daily = attn.daily_attention_graph || [];
    destroyChart("dailyAttention");
    charts.dailyAttention = new Chart(document.getElementById("chartDailyAttention"), {
        type: "line",
        data: {
            labels: daily.map(r => r.date),
            datasets: [{
                label: "Avg Attention %",
                data: daily.map(r => r.attention_percentage),
                borderColor: "#f59e0b",
                backgroundColor: "rgba(245,158,11,0.15)",
                fill: true,
                tension: 0.3
            }]
        },
        options: { responsive: true, scales: { y: { beginAtZero: true, max: 100 } } }
    });

    /* ---- Attention distribution pie (new) ---- */
    const dist = attn.attention_distribution || {};
    destroyChart("attentionDistribution");
    charts.attentionDistribution = new Chart(document.getElementById("chartAttentionDistribution"), {
        type: "pie",
        data: {
            labels: Object.keys(dist),
            datasets: [{
                data: Object.values(dist),
                backgroundColor: ["#16a34a", "#f59e0b", "#dc2626"]
            }]
        }
    });

    /* ---- Poll analytics (new) ---- */
    document.getElementById("poll-score").innerText = pollA.poll_score ?? 0;
    document.getElementById("poll-correct").innerText = pollA.correct_answers_count ?? 0;
    document.getElementById("poll-incorrect").innerText = pollA.incorrect_answers_count ?? 0;
    document.getElementById("poll-skipped").innerText = pollA.skipped_count ?? 0;

    destroyChart("pollCorrectIncorrect");
    charts.pollCorrectIncorrect = new Chart(document.getElementById("chartPollCorrectIncorrect"), {
        type: "pie",
        data: {
            labels: ["Correct", "Incorrect", "Skipped"],
            datasets: [{
                data: [
                    pollA.correct_answers_count || 0,
                    pollA.incorrect_answers_count || 0,
                    pollA.skipped_count || 0
                ],
                backgroundColor: ["#16a34a", "#dc2626", "#94a3b8"]
            }]
        }
    });

    const pollList = pollA.polls || [];
    const gradedPollList = pollList.filter(p => p.correct_option);
    destroyChart("pollWiseAccuracy");
    charts.pollWiseAccuracy = new Chart(document.getElementById("chartPollWiseAccuracy"), {
        type: "bar",
        data: {
            labels: gradedPollList.map((p, i) => "Poll " + (i + 1)),
            datasets: [{
                label: "Result (1 = correct)",
                data: gradedPollList.map(p => p.result === "correct" ? 1 : 0),
                backgroundColor: gradedPollList.map(p => p.result === "correct" ? "#16a34a" : "#dc2626")
            }]
        },
        options: { responsive: true, scales: { y: { beginAtZero: true, max: 1, ticks: { stepSize: 1 } } } }
    });

    const pollRows = document.getElementById("poll-detail-rows");
    pollRows.innerHTML = "";
    if (pollList.length === 0) {
        pollRows.innerHTML = `<tr><td colspan="6">No polls in this student's lectures yet</td></tr>`;
    }
    const resultLabel = { correct: "✓ Correct", incorrect: "✗ Incorrect", skipped: "— Skipped", ungraded: "Ungraded" };
    pollList.forEach(p => {
        const selectedText = p.selected_option ? `${p.selected_option}. ${p.options[p.selected_option] || ""}` : "—";
        const correctText = p.correct_option ? `${p.correct_option}. ${p.options[p.correct_option] || ""}` : "—";
        pollRows.innerHTML += `
            <tr>
                <td>${p.lecture_title || ""}</td>
                <td>${p.question}</td>
                <td>${selectedText}</td>
                <td>${correctText}</td>
                <td>${resultLabel[p.result] || p.result}</td>
                <td>${p.submitted_at ? new Date(p.submitted_at).toLocaleString() : "—"}</td>
            </tr>
        `;
    });

    /* ---- Chat analytics (new) ---- */
    document.getElementById("chat-total").innerText = chatA.total_messages ?? 0;
    document.getElementById("chat-questions").innerText = chatA.questions_asked ?? 0;
    document.getElementById("chat-engagement").innerText = chatA.engagement_score ?? 0;

    const activity = chatA.message_activity || [];
    destroyChart("messageActivity");
    charts.messageActivity = new Chart(document.getElementById("chartMessageActivity"), {
        type: "bar",
        data: {
            labels: activity.map(a => a.title || ("Lecture " + a.lecture_id)),
            datasets: [{ label: "Messages", data: activity.map(a => a.message_count), backgroundColor: "#2563eb" }]
        },
        options: { responsive: true, scales: { y: { beginAtZero: true } } }
    });

    destroyChart("participationMix");
    charts.participationMix = new Chart(document.getElementById("chartParticipationMix"), {
        type: "pie",
        data: {
            labels: ["Poll Participation %", "Chat Engagement Score"],
            datasets: [{
                data: [part.poll_participation_percentage || 0, chatA.engagement_score || 0],
                backgroundColor: ["#f59e0b", "#2563eb"]
            }]
        }
    });

    const chatRows = document.getElementById("chat-message-rows");
    chatRows.innerHTML = "";
    const messages = chatA.messages || [];
    if (messages.length === 0) {
        chatRows.innerHTML = `<tr><td colspan="4">No chat messages yet</td></tr>`;
    }
    messages.forEach(m => {
        chatRows.innerHTML += `
            <tr>
                <td>Lecture ${m.lecture_id}</td>
                <td>${m.message}</td>
                <td>${m.is_question ? "Yes" : "No"}</td>
                <td>${m.created_at ? new Date(m.created_at).toLocaleString() : ""}</td>
            </tr>
        `;
    });

    /* ---- Class comparison (new) ---- */
    const comparison = perf.class_comparison || [];
    destroyChart("classComparison");
    charts.classComparison = new Chart(document.getElementById("chartClassComparison"), {
        type: "bar",
        data: {
            labels: comparison.map(s => s.name),
            datasets: [{
                label: "Performance %",
                data: comparison.map(s => s.performance_percentage),
                backgroundColor: comparison.map(s => s.student_id === studentId ? "#2563eb" : "#cbd5e1")
            }]
        },
        options: { responsive: true, scales: { y: { beginAtZero: true, max: 100 } } }
    });
}

loadOverview();
