/* =========================================================
   attention_tracker.js
   Runs ENTIRELY on the student's device.

   - Uses MediaPipe Face Detection (via @mediapipe/tasks-vision)
     on the student's own local camera stream.
   - Raw video frames are processed in-browser only; they are
     NEVER uploaded. Only derived analytics values (face
     present/missing, looking at screen/away, attention %,
     focus/away seconds) are sent to the server.
   - Posts periodic samples to POST /api/analytics/attention-update
   - Requires `lectureId`, `studentId` and `localStream`
     globals from student_live_lecture.js (loaded first).
   ========================================================= */

(function () {

    const SAMPLE_INTERVAL_MS = 5000;   // how often we POST a sample to the server
    const DETECT_INTERVAL_MS = 500;    // how often we run face detection locally

    let faceDetector = null;
    let detecting = false;

    // Rolling window state since the last POST
    let windowSamples = [];     // attention scores (0-100) collected this window
    let focusSecondsWindow = 0;
    let awaySecondsWindow = 0;
    let lastFacePresent = false;

    const hiddenCanvas = document.createElement("canvas");
    hiddenCanvas.width = 320;
    hiddenCanvas.height = 240;
    const ctx = hiddenCanvas.getContext("2d");

    async function initDetector() {
        try {
            const vision = await import(
                "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/+esm"
            );
            const { FaceDetector, FilesetResolver } = vision;

            const filesetResolver = await FilesetResolver.forVisionTasks(
                "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm"
            );

            faceDetector = await FaceDetector.createFromOptions(filesetResolver, {
                baseOptions: {
                    modelAssetPath:
                        "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite",
                    delegate: "GPU"
                },
                runningMode: "VIDEO",
                minDetectionConfidence: 0.5
            });

            startTracking();

        } catch (err) {
            console.log("Attention tracker init failed (continuing without it):", err);
        }
    }

    function getVideoEl() {
        return document.getElementById("studentPreview");
    }

    function startTracking() {

        if (detecting) return;
        detecting = true;

        const intervalHandle = setInterval(runDetectionTick, DETECT_INTERVAL_MS);
        const sendHandle = setInterval(sendSample, SAMPLE_INTERVAL_MS);

        window.addEventListener("beforeunload", () => {
            clearInterval(intervalHandle);
            clearInterval(sendHandle);
        });
    }

    function runDetectionTick() {

        const video = getVideoEl();
        if (!video || video.readyState < 2 || !faceDetector) return;

        try {
            ctx.drawImage(video, 0, 0, hiddenCanvas.width, hiddenCanvas.height);

            const result = faceDetector.detectForVideo(hiddenCanvas, performance.now());
            const detections = result && result.detections ? result.detections : [];

            const facePresent = detections.length > 0;
            let lookingAtScreen = false;
            let attentionScore = 0;

            if (facePresent) {
                const box = detections[0].boundingBox;
                const frameCenterX = hiddenCanvas.width / 2;
                const frameCenterY = hiddenCanvas.height / 2;
                const faceCenterX = box.originX + box.width / 2;
                const faceCenterY = box.originY + box.height / 2;

                // Heuristic: a centered, reasonably sized face == looking at screen
                const offsetX = Math.abs(faceCenterX - frameCenterX) / hiddenCanvas.width;
                const offsetY = Math.abs(faceCenterY - frameCenterY) / hiddenCanvas.height;
                const sizeRatio = box.width / hiddenCanvas.width;

                lookingAtScreen = offsetX < 0.28 && offsetY < 0.3 && sizeRatio > 0.12;

                const centerScore = Math.max(0, 1 - (offsetX + offsetY));
                attentionScore = Math.round(
                    (lookingAtScreen ? 70 : 35) + centerScore * 30
                );
                attentionScore = Math.min(100, Math.max(0, attentionScore));
            }

            windowSamples.push(attentionScore);
            lastFacePresent = facePresent;

            const tickSeconds = DETECT_INTERVAL_MS / 1000;
            if (facePresent && lookingAtScreen) {
                focusSecondsWindow += tickSeconds;
            } else {
                awaySecondsWindow += tickSeconds;
            }

        } catch (err) {
            console.log("Attention detection tick error:", err);
        }
    }

    function sendSample() {

        if (windowSamples.length === 0) return;

        const avgAttention = Math.round(
            windowSamples.reduce((a, b) => a + b, 0) / windowSamples.length
        );

        const payload = {
            student_id: typeof studentId !== "undefined" ? Number(studentId) : null,
            lecture_id: typeof lectureId !== "undefined" ? Number(lectureId) : null,
            attention: avgAttention,
            focus_seconds: Math.round(focusSecondsWindow),
            away_seconds: Math.round(awaySecondsWindow),
            face_present: lastFacePresent
        };

        windowSamples = [];
        focusSecondsWindow = 0;
        awaySecondsWindow = 0;

        if (!payload.student_id || !payload.lecture_id) return;

        fetch("/api/analytics/attention-update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        }).catch(err => console.log("Attention sample send failed:", err));
    }

    // Wait for localStream (camera) to be ready before starting the detector.
    function waitForStreamThenInit() {
        if (typeof localStream !== "undefined" && localStream) {
            initDetector();
        } else {
            setTimeout(waitForStreamThenInit, 1000);
        }
    }

    waitForStreamThenInit();

})();
