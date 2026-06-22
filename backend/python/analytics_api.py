from fastapi import APIRouter, Body
from sqlalchemy.orm import Session
from datetime import datetime

from backend.database.database import SessionLocal
from backend.database.models import (
    Lecture,
    Student,
    Subject,
    LectureAttendance,
    LectureAnalytics,
    LectureChatMessage,
    LecturePoll,
    LecturePollAnswer,
)
from backend.python.analytics_storage import write_lecture_analytics

router = APIRouter()


# =========================================================
# 1. ATTENTION TRACKING INGEST
# Browser (MediaPipe/OpenCV-derived values only — no video
# ever reaches the server) posts periodic samples here.
# =========================================================

@router.post("/api/analytics/attention-update")
def attention_update(payload: dict = Body(...)):
    """
    Expected payload:
    {
      "student_id": 1,
      "lecture_id": 5,
      "attention": 84,       # 0-100 instantaneous attention score
      "focus_seconds": 5,    # seconds of "looking at screen" since last sample
      "away_seconds": 0,     # seconds "looking away"/face missing since last sample
      "face_present": true
    }
    """

    lecture_id = payload.get("lecture_id")
    student_id = payload.get("student_id")

    if not lecture_id or not student_id:
        return {"message": "lecture_id and student_id are required"}

    attention = int(payload.get("attention", 0))
    focus_seconds = int(payload.get("focus_seconds", 0))
    away_seconds = int(payload.get("away_seconds", 0))
    face_present = bool(payload.get("face_present", False))

    db: Session = SessionLocal()

    try:
        record = db.query(LectureAnalytics).filter(
            LectureAnalytics.lecture_id == lecture_id,
            LectureAnalytics.student_id == student_id
        ).first()


        if not record:
            record = LectureAnalytics(
                lecture_id=lecture_id,
                student_id=student_id,
                started_at=datetime.utcnow(),

                samples_count=0,
                attention_sum=0,
                attention_percentage=0,

                focus_time_seconds=0,
                away_time_seconds=0,

                face_present_count=0,
                face_missing_count=0
            )

            db.add(record)

        # Safety for old NULL rows
        record.samples_count = record.samples_count or 0
        record.attention_sum = record.attention_sum or 0
        record.attention_percentage = record.attention_percentage or 0
        record.focus_time_seconds = record.focus_time_seconds or 0
        record.away_time_seconds = record.away_time_seconds or 0
        record.face_present_count = record.face_present_count or 0
        record.face_missing_count = record.face_missing_count or 0

        record.samples_count += 1
        record.attention_sum += attention
        record.attention_percentage = round(
            record.attention_sum / record.samples_count
        )
        record.focus_time_seconds += focus_seconds
        record.away_time_seconds += away_seconds
        record.face_present = "present" if face_present else "missing"

        if face_present:
            record.face_present_count += 1
        else:
            record.face_missing_count += 1

        record.last_updated = datetime.utcnow()

        db.commit()
        db.refresh(record)

        lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
        _sync_lecture_analytics_file(db, lecture)

        return {
            "message": "Attention updated",
            "attention_percentage": record.attention_percentage
        }
    finally:
        db.close()


# =========================================================
# 2. ANALYTICS STORAGE SYNC
# Rebuilds the on-disk analytics.json snapshot from the DB.
# =========================================================

def _sync_lecture_analytics_file(db: Session, lecture):
    if not lecture:
        return

    analytics_rows = db.query(LectureAnalytics).filter(
        LectureAnalytics.lecture_id == lecture.id
    ).all()

    attendance_rows = db.query(LectureAttendance).filter(
        LectureAttendance.lecture_id == lecture.id
    ).all()

    students_payload = []
    for row in analytics_rows:
        student = db.query(Student).filter(Student.id == row.student_id).first()
        students_payload.append({
            "student_id": row.student_id,
            "student_name": student.full_name if student else "Unknown",
            "attention_percentage": row.attention_percentage,
            "focus_time_seconds": row.focus_time_seconds,
            "away_time_seconds": row.away_time_seconds,
            "face_present": row.face_present,
            "samples_count": row.samples_count
        })

    payload = {
        "lecture_id": lecture.id,
        "lecture_title": lecture.title,
        "status": lecture.status,
        "student_analytics": students_payload,
        "lecture_analytics": {
            "students_present": len([a for a in attendance_rows]),
            "average_attention": (
                round(sum(r.attention_percentage for r in analytics_rows) / len(analytics_rows))
                if analytics_rows else 0
            )
        }
    }

    write_lecture_analytics(lecture.id, lecture.title, payload)


