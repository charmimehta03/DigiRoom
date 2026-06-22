import socketio

from fastapi import APIRouter, Form
from sqlalchemy.orm import Session

from backend.database.database import SessionLocal
from backend.database.models import (
    Lecture,
    Student,
    Teacher,
    LectureChatMessage,
    LecturePoll,
    LecturePollAnswer
)

# =========================================================
# SOCKET.IO SERVER
# =========================================================

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*"
)

socket_app = socketio.ASGIApp(
    sio
)

router = APIRouter()


# =========================================================
# IN-MEMORY ROOM STATE
# Tracks who is currently connected to each lecture room.
# This is presence/signaling state only — NOT persisted data.
# Cleared automatically when people leave / disconnect.
# =========================================================

# rooms[lecture_id] = {
#     "teacher_sid": str | None,
#     "students": { sid: { "student_id": int, "name": str,
#                           "cam_on": bool, "mic_on": bool } }
# }
rooms = {}

# sid_map[sid] = { "lecture_id": str, "role": "teacher"/"student", "student_id": int|None }
sid_map = {}


def get_room(lecture_id):
    lecture_id = str(lecture_id)
    if lecture_id not in rooms:
        rooms[lecture_id] = {
            "teacher_sid": None,
            "students": {}
        }
    return rooms[lecture_id]


async def broadcast_student_list(lecture_id):
    room = get_room(lecture_id)
    student_list = [
        {
            "sid": sid,
            "student_id": info["student_id"],
            "name": info["name"],
            "cam_on": info["cam_on"],
            "mic_on": info["mic_on"]
        }
        for sid, info in room["students"].items()
    ]

    await sio.emit(
        "student_list",
        {
            "students": student_list,
            "count": len(student_list)
        },
        room=str(lecture_id)
    )


# =========================================================
# CONNECTION LIFECYCLE
# =========================================================

@sio.event
async def connect(sid, environ):
    print(f"Connected: {sid}")


@sio.event
async def disconnect(sid):
    print(f"Disconnected: {sid}")

    info = sid_map.pop(sid, None)

    if not info:
        return

    lecture_id = info["lecture_id"]
    room = get_room(lecture_id)

    if info["role"] == "teacher":

        if room["teacher_sid"] == sid:
            room["teacher_sid"] = None

        await sio.emit(
            "teacher_left",
            {},
            room=str(lecture_id)
        )

    else:

        if sid in room["students"]:
            del room["students"][sid]

        await sio.emit(
            "student_left",
            {"student_sid": sid},
            room=str(lecture_id)
        )

        await broadcast_student_list(lecture_id)


# =========================================================
# JOIN / LEAVE EVENTS
# =========================================================

@sio.event
async def teacher_join(sid, data):

    lecture_id = data["lecture_id"]

    await sio.enter_room(sid, str(lecture_id))

    room = get_room(lecture_id)
    room["teacher_sid"] = sid

    sid_map[sid] = {
        "lecture_id": str(lecture_id),
        "role": "teacher",
        "student_id": None
    }

    print(f"Teacher joined lecture {lecture_id}")

    await sio.emit(
        "teacher_joined",
        {"teacher_sid": sid},
        room=str(lecture_id),
        skip_sid=sid
    )

    await broadcast_student_list(lecture_id)


@sio.event
async def student_join(sid, data):

    lecture_id = data["lecture_id"]
    student_id = data.get("student_id")
    name = data.get("name", "Student")

    await sio.enter_room(sid, str(lecture_id))

    room = get_room(lecture_id)
    room["students"][sid] = {
        "student_id": student_id,
        "name": name,
        "cam_on": True,
        "mic_on": True
    }

    sid_map[sid] = {
        "lecture_id": str(lecture_id),
        "role": "student",
        "student_id": student_id
    }

    print(f"Student joined lecture {lecture_id}")

    # Notify teacher (and others) a new student arrived
    await sio.emit(
        "student_joined",
        {
            "student_sid": sid,
            "student_id": student_id,
            "name": name
        },
        room=str(lecture_id)
    )

    # If teacher is already live, tell the student so it can
    # request the teacher's stream
    if room["teacher_sid"]:
        await sio.emit(
            "teacher_ready",
            {},
            to=sid
        )

    await broadcast_student_list(lecture_id)


