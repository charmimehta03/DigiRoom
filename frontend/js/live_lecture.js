/* =========================================================
   live_lecture.js
   Teacher-side live lecture page controller.
   Loaded AFTER socket.io.min.js and BEFORE webrtc_teacher.js,
   chat.js, poll.js (see live_lecture.html script order).
   ========================================================= */

const socket = io();

let localStream = null;
let screenStream = null;
let isCamOn = true;
let isMicOn = true;

const params = new URLSearchParams(window.location.search);
const lectureId = params.get("id");

/* Globals consumed by chat.js / poll.js */
const role = "teacher";
let senderId = params.get("teacher_id") || null;
let senderName = "Teacher";


/* ---------------------------------------------------------
   Join the signaling room immediately so student_joined
   events aren't missed.
   --------------------------------------------------------- */
socket.emit("teacher_join", { lecture_id: lectureId });


/* ---------------------------------------------------------
   Load lecture details (existing endpoint, unchanged).
   --------------------------------------------------------- */
fetch(`/api/teacher/live-lecture/${lectureId}`)
.then(response => response.json())
.then(data => {

    document.getElementById("lecture-title").innerText = data.title;
    document.getElementById("subject-name").innerText = data.subject;

    senderName = data.teacher_name || "Teacher";

    if (data.presentation_id) {
        document.getElementById("downloadPresentation").href =
            `/api/teacher/download-presentation/${data.presentation_id}`;
    } else {
        document.getElementById("downloadPresentation").innerText =
            "No Presentation Uploaded";
    }
})
.catch(error => console.log(error));


/* ---------------------------------------------------------
   Acquire camera + mic, then announce readiness.
   --------------------------------------------------------- */
navigator.mediaDevices
.getUserMedia({ video: true, audio: true })
.then(stream => {

    localStream = stream;

    document.getElementById("teacherVideo").srcObject = stream;

    console.log("Teacher Ready Sent");

    socket.emit("teacher_ready", { lecture_id: lectureId });
})
.catch(error => console.log(error));


/* ---------------------------------------------------------
   Camera / Mic toggle buttons.
   --------------------------------------------------------- */
const camToggleBtn = document.getElementById("toggleCamera");
const micToggleBtn = document.getElementById("toggleMic");

if (camToggleBtn) {
    camToggleBtn.addEventListener("click", () => {

        if (!localStream) return;

        isCamOn = !isCamOn;

        localStream.getVideoTracks().forEach(track => {
            track.enabled = isCamOn;
        });

        camToggleBtn.innerText = isCamOn ? "Turn Camera Off" : "Turn Camera On";

        socket.emit("teacher_camera_toggle", {
            lecture_id: lectureId,
            cam_on: isCamOn
        });
    });
}

if (micToggleBtn) {
    micToggleBtn.addEventListener("click", () => {

        if (!localStream) return;

        isMicOn = !isMicOn;

        localStream.getAudioTracks().forEach(track => {
            track.enabled = isMicOn;
        });

        micToggleBtn.innerText = isMicOn ? "Mute Mic" : "Unmute Mic";

        socket.emit("teacher_mic_toggle", {
            lecture_id: lectureId,
            mic_on: isMicOn
        });
    });
}


/* ---------------------------------------------------------
   Screen Share start / stop.
   --------------------------------------------------------- */
document.getElementById("shareScreen")
.addEventListener("click", async () => {

    if (screenStream) {
        stopScreenShare();
        return;
    }

    try {

        screenStream = await navigator.mediaDevices.getDisplayMedia({
            video: true
        });

        document.getElementById("screenVideo").srcObject = screenStream;

        document.getElementById("shareScreen").innerText = "Stop Screen Share";

        socket.emit("screen_share_start", { lecture_id: lectureId });

        if (typeof broadcastScreenShareToAll === "function") {
            broadcastScreenShareToAll();
        }

        // Auto-stop if the user stops sharing from the browser's
        // native "Stop sharing" control.
        screenStream.getVideoTracks()[0].onended = stopScreenShare;

    } catch (error) {
        console.log("Screen Share Error:", error);
    }
});

