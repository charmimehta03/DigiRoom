/* =========================================================
   chat.js
   Shared real-time chat module, used by both the teacher and
   the student live lecture pages.

   Required globals (already defined by the page that loads
   this script, e.g. live_lecture.js / student_live_lecture.js):
       socket, lectureId
       role         -> "teacher" or "student"
       senderId     -> teacher_id or student_id
       senderName   -> display name

   Required DOM elements on the page:
       #chatMessages   (scrollable container)
       #chatInput      (text input)
       #sendChat       (send button)
   ========================================================= */

function renderChatMessage(msg) {

    const container = document.getElementById("chatMessages");
    if (!container) return;

    const isMine =
        msg.sender_type === role &&
        String(msg.sender_id) === String(senderId);

    const row = document.createElement("div");
    row.style.margin = "6px 0";
    row.style.textAlign = isMine ? "right" : "left";

    const bubble = document.createElement("span");
    bubble.style.display = "inline-block";
    bubble.style.padding = "6px 10px";
    bubble.style.borderRadius = "10px";
    bubble.style.maxWidth = "75%";
    bubble.style.background =
        msg.sender_type === "teacher" ? "#dff0d8" : "#eef1f5";

    const label = document.createElement("div");
    label.style.fontSize = "11px";
    label.style.fontWeight = "bold";
    label.style.opacity = "0.7";
    label.innerText =
        (msg.sender_type === "teacher" ? "👨‍🏫 " : "🎓 ") +
        msg.sender_name;

    const text = document.createElement("div");
    text.innerText = msg.message;

    bubble.appendChild(label);
    bubble.appendChild(text);
    row.appendChild(bubble);
    container.appendChild(row);

    container.scrollTop = container.scrollHeight;
}


function loadChatHistory() {

    fetch(`/api/live-lecture/chat-history/${lectureId}`)
    .then(response => response.json())
    .then(messages => {

        const container = document.getElementById("chatMessages");
        if (container) container.innerHTML = "";

        messages.forEach(renderChatMessage);
    })
    .catch(error => {
        console.log("Chat history load error:", error);
    });
}


function sendChatMessage() {

    const input = document.getElementById("chatInput");
    if (!input) return;

    const text = input.value.trim();
    if (!text) return;

    socket.emit("chat_message", {
        lecture_id: lectureId,
        sender_type: role,
        sender_id: senderId,
        sender_name: senderName,
        message: text
    });

    input.value = "";
}


/* ---------------------------------------------------------
   Wire up UI + socket listener once the DOM is ready.
   --------------------------------------------------------- */
document.addEventListener("DOMContentLoaded", () => {

    loadChatHistory();

    const sendBtn = document.getElementById("sendChat");
    const input = document.getElementById("chatInput");

    if (sendBtn) {
        sendBtn.addEventListener("click", sendChatMessage);
    }

    if (input) {
        input.addEventListener("keydown", event => {
            if (event.key === "Enter") {
                sendChatMessage();
            }
        });
    }
});

socket.on("chat_message", renderChatMessage);
