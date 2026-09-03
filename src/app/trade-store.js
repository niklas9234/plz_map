const TRADE_API_URL = "/api/trades";
const LEGACY_TRADE_STORAGE_KEY = "plz-map.trades.v1";

// Gut unterscheidbare, etwas entsättigte Farben für Karte und Farbwähler.
const TRADE_COLORS = [
    "#72b788", "#63b5ad", "#68a9c7", "#7898ca", "#938bc5",
    "#a85fa8", "#c45c83", "#d06a62", "#d1844f", "#c39a3d",
    "#b3b65e", "#8eb969", "#69b99a", "#5fb3c3", "#758fc8",
    "#73599b", "#92527e", "#a65e68", "#ad684f", "#8f7848"
];

const tradeStore = (() => {
    let trades;

    function clone(value) {
        return JSON.parse(JSON.stringify(value));
    }

    function normalizeTrade(trade) {
        return {
            id: trade.id == null ? "" : String(trade.id),
            name: String(trade.name || "").trim(),
            active: trade.active !== undefined ? trade.active !== false : trade.status !== "inactive",
            color: trade.color || "#d7ded9"
        };
    }

    function errorMessage(status, details) {
        const suffix = details?.message ? ` ${details.message}` : "";
        if (status === 400 || status === 422) return `Die Gewerkdaten sind ungültig.${suffix}`;
        if (status === 409) return `Konflikt bei den Gewerkdaten.${suffix}`;
        if (status === 404) return `Das Gewerk wurde nicht gefunden.${suffix}`;
        return `Das Backend konnte die Gewerk-Anfrage nicht verarbeiten (${status}).${suffix}`;
    }

    async function request(path = "", options = {}) {
        let response;
        try {
            response = await fetch(`${TRADE_API_URL}${path}`, {
                ...options,
                headers: { "Content-Type": "application/json", Accept: "application/json", ...options.headers }
            });
        } catch (_) {
            throw new Error("Das Backend ist nicht erreichbar. Bitte prüfen Sie die Verbindung und versuchen Sie es erneut.");
        }
        let body = null;
        if (response.status !== 204) {
            try { body = await response.json(); } catch (_) { /* Eine Fehlerantwort darf leer sein. */ }
        }
        if (!response.ok) throw new Error(errorMessage(response.status, body));
        return body;
    }

    async function initialize() {
        if (trades) return;
        const result = await request();
        const items = Array.isArray(result) ? result : result?.items;
        if (!Array.isArray(items)) throw new Error("Das Backend hat ungültige Gewerkdaten geliefert.");
        trades = items.map(normalizeTrade);
        // Kontrollierter Abschluss der Übergangsphase: erst nach erfolgreichem GET,
        // niemals als Fallback oder dauerhafte Datenquelle.
        try { localStorage.removeItem(LEGACY_TRADE_STORAGE_KEY); } catch (_) { /* Storage kann gesperrt sein. */ }
    }

    function changed() {
        window.dispatchEvent(new CustomEvent("trades:changed"));
    }

    function findByName(name) {
        const trade = trades.find((item) => item.name === name);
        if (!trade) throw new Error("Das Gewerk wurde nicht gefunden.");
        return trade;
    }

    async function list() {
        await initialize();
        return clone(trades);
    }

    async function add(name, color) {
        await initialize();
        const response = await request("", {
            method: "POST",
            body: JSON.stringify({ name: name.trim(), color })
        });
        if (!response) throw new Error("Das Backend hat das gespeicherte Gewerk nicht zurückgegeben.");
        const created = normalizeTrade(response);
        trades.push(created);
        trades.sort((left, right) => left.name.localeCompare(right.name, "de"));
        changed();
        return clone(created);
    }

    async function patch(name, payload) {
        const current = findByName(name);
        const response = await request(`/${encodeURIComponent(current.id)}`, {
            method: "PATCH",
            body: JSON.stringify(payload)
        });
        const updated = normalizeTrade(response || { ...current, ...payload });
        trades[trades.indexOf(current)] = updated;
        changed();
        return clone(updated);
    }

    async function setColor(name, color) {
        await initialize();
        return patch(name, { color });
    }

    async function remove(name) {
        await initialize();
        const trade = findByName(name);
        await request(`/${encodeURIComponent(trade.id)}`, { method: "DELETE" });
        trades = trades.filter((item) => item.id !== trade.id);
        changed();
    }

    async function colorFor(name) {
        await initialize();
        return trades.find((trade) => trade.name === name)?.color || "#d7ded9";
    }

    async function setActive(name, active) {
        await initialize();
        const current = findByName(name);
        const response = await request(`/${encodeURIComponent(current.id)}/${active ? "activate" : "deactivate"}`, { method: "POST" });
        const updated = normalizeTrade(response || { ...current, active });
        trades[trades.indexOf(current)] = updated;
        changed();
        return clone(updated);
    }

    return { list, add, remove, setActive, setColor, colorFor, colors: TRADE_COLORS };
})();
