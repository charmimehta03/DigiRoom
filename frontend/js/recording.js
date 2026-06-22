/* =========================================================
   recording.js
   Teacher-side recording + marker system for DigiRoom.

   Loaded AFTER live_lecture.js so it can reference:
       lectureId     — from live_lecture.js
       localStream   — teacher camera + mic MediaStream
       screenStream  — screen share MediaStream (may be null)

   What it records:
       Teacher camera track  (from localStream)
       Teacher mic track     (from localStream)
       Screen share track    (from screenStream, if active)
   What it does NOT record:
       Student cameras
       Student audio

   Storage format: WebM (VP8/Opus) — minimal file size.
   ========================================================= */

// =========================================================
// STATE
// =========================================================

let mediaRecorder = null;
let recordedChunks = [];
let recordingStartTime = null;
let timerInterval = null;
let markers = [];
let isRecording = false;

// =========================================================
// ELEMENT REFERENCES
// =========================================================

const startBtn    = document.getElementById("startRecording");
const stopBtn     = document.getElementById("stopRecording");
const markerBtn   = document.getElementById("addMarker");
const timerEl     = document.getElementById("recordingTimer");
const statusEl    = document.getElementById("recordingStatus");
const markerList  = document.getElementById("markerList");
const markerItems = document.getElementById("markerItems");


// =========================================================
// UTILITIES
// =========================================================

