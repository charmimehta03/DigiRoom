/* =========================================================
   poll.js
   Shared poll module, used by both the teacher and the
   student live lecture pages. Behavior branches on `role`.

   Required globals (set by live_lecture.js / student_live_lecture.js):
       socket, lectureId
       role        -> "teacher" or "student"
       senderId    -> teacher_id or student_id (studentId for students)

   Teacher DOM elements:
       #pollQuestion, #optionA, #optionB, #optionC, #optionD
       #createPoll
       #pollResults   (container where live results render)

   Student DOM elements:
       #pollPanel     (container where the active poll renders)
   ========================================================= */

let activePollId = null;
let hasAnsweredActivePoll = false;


/* ---------------------------------------------------------
   TEACHER: create a poll from the form fields.
   --------------------------------------------------------- */
function createPoll() {

    if (role !== "teacher") return;

    const question = document.getElementById("pollQuestion").value.trim();
    const a = document.getElementById("optionA").value.trim();
    const b = document.getElementById("optionB").value.trim();
    const c = document.getElementById("optionC").value.trim();
    const d = document.getElementById("optionD").value.trim();

    // #correctOption is a new, optional element. Polls work exactly
    // as before on any page that doesn't have it.
    const correctOptionEl = document.getElementById("correctOption");
    const correctOption = correctOptionEl ? correctOptionEl.value.trim() : "";

    if (!question || !a || !b) {
        alert("Question, Option A and Option B are required.");
        return;
    }

    const filledOptions = { A: a, B: b, C: c, D: d };

    if (correctOption && !filledOptions[correctOption]) {
        alert(`Correct Answer is set to Option ${correctOption}, but Option ${correctOption} is empty.`);
        return;
    }

    socket.emit("poll_created", {
        lecture_id: lectureId,
        question: question,
        option_a: a,
        option_b: b,
        option_c: c || null,
        option_d: d || null,
        correct_option: correctOption || null
    });

    document.getElementById("pollQuestion").value = "";
    document.getElementById("optionA").value = "";
    document.getElementById("optionB").value = "";
    document.getElementById("optionC").value = "";
    document.getElementById("optionD").value = "";
    if (correctOptionEl) correctOptionEl.value = "";
}


/* ---------------------------------------------------------
   TEACHER: render live results (counts + percentages).
   Shows accuracy too, but only when the poll has a correct
   answer defined — ungraded polls render exactly as before.
   --------------------------------------------------------- */
function renderPollResults(data) {

    if (role !== "teacher") return;

    const container = document.getElementById("pollResults");
    if (!container) return;

    let html = `
        <strong>Live Results</strong> (${data.total_votes} votes)<br>
        A: ${data.counts.A} (${data.percentages.A}%)<br>
        B: ${data.counts.B} (${data.percentages.B}%)<br>
        C: ${data.counts.C} (${data.percentages.C}%)<br>
        D: ${data.counts.D} (${data.percentages.D}%)
    `;

    if (data.has_correct_answer) {
        html += `
            <br><strong>Accuracy:</strong> ${data.accuracy_percentage}%
            (${data.correct_count} correct / ${data.incorrect_count} incorrect)
        `;
    }

    container.innerHTML = html;
}


/* ---------------------------------------------------------
   STUDENT: render an incoming poll with selectable options.
   Students never see other students' answers — only whether
   THEIR OWN answer was recorded.
   --------------------------------------------------------- */
function renderStudentPoll(poll) {

    if (role !== "student") return;

    activePollId = poll.id;
    hasAnsweredActivePoll = false;

    const container = document.getElementById("pollPanel");
    if (!container) return;

    const options = [
        ["A", poll.option_a],
        ["B", poll.option_b],
        ["C", poll.option_c],
        ["D", poll.option_d]
    ].filter(([, label]) => !!label);

    let html = `<strong>${poll.question}</strong><br>`;

    options.forEach(([key, label]) => {
        html += `
            <button
                class="pollOptionBtn"
                data-option="${key}"
                style="display:block;margin:6px 0;padding:8px;width:100%;text-align:left;"
            >${key}. ${label}</button>
        `;
    });

    html += `<div id="pollStatus" style="margin-top:8px;font-style:italic;"></div>`;

    container.innerHTML = html;

    container.querySelectorAll(".pollOptionBtn").forEach(btn => {
        btn.addEventListener("click", () => {
            submitPollAnswer(poll.id, btn.getAttribute("data-option"));
        });
    });
}


/* ---------------------------------------------------------
   STUDENT: submit an answer.
   --------------------------------------------------------- */
function submitPollAnswer(pollId, selectedOption) {

    if (role !== "student") return;
    if (hasAnsweredActivePoll) return;

    socket.emit("poll_answer", {
        lecture_id: lectureId,
        poll_id: pollId,
        student_id: senderId,
        selected_option: selectedOption
    });
}


/* ---------------------------------------------------------
   Socket listeners
   --------------------------------------------------------- */

socket.on("poll_created", data => {

    if (role === "student") {
        renderStudentPoll(data);
    }
});

socket.on("poll_results", data => {

    if (role === "teacher") {
        renderPollResults(data);
    }
});

socket.on("poll_answer_received", data => {

    if (role !== "student") return;
    if (data.poll_id !== activePollId) return;

    hasAnsweredActivePoll = true;

    const status = document.getElementById("pollStatus");
    if (status) {
        // is_correct is only ever present here because the server
        // scopes it to this student's own just-submitted answer.
        // Polls without a correct answer keep the original message.
        if (data.is_correct === "correct") {
            status.innerText = "✓ Your answer has been submitted. Correct! 🎉";
        } else if (data.is_correct === "incorrect") {
            status.innerText = "✓ Your answer has been submitted. Incorrect.";
        } else {
            status.innerText = "✓ Your answer has been submitted.";
        }
    }
});


/* ---------------------------------------------------------
   Wire up the teacher's "Create Poll" button, if present.
   --------------------------------------------------------- */
document.addEventListener("DOMContentLoaded", () => {

    const createBtn = document.getElementById("createPoll");

    if (createBtn) {
        createBtn.addEventListener("click", createPoll);
    }
});
