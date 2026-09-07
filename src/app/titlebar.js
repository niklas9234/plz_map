(function initializeDesktopTitlebar() {
    "use strict";

    const HIDE_DELAY_MS = 2000;

    const WINDOW_ACTIONS = {
        minimize: "window_minimize",
        maximize: "window_toggle_maximize",
        close: "window_close",
    };

    function createController(titlebar, trigger, timers = window) {
        let hideTimer;

        function cancelHide() {
            if (hideTimer !== undefined) timers.clearTimeout(hideTimer);
            hideTimer = undefined;
        }

        function hideTitlebar() {
            hideTimer = undefined;
            titlebar.classList.remove("is-visible");
            titlebar.inert = true;
        }

        function scheduleHide() {
            cancelHide();
            hideTimer = timers.setTimeout(hideTitlebar, HIDE_DELAY_MS);
        }

        function showTitlebar() {
            cancelHide();
            titlebar.inert = false;
            titlebar.classList.add("is-visible");
        }

        trigger.addEventListener("mouseenter", showTitlebar);
        titlebar.addEventListener("mouseenter", cancelHide);
        titlebar.addEventListener("mouseleave", scheduleHide);

        return { hideTitlebar, scheduleHide, showTitlebar };
    }

    if (typeof module !== "undefined") module.exports = { createController, HIDE_DELAY_MS };
    if (typeof document === "undefined") return;

    const titlebar = document.getElementById("desktop-titlebar");
    const trigger = document.getElementById("desktop-titlebar-trigger");
    if (!titlebar || !trigger) return;

    async function callWindowAction(action) {
        const api = window.pywebview && window.pywebview.api;
        const method = WINDOW_ACTIONS[action];
        if (!api || typeof api[method] !== "function") return;
        await api[method]();
    }

    function enableTitlebar() {
        document.documentElement.classList.add("desktop-window");
        titlebar.hidden = false;
        titlebar.inert = true;
        trigger.hidden = false;
    }

    // The explicit URL marker is available before any scripts execute. The
    // bridge checks remain as a fallback when an older launcher opens the app.
    if (new URLSearchParams(window.location.search).has("desktop") || window.pywebview) {
        enableTitlebar();
    }
    window.addEventListener("pywebviewready", enableTitlebar);

    createController(titlebar, trigger);

    document.getElementById("window-minimize").addEventListener("click", () => callWindowAction("minimize"));
    document.getElementById("window-maximize").addEventListener("click", () => callWindowAction("maximize"));
    document.getElementById("window-close").addEventListener("click", () => callWindowAction("close"));

}());