@sio.event
async def teacher_leave(sid, data):

    lecture_id = data["lecture_id"]
    room = get_room(lecture_id)

    if room["teacher_sid"] == sid:
        room["teacher_sid"] = None

    await sio.emit(
        "teacher_left",
        {},
        room=str(lecture_id)
    )

    await sio.leave_room(sid, str(lecture_id))


@sio.event
async def student_leave(sid, data):

    lecture_id = data["lecture_id"]
    room = get_room(lecture_id)

    if sid in room["students"]:
        del room["students"][sid]

    await sio.emit(
        "student_left",
        {"student_sid": sid},
        room=str(lecture_id)
    )

    await sio.leave_room(sid, str(lecture_id))

    await broadcast_student_list(lecture_id)


# =========================================================
# WEBRTC SIGNALING (two-way mesh)
# Teacher -> each Student (camera/mic/screen)
# Each Student -> Teacher (camera/mic)
# Routed directly to the target sid so multiple concurrent
# peer connections in the same room don't cross-talk.
# =========================================================

def resolve_target(sid, target):
    """
    Students don't know the teacher's sid, so they address
    offers/answers/ICE candidates to the sentinel "__teacher__".
    Resolve that to the real teacher_sid of the sender's room.
    Any other target is already a concrete sid and passes through
    unchanged.
    """

    if target != "__teacher__":
        return target

    sender_info = sid_map.get(sid)

    if not sender_info:
        return None

    room = get_room(sender_info["lecture_id"])

    return room["teacher_sid"]


@sio.event
async def offer(sid, data):

    target = resolve_target(sid, data["target"])

    if not target:
        return

    await sio.emit(
        "offer",
        {
            "offer": data["offer"],
            "from_sid": sid,
            "stream_type": data.get("stream_type", "camera")
        },
        to=target
    )


@sio.event
async def answer(sid, data):

    target = resolve_target(sid, data["target"])

    if not target:
        return

    await sio.emit(
        "answer",
        {
            "answer": data["answer"],
            "from_sid": sid,
            "stream_type": data.get("stream_type", "camera")
        },
        to=target
    )


@sio.event
async def ice_candidate(sid, data):

    target = resolve_target(sid, data["target"])

    if not target:
        return

    await sio.emit(
        "ice_candidate",
        {
            "candidate": data["candidate"],
            "from_sid": sid,
            "stream_type": data.get("stream_type", "camera")
        },
        to=target
    )


@sio.event
async def teacher_ready(sid, data):

    lecture_id = data["lecture_id"]

    print(f"Teacher Ready {lecture_id}")

    await sio.emit(
        "teacher_ready",
        {},
        room=str(lecture_id),
        skip_sid=sid
    )


# =========================================================
# MEDIA TOGGLE EVENTS
# =========================================================

@sio.event
async def teacher_camera_toggle(sid, data):

    lecture_id = data["lecture_id"]

    await sio.emit(
        "teacher_camera_toggle",
        {"cam_on": data["cam_on"]},
        room=str(lecture_id),
        skip_sid=sid
    )


@sio.event
async def teacher_mic_toggle(sid, data):

    lecture_id = data["lecture_id"]

    await sio.emit(
        "teacher_mic_toggle",
        {"mic_on": data["mic_on"]},
        room=str(lecture_id),
        skip_sid=sid
    )


@sio.event
async def student_camera_toggle(sid, data):

    lecture_id = data["lecture_id"]
    room = get_room(lecture_id)

    if sid in room["students"]:
        room["students"][sid]["cam_on"] = data["cam_on"]

    await sio.emit(
        "student_camera_toggle",
        {"student_sid": sid, "cam_on": data["cam_on"]},
        room=str(lecture_id),
        skip_sid=sid
    )


@sio.event
async def student_mic_toggle(sid, data):

    lecture_id = data["lecture_id"]
    room = get_room(lecture_id)

    if sid in room["students"]:
        room["students"][sid]["mic_on"] = data["mic_on"]

    await sio.emit(
        "student_mic_toggle",
        {"student_sid": sid, "mic_on": data["mic_on"]},
        room=str(lecture_id),
        skip_sid=sid
    )


# =========================================================
# SCREEN SHARE EVENTS
# =========================================================

@sio.event
async def screen_share_start(sid, data):

    lecture_id = data["lecture_id"]

    await sio.emit(
        "screen_share_start",
        {},
        room=str(lecture_id),
        skip_sid=sid
    )


