/* =========================================================
   student_live_lecture.js
   Student-side live lecture page controller.
   Loaded AFTER socket.io.min.js and BEFORE webrtc_student.js,
   chat.js, poll.js (see student/live_lecture.html script order).
   ========================================================= */

const socket = io();

let localStream = null;
let isCamOn = true;
let isMicOn = true;

const params = new URLSearchParams(window.location.search);
const lectureId = params.get("lecture_id");
const studentId = params.get("student_id");

/* Globals consumed by chat.js / poll.js */
const role = "student";
let senderId = studentId;
let senderName = "Student";


/* ---------------------------------------------------------
   Join the signaling room.
   --------------------------------------------------------- */
socket.emit("student_join", {
    lecture_id: lectureId,
    student_id: studentId,
    name: senderName
});


/* ---------------------------------------------------------
   Load lecture details (existing endpoint, unchanged).
   --------------------------------------------------------- */
fetch(`/api/teacher/live-lecture/${lectureId}`)
.then(response => response.json())
.then(data => {

    document.getElementById("lectureTitle").innerText = data.title;
    document.getElementById("subjectName").innerText =
        "Subject : " + data.subject;
})
.catch(error => console.log("Lecture Load Error:", error));


/* ---------------------------------------------------------
   Acquire camera + mic for this student, show local preview,
   then offer it to the teacher.
   --------------------------------------------------------- */
navigator.mediaDevices
.getUserMedia({ video: true, audio: true })
.then(stream => {

    localStream = stream;

    const previewEl = document.getElementById("studentPreview");
    if (previewEl) previewEl.srcObject = stream;

    if (typeof sendStudentStreamToTeacher === "function") {
        sendStudentStreamToTeacher();
    }
})
.catch(error => console.log("Media Error:", error));


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

        socket.emit("student_camera_toggle", {
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

        socket.emit("student_mic_toggle", {
            lecture_id: lectureId,
            mic_on: isMicOn
        });
    });
}


/* ---------------------------------------------------------
   Teacher camera / mic toggle indicators (read-only on
   the student side — just reflects teacher state visually).
   --------------------------------------------------------- */
socket.on("teacher_camera_toggle", data => {

    const teacherVideo = document.getElementById("teacherVideo");
    if (teacherVideo) {
        teacherVideo.style.opacity = data.cam_on ? "1" : "0.3";
    }
});

socket.on("teacher_mic_toggle", data => {

    const micIndicator = document.getElementById("teacherMicIndicator");
    if (micIndicator) {
        micIndicator.innerText = data.mic_on ? "🎤" : "🚫🎤";
    }
});


/* ---------------------------------------------------------
   Screen share visual state hooks (called from webrtc_student.js).
   --------------------------------------------------------- */
function onScreenShareStarted() {
    const section = document.getElementById("screenShareSection");
    if (section) section.style.display = "block";
}

function onScreenShareStopped() {
    const section = document.getElementById("screenShareSection");
    if (section) section.style.display = "none";
}


/* ---------------------------------------------------------
   JOIN ATTENDANCE (existing logic, unchanged).
   --------------------------------------------------------- */
async function joinLecture() {

    const formData = new FormData();
    formData.append("student_id", studentId);

    try {

        const response = await fetch(
            `/api/student/join-lecture/${lectureId}`,
            { method: "POST", body: formData }
        );

        const result = await response.json();
        console.log(result.message);

    } catch (error) {
        console.log("Join Error:", error);
    }
}

joinLecture();


/* ---------------------------------------------------------
   LEAVE LECTURE (existing logic, unchanged, plus signaling
   leave + media cleanup).
   --------------------------------------------------------- */
document.getElementById("leaveLecture")
.addEventListener("click", async () => {

    const formData = new FormData();
    formData.append("student_id", studentId);

    try {

        const response = await fetch(
            `/api/student/leave-lecture/${lectureId}`,
            { method: "PUT", body: formData }
        );

        const result = await response.json();

        socket.emit("student_leave", { lecture_id: lectureId });

        if (localStream) {
            localStream.getTracks().forEach(track => track.stop());
        }

        alert(result.message);

        window.location.href = `/student/dashboard?id=${studentId}`;

    } catch (error) {
        console.log("Leave Error:", error);
    }
});


/* ---------------------------------------------------------
   AUTO LEAVE IF TAB CLOSED (existing logic, unchanged, plus
   a signaling leave beacon).
   --------------------------------------------------------- */
window.addEventListener("beforeunload", function () {

    const formData = new FormData();
    formData.append("student_id", studentId);

    navigator.sendBeacon(
        `/api/student/leave-lecture/${lectureId}`,
        formData
    );

    socket.emit("student_leave", { lecture_id: lectureId });
});
