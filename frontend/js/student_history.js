/**
 * student_history.js  (MODIFIED)
 * Student Lecture History – adds Recording column and Watch Recording button
 */

(function () {
    "use strict";

    const params    = new URLSearchParams(window.location.search);
    const studentId = params.get("id");

    /* Sidebar nav links */
    const navDashboard = document.getElementById("nav-dashboard");
    const navScheduled = document.getElementById("nav-scheduled");
    if (navDashboard) navDashboard.href = `/student/dashboard?id=${studentId}`;
    if (navScheduled) navScheduled.href = `/student/scheduled-lectures?id=${studentId}`;

    /* ── Fetch student lecture history ──────────────────── */
    fetch(`/api/student/lecture-history?student_id=${studentId}`)
        .then(r => r.json())
        .then(async data => {

            const tbody = document.getElementById("historyTable");
            tbody.innerHTML = "";

            if (!data || data.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="7" style="text-align:center;color:#8892B0;padding:2rem">
                            No completed lectures found.
                        </td>
                    </tr>
                `;
                return;
            }

            /* Check recording availability for each lecture */
            const rows = await Promise.all(data.map(async item => {

                let hasRecording = false;
                try {
                    const rec     = await fetch(`/api/recording/info/${item.id}`);
                    const recData = await rec.json();
                    hasRecording  = recData.has_recording === true;
                } catch (e) {
                    hasRecording = false;
                }

                const recBadge = hasRecording
                    ? `<span class="badge-rec">🎬 Available</span>`
                    : `<span class="badge-none">—</span>`;

                const actionBtn = hasRecording
                    ? `<a class="btn-watch-rec"
                            href="/student/view-recording?lecture_id=${item.id}&student_id=${studentId}">
                            ▶ Watch
                        </a>`
                    : `<span class="badge-none">—</span>`;

                return `
                    <tr>
                        <td>${escHtml(item.title)}</td>
                        <td>${escHtml(item.subject || "—")}</td>
                        <td>${item.date  || "—"}</td>
                        <td>${item.time  || "—"}</td>
                        <td>${item.minutes != null ? item.minutes + " min" : "—"}</td>
                        <td>${recBadge}</td>
                        <td>${actionBtn}</td>
                    </tr>
                `;
            }));

            tbody.innerHTML = rows.join("");
        })
        .catch(err => {
            const tbody = document.getElementById("historyTable");
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align:center;color:#EF4444;padding:2rem">
                        Error loading history: ${err.message}
                    </td>
                </tr>
            `;
        });

    function escHtml(str) {
        return String(str)
            .replace(/&/g,"&amp;")
            .replace(/</g,"&lt;")
            .replace(/>/g,"&gt;");
    }

})();
