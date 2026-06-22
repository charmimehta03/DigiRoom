/**
 * lecture_history.js  (MODIFIED)
 * Teacher Lecture History – now shows recording availability + View Recording button
 */

(function () {
    "use strict";

    const params    = new URLSearchParams(window.location.search);
    const teacherId = params.get("id");

    /* Back link */
    const backLink = document.getElementById("back-link");
    if (backLink) backLink.href = `/teacher/dashboard?id=${teacherId}`;

    /* Search */
    const searchInput = document.getElementById("search");
    if (searchInput) {
        searchInput.addEventListener("input", () => {
            const q = searchInput.value.toLowerCase();
            document.querySelectorAll("#lecture-history-body tr").forEach(row => {
                row.style.display =
                    row.textContent.toLowerCase().includes(q) ? "" : "none";
            });
        });
    }

    /* ── Fetch all lectures for this teacher ──────────────── */
    fetch(`/api/teacher/lecture-history?teacher_id=${teacherId}`)
        .then(r => r.json())
        .then(async lectures => {

            const table = document.getElementById("lecture-history-body");
            table.innerHTML = "";

            if (!lectures || lectures.length === 0) {
                table.innerHTML = `<tr><td colspan="7" style="text-align:center;color:#8892B0;padding:2rem">No lectures found.</td></tr>`;
                return;
            }

            /* For each completed lecture, check if a recording exists */
            const recordingCache = {};

            const rows = await Promise.all(lectures.map(async lecture => {

                let hasRecording = false;

                if (lecture.status === "completed") {
                    try {
                        const rec = await fetch(`/api/recording/info/${lecture.id}`);
                        const recData = await rec.json();
                        hasRecording = recData.has_recording === true;
                        recordingCache[lecture.id] = hasRecording;
                    } catch (e) {
                        hasRecording = false;
                    }
                }

                const statusClass = {
                    completed:  "status-completed",
                    scheduled:  "status-upcoming",
                    cancelled:  "status-cancelled",
                    live:       "status-upcoming"
                }[lecture.status] || "";

                const recBadge = hasRecording
                    ? `<span class="badge-rec">🎬 Available</span>`
                    : (lecture.status === "completed"
                        ? `<span class="badge-none">—</span>`
                        : `<span class="badge-none">—</span>`);

                const actionBtn = hasRecording
                    ? `<a class="btn-view-rec"
                            href="/teacher/view-recording?lecture_id=${lecture.id}&teacher_id=${teacherId}">
                            ▶ View Recording
                        </a>`
                    : `<span class="badge-none" style="padding:6px 14px;">—</span>`;

                return `
                    <tr>
                        <td>${lecture.date || "—"}</td>
                        <td>${lecture.time || "—"}</td>
                        <td>${escHtml(lecture.title || "")}</td>
                        <td>${escHtml(lecture.subject || "")}</td>
                        <td><span class="${statusClass}">${lecture.status}</span></td>
                        <td>${recBadge}</td>
                        <td>${actionBtn}</td>
                    </tr>
                `;
            }));

            table.innerHTML = rows.join("");
        })
        .catch(err => {
            const table = document.getElementById("lecture-history-body");
            table.innerHTML = `<tr><td colspan="7" style="text-align:center;color:#EF4444;padding:2rem">Error loading lectures: ${err.message}</td></tr>`;
        });

    function escHtml(str) {
        return String(str)
            .replace(/&/g,"&amp;")
            .replace(/</g,"&lt;")
            .replace(/>/g,"&gt;");
    }

})();