function stopScreenShare() {

    if (!screenStream) return;

    screenStream.getTracks().forEach(track => track.stop());
    screenStream = null;

    document.getElementById("screenVideo").srcObject = null;
    document.getElementById("shareScreen").innerText = "Start Screen Share";

    socket.emit("screen_share_stop", { lecture_id: lectureId });

    if (typeof stopScreenShareToAll === "function") {
        stopScreenShareToAll();
    }
}


/* ---------------------------------------------------------
   Connected student count (existing endpoint, unchanged).
   --------------------------------------------------------- */
function loadStudentCount() {

    fetch(`/api/teacher/live-count/${lectureId}`)
    .then(response => response.json())
    .then(data => {
        document.getElementById("studentCount").innerText = data.students;
    });
}

loadStudentCount();
setInterval(loadStudentCount, 3000);


/* ---------------------------------------------------------
   Live student presence list (cam/mic state) from the
   signaling layer — refines the grid beyond raw attendance.
   --------------------------------------------------------- */
socket.on("student_list", data => {

    document.getElementById("studentCount").innerText = data.count;

    data.students.forEach(s => {
        if (typeof addStudentTile === "function") {
            addStudentTile(s.sid, s.name);
        }
        updateStudentToggleUI(s.sid, s.cam_on, s.mic_on);
    });
});

socket.on("student_camera_toggle", data => {
    updateStudentToggleUI(data.student_sid, data.cam_on, null);
});

socket.on("student_mic_toggle", data => {
    updateStudentToggleUI(data.student_sid, null, data.mic_on);
});

function updateStudentToggleUI(sid, camOn, micOn) {

    const tile = document.getElementById("tile-" + sid);
    if (!tile) return;

    if (camOn !== null && camOn !== undefined) {
        const camBadge = tile.querySelector(".camBadge");
        if (camBadge) camBadge.innerText = camOn ? "📷" : "🚫📷";
    }

    if (micOn !== null && micOn !== undefined) {
        const micBadge = tile.querySelector(".micBadge");
        if (micBadge) micBadge.innerText = micOn ? "🎤" : "🚫🎤";
    }
}


/* ---------------------------------------------------------
   Student Grid rendering helpers
   (called from webrtc_teacher.js).
   --------------------------------------------------------- */
function addStudentTile(sid, name) {

    const grid = document.getElementById("studentGrid");
    if (!grid) return;
    if (document.getElementById("tile-" + sid)) return;

    const tile = document.createElement("div");
    tile.id = "tile-" + sid;
    tile.style.border = "1px solid #ccc";
    tile.style.padding = "6px";
    tile.style.width = "220px";
    tile.style.display = "inline-block";
    tile.style.margin = "6px";

    tile.innerHTML = `
        <video autoplay playsinline width="200" height="150"></video>
        <div style="font-size:12px;">
            ${name}
            <span class="camBadge">📷</span>
            <span class="micBadge">🎤</span>
        </div>
    `;

    grid.appendChild(tile);
}

function removeStudentTile(sid) {
    const tile = document.getElementById("tile-" + sid);
    if (tile) tile.remove();
}

function setStudentTileStream(sid, stream) {

    const tile = document.getElementById("tile-" + sid);
    if (!tile) return;

    const video = tile.querySelector("video");
    if (video) video.srcObject = stream;
}


/* ---------------------------------------------------------
   End Lecture.
   --------------------------------------------------------- */
document.getElementById("endLecture")
.addEventListener("click", async () => {

    if (!confirm("End the lecture for everyone?")) return;

    try {

        await fetch(`/api/teacher/complete-lecture/${lectureId}`, {
            method: "PUT"
        });

        socket.emit("teacher_leave", { lecture_id: lectureId });

        if (localStream) {
            localStream.getTracks().forEach(track => track.stop());
        }

        if (screenStream) {
            screenStream.getTracks().forEach(track => track.stop());
        }

        window.location.href='/teacher/dashboard?id={teacher.id}';

    } catch (error) {
        console.log("End Lecture Error:", error);
    }
});


/* ---------------------------------------------------------
   Auto leave-room signal if the tab is closed without
   pressing "End Lecture".
   --------------------------------------------------------- */
window.addEventListener("beforeunload", () => {
    socket.emit("teacher_leave", { lecture_id: lectureId });
});