@sio.event
async def screen_share_stop(sid, data):

    lecture_id = data["lecture_id"]

    await sio.emit(
        "screen_share_stop",
        {},
        room=str(lecture_id),
        skip_sid=sid
    )


# =========================================================
# CHAT (real-time + persisted to DB)
# =========================================================

@sio.event
async def chat_message(sid, data):

    lecture_id = data["lecture_id"]
    sender_type = data["sender_type"]   # "teacher" / "student"
    sender_id = data.get("sender_id")
    sender_name = data.get("sender_name", "Unknown")
    message = data["message"]

    db: Session = SessionLocal()

    chat_row = LectureChatMessage(
        lecture_id=lecture_id,
        sender_type=sender_type,
        sender_id=sender_id,
        sender_name=sender_name,
        message=message
    )

    db.add(chat_row)
    db.commit()
    db.refresh(chat_row)

    payload = {
        "id": chat_row.id,
        "sender_type": sender_type,
        "sender_id": sender_id,
        "sender_name": sender_name,
        "message": message,
        "created_at": chat_row.created_at.isoformat()
    }

    db.close()

    await sio.emit(
        "chat_message",
        payload,
        room=str(lecture_id)
    )


# =========================================================
# POLLS (real-time + persisted to DB)
# =========================================================

@sio.event
async def poll_created(sid, data):

    lecture_id = data["lecture_id"]

    # Normalize: "" / missing / not in A-D => ungraded poll (None),
    # exactly like every poll created before this feature existed.
    correct_option = data.get("correct_option")
    if correct_option:
        correct_option = str(correct_option).strip().upper()
        if correct_option not in ("A", "B", "C", "D"):
            correct_option = None
    else:
        correct_option = None

    db: Session = SessionLocal()

    poll = LecturePoll(
        lecture_id=lecture_id,
        question=data["question"],
        option_a=data.get("option_a"),
        option_b=data.get("option_b"),
        option_c=data.get("option_c"),
        option_d=data.get("option_d"),
        status="open",
        correct_option=correct_option
    )

    db.add(poll)
    db.commit()
    db.refresh(poll)

    poll_id = poll.id
    db.close()

    # SECURITY: correct_option is intentionally NEVER included in
    # this broadcast payload. It is broadcast to the whole room
    # (teacher + every student), so leaking it here would let
    # students see the answer before submitting. Students only
    # learn correctness afterwards, via poll_answer_received.
    payload = {
        "id": poll_id,
        "question": poll.question,
        "option_a": poll.option_a,
        "option_b": poll.option_b,
        "option_c": poll.option_c,
        "option_d": poll.option_d,
        "has_correct_answer": correct_option is not None
    }

    # Students receive the poll. Teacher does NOT need to
    # re-receive it (already has it locally) but we broadcast
    # to the whole room for simplicity / multi-tab support.
    await sio.emit(
        "poll_created",
        payload,
        room=str(lecture_id)
    )


async def _emit_poll_results(lecture_id, poll_id):

    db: Session = SessionLocal()

    poll = db.query(LecturePoll).filter(
        LecturePoll.id == poll_id
    ).first()

    if not poll:
        db.close()
        return

    answers = db.query(LecturePollAnswer).filter(
        LecturePollAnswer.poll_id == poll_id
    ).all()

    total = len(answers)

    counts = {"A": 0, "B": 0, "C": 0, "D": 0}

    for ans in answers:
        if ans.selected_option in counts:
            counts[ans.selected_option] += 1

    percentages = {}

    for key, value in counts.items():
        percentages[key] = (
            round((value / total) * 100, 1) if total > 0 else 0
        )

    # Aggregate-only accuracy (no per-student reveal, no answer
    # key leak). Only meaningful when the poll has a correct
    # answer defined; otherwise these stay None like before.
    has_correct_answer = poll.correct_option is not None
    correct_count = None
    incorrect_count = None
    accuracy_percentage = None

    if has_correct_answer:
        correct_count = sum(1 for a in answers if a.is_correct == "correct")
        incorrect_count = total - correct_count
        accuracy_percentage = (
            round((correct_count / total) * 100, 1) if total > 0 else 0
        )

    db.close()

    await sio.emit(
        "poll_results",
        {
            "poll_id": poll_id,
            "total_votes": total,
            "counts": counts,
            "percentages": percentages,
            "has_correct_answer": has_correct_answer,
            "correct_count": correct_count,
            "incorrect_count": incorrect_count,
            "accuracy_percentage": accuracy_percentage
        },
        room=str(lecture_id)
    )