function formatTime(seconds) {
    const m = Math.floor(seconds / 60).toString().padStart(2, "0");
    const s = Math.floor(seconds % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
}

function elapsedSeconds() {
    if (!recordingStartTime) return 0;
    return (Date.now() - recordingStartTime) / 1000;
}

function setStatus(msg) {
    if (statusEl) statusEl.innerText = msg;
}

function setButtonStates(recording) {
    startBtn.disabled  = recording;
    stopBtn.disabled   = !recording;
    markerBtn.disabled = !recording;

    startBtn.style.opacity  = recording ? "0.5" : "1";
    stopBtn.style.opacity   = recording ? "1"   : "0.5";
    markerBtn.style.opacity = recording ? "1"   : "0.5";
}


// =========================================================
// BUILD COMBINED STREAM
// Merges teacher camera + mic + screen (if active) into a
// single MediaStream that MediaRecorder can capture.
// =========================================================

function buildRecordingStream() {
    const tracks = [];

    // Camera + mic
    if (localStream) {
        localStream.getTracks().forEach(t => tracks.push(t));
    }

    // Screen share (if currently active)
    if (typeof screenStream !== "undefined" && screenStream) {
        screenStream.getVideoTracks().forEach(t => tracks.push(t));
    }

    if (tracks.length === 0) {
        throw new Error("No media tracks available to record.");
    }

    return new MediaStream(tracks);
}


// =========================================================
// PICK BEST SUPPORTED MIME TYPE
// Prefers WebM with VP8+Opus for smallest file size.
// =========================================================

function getBestMimeType() {
    const candidates = [
        "video/webm;codecs=vp8,opus",
        "video/webm;codecs=vp9,opus",
        "video/webm;codecs=vp8",
        "video/webm;codecs=opus",
        "video/webm",
        "video/mp4"
    ];

    for (const mime of candidates) {
        if (MediaRecorder.isTypeSupported(mime)) {
            return mime;
        }
    }

    return "";
}


// =========================================================
// START RECORDING
// =========================================================

async function startRecording() {
    if (isRecording) return;

    try {
        await fetch(`/api/recording/start/${lectureId}`, { method: "POST" });
    } catch (err) {
        console.warn("Recording start signal failed:", err);
    }

    let stream;
    try {
        stream = buildRecordingStream();
    } catch (err) {
        alert("Cannot start recording: " + err.message);
        return;
    }

    const mimeType = getBestMimeType();
    const options  = mimeType ? { mimeType } : {};

    try {
        mediaRecorder = new MediaRecorder(stream, options);
    } catch (err) {
        alert("MediaRecorder error: " + err.message);
        return;
    }

    recordedChunks   = [];
    markers          = [];
    recordingStartTime = Date.now();
    isRecording      = true;

    mediaRecorder.ondataavailable = event => {
        if (event.data && event.data.size > 0) {
            recordedChunks.push(event.data);
        }
    };

    mediaRecorder.onstop = handleRecordingStop;

    mediaRecorder.start(1000);

    setButtonStates(true);
    setStatus("● Recording...");
    if (markerList) markerList.style.display = "none";
    if (markerItems) markerItems.innerHTML = "";

    timerInterval = setInterval(() => {
        if (timerEl) timerEl.innerText = formatTime(elapsedSeconds());
    }, 500);

    console.log("Recording started — mimeType:", mimeType || "browser default");
}


// =========================================================
// STOP RECORDING
// =========================================================

function stopRecording() {
    if (!isRecording || !mediaRecorder) return;

    mediaRecorder.stop();
    isRecording = false;

    clearInterval(timerInterval);
    setButtonStates(false);
    setStatus("Saving...");
}


// =========================================================
// POST-RECORDING: UPLOAD + SAVE MARKERS
// =========================================================

async function handleRecordingStop() {
    const durationSecs = Math.round(elapsedSeconds());

    const mimeType = mediaRecorder.mimeType || "video/webm";
    const blob      = new Blob(recordedChunks, { type: mimeType });

    recordedChunks = [];

    console.log(
        `Recording stopped. Duration: ${durationSecs}s, ` +
        `Size: ${(blob.size / 1024 / 1024).toFixed(2)} MB`
    );

    try {
        const formData = new FormData();
        formData.append("file", blob, "recording.webm");

        const resp = await fetch(`/api/recording/upload/${lectureId}`, {
            method: "POST",
            body:   formData
        });

        if (!resp.ok) {
            throw new Error(`Upload failed: ${resp.status}`);
        }

        const result = await resp.json();
        console.log("Recording saved:", result);

    } catch (err) {
        console.error("Recording upload error:", err);
        setStatus("Upload failed — see console");
        return;
    }

    try {
        await fetch(`/api/recording/markers/${lectureId}`, {
            method:  "POST",
            headers: { "Content-Type": "application/json" },
            body:    JSON.stringify({ markers })
        });
    } catch (err) {
        console.warn("Marker save failed:", err);
    }

    const sizeMB = (blob.size / 1024 / 1024).toFixed(2);
    setStatus(`Saved (${formatTime(durationSecs)}, ${sizeMB} MB)`);
    if (timerEl) timerEl.innerText = formatTime(durationSecs);

    console.log("Recording + markers saved successfully.");
}


// =========================================================
// ADD MARKER
// =========================================================

function addMarker() {
    if (!isRecording) return;

    const title = prompt("Marker title (e.g. Introduction, Unit 1):");
    if (!title || !title.trim()) return;

    const timeSeconds = Math.round(elapsedSeconds());
    const marker = {
        time:  timeSeconds,
        title: title.trim()
    };

    markers.push(marker);

    if (markerList && markerItems) {
        markerList.style.display = "block";
        const li = document.createElement("li");
        li.innerText = `${formatTime(timeSeconds)}  —  ${marker.title}`;
        markerItems.appendChild(li);
    }

    console.log("Marker added:", marker);
}


// =========================================================
// BUTTON EVENT LISTENERS
// =========================================================

if (startBtn)  startBtn.addEventListener("click",  startRecording);
if (stopBtn)   stopBtn.addEventListener("click",   stopRecording);
if (markerBtn) markerBtn.addEventListener("click", addMarker);


// =========================================================
// SAFETY: stop recording on page unload / End Lecture
// =========================================================

window.addEventListener("beforeunload", () => {
    if (isRecording && mediaRecorder) {
        mediaRecorder.stop();
    }
});

const endLectureBtn = document.getElementById("endLecture");
if (endLectureBtn) {
    endLectureBtn.addEventListener("click", async (e) => {
        if (!isRecording) return;
        stopRecording();
        await new Promise(resolve => setTimeout(resolve, 800));
    }, true);
}
