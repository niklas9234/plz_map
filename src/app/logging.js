(function () {
  "use strict";

  const endpoint = "/api/logs/frontend";

  function write(level, message) {
    const body = JSON.stringify({ level, message: String(message) });
    if (navigator.sendBeacon && level === "error") {
      navigator.sendBeacon(endpoint, new Blob([body], { type: "application/json" }));
      return;
    }
    fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      keepalive: true
    }).catch(() => {});
  }

  window.plzLog = {
    info: (message) => write("info", message),
    warning: (message) => write("warning", message),
    error: (message) => write("error", message)
  };

  window.addEventListener("error", (event) => {
    write("error", `JavaScript-Fehler: ${event.message} (${event.filename}:${event.lineno}:${event.colno})`);
  });
  window.addEventListener("unhandledrejection", (event) => {
    write("error", `Unbehandelte Promise-Ablehnung: ${event.reason}`);
  });
  window.addEventListener("DOMContentLoaded", () => write("info", "Frontend geladen"));
})();
