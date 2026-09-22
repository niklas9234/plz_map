(function initializeLifecycle() {
    const shutdownButton = document.getElementById("shutdown-application");
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
            shutdownButton.hidden = false;
            await sendHeartbeat();
            heartbeatTimer = window.setInterval(
                sendHeartbeat,
                Math.max(5, session.heartbeatInterval) * 1000,
            );
        } catch (error) {
            window.logFrontend?.("warning", `Lebenszyklus konnte nicht gestartet werden: ${error.message}`);
        }
    }

    shutdownButton.addEventListener("click", async () => {
        if (!session || !window.confirm("PLZ-Karte wirklich beenden?")) return;
        shutdownButton.disabled = true;
        window.clearInterval(heartbeatTimer);
        try {
            const response = await fetch("/api/system/shutdown", {
                method: "POST",
                headers: {"X-PLZ-Map-Token": session.token},
            });
            if (!response.ok) throw new Error(`Beenden fehlgeschlagen (${response.status})`);
            document.body.innerHTML = "<main><h1>PLZ-Karte wurde beendet.</h1><p>Dieses Fenster kann geschlossen werden.</p></main>";
        } catch (error) {
            shutdownButton.disabled = false;
            window.alert(error.message);
        }
    });

    startHeartbeat();
})();
