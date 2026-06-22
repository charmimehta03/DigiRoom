async function loadDashboard() {
  try {
    const response = await fetch("/api/institute/dashboard");
    const data = await response.json();

    // Stat cards
    document.getElementById("totalTeachers").innerText    = data.total_teachers;
    document.getElementById("approvedTeachers").innerText = data.approved_teachers;
    document.getElementById("pendingTeachers").innerText  = data.pending_teachers;
    document.getElementById("totalStudents").innerText    = data.total_students;
    document.getElementById("approvedStudents").innerText = data.approved_students;
    document.getElementById("pendingStudents").innerText  = data.pending_students;
    document.getElementById("departmentsCount").innerText = data.departments;
    document.getElementById("subjectsCount").innerText    = data.subjects;

    // Animate stat values counting up
    animateCounters();

  } catch (err) {
    console.error("Dashboard load error:", err);
    document.querySelectorAll(".stat-value, .badge").forEach(el => {
      if (el.innerText === "—") el.innerText = "N/A";
    });
  }
}

// Count-up animation for stat values
function animateCounters() {
  document.querySelectorAll(".stat-value").forEach(el => {
    const target = parseInt(el.innerText);
    if (isNaN(target)) return;
    let current = 0;
    const step = Math.ceil(target / 40);
    const timer = setInterval(() => {
      current = Math.min(current + step, target);
      el.innerText = current;
      if (current >= target) clearInterval(timer);
    }, 30);
  });
}

// Active nav highlight on scroll
const sections = document.querySelectorAll("[id]");
const navItems = document.querySelectorAll(".nav-item");

window.addEventListener("scroll", () => {
  let current = "";
  sections.forEach(sec => {
    if (window.scrollY >= sec.offsetTop - 120) current = sec.id;
  });
  navItems.forEach(item => {
    item.classList.remove("active");
    if (item.getAttribute("href") === `#${current}`) item.classList.add("active");
  });
});

loadDashboard();