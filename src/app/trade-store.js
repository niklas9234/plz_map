const TRADE_API_URL = "/api/trades";
const TRADE_COLORS = [
    "#72b788", "#63b5ad", "#68a9c7", "#7898ca", "#938bc5",
    "#a85fa8", "#c45c83", "#d06a62", "#d1844f", "#c39a3d",
    "#b3b65e", "#8eb969", "#69b99a", "#5fb3c3", "#758fc8",
    "#73599b", "#92527e", "#a65e68", "#ad684f", "#8f7848"
];

const tradeStore = (() => {
    async function request(path = "", options = {}) {
        const response = await fetch(`${TRADE_API_URL}${path}`, {
            ...options,
            headers: options.body ? { "Content-Type": "application/json", ...(options.headers || {}) } : options.headers
        });
        if (response.status === 204) return null;
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.message || `Gewerkedaten konnten nicht verarbeitet werden (${response.status}).`);
        return data;
    }
    async function list(filters = {}) {
        const query = new URLSearchParams(Object.entries(filters).filter(([, value]) => value));
        return request(query.size ? `?${query}` : "");
    }
    async function add(name, color) {
        const created = await request("", { method: "POST", body: JSON.stringify({ name: name.trim(), color, status: "active" }) });
        window.dispatchEvent(new CustomEvent("trades:changed"));
        return created;
    }
    async function update(id, changes) {
        const result = await request(`/${id}`, { method: "PATCH", body: JSON.stringify(changes) });
        window.dispatchEvent(new CustomEvent("trades:changed"));
        return result;
    }
    async function setColor(id, color) { return update(id, { color }); }
    async function setActive(id, active) {
        const result = await request(`/${id}/${active ? "activate" : "deactivate"}`, { method: "POST" });
        window.dispatchEvent(new CustomEvent("trades:changed"));
        return result;
    }
    async function remove(id) {
        await request(`/${id}`, { method: "DELETE" });
        window.dispatchEvent(new CustomEvent("trades:changed"));
    }
    async function colorFor(id) { return (await list()).find((trade) => trade.id === id)?.color || "#d7ded9"; }
    return { list, add, remove, setActive, setColor, colorFor, colors: TRADE_COLORS };
})();