@sio.event
async def poll_answer(sid, data):

    lecture_id = data["lecture_id"]
    poll_id = data["poll_id"]
    student_id = data["student_id"]
    selected_option = data["selected_option"]

    db: Session = SessionLocal()

    poll = db.query(LecturePoll).filter(
        LecturePoll.id == poll_id
    ).first()

    # Evaluate correctness server-side only. If the poll has no
    # correct_option defined, is_correct stays None — same as
    # every poll created before this feature existed.
    is_correct = None
    if poll and poll.correct_option:
        is_correct = "correct" if selected_option == poll.correct_option else "incorrect"

    # Prevent duplicate voting on the same poll by the same student
    existing = db.query(LecturePollAnswer).filter(
        LecturePollAnswer.poll_id == poll_id,
        LecturePollAnswer.student_id == student_id
    ).first()

    if existing:
        existing.selected_option = selected_option
        existing.is_correct = is_correct
    else:
        answer_row = LecturePollAnswer(
            poll_id=poll_id,
            student_id=student_id,
            selected_option=selected_option,
            is_correct=is_correct
        )
        db.add(answer_row)

    db.commit()
    db.close()

    # Confirm to the submitting student only (students must not
    # see other students' answers). is_correct is included here
    # because it is scoped to THIS student's own submission only.
    await sio.emit(
        "poll_answer_received",
        {
            "poll_id": poll_id,
            "selected_option": selected_option,
            "is_correct": is_correct
        },
        to=sid
    )

    # Push fresh live results to the teacher / room
    await _emit_poll_results(lecture_id, poll_id)


# =========================================================
# REST ENDPOINTS
# (history loading on page entry, no socket connection needed)
# =========================================================

@router.get("/api/live-lecture/chat-history/{lecture_id}")
def chat_history(lecture_id: int):

    db: Session = SessionLocal()

    messages = db.query(LectureChatMessage).filter(
        LectureChatMessage.lecture_id == lecture_id
    ).order_by(LectureChatMessage.created_at.asc()).all()

    data = []

    for msg in messages:
        data.append({
            "id": msg.id,
            "sender_type": msg.sender_type,
            "sender_id": msg.sender_id,
            "sender_name": msg.sender_name,
            "message": msg.message,
            "created_at": msg.created_at.isoformat()
        })

    db.close()

    return data


@router.get("/api/live-lecture/polls/{lecture_id}")
def lecture_polls(lecture_id: int):

    db: Session = SessionLocal()

    polls = db.query(LecturePoll).filter(
        LecturePoll.lecture_id == lecture_id
    ).order_by(LecturePoll.created_at.asc()).all()

    data = []

    for poll in polls:
        data.append({
            "id": poll.id,
            "question": poll.question,
            "option_a": poll.option_a,
            "option_b": poll.option_b,
            "option_c": poll.option_c,
            "option_d": poll.option_d,
            "status": poll.status,
            "correct_option": poll.correct_option
        })

    db.close()

    return data


@router.get("/api/live-lecture/poll-results/{poll_id}")
def poll_results(poll_id: int):

    db: Session = SessionLocal()

    poll = db.query(LecturePoll).filter(
        LecturePoll.id == poll_id
    ).first()

    if not poll:
        db.close()
        return {"message": "Poll not found"}

    answers = db.query(LecturePollAnswer).filter(
        LecturePollAnswer.poll_id == poll_id
    ).all()

    total = len(answers)

    counts = {"A": 0, "B": 0, "C": 0, "D": 0}

    for ans in answers:
        if ans.selected_option in counts:
            counts[ans.selected_option] += 1

    percentages = {}

    for key, value in counts.items():
        percentages[key] = (
            round((value / total) * 100, 1) if total > 0 else 0
        )

    has_correct_answer = poll.correct_option is not None
    correct_count = None
    incorrect_count = None
    accuracy_percentage = None

    if has_correct_answer:
        correct_count = sum(1 for a in answers if a.is_correct == "correct")
        incorrect_count = total - correct_count
        accuracy_percentage = (
            round((correct_count / total) * 100, 1) if total > 0 else 0
        )

    db.close()

    return {
        "poll_id": poll_id,
        "question": poll.question,
        "total_votes": total,
        "counts": counts,
        "percentages": percentages,
        "correct_option": poll.correct_option,
        "has_correct_answer": has_correct_answer,
        "correct_count": correct_count,
        "incorrect_count": incorrect_count,
        "accuracy_percentage": accuracy_percentage
    }