# =========================================================
# 3 & 4. TEACHER ANALYTICS DASHBOARD (overall class analytics)
# =========================================================

def _lecture_stats(db: Session, lecture: Lecture):
    """Compute real (non-static) stats for a single lecture."""

    total_students = db.query(Student).filter(
        Student.year == lecture.year,
        Student.division == lecture.division,
        Student.institute_code == lecture.teacher.institute_code if lecture.teacher else None
    ).count()

    attendance_rows = db.query(LectureAttendance).filter(
        LectureAttendance.lecture_id == lecture.id
    ).all()
    students_present = len(attendance_rows)

    attendance_pct = (
        round((students_present / total_students) * 100)
        if total_students > 0 else 0
    )

    analytics_rows = db.query(LectureAnalytics).filter(
        LectureAnalytics.lecture_id == lecture.id
    ).all()

    avg_attention = (
        round(sum(r.attention_percentage for r in analytics_rows) / len(analytics_rows))
        if analytics_rows else 0
    )

    duration_minutes = 0
    if lecture.actual_start and lecture.actual_end:
        duration_minutes = int(
            (lecture.actual_end - lecture.actual_start).total_seconds() / 60
        )

    polls = db.query(LecturePoll).filter(LecturePoll.lecture_id == lecture.id).all()
    poll_answer_count = db.query(LecturePollAnswer).join(
        LecturePoll, LecturePollAnswer.poll_id == LecturePoll.id
    ).filter(LecturePoll.lecture_id == lecture.id).count()

    poll_participation = (
        round((poll_answer_count / (len(polls) * total_students)) * 100)
        if polls and total_students > 0 else 0
    )

    chat_count = db.query(LectureChatMessage).filter(
        LectureChatMessage.lecture_id == lecture.id,
        LectureChatMessage.sender_type == "student"
    ).count()

    chat_participation = (
        round((chat_count / total_students) * 100)
        if total_students > 0 else 0
    )

    return {
        "lecture_id": lecture.id,
        "title": lecture.title,
        "date": lecture.scheduled_date,
        "status": lecture.status,
        "total_students": total_students,
        "students_present": students_present,
        "attendance_percentage": attendance_pct,
        "average_attention": avg_attention,
        "duration_minutes": duration_minutes,
        "poll_participation_percentage": poll_participation,
        "chat_participation_percentage": chat_participation,
        "chat_messages": chat_count,
        "activity_score": round(
            (attendance_pct + avg_attention + poll_participation + chat_participation) / 4
        )
    }


@router.get("/api/teacher/analytics/overview")
def teacher_analytics_overview(teacher_id: int):

    db: Session = SessionLocal()

    try:
        lectures = db.query(Lecture).filter(
            Lecture.teacher_id == teacher_id
        ).all()

        lecture_stats = [_lecture_stats(db, lec) for lec in lectures]

        completed = [s for s in lecture_stats if s["status"] == "completed" or s["students_present"] > 0]

        def avg(field):
            vals = [s[field] for s in completed]
            return round(sum(vals) / len(vals)) if vals else 0

        sorted_by_activity = sorted(lecture_stats, key=lambda s: s["activity_score"], reverse=True)
        most_active = sorted_by_activity[:5]
        least_active = sorted_by_activity[-5:][::-1] if len(sorted_by_activity) > 0 else []

        total_unique_students = db.query(Student).filter(
            Student.institute_code.in_(
                [lec.teacher.institute_code for lec in lectures if lec.teacher]
            ) if lectures else False
        ).count() if lectures else 0

        return {
            "total_lectures": len(lectures),
            "average_attendance": avg("attendance_percentage"),
            "average_attention": avg("average_attention"),
            "average_poll_participation": avg("poll_participation_percentage"),
            "average_chat_participation": avg("chat_participation_percentage"),
            "total_students": total_unique_students,
            "lectures": lecture_stats,
            "most_active_lectures": most_active,
            "least_active_lectures": least_active
        }
    finally:
        db.close()


