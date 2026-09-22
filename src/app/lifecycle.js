(function initializeLifecycle() {
    let session;
    let heartbeatTimer;

    function closeSurface() {
        if (!session) return;
        window.clearInterval(heartbeatTimer);
        const closingSession = session;
        session = undefined;
        const body = JSON.stringify({
            token: closingSession.token,
            surfaceId: closingSession.surfaceId,
        });
        if (navigator.sendBeacon) {
            const queued = navigator.sendBeacon(
                "/api/system/session/close",
                new Blob([body], {type: "application/json"}),
            );
            if (queued) return;
        }
        fetch("/api/system/session/close", {
            method: "POST",
            cache: "no-store",
            keepalive: true,
            headers: {"Content-Type": "application/json"},
            body,
        }).catch(() => {});
    }

    async function sendHeartbeat() {
        if (!session) return;
        try {
            const response = await fetch("/api/system/heartbeat", {
                method: "POST",
                cache: "no-store",
                headers: {
                    "X-PLZ-Map-Token": session.token,
                    "X-PLZ-Map-Surface": session.surfaceId,
                },
            });
            if (!response.ok) throw new Error(`Heartbeat fehlgeschlagen (${response.status})`);
        } catch (error) {
            window.logFrontend?.("warning", error.message);
        }
    }

    async function startHeartbeat() {
        try {
            const response = await fetch("/api/system/session", {
                method: "POST",
                cache: "no-store",
            });
            if (!response.ok) return;
            session = await response.json();
            await sendHeartbeat();
            heartbeatTimer = window.setInterval(
                sendHeartbeat,
                Math.max(5, session.heartbeatInterval) * 1000,
            );
        } catch (error) {
            window.logFrontend?.("warning", `Lebenszyklus konnte nicht gestartet werden: ${error.message}`);
        }
    }

    window.addEventListener("pagehide", () => {
        if (!session) return;
        window.clearInterval(heartbeatTimer);
        fetch("/api/system/session/close", {
            method: "POST",
            cache: "no-store",
            keepalive: true,
            headers: {
                "X-PLZ-Map-Token": session.token,
                "X-PLZ-Map-Surface": session.surfaceId,
            },
        }).catch(() => {});
    });

    // Reloads and short navigations register again before the server-side
    // grace period expires. A page restored from the back-forward cache must
    // explicitly obtain a fresh surface because its script is not reloaded.
    window.addEventListener("pagehide", closeSurface);
    window.addEventListener("pageshow", (event) => {
        if (event.persisted && !session) startHeartbeat();
    });

    startHeartbeat();
})();
