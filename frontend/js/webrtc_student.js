/* =========================================================
   webrtc_student.js
   Handles all WebRTC peer connections on the student side.

   Two incoming connections FROM the teacher:
     - "camera" stream_type -> teacher's camera/mic
     - "screen" stream_type -> teacher's screen share

   One outgoing connection TO the teacher:
     - this student's own camera/mic ("camera_in" on the wire,
       so the teacher's offer/answer handler can tell it apart
       from teacher-initiated streams)

   Depends on globals already defined in student_live_lecture.js:
       socket, lectureId, studentId, localStream
   ========================================================= */

const rtcConfig = {
    iceServers: [
        { urls: "stun:stun.l.google.com:19302" }
    ]
};

let teacherCameraPeer = null;   // incoming: teacher camera/mic
let teacherScreenPeer = null;   // incoming: teacher screen share
let outgoingPeer = null;        // outgoing: this student's cam/mic


/* ---------------------------------------------------------
   Incoming offer from the teacher (camera/mic or screen).
   --------------------------------------------------------- */
socket.on("offer", async data => {

    const streamType = data.stream_type;

    // Offers with stream_type "camera_in" are this student's
    // own offers being echoed back via room broadcast in some
    // edge cases — ignore, they are not meant for students.
    if (streamType === "camera_in") {
        return;
    }

    console.log("Offer received from teacher:", streamType);

    const peer = new RTCPeerConnection(rtcConfig);

    if (streamType === "screen") {
        teacherScreenPeer = peer;
    } else {
        teacherCameraPeer = peer;
    }

    peer.ontrack = event => {

        if (streamType === "screen") {
            const screenEl = document.getElementById("screenVideo");
            if (screenEl) {
                screenEl.srcObject = event.streams[0];
            }
            if (typeof onScreenShareStarted === "function") {
                onScreenShareStarted();
            }
        } else {
            const camEl = document.getElementById("teacherVideo");
            if (camEl) {
                camEl.srcObject = event.streams[0];
            }
        }
    };

    peer.onicecandidate = event => {
        if (event.candidate) {
            socket.emit("ice_candidate", {
                target: data.from_sid,
                candidate: event.candidate,
                stream_type: streamType
            });
        }
    };

    await peer.setRemoteDescription(
        new RTCSessionDescription(data.offer)
    );

    const answer = await peer.createAnswer();
    await peer.setLocalDescription(answer);

    socket.emit("answer", {
        target: data.from_sid,
        answer: answer,
        stream_type: streamType
    });
});


/* ---------------------------------------------------------
   Answer from the teacher, replying to this student's
   own outgoing camera/mic offer.
   --------------------------------------------------------- */
socket.on("answer", async data => {

    if (data.stream_type !== "camera_in") return;

    if (!outgoingPeer) return;

    await outgoingPeer.setRemoteDescription(
        new RTCSessionDescription(data.answer)
    );
});


/* ---------------------------------------------------------
   ICE candidates, routed by stream_type.
   --------------------------------------------------------- */
socket.on("ice_candidate", async data => {

    const streamType = data.stream_type;

    let peer = null;

    if (streamType === "screen") {
        peer = teacherScreenPeer;
    } else if (streamType === "camera") {
        peer = teacherCameraPeer;
    } else if (streamType === "camera_in") {
        peer = outgoingPeer;
    }

    if (!peer) return;

    try {
        await peer.addIceCandidate(
            new RTCIceCandidate(data.candidate)
        );
    } catch (error) {
        console.log("ICE add error:", error);
    }
});


/* ---------------------------------------------------------
   Teacher signals it stopped screen sharing -> clear element
   and tear down that peer connection.
   --------------------------------------------------------- */
socket.on("screen_share_stop", () => {

    const screenEl = document.getElementById("screenVideo");
    if (screenEl) {
        screenEl.srcObject = null;
    }

    if (teacherScreenPeer) {
        teacherScreenPeer.close();
        teacherScreenPeer = null;
    }

    if (typeof onScreenShareStopped === "function") {
        onScreenShareStopped();
    }
});


/* ---------------------------------------------------------
   Send THIS student's camera/mic to the teacher.
   Called once localStream is ready (see student_live_lecture.js).
   We don't wait for a teacher offer here — the student
   proactively offers its own stream so the teacher can see/hear it.
   --------------------------------------------------------- */
async function sendStudentStreamToTeacher() {

    if (!localStream) return;

    console.log("Sending student camera/mic to teacher");

    outgoingPeer = new RTCPeerConnection(rtcConfig);

    localStream.getTracks().forEach(track => {
        outgoingPeer.addTrack(track, localStream);
    });

    outgoingPeer.onicecandidate = event => {
        if (event.candidate) {
            socket.emit("ice_candidate", {
                target: "__teacher__",   // resolved server-side via room
                candidate: event.candidate,
                stream_type: "camera_in"
            });
        }
    };

    const offer = await outgoingPeer.createOffer();
    await outgoingPeer.setLocalDescription(offer);

    socket.emit("offer", {
        target: "__teacher__",
        offer: offer,
        stream_type: "camera_in"
    });
}


/* ---------------------------------------------------------
   Teacher becomes ready (joins/re-announces) -> (re)send our
   stream so a late-joining teacher still sees this student.
   --------------------------------------------------------- */
socket.on("teacher_ready", () => {
    if (localStream && !outgoingPeer) {
        sendStudentStreamToTeacher();
    }
});
