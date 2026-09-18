(function () {
  const toggle = document.getElementById("notif-bell-toggle");
  const dropdown = document.getElementById("notif-dropdown");
  const badge = document.getElementById("notif-badge");
  if (!toggle || !dropdown) return;

  toggle.addEventListener("click", (e) => {
    e.stopPropagation();
    dropdown.classList.toggle("hidden");
  });

  document.addEventListener("click", (e) => {
    if (!dropdown.contains(e.target) && e.target !== toggle) {
      dropdown.classList.add("hidden");
    }
  });

  if (badge) {
    setInterval(() => {
      fetch("/notifications/unread-count")
        .then((res) => res.json())
        .then((data) => {
          const count = data.unread_count || 0;
          badge.textContent = count;
          badge.classList.toggle("hidden", count === 0);
        })
        .catch(() => {});
    }, 20000);
  }
})();
