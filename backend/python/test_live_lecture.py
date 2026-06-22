"""
End-to-end test for the DigiRoom Live Lecture system.

Runs against the REAL uploaded digiroom.db (lecture_id=1, status=live,
teacher_id=1, student_id=1, both year='1' division='A').

Covers:
  - REST: lecture details, live count, chat history, polls, room-state
  - Socket.IO: teacher_join, student_join, student_joined event,
    chat_message round trip + persistence, poll_created -> students,
    poll_answer -> poll_results with correct percentages,
    duplicate-vote overwrite, screen_share_start/stop relay,
    camera/mic toggle relay, offer/answer/ice_candidate relay
    (including the "__teacher__" sentinel resolution),
    student_leave / teacher_leave -> student_list updates.
"""

import asyncio
import socketio
import requests

BASE = "http://127.0.0.1:8123"

results = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append((name, status, detail))
    print(f"[{status}] {name} {('- ' + detail) if detail and not condition else ''}")


def test_rest_endpoints():

    r = requests.get(f"{BASE}/api/teacher/live-lecture/1")
    check("GET live-lecture/1 status 200", r.status_code == 200, str(r.status_code))
    data = r.json()
    check("live-lecture/1 has title", "title" in data, str(data))
    check("live-lecture/1 status is live", data.get("status") == "live", str(data))

    r = requests.get(f"{BASE}/api/teacher/live-count/1")
    check("GET live-count/1 status 200", r.status_code == 200)
    check("live-count/1 has students key", "students" in r.json(), str(r.json()))

    r = requests.get(f"{BASE}/api/live-lecture/chat-history/1")
    check("GET chat-history/1 status 200", r.status_code == 200)
    check("chat-history/1 returns list", isinstance(r.json(), list), str(r.json()))

    r = requests.get(f"{BASE}/api/live-lecture/polls/1")
    check("GET polls/1 status 200", r.status_code == 200)
    check("polls/1 returns list", isinstance(r.json(), list), str(r.json()))

    r = requests.get(f"{BASE}/api/live-lecture/room-state/1")
    check("GET room-state/1 status 200", r.status_code == 200)
    rs = r.json()
    check("room-state/1 has student_count", "student_count" in rs, str(rs))

    # Existing, unmodified endpoint still works
    r = requests.get(f"{BASE}/api/student/scheduled-lectures?student_id=1")
    check("Existing /api/student/scheduled-lectures still works", r.status_code == 200, str(r.status_code))

    r = requests.get(f"{BASE}/api/student/live-lectures?student_id=1")
    check("Existing /api/student/live-lectures still works", r.status_code == 200, str(r.status_code))
    live = r.json()
    check("Live lecture 1 visible to student 1", any(l["id"] == 1 for l in live), str(live))


async def drain_until(client, event_name, max_events=10, timeout=3):
    """
    Receive events from `client` until one matching `event_name` is
    found, or `max_events` have been consumed. Returns the matching
    event (name, data) tuple, or None if not found.
    Other (skipped) events are returned as a list for optional inspection.
    """
    skipped = []
    for _ in range(max_events):
        ev = await client.receive(timeout=timeout)
        if ev[0] == event_name:
            return ev, skipped
        skipped.append(ev)
    return None, skipped