@router.get("/api/live-lecture/my-poll-answer/{poll_id}")
def my_poll_answer(poll_id: int, student_id: int):

    db: Session = SessionLocal()

    answer = db.query(LecturePollAnswer).filter(
        LecturePollAnswer.poll_id == poll_id,
        LecturePollAnswer.student_id == student_id
    ).first()

    db.close()

    if not answer:
        return {"answered": False}

    return {
        "answered": True,
        "selected_option": answer.selected_option,
        "is_correct": answer.is_correct
    }


@router.get("/api/live-lecture/poll-detail/{poll_id}")
def poll_detail(poll_id: int):
    """
    TEACHER-FACING ONLY. Full per-student breakdown for one poll:
    who answered correctly, who answered incorrectly, and (by
    diffing against the lecture's attendance roster) who skipped
    it entirely. This powers the "Poll Results Table" required by
    the analytics spec — never call this from a student-facing page.
    """

    db: Session = SessionLocal()

    poll = db.query(LecturePoll).filter(
        LecturePoll.id == poll_id
    ).first()

    if not poll:
        db.close()
        return {"message": "Poll not found"}

    from backend.database.models import LectureAttendance

    answers = db.query(LecturePollAnswer).filter(
        LecturePollAnswer.poll_id == poll_id
    ).all()

    answered_student_ids = {a.student_id for a in answers}

    # Roster = everyone who attended this lecture (skip = attended
    # but never submitted this particular poll).
    attendance_rows = db.query(LectureAttendance).filter(
        LectureAttendance.lecture_id == poll.lecture_id
    ).all()

    options = {
        "A": poll.option_a,
        "B": poll.option_b,
        "C": poll.option_c,
        "D": poll.option_d
    }

    responses = []
    for ans in answers:
        student = db.query(Student).filter(Student.id == ans.student_id).first()
        responses.append({
            "student_id": ans.student_id,
            "student_name": student.full_name if student else "Unknown",
            "roll_number": student.roll_number if student else "",
            "selected_option": ans.selected_option,
            "selected_text": options.get(ans.selected_option),
            "result": ans.is_correct,   # "correct" / "incorrect" / None (ungraded)
            "submitted_at": ans.created_at.isoformat() if ans.created_at else None
        })

    skipped = []
    for att in attendance_rows:
        if att.student_id not in answered_student_ids:
            student = db.query(Student).filter(Student.id == att.student_id).first()
            if student:
                skipped.append({
                    "student_id": student.id,
                    "student_name": student.full_name,
                    "roll_number": student.roll_number
                })

    db.close()

    total_responses = len(responses)
    correct_responses = len([r for r in responses if r["result"] == "correct"])
    incorrect_responses = len([r for r in responses if r["result"] == "incorrect"])

    return {
        "poll_id": poll.id,
        "question": poll.question,
        "options": options,
        "correct_option": poll.correct_option,
        "has_correct_answer": poll.correct_option is not None,
        "total_responses": total_responses,
        "correct_responses": correct_responses,
        "incorrect_responses": incorrect_responses,
        "accuracy_percentage": (
            round((correct_responses / total_responses) * 100, 1)
            if poll.correct_option and total_responses > 0 else None
        ),
        "skipped_count": len(skipped),
        "responses": responses,
        "skipped_students": skipped
    }


@router.get("/api/live-lecture/room-state/{lecture_id}")
def room_state(lecture_id: int):
    """
    Returns current in-memory presence state for a lecture room.
    Useful for a page refresh / reconnect to rehydrate UI.
    """

    room = get_room(lecture_id)

    return {
        "teacher_online": room["teacher_sid"] is not None,
        "students": [
            {
                "student_id": info["student_id"],
                "name": info["name"],
                "cam_on": info["cam_on"],
                "mic_on": info["mic_on"]
            }
            for info in room["students"].values()
        ],
        "student_count": len(room["students"])
    }
