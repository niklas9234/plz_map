(function initializeDesktopTitlebar() {
    "use strict";

    const titlebar = document.getElementById("desktop-titlebar");
    const trigger = document.getElementById("desktop-titlebar-trigger");
    if (!titlebar || !trigger) return;

    const visibleDuration = 5000;
    let hideTimer;

    function hideTitlebar() {
        titlebar.classList.remove("is-visible");
    }

    function scheduleHide() {
        window.clearTimeout(hideTimer);
        hideTimer = window.setTimeout(hideTitlebar, visibleDuration);
    }

    function showTitlebar() {
        window.clearTimeout(hideTimer);
        titlebar.classList.add("is-visible");
        scheduleHide();
    }

    async function callWindowAction(action) {
        const api = window.pywebview && window.pywebview.api;
        if (api && typeof api[action] === "function") await api[action]();
    }

    function enableTitlebar() {
        document.documentElement.classList.add("desktop-window");
        titlebar.hidden = false;
        trigger.hidden = false;
    }

    // Depending on the webview engine, the bridge can be ready before the last
    // page scripts execute. Support both that case and the regular ready event.
    if (window.pywebview) enableTitlebar();
    window.addEventListener("pywebviewready", enableTitlebar);

    trigger.addEventListener("mouseenter", showTitlebar);
    titlebar.addEventListener("mouseenter", () => window.clearTimeout(hideTimer));
    titlebar.addEventListener("mouseleave", scheduleHide);
    titlebar.addEventListener("focusin", () => window.clearTimeout(hideTimer));
    titlebar.addEventListener("focusout", event => {
        if (!titlebar.contains(event.relatedTarget)) scheduleHide();
    });

    document.getElementById("window-minimize").addEventListener("click", () => callWindowAction("minimize"));
    document.getElementById("window-maximize").addEventListener("click", () => callWindowAction("toggle_maximize"));
    document.getElementById("window-close").addEventListener("click", () => callWindowAction("close"));
}());