@router.get("/api/teacher/analytics/lecture/{lecture_id}")
def teacher_analytics_lecture(lecture_id: int):

    db: Session = SessionLocal()

    try:
        lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()

        if not lecture:
            return {"message": "Lecture not found"}

        stats = _lecture_stats(db, lecture)

        attendance_rows = db.query(LectureAttendance).filter(
            LectureAttendance.lecture_id == lecture_id
        ).all()

        students = []
        for att in attendance_rows:
            student = db.query(Student).filter(Student.id == att.student_id).first()
            if not student:
                continue

            analytics_row = db.query(LectureAnalytics).filter(
                LectureAnalytics.lecture_id == lecture_id,
                LectureAnalytics.student_id == student.id
            ).first()

            chat_count = db.query(LectureChatMessage).filter(
                LectureChatMessage.lecture_id == lecture_id,
                LectureChatMessage.sender_type == "student",
                LectureChatMessage.sender_id == student.id
            ).count()

            students.append({
                "student_id": student.id,
                "name": student.full_name,
                "roll_number": student.roll_number,
                "time_present_minutes": att.total_minutes,
                "attention_percentage": analytics_row.attention_percentage if analytics_row else 0,
                "focus_time_seconds": analytics_row.focus_time_seconds if analytics_row else 0,
                "away_time_seconds": analytics_row.away_time_seconds if analytics_row else 0,
                "chat_messages": chat_count
            })

        # ---- NEW: per-poll breakdown for this lecture (additive) ----
        polls = db.query(LecturePoll).filter(
            LecturePoll.lecture_id == lecture_id
        ).order_by(LecturePoll.created_at.asc()).all()

        poll_summaries = []
        for poll in polls:
            answers = db.query(LecturePollAnswer).filter(
                LecturePollAnswer.poll_id == poll.id
            ).all()

            total_responses = len(answers)
            correct = len([a for a in answers if a.is_correct == "correct"])
            incorrect = len([a for a in answers if a.is_correct == "incorrect"])
            skipped = max(stats["students_present"] - total_responses, 0)

            options = {
                "A": poll.option_a, "B": poll.option_b,
                "C": poll.option_c, "D": poll.option_d
            }
            correct_text = options.get(poll.correct_option) if poll.correct_option else None

            poll_summaries.append({
                "poll_id": poll.id,
                "question": poll.question,
                "correct_option": poll.correct_option,
                "correct_text": correct_text,
                "has_correct_answer": poll.correct_option is not None,
                "total_responses": total_responses,
                "correct_responses": correct,
                "incorrect_responses": incorrect,
                "skipped_count": skipped,
                "accuracy_percentage": (
                    round((correct / total_responses) * 100, 1)
                    if poll.correct_option and total_responses > 0 else None
                ),
                "created_at": poll.created_at.isoformat() if poll.created_at else None
            })

        return {
            "lecture": stats,
            "students": students,
            "polls": poll_summaries
        }
    finally:
        db.close()


# =========================================================
# 5. INDIVIDUAL STUDENT ANALYTICS
# Aggregated across every lecture this teacher has taught
# that the student was eligible to attend.
#
# NOTE: every field that existed in this response before is
# still returned, unchanged, at the same path (student_details,
# attendance_analytics.{total_lectures, attended_lectures,
# attendance_percentage, time_present_minutes},
# attention_analytics.{average_attention, focus_time_seconds,
# away_time_seconds, attention_trend}, participation_analytics.*).
# Everything new is additive, either as new keys on those same
# objects or as new top-level sections.
# =========================================================

