(function initializeDesktopTitlebar() {
    "use strict";

    const titlebar = document.getElementById("desktop-titlebar");
    const trigger = document.getElementById("desktop-titlebar-trigger");
    if (!titlebar || !trigger) return;

    let hideTimer;

    function showTitlebar() {
        window.clearTimeout(hideTimer);
        titlebar.classList.add("is-visible");
    }

    function scheduleHide() {
        window.clearTimeout(hideTimer);
        hideTimer = window.setTimeout(() => {
            titlebar.classList.remove("is-visible");
        }, 3000);
    }

    async function callWindowAction(action) {
        const api = window.pywebview && window.pywebview.api;
        if (api && typeof api[action] === "function") await api[action]();
    }

    window.addEventListener("pywebviewready", () => {
        document.documentElement.classList.add("desktop-window");
        titlebar.hidden = false;
        trigger.hidden = false;
    });

    trigger.addEventListener("mouseenter", showTitlebar);
    titlebar.addEventListener("mouseenter", showTitlebar);
    titlebar.addEventListener("mouseleave", scheduleHide);
    titlebar.addEventListener("focusin", showTitlebar);
    titlebar.addEventListener("focusout", event => {
        if (!titlebar.contains(event.relatedTarget)) scheduleHide();
    });

    document.getElementById("window-minimize").addEventListener("click", () => callWindowAction("minimize"));
    document.getElementById("window-maximize").addEventListener("click", () => callWindowAction("toggle_maximize"));
    document.getElementById("window-close").addEventListener("click", () => callWindowAction("close"));
}());
