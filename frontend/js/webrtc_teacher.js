/* =========================================================
   webrtc_teacher.js
   Handles all WebRTC peer connections on the teacher side.

   Two kinds of peer connections per student:
   1. teacherPeers[studentSid]        -> teacher sends camera/mic
                                          (and screen, when active)
                                          to that student.
   2. incomingPeers[studentSid]       -> teacher receives that
                                          student's camera/mic.

   Depends on globals already defined in live_lecture.js:
       socket, lectureId, localStream
   ========================================================= */

const teacherPeers = {};     // outgoing: teacher -> student (cam/mic)
const screenPeers = {};      // outgoing: teacher -> student (screen)
const incomingPeers = {};    // incoming: student -> teacher (cam/mic)

const rtcConfig = {
    iceServers: [
        { urls: "stun:stun.l.google.com:19302" }
    ]
};


/* ---------------------------------------------------------
   Create (or recreate) the outgoing camera/mic connection
   to a single student and send them an offer.
   --------------------------------------------------------- */
async function createTeacherPeer(studentSid) {

    console.log("Creating camera/mic peer for", studentSid);

    const peer = new RTCPeerConnection(rtcConfig);

    teacherPeers[studentSid] = peer;

    if (localStream) {
        localStream.getTracks().forEach(track => {
            peer.addTrack(track, localStream);
        });
    }

    peer.onicecandidate = event => {
        if (event.candidate) {
            socket.emit("ice_candidate", {
                target: studentSid,
                candidate: event.candidate,
                stream_type: "camera"
            });
        }
    };

    const offer = await peer.createOffer();
    await peer.setLocalDescription(offer);

    socket.emit("offer", {
        target: studentSid,
        offer: offer,
        stream_type: "camera"
    });
}


/* ---------------------------------------------------------
   Create the outgoing screen-share connection to a student.
   --------------------------------------------------------- */
async function createScreenPeer(studentSid) {

    if (!screenStream) return;

    console.log("Creating screen peer for", studentSid);

    const peer = new RTCPeerConnection(rtcConfig);

    screenPeers[studentSid] = peer;

    screenStream.getTracks().forEach(track => {
        peer.addTrack(track, screenStream);
    });

    peer.onicecandidate = event => {
        if (event.candidate) {
            socket.emit("ice_candidate", {
                target: studentSid,
                candidate: event.candidate,
                stream_type: "screen"
            });
        }
    };

    const offer = await peer.createOffer();
    await peer.setLocalDescription(offer);

    socket.emit("offer", {
        target: studentSid,
        offer: offer,
        stream_type: "screen"
    });
}


/* ---------------------------------------------------------
   When screen share starts, push it to every connected student.
   Called from live_lecture.js after getDisplayMedia succeeds.
   --------------------------------------------------------- */
function broadcastScreenShareToAll() {
    Object.keys(teacherPeers).forEach(studentSid => {
        createScreenPeer(studentSid);
    });
}


/* ---------------------------------------------------------
   When screen share stops, tear down all screen peers.
   --------------------------------------------------------- */
function stopScreenShareToAll() {
    Object.values(screenPeers).forEach(peer => peer.close());
    for (const sid in screenPeers) {
        delete screenPeers[sid];
    }
}


/* ---------------------------------------------------------
   A new student joined -> set up outgoing camera/mic peer,
   and (if currently screen sharing) an outgoing screen peer.
   --------------------------------------------------------- */
socket.on("student_joined", data => {

    const studentSid = data.student_sid;

    createTeacherPeer(studentSid);

    if (screenStream) {
        createScreenPeer(studentSid);
    }

    if (typeof addStudentTile === "function") {
        addStudentTile(studentSid, data.name || "Student");
    }
});


/* ---------------------------------------------------------
   A student left / disconnected -> tear down both peers
   and remove their tile from the grid.
   --------------------------------------------------------- */
socket.on("student_left", data => {

    const studentSid = data.student_sid;

    if (teacherPeers[studentSid]) {
        teacherPeers[studentSid].close();
        delete teacherPeers[studentSid];
    }

    if (screenPeers[studentSid]) {
        screenPeers[studentSid].close();
        delete screenPeers[studentSid];
    }

    if (incomingPeers[studentSid]) {
        incomingPeers[studentSid].close();
        delete incomingPeers[studentSid];
    }

    if (typeof removeStudentTile === "function") {
        removeStudentTile(studentSid);
    }
});


/* ---------------------------------------------------------
   Incoming offer FROM a student (their camera/mic).
   Teacher answers it so it can see/hear that student.
   --------------------------------------------------------- */
socket.on("offer", async data => {

    // Only handle offers that originate from a student
    // (i.e. ones not already tied to teacherPeers/screenPeers,
    // which are teacher-initiated).
    if (data.stream_type !== "camera_in") {
        return;
    }

    const studentSid = data.from_sid;

    console.log("Incoming student offer from", studentSid);

    const peer = new RTCPeerConnection(rtcConfig);

    incomingPeers[studentSid] = peer;

    peer.ontrack = event => {
        if (typeof setStudentTileStream === "function") {
            setStudentTileStream(studentSid, event.streams[0]);
        }
    };

    peer.onicecandidate = event => {
        if (event.candidate) {
            socket.emit("ice_candidate", {
                target: studentSid,
                candidate: event.candidate,
                stream_type: "camera_in"
            });
        }
    };

    await peer.setRemoteDescription(
        new RTCSessionDescription(data.offer)
    );

    const answer = await peer.createAnswer();
    await peer.setLocalDescription(answer);

    socket.emit("answer", {
        target: studentSid,
        answer: answer,
        stream_type: "camera_in"
    });
});


/* ---------------------------------------------------------
   Answer FROM a student, for the teacher's outgoing
   camera/mic or screen offer.
   --------------------------------------------------------- */
socket.on("answer", async data => {

    const studentSid = data.from_sid;
    const streamType = data.stream_type;

    let peer = null;

    if (streamType === "screen") {
        peer = screenPeers[studentSid];
    } else if (streamType === "camera") {
        peer = teacherPeers[studentSid];
    }

    if (!peer) return;

    await peer.setRemoteDescription(
        new RTCSessionDescription(data.answer)
    );
});


/* ---------------------------------------------------------
   ICE candidates, routed by stream_type + sender.
   --------------------------------------------------------- */
socket.on("ice_candidate", async data => {

    const fromSid = data.from_sid;
    const streamType = data.stream_type;

    let peer = null;

    if (streamType === "screen") {
        peer = screenPeers[fromSid];
    } else if (streamType === "camera") {
        peer = teacherPeers[fromSid];
    } else if (streamType === "camera_in") {
        peer = incomingPeers[fromSid];
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
