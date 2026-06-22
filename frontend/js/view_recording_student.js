/**
 * view_recording_student.js
 * Student Recording Viewer – DigiRoom
 *
 * Reads:  ?lecture_id=<N>&student_id=<N>
 *
 * Eligibility:  Student can only watch recordings for lectures where
 *               lecture.year == student.year AND lecture.division == student.division
 *               (same restriction used in live lectures / student_api.py)
 *
 * APIs used:
 *   GET /api/recording/info/{lecture_id}
 *   GET /api/student/lecture-history?student_id=<N>   (verifies eligibility)
 *   GET /api/student/materials?lecture_id=<N>
 */

(function () {
    "use strict";

    /* ── URL params ─────────────────────────────────────── */
    const params     = new URLSearchParams(window.location.search);
    const lectureId  = params.get("lecture_id");
    const studentId  = params.get("student_id");

    /* ── Guards ─────────────────────────────────────────── */
    if (!lectureId || !studentId) {
        showError("Missing lecture_id or student_id in URL.");
        return;
    }

    /* ── Sidebar / back links ───────────────────────────── */
    document.getElementById("back-dashboard").href =
        `/student/dashboard?id=${studentId}`;
    document.getElementById("back-history").href =
        `/student/student_lecture_history?id=${studentId}`;
    document.getElementById("btn-back").addEventListener("click", () => {
        window.location.href =
            `/student/student_lecture_history?id=${studentId}`;
    });

    /* ── Elements ───────────────────────────────────────── */
    const video         = document.getElementById("lecture-video");
    const titleEl       = document.getElementById("lecture-title");
    const metaEl        = document.getElementById("lecture-meta");
    const durationEl    = document.getElementById("info-duration");
    const dateEl        = document.getElementById("info-date");
    const subjectEl     = document.getElementById("info-subject");
    const markerList    = document.getElementById("marker-list");
    const materialsCard = document.getElementById("materials-card");
    const materialsList = document.getElementById("materials-list");

    /* ── Helpers ────────────────────────────────────────── */
    function fmtSeconds(s) {
        if (!s && s !== 0) return "—";
        const h   = Math.floor(s / 3600);
        const m   = Math.floor((s % 3600) / 60);
        const sec = Math.floor(s % 60);
        if (h > 0) return `${h}:${String(m).padStart(2,"0")}:${String(sec).padStart(2,"0")}`;
        return `${m}:${String(sec).padStart(2,"0")}`;
    }

    function fmtDate(iso) {
        if (!iso) return "—";
        try {
            return new Date(iso).toLocaleDateString("en-IN", {
                day: "2-digit", month: "short", year: "numeric"
            });
        } catch { return iso; }
    }

    function escHtml(str) {
        return String(str)
            .replace(/&/g,"&amp;")
            .replace(/</g,"&lt;")
            .replace(/>/g,"&gt;")
            .replace(/"/g,"&quot;");
    }

    function showError(msg) {
        if (titleEl) titleEl.textContent = "Access Denied";
        if (metaEl)  metaEl.textContent  = msg;
        if (video)   video.style.display = "none";
    }

    /* ── Marker list ─────────────────────────────────────── */
    function buildMarkers(markers) {
        if (!markers || markers.length === 0) return;

        markerList.innerHTML = "";

        markers.forEach(m => {
            const btn = document.createElement("button");
            btn.className     = "marker-item";
            btn.dataset.time  = m.time;
            btn.innerHTML = `
                <div class="marker-dot"></div>
                <div class="marker-info">
                    <div class="marker-title">${escHtml(m.title)}</div>
                    <div class="marker-time">${fmtSeconds(m.time)}</div>
                </div>
                <span class="marker-play-icon">▶</span>
            `;

            btn.addEventListener("click", () => {
                video.currentTime = m.time;
                video.play();
                document.querySelectorAll(".marker-item").forEach(b =>
                    b.classList.remove("active")
                );
                btn.classList.add("active");
            });

            markerList.appendChild(btn);
        });
    }

    /* ── Highlight current marker during playback ────────── */
    video.addEventListener("timeupdate", () => {
        const t     = video.currentTime;
        const items = document.querySelectorAll(".marker-item");
        let activeIdx = -1;

        items.forEach((btn, i) => {
            if (t >= parseFloat(btn.dataset.time)) activeIdx = i;
        });

        items.forEach((btn, i) =>
            btn.classList.toggle("active", i === activeIdx)
        );
    });

    /* ── Duration from video element ─────────────────────── */
    video.addEventListener("loadedmetadata", () => {
        if (video.duration && isFinite(video.duration)) {
            durationEl.textContent = fmtSeconds(video.duration);
        }
    });

    /* ── Load materials ───────────────────────────────────── */
    async function loadMaterials() {
        try {
            const res  = await fetch(`/api/student/materials?lecture_id=${lectureId}&student_id=${studentId}`);
            if (!res.ok) return;
            const data = await res.json();

            const docs = data.documents      || [];
            const pres = data.presentations  || [];
            const recs = data.recordings     || [];

            const all = [
                ...pres.map(p => ({ name: p.file_name, url: `/api/student/download-presentation/${p.id}`, icon: "📊" })),
                ...docs.map(d => ({ name: d.file_name, url: `/api/student/download-document/${d.id}`,     icon: "📄" })),
            ];

            if (all.length === 0) return;

            materialsCard.style.display = "block";
            materialsList.innerHTML = all.map(f => `
                <a class="material-item" href="${f.url}" download>
                    <span class="material-icon">${f.icon}</span>
                    <span class="material-name">${escHtml(f.name)}</span>
                    <span class="material-dl">⬇</span>
                </a>
            `).join("");

        } catch (e) {
            console.warn("Materials load failed:", e);
        }
    }

    /* ── Main ────────────────────────────────────────────── */
    async function loadRecording() {
        titleEl.textContent = "Loading…";

        try {
            // 1. Verify eligibility via student lecture-history
            //    (student_api only returns lectures matching student year+division)
            const histRes  = await fetch(
                `/api/student/lecture-history?student_id=${studentId}`
            );
            const histData = await histRes.json();
            const eligible = histData.find(
                l => String(l.id) === String(lectureId)
            );

            if (!eligible) {
                showError("You are not authorised to view this recording.");
                return;
            }

            // 2. Fetch recording info
            const recRes  = await fetch(`/api/recording/info/${lectureId}`);
            const recData = await recRes.json();

            if (!recData.has_recording) {
                titleEl.textContent = "Recording Not Available";
                metaEl.textContent  = "The recording for this lecture is not ready yet.";
                video.style.display = "none";
                return;
            }

            // ── Populate UI ──────────────────────────────
            titleEl.textContent = eligible.title   || `Lecture #${lectureId}`;
            metaEl.textContent  = eligible.subject
                ? `${eligible.subject} · ${eligible.date}`
                : eligible.date || "";

            dateEl.textContent    = fmtDate(recData.created_at);
            subjectEl.textContent = eligible.subject || "—";
            if (recData.duration_seconds) {
                durationEl.textContent = fmtSeconds(recData.duration_seconds);
            }

            // ── Video ─────────────────────────────────────
            const webmPath = recData.recording_path.replace(/\\/g, "/");
            video.src      = "/" + webmPath;

            // ── Markers ───────────────────────────────────
            buildMarkers(recData.markers);

            // ── Materials ─────────────────────────────────
            await loadMaterials();

        } catch (err) {
            console.error(err);
            showError("Error loading recording: " + err.message);
        }
    }

    loadRecording();

})();
