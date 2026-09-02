// Mobile nav toggle
document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.getElementById("navToggle");
  const nav = document.getElementById("mainNav");
  if (toggle && nav) {
    toggle.addEventListener("click", () => nav.classList.toggle("open"));
  }

  // Auto-dismiss flash messages after 5s
  document.querySelectorAll(".flash").forEach((el) => {
    setTimeout(() => { el.style.transition = "opacity .4s"; el.style.opacity = "0"; }, 5000);
  });
});