def _class_performance_scores(db: Session, teacher_id: int, year: str, division: str):
    """
    Performance score for every student in this teacher's class
    (same year+division), used both for the requesting student's
    own ranking and for the "Student Comparison Graph". Mirrors
    the same 4-factor blend used for lecture activity_score:
    attendance, attention, poll accuracy, participation (chat+poll).
    """

    classmates = db.query(Student).filter(
        Student.year == year,
        Student.division == division
    ).all()

    eligible_lectures = db.query(Lecture).filter(
        Lecture.teacher_id == teacher_id,
        Lecture.year == year,
        Lecture.division == division
    ).all()
    lecture_ids = [l.id for l in eligible_lectures]
    total_lectures = len(eligible_lectures)

    polls = db.query(LecturePoll).filter(
        LecturePoll.lecture_id.in_(lecture_ids) if lecture_ids else False
    ).all()
    poll_ids = [p.id for p in polls]
    graded_poll_ids = {p.id for p in polls if p.correct_option}

    scores = []
    for s in classmates:
        att_rows = db.query(LectureAttendance).filter(
            LectureAttendance.student_id == s.id,
            LectureAttendance.lecture_id.in_(lecture_ids) if lecture_ids else False
        ).all()
        attendance_pct = (
            round((len(att_rows) / total_lectures) * 100) if total_lectures > 0 else 0
        )

        an_rows = db.query(LectureAnalytics).filter(
            LectureAnalytics.student_id == s.id,
            LectureAnalytics.lecture_id.in_(lecture_ids) if lecture_ids else False
        ).all()
        avg_attention = (
            round(sum(r.attention_percentage for r in an_rows) / len(an_rows))
            if an_rows else 0
        )

        s_poll_answers = db.query(LecturePollAnswer).filter(
            LecturePollAnswer.student_id == s.id,
            LecturePollAnswer.poll_id.in_(poll_ids) if poll_ids else False
        ).all()
        graded_answers = [a for a in s_poll_answers if a.poll_id in graded_poll_ids]
        poll_accuracy = (
            round((len([a for a in graded_answers if a.is_correct == "correct"]) / len(graded_answers)) * 100)
            if graded_answers else 0
        )

        s_chat_count = db.query(LectureChatMessage).filter(
            LectureChatMessage.sender_type == "student",
            LectureChatMessage.sender_id == s.id,
            LectureChatMessage.lecture_id.in_(lecture_ids) if lecture_ids else False
        ).count()
        poll_participation_pct = (
            round((len(s_poll_answers) / len(polls)) * 100) if polls else 0
        )
        chat_participation_pct = (
            round((s_chat_count / total_lectures) * 100) if total_lectures > 0 else 0
        )
        participation_pct = round((poll_participation_pct + chat_participation_pct) / 2)

        performance = round(
            (attendance_pct + avg_attention + poll_accuracy + participation_pct) / 4
        )

        scores.append({
            "student_id": s.id,
            "name": s.full_name,
            "performance_percentage": performance,
            "attendance_percentage": attendance_pct,
            "average_attention": avg_attention,
            "poll_accuracy": poll_accuracy,
            "participation_percentage": participation_pct
        })

    scores.sort(key=lambda x: x["performance_percentage"], reverse=True)
    for i, s in enumerate(scores):
        s["class_rank"] = i + 1

    return scores


@router.get("/api/teacher/analytics/student/{teacher_id}/{student_id}")
def teacher_analytics_student(teacher_id: int, student_id: int):

    db: Session = SessionLocal()

    try:
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            return {"message": "Student not found"}

        eligible_lectures = db.query(Lecture).filter(
            Lecture.teacher_id == teacher_id,
            Lecture.year == student.year,
            Lecture.division == student.division
        ).order_by(Lecture.created_at.asc()).all()

        total_lectures = len(eligible_lectures)
        lecture_ids = [l.id for l in eligible_lectures]

        # -----------------------------------------------------
        # ATTENDANCE ANALYTICS
        # -----------------------------------------------------
        attendance_rows = db.query(LectureAttendance).filter(
            LectureAttendance.student_id == student_id,
            LectureAttendance.lecture_id.in_(lecture_ids) if lecture_ids else False
        ).all()

        attended_lectures = len(attendance_rows)
        attendance_pct = (
            round((attended_lectures / total_lectures) * 100)
            if total_lectures > 0 else 0
        )
        time_present_minutes = sum(a.total_minutes for a in attendance_rows)
        average_attendance_minutes = (
            round(time_present_minutes / attended_lectures)
            if attended_lectures > 0 else 0
        )

        attended_lecture_ids = {a.lecture_id for a in attendance_rows}
        attendance_table = []
        for lec in eligible_lectures:
            att_row = next((a for a in attendance_rows if a.lecture_id == lec.id), None)
            attendance_table.append({
                "lecture_id": lec.id,
                "title": lec.title,
                "date": lec.scheduled_date,
                "attended": lec.id in attended_lecture_ids,
                "time_present_minutes": att_row.total_minutes if att_row else 0
            })

        # -----------------------------------------------------
        # ATTENTION ANALYTICS
        # -----------------------------------------------------
        analytics_rows = db.query(LectureAnalytics).filter(
            LectureAnalytics.student_id == student_id,
            LectureAnalytics.lecture_id.in_(lecture_ids) if lecture_ids else False
        ).all()

        avg_attention = (
            round(sum(r.attention_percentage for r in analytics_rows) / len(analytics_rows))
            if analytics_rows else 0
        )
        total_focus = sum(r.focus_time_seconds for r in analytics_rows)
        total_away = sum(r.away_time_seconds for r in analytics_rows)
        total_face_present = sum((r.face_present_count or 0) for r in analytics_rows)
        total_face_missing = sum((r.face_missing_count or 0) for r in analytics_rows)

        # Attention trend: one point per lecture, chronological
        # (also doubles as the "Lecture-wise Attention Graph")
        analytics_by_lecture = {r.lecture_id: r for r in analytics_rows}
        attention_trend = []
        daily_attention = {}   # date -> [percentages] for the "Daily Attention Graph"
        for lec in eligible_lectures:
            row = analytics_by_lecture.get(lec.id)
            pct = row.attention_percentage if row else None
            attention_trend.append({
                "lecture_id": lec.id,
                "title": lec.title,
                "date": lec.scheduled_date,
                "attention_percentage": pct
            })
            if pct is not None and lec.scheduled_date:
                daily_attention.setdefault(lec.scheduled_date, []).append(pct)

        daily_attention_graph = [
            {"date": d, "attention_percentage": round(sum(v) / len(v))}
            for d, v in sorted(daily_attention.items())
        ]

        # Attention distribution buckets, for the pie chart
        attention_distribution = {"high (>=75%)": 0, "medium (40-74%)": 0, "low (<40%)": 0}
        for r in analytics_rows:
            p = r.attention_percentage or 0
            if p >= 75:
                attention_distribution["high (>=75%)"] += 1
            elif p >= 40:
                attention_distribution["medium (40-74%)"] += 1
            else:
                attention_distribution["low (<40%)"] += 1

        # -----------------------------------------------------
        # POLL ANALYTICS
        # -----------------------------------------------------
        polls = db.query(LecturePoll).filter(
            LecturePoll.lecture_id.in_(lecture_ids) if lecture_ids else False
        ).order_by(LecturePoll.created_at.asc()).all()
        poll_ids = [p.id for p in polls]

        poll_answer_rows = db.query(LecturePollAnswer).filter(
            LecturePollAnswer.student_id == student_id,
            LecturePollAnswer.poll_id.in_(poll_ids) if poll_ids else False
        ).all()
        answers_by_poll = {a.poll_id: a for a in poll_answer_rows}

        poll_participation_pct = (
            round((len(poll_answer_rows) / len(polls)) * 100) if polls else 0
        )

        options_map = {}
        poll_detail = []
        graded_count = 0
        correct_count = 0
        incorrect_count = 0
        skipped_count = 0

        for poll in polls:
            options = {
                "A": poll.option_a, "B": poll.option_b,
                "C": poll.option_c, "D": poll.option_d
            }
            ans = answers_by_poll.get(poll.id)
            lecture = next((l for l in eligible_lectures if l.id == poll.lecture_id), None)

            if ans is None:
                result = "skipped"
                skipped_count += 1
            elif poll.correct_option is None:
                result = "ungraded"
            elif ans.is_correct == "correct":
                result = "correct"
                graded_count += 1
                correct_count += 1
            else:
                result = "incorrect"
                graded_count += 1
                incorrect_count += 1

            poll_detail.append({
                "poll_id": poll.id,
                "lecture_id": poll.lecture_id,
                "lecture_title": lecture.title if lecture else None,
                "question": poll.question,
                "options": options,
                "correct_option": poll.correct_option,
                "selected_option": ans.selected_option if ans else None,
                "result": result,
                "submitted_at": ans.created_at.isoformat() if ans and ans.created_at else None
            })

        poll_accuracy_pct = (
            round((correct_count / graded_count) * 100) if graded_count > 0 else 0
        )
        poll_score = correct_count  # 1 point per correct answer, simple & transparent

        # -----------------------------------------------------
        # CHAT ANALYTICS
        # -----------------------------------------------------
        chat_rows = db.query(LectureChatMessage).filter(
            LectureChatMessage.sender_type == "student",
            LectureChatMessage.sender_id == student_id,
            LectureChatMessage.lecture_id.in_(lecture_ids) if lecture_ids else False
        ).order_by(LectureChatMessage.created_at.asc()).all()

        questions_asked = len([m for m in chat_rows if "?" in (m.message or "")])

        chat_messages_detail = [
            {
                "lecture_id": m.lecture_id,
                "message": m.message,
                "is_question": "?" in (m.message or ""),
                "created_at": m.created_at.isoformat() if m.created_at else None
            }
            for m in chat_rows
        ]

        # Message activity graph: messages per lecture (chronological)
        chat_by_lecture = {}
        for m in chat_rows:
            chat_by_lecture[m.lecture_id] = chat_by_lecture.get(m.lecture_id, 0) + 1
        message_activity = [
            {
                "lecture_id": lec.id,
                "title": lec.title,
                "date": lec.scheduled_date,
                "message_count": chat_by_lecture.get(lec.id, 0)
            }
            for lec in eligible_lectures
        ]

        chat_engagement_score = round(
            min(100, (len(chat_rows) * 10) + (questions_asked * 5))
        )  # simple bounded heuristic: participation, weighted toward asking questions

        # -----------------------------------------------------
        # OVERALL PERFORMANCE + RANKING
        # -----------------------------------------------------
        class_scores = _class_performance_scores(
            db, teacher_id, student.year, student.division
        )
        my_score = next((s for s in class_scores if s["student_id"] == student_id), None)
        performance_percentage = my_score["performance_percentage"] if my_score else 0
        class_rank = my_score["class_rank"] if my_score else None
        class_size = len(class_scores)

        return {
            "student_details": {
                "student_id": student.id,
                "name": student.full_name,
                "roll_number": student.roll_number,
                "department": student.course,
                "year": student.year,
                "semester": student.semester,
                "division": student.division
            },

            # ---- existing shape, fully preserved ----
            "attendance_analytics": {
                "total_lectures": total_lectures,
                "attended_lectures": attended_lectures,
                "attendance_percentage": attendance_pct,
                "time_present_minutes": time_present_minutes,
                # new:
                "average_attendance_minutes": average_attendance_minutes,
                "attendance_table": attendance_table
            },
            "attention_analytics": {
                "average_attention": avg_attention,
                "focus_time_seconds": total_focus,
                "away_time_seconds": total_away,
                "attention_trend": attention_trend,
                # new:
                "face_present_count": total_face_present,
                "face_missing_count": total_face_missing,
                "daily_attention_graph": daily_attention_graph,
                "lecture_wise_attention_graph": attention_trend,
                "attention_distribution": attention_distribution
            },
            "participation_analytics": {
                "poll_participation_percentage": poll_participation_pct,
                "chat_messages": len(chat_rows),
                "questions_asked": questions_asked
            },

            # ---- new top-level sections ----
            "poll_analytics": {
                "poll_score": poll_score,
                "poll_accuracy_percentage": poll_accuracy_pct,
                "correct_answers_count": correct_count,
                "incorrect_answers_count": incorrect_count,
                "skipped_count": skipped_count,
                "graded_polls_count": graded_count,
                "total_polls": len(polls),
                "polls": poll_detail
            },
            "chat_analytics": {
                "total_messages": len(chat_rows),
                "questions_asked": questions_asked,
                "engagement_score": chat_engagement_score,
                "messages": chat_messages_detail,
                "message_activity": message_activity
            },
            "performance": {
                "performance_percentage": performance_percentage,
                "class_rank": class_rank,
                "class_size": class_size,
                "breakdown": {
                    "attendance_percentage": attendance_pct,
                    "average_attention": avg_attention,
                    "poll_accuracy_percentage": poll_accuracy_pct,
                    "participation_percentage": (
                        my_score["participation_percentage"] if my_score else 0
                    )
                },
                "class_comparison": class_scores
            }
        }
    finally:
        db.close()


@router.get("/api/teacher/analytics/students/{lecture_id}")
def students_in_lecture_for_analytics(lecture_id: int):
    """Lightweight list used by the dashboard to populate the
    'pick a student' selector for a given lecture."""

    db: Session = SessionLocal()

    try:
        attendance_rows = db.query(LectureAttendance).filter(
            LectureAttendance.lecture_id == lecture_id
        ).all()

        data = []
        for att in attendance_rows:
            student = db.query(Student).filter(Student.id == att.student_id).first()
            if student:
                data.append({"student_id": student.id, "name": student.full_name})

        return data
    finally:
        db.close()