async def test_socketio_flow():

    LECTURE_ID = "1"

    teacher = socketio.AsyncSimpleClient()
    student1 = socketio.AsyncSimpleClient()
    student2 = socketio.AsyncSimpleClient()

    await teacher.connect(BASE, transports=["websocket"])
    await student1.connect(BASE, transports=["websocket"])
    await student2.connect(BASE, transports=["websocket"])

    check("Teacher socket connected", teacher.connected)
    check("Student1 socket connected", student1.connected)
    check("Student2 socket connected", student2.connected)

    # ---- JOIN FLOW ----
    await teacher.emit("teacher_join", {"lecture_id": LECTURE_ID})

    ev, _ = await drain_until(teacher, "student_list")
    check("Teacher receives student_list on join", ev is not None, str(ev))

    await student1.emit("student_join", {
        "lecture_id": LECTURE_ID, "student_id": 1, "name": "Omkar"
    })

    ev, _ = await drain_until(teacher, "student_joined")
    check("Teacher receives student_joined for student1", ev is not None, str(ev))
    student1_sid = ev[1]["student_sid"]
    check("student_joined carries student_id", ev[1].get("student_id") == 1, str(ev))

    # student1 receives both its own student_joined echo AND teacher_ready
    # (order between them is not guaranteed) - drain for teacher_ready specifically
    ev, _ = await drain_until(student1, "teacher_ready")
    check("Student1 receives teacher_ready", ev is not None, str(ev))

    ev, _ = await drain_until(teacher, "student_list")
    check("Teacher receives student_list after student1 join", ev is not None and ev[1]["count"] == 1, str(ev))

    await student2.emit("student_join", {
        "lecture_id": LECTURE_ID, "student_id": 2, "name": "SecondStudent"
    })

    ev, _ = await drain_until(teacher, "student_joined")
    check("Teacher receives student_joined for student2", ev is not None, str(ev))
    student2_sid = ev[1]["student_sid"]

    # student1 also receives the room-wide student_joined broadcast for student2
    ev, _ = await drain_until(student1, "student_joined")
    check("Student1 also sees student_joined broadcast (room event)", ev is not None, str(ev))

    ev, _ = await drain_until(student2, "teacher_ready")
    check("Student2 receives teacher_ready", ev is not None, str(ev))

    ev, _ = await drain_until(teacher, "student_list")
    check("Teacher receives student_list with count 2", ev is not None and ev[1]["count"] == 2, str(ev))

    # ---- ROOM STATE REST CHECK ----
    r = requests.get(f"{BASE}/api/live-lecture/room-state/1")
    rs = r.json()
    check("room-state shows teacher_online True", rs["teacher_online"] is True, str(rs))
    check("room-state shows 2 students", rs["student_count"] == 2, str(rs))

    # ---- WEBRTC SIGNALING: teacher -> student offer/answer/ice ----
    await teacher.emit("offer", {
        "target": student1_sid,
        "offer": {"type": "offer", "sdp": "FAKE_SDP_TEACHER"},
        "stream_type": "camera"
    })

    ev, _ = await drain_until(student1, "offer")
    check("Student1 receives offer from teacher", ev is not None, str(ev))
    if ev:
        check("Offer payload has stream_type camera", ev[1]["stream_type"] == "camera", str(ev))
        check("Offer payload sdp matches", ev[1]["offer"]["sdp"] == "FAKE_SDP_TEACHER", str(ev))

    await student1.emit("answer", {
        "target": ev[1]["from_sid"],
        "answer": {"type": "answer", "sdp": "FAKE_SDP_STUDENT"},
        "stream_type": "camera"
    })

    ev, _ = await drain_until(teacher, "answer")
    check("Teacher receives answer from student1", ev is not None, str(ev))

    await teacher.emit("ice_candidate", {
        "target": student1_sid,
        "candidate": {"candidate": "FAKE_ICE"},
        "stream_type": "camera"
    })
    ev, _ = await drain_until(student1, "ice_candidate")
    check("Student1 receives ICE candidate from teacher", ev is not None, str(ev))

    # ---- WEBRTC SIGNALING: student -> teacher via __teacher__ sentinel ----
    await student1.emit("offer", {
        "target": "__teacher__",
        "offer": {"type": "offer", "sdp": "FAKE_SDP_STUDENT_CAM"},
        "stream_type": "camera_in"
    })

    ev, _ = await drain_until(teacher, "offer")
    check("Teacher receives student's __teacher__-routed offer", ev is not None and ev[1]["stream_type"] == "camera_in", str(ev))
    if ev:
        check("Resolved sentinel target reaches teacher with correct from_sid", ev[1]["from_sid"] == student1_sid, str(ev))

    # ---- SCREEN SHARE ----
    await teacher.emit("screen_share_start", {"lecture_id": LECTURE_ID})
    ev1, _ = await drain_until(student1, "screen_share_start")
    ev2, _ = await drain_until(student2, "screen_share_start")
    check("Student1 receives screen_share_start", ev1 is not None, str(ev1))
    check("Student2 receives screen_share_start", ev2 is not None, str(ev2))

    await teacher.emit("screen_share_stop", {"lecture_id": LECTURE_ID})
    ev1, _ = await drain_until(student1, "screen_share_stop")
    ev2, _ = await drain_until(student2, "screen_share_stop")
    check("Student1 receives screen_share_stop", ev1 is not None, str(ev1))
    check("Student2 receives screen_share_stop", ev2 is not None, str(ev2))

    # ---- TOGGLES ----
    await teacher.emit("teacher_camera_toggle", {"lecture_id": LECTURE_ID, "cam_on": False})
    ev1, _ = await drain_until(student1, "teacher_camera_toggle")
    check("Student1 receives teacher_camera_toggle (off)", ev1 is not None and ev1[1]["cam_on"] is False, str(ev1))

    await student1.emit("student_mic_toggle", {"lecture_id": LECTURE_ID, "mic_on": False})
    ev, _ = await drain_until(teacher, "student_mic_toggle")
    check("Teacher receives student_mic_toggle", ev is not None and ev[1]["mic_on"] is False, str(ev))

    r = requests.get(f"{BASE}/api/live-lecture/room-state/1")
    rs = r.json()
    s1_state = next(s for s in rs["students"] if s["student_id"] == 1)
    check("room-state reflects mic_on False for student1", s1_state["mic_on"] is False, str(rs))

    # ---- CHAT ----
    await teacher.emit("chat_message", {
        "lecture_id": LECTURE_ID,
        "sender_type": "teacher",
        "sender_id": 1,
        "sender_name": "TeacherOmkar",
        "message": "Welcome to the lecture!"
    })

    ev_s1, _ = await drain_until(student1, "chat_message")
    ev_s2, _ = await drain_until(student2, "chat_message")
    await drain_until(teacher, "chat_message")  # teacher's own broadcast echo

    check("Teacher chat broadcast reaches student1", ev_s1 is not None and ev_s1[1]["message"] == "Welcome to the lecture!", str(ev_s1))
    check("Teacher chat broadcast reaches student2", ev_s2 is not None, str(ev_s2))
    check("Chat message has sender_type teacher", ev_s1 is not None and ev_s1[1]["sender_type"] == "teacher", str(ev_s1))

    await student1.emit("chat_message", {
        "lecture_id": LECTURE_ID,
        "sender_type": "student",
        "sender_id": 1,
        "sender_name": "Omkar",
        "message": "Hello teacher!"
    })

    ev_t, _ = await drain_until(teacher, "chat_message")
    check("Teacher receives student chat message", ev_t is not None and ev_t[1]["sender_name"] == "Omkar", str(ev_t))

    # drain echoes to student1/student2
    await drain_until(student1, "chat_message")
    await drain_until(student2, "chat_message")

    # verify chat persisted to DB via REST
    r = requests.get(f"{BASE}/api/live-lecture/chat-history/1")
    history = r.json()
    check("Chat history persisted >= 2 messages", len(history) >= 2, str(history))
    check("Chat history contains teacher message", any(m["message"] == "Welcome to the lecture!" for m in history), str(history))
    check("Chat history contains student message", any(m["message"] == "Hello teacher!" for m in history), str(history))

    # ---- POLLS ----
    await teacher.emit("poll_created", {
        "lecture_id": LECTURE_ID,
        "question": "Is this clear?",
        "option_a": "Yes",
        "option_b": "No",
        "option_c": None,
        "option_d": None
    })

    ev_s1, _ = await drain_until(student1, "poll_created")
    ev_s2, _ = await drain_until(student2, "poll_created")
    await drain_until(teacher, "poll_created")  # teacher's own broadcast echo

    check("Student1 receives poll_created", ev_s1 is not None and ev_s1[1]["question"] == "Is this clear?", str(ev_s1))
    check("Student2 receives poll_created", ev_s2 is not None, str(ev_s2))

    poll_id = ev_s1[1]["id"]
    check("Poll has valid id", isinstance(poll_id, int), str(ev_s1))

    # student1 answers A
    await student1.emit("poll_answer", {
        "lecture_id": LECTURE_ID,
        "poll_id": poll_id,
        "student_id": 1,
        "selected_option": "A"
    })

    ev_confirm, _ = await drain_until(student1, "poll_answer_received")
    check("Student1 receives poll_answer_received", ev_confirm is not None, str(ev_confirm))

    # results broadcast to room
    ev_t, _ = await drain_until(teacher, "poll_results")
    await drain_until(student1, "poll_results")
    await drain_until(student2, "poll_results")

    check("Teacher receives poll_results after student1 answer", ev_t is not None and ev_t[1]["total_votes"] == 1, str(ev_t))
    check("poll_results counts A=1", ev_t[1]["counts"]["A"] == 1, str(ev_t))
    check("poll_results percentage A=100.0", ev_t[1]["percentages"]["A"] == 100.0, str(ev_t))

    # student2 answers B
    await student2.emit("poll_answer", {
        "lecture_id": LECTURE_ID,
        "poll_id": poll_id,
        "student_id": 2,
        "selected_option": "B"
    })

    ev_confirm2, _ = await drain_until(student2, "poll_answer_received")
    check("Student2 receives poll_answer_received", ev_confirm2 is not None, str(ev_confirm2))

    ev_t2, _ = await drain_until(teacher, "poll_results")
    await drain_until(student1, "poll_results")
    await drain_until(student2, "poll_results")

    check("poll_results total_votes=2 after both answer", ev_t2[1]["total_votes"] == 2, str(ev_t2))
    check("poll_results counts A=1,B=1", ev_t2[1]["counts"]["A"] == 1 and ev_t2[1]["counts"]["B"] == 1, str(ev_t2))
    check("poll_results percentages 50/50", ev_t2[1]["percentages"]["A"] == 50.0 and ev_t2[1]["percentages"]["B"] == 50.0, str(ev_t2))

    # duplicate vote (student1 changes answer to B) should overwrite, not duplicate
    await student1.emit("poll_answer", {
        "lecture_id": LECTURE_ID,
        "poll_id": poll_id,
        "student_id": 1,
        "selected_option": "B"
    })
    await drain_until(student1, "poll_answer_received")
    ev_t3, _ = await drain_until(teacher, "poll_results")
    await drain_until(student1, "poll_results")
    await drain_until(student2, "poll_results")

    check("Changed vote still totals 2 (no duplicate row)", ev_t3[1]["total_votes"] == 2, str(ev_t3))
    check("After change: A=0, B=2", ev_t3[1]["counts"]["A"] == 0 and ev_t3[1]["counts"]["B"] == 2, str(ev_t3))

    # verify via REST poll-results endpoint too
    r = requests.get(f"{BASE}/api/live-lecture/poll-results/{poll_id}")
    pr = r.json()
    check("REST poll-results matches socket results", pr["total_votes"] == 2 and pr["counts"]["B"] == 2, str(pr))

    # verify my-poll-answer endpoint
    r = requests.get(f"{BASE}/api/live-lecture/my-poll-answer/{poll_id}?student_id=2")
    mpa = r.json()
    check("my-poll-answer for student2 is B", mpa["answered"] is True and mpa["selected_option"] == "B", str(mpa))

    # verify polls list via REST
    r = requests.get(f"{BASE}/api/live-lecture/polls/1")
    polls = r.json()
    check("Polls REST list contains created poll", any(p["id"] == poll_id for p in polls), str(polls))

    # ---- LEAVE FLOW ----
    await student2.emit("student_leave", {"lecture_id": LECTURE_ID})

    ev_t, _ = await drain_until(teacher, "student_left")
    check("Teacher receives student_left for student2", ev_t is not None, str(ev_t))

    ev_s1, _ = await drain_until(student1, "student_left")
    check("Student1 also sees student_left broadcast", ev_s1 is not None, str(ev_s1))

    ev_t2, _ = await drain_until(teacher, "student_list")
    check("Teacher receives updated student_list count=1 after leave", ev_t2 is not None and ev_t2[1]["count"] == 1, str(ev_t2))

    r = requests.get(f"{BASE}/api/live-lecture/room-state/1")
    rs = r.json()
    check("room-state student_count=1 after student2 leaves", rs["student_count"] == 1, str(rs))

    await teacher.emit("teacher_leave", {"lecture_id": LECTURE_ID})
    ev_s1, _ = await drain_until(student1, "teacher_left")
    check("Student1 receives teacher_left", ev_s1 is not None, str(ev_s1))

    r = requests.get(f"{BASE}/api/live-lecture/room-state/1")
    rs = r.json()
    check("room-state teacher_online False after teacher leaves", rs["teacher_online"] is False, str(rs))

    await teacher.disconnect()
    await student1.disconnect()
    await student2.disconnect()


async def main():
    test_rest_endpoints()
    await test_socketio_flow()

    print("\n========== SUMMARY ==========")
    passed = sum(1 for _, s, _ in results if s == "PASS")
    failed = sum(1 for _, s, _ in results if s == "FAIL")
    print(f"PASSED: {passed}  FAILED: {failed}  TOTAL: {len(results)}")

    if failed:
        print("\nFAILED CASES:")
        for name, status, detail in results:
            if status == "FAIL":
                print(f" - {name}: {detail}")


if __name__ == "__main__":
    asyncio.run(main())
