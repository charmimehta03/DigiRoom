/**
 * view_recording_teacher.js
 * Teacher Recording Viewer – DigiRoom
 *
 * Reads:  ?lecture_id=<N>&teacher_id=<N>
 * APIs used:
 *   GET /api/recording/info/{lecture_id}      — recording path + markers
 *   GET /api/teacher/lecture-history          — lecture meta (subject, date)
 *   GET /api/student/materials?lecture_id=N   — lecture materials list
 */

(function () {
    "use strict";

    /* ── URL params ─────────────────────────────────────── */
    const params     = new URLSearchParams(window.location.search);
    const lectureId  = params.get("lecture_id");
    const teacherId  = params.get("teacher_id");

    /* ── Guards ─────────────────────────────────────────── */
    if (!lectureId || !teacherId) {
        document.querySelector(".main-content").innerHTML =
            '<p class="state-msg">❌ Missing lecture_id or teacher_id in URL.</p>';
        return;
    }

    /* ── Sidebar links ──────────────────────────────────── */
    document.getElementById("back-dashboard").href =
        `/teacher/dashboard?id=${teacherId}`;
    document.getElementById("back-history").href =
        `/teacher/lecture-history?id=${teacherId}`;
    document.getElementById("btn-back").addEventListener("click", () => {
        window.location.href = `/teacher/lecture-history?id=${teacherId}`;
    });

    /* ── Elements ───────────────────────────────────────── */
    const video          = document.getElementById("lecture-video");
    const titleEl        = document.getElementById("lecture-title");
    const metaEl         = document.getElementById("lecture-meta");
    const durationEl     = document.getElementById("info-duration");
    const sizeEl         = document.getElementById("info-size");
    const dateEl         = document.getElementById("info-date");
    const subjectEl      = document.getElementById("info-subject");
    const markerList     = document.getElementById("marker-list");
    const materialsCard  = document.getElementById("materials-card");
    const materialsList  = document.getElementById("materials-list");
    const downloadBtn    = document.getElementById("download-btn");

    /* ── Helpers ────────────────────────────────────────── */
    function fmtSeconds(s) {
        if (!s && s !== 0) return "—";
        const h = Math.floor(s / 3600);
        const m = Math.floor((s % 3600) / 60);
        const sec = Math.floor(s % 60);
        if (h > 0) return `${h}:${String(m).padStart(2,"0")}:${String(sec).padStart(2,"0")}`;
        return `${m}:${String(sec).padStart(2,"0")}`;
    }

    function fmtBytes(b) {
        if (!b) return "—";
        if (b < 1024) return `${b} B`;
        if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
        return `${(b / (1024 * 1024)).toFixed(1)} MB`;
    }

    function fmtDate(iso) {
        if (!iso) return "—";
        try {
            return new Date(iso).toLocaleDateString("en-IN", {
                day: "2-digit", month: "short", year: "numeric"
            });
        } catch { return iso; }
    }

    /* ── Build marker list ──────────────────────────────── */
    function buildMarkers(markers) {
        if (!markers || markers.length === 0) return;

        markerList.innerHTML = "";

        markers.forEach((m, idx) => {
            const btn = document.createElement("button");
            btn.className = "marker-item";
            btn.dataset.time = m.time;
            btn.innerHTML = `
                <div class="marker-dot"></div>
                <div class="marker-info">
                    <div class="marker-title">${escHtml(m.title)}</div>
                    <div class="marker-time">${fmtSeconds(m.time)}</div>
                </div>
                <span class="marker-play-icon">▶</span>
            `;

            btn.addEventListener("click", () => {
                // Seek video
                video.currentTime = m.time;
                video.play();
                // Highlight active marker
                document.querySelectorAll(".marker-item").forEach(b =>
                    b.classList.remove("active")
                );
                btn.classList.add("active");
            });

            markerList.appendChild(btn);
        });
    }

    /* ── Highlight active marker while playing ──────────── */
    video.addEventListener("timeupdate", () => {
        const t = video.currentTime;
        const items = document.querySelectorAll(".marker-item");
        let activeIdx = -1;

        items.forEach((btn, i) => {
            const markerTime = parseFloat(btn.dataset.time);
            if (t >= markerTime) activeIdx = i;
        });

        items.forEach((btn, i) => {
            btn.classList.toggle("active", i === activeIdx);
        });
    });

    /* ── Show duration from video metadata ──────────────── */
    video.addEventListener("loadedmetadata", () => {
        if (video.duration && isFinite(video.duration)) {
            durationEl.textContent = fmtSeconds(video.duration);
        }
    });

    /* ── Escape HTML ─────────────────────────────────────── */
    function escHtml(str) {
        return String(str)
            .replace(/&/g,"&amp;")
            .replace(/</g,"&lt;")
            .replace(/>/g,"&gt;")
            .replace(/"/g,"&quot;");
    }

    /* ── Load materials ──────────────────────────────────── */
    async function loadMaterials() {
        try {
            const res  = await fetch(`/api/student/materials?lecture_id=${lectureId}`);
            if (!res.ok) return;
            const data = await res.json();

            const docs  = data.documents  || [];
            const pres  = data.presentations || [];
            const all   = [
                ...docs.map(d  => ({ name: d.file_name,  url: `/api/teacher/download-document/${d.id}`,      icon: "📄" })),
                ...pres.map(p  => ({ name: p.file_name,  url: `/api/teacher/download-presentation/${p.id}`,  icon: "📊" }))
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

    /* ── Main load ───────────────────────────────────────── */
    async function loadRecording() {
        titleEl.textContent = "Loading recording…";

        try {
            // 1. Recording info (path + markers)
            const recRes  = await fetch(`/api/recording/info/${lectureId}`);
            const recData = await recRes.json();

            if (!recData.has_recording) {
                titleEl.textContent = "No Recording Found";
                metaEl.textContent  = "This lecture has no saved recording yet.";
                video.style.display = "none";
                return;
            }

            // 2. Lecture meta from history endpoint
            let lectureMeta = null;
            try {
                const histRes  = await fetch(`/api/teacher/lecture-history?teacher_id=${teacherId}`);
                const histData = await histRes.json();
                lectureMeta = histData.find(l => String(l.id) === String(lectureId));
            } catch (e) { /* non-fatal */ }

            // ── Populate title & meta ────────────────────
            const lectureTitle = lectureMeta ? lectureMeta.title : `Lecture #${lectureId}`;
            titleEl.textContent = lectureTitle;
            metaEl.textContent  = lectureMeta
                ? `${lectureMeta.subject} · ${lectureMeta.date}`
                : "";

            // ── Info strip ───────────────────────────────
            sizeEl.textContent    = fmtBytes(recData.file_size_bytes);
            dateEl.textContent    = fmtDate(recData.created_at);
            subjectEl.textContent = lectureMeta ? lectureMeta.subject : "—";
            if (recData.duration_seconds) {
                durationEl.textContent = fmtSeconds(recData.duration_seconds);
            }

            // ── Video source ─────────────────────────────
            // Serve via /uploads/ static mount
            const webmPath   = recData.recording_path.replace(/\\/g, "/");
            // recording_path stored as e.g. uploads/recordings/lecture_1_foo/recording.webm
            const videoUrl   = "/" + webmPath;
            video.src        = videoUrl;

            // ── Download button ──────────────────────────
            downloadBtn.href     = videoUrl;
            downloadBtn.download = `${lectureTitle.replace(/[^a-z0-9]/gi,"_")}.webm`;

            // ── Markers ──────────────────────────────────
            buildMarkers(recData.markers);

            // ── Materials ─────────────────────────────────
            await loadMaterials();

        } catch (err) {
            console.error(err);
            titleEl.textContent = "Error loading recording";
            metaEl.textContent  = err.message;
        }
    }

    loadRecording();

})();
