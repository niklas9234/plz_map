(function initializeLifecycle() {
    let session;
    let heartbeatTimer;

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

    startHeartbeat();
})();
