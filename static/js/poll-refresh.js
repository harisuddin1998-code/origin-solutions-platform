(function () {
  // Deliberate trade-off for hosts without WebSocket support (see README):
  // pages that used to update instantly via a socket push now just poll by
  // reloading on an interval set via {% block poll_interval %} in base.html.
  const interval = parseInt(document.body.dataset.pollInterval || "", 10);
  if (!interval) return;
  setInterval(() => window.location.reload(), interval);
})();
