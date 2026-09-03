const TRADE_DATA_URL = "./companies.json";
const TRADE_STORAGE_KEY = "plz-map.trades.v2";
const LEGACY_TRADE_STORAGE_KEY = "plz-map.trades.v1";

const TRADE_COLORS = [
    "#72b788", "#63b5ad", "#68a9c7", "#7898ca", "#938bc5",
    "#a85fa8", "#c45c83", "#d06a62", "#d1844f", "#c39a3d",
    "#b3b65e", "#8eb969", "#69b99a", "#5fb3c3", "#758fc8",
    "#73599b", "#92527e", "#a65e68", "#ad684f", "#8f7848"
];

const tradeStore = (() => {
    let trades;
    const clone = (value) => JSON.parse(JSON.stringify(value));
    const now = () => new Date().toISOString();
    const isUuid = (value) => /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value || "");

    function normalizeTrade(trade) {
        const timestamp = now();
        const name = String(trade.name || "").trim();
        if (!name) throw new Error("Der Gewerkname darf nicht leer sein.");
        return {
            id: isUuid(trade.id) ? trade.id : crypto.randomUUID(),
            name,
            color: trade.color,
            status: trade.status === "inactive" || trade.active === false ? "inactive" : "active",
            createdAt: trade.createdAt || timestamp,
            updatedAt: trade.updatedAt || timestamp
        };
    }

    function assignColors(items) {
        const assigned = new Set();
        items.forEach((trade) => {
            if (!TRADE_COLORS.includes(trade.color) || assigned.has(trade.color)) {
                trade.color = TRADE_COLORS.find((color) => !assigned.has(color));
            }
            if (trade.color) assigned.add(trade.color);
        });
    }

    async function initialize() {
        if (trades) return;
        const stored = localStorage.getItem(TRADE_STORAGE_KEY);
        const legacy = localStorage.getItem(LEGACY_TRADE_STORAGE_KEY);
        if (stored || legacy) {
            trades = JSON.parse(stored || legacy).map(normalizeTrade);
            assignColors(trades);
            if (!stored) persist(false);
            return;
        }
        const response = await fetch(TRADE_DATA_URL);
        if (!response.ok) throw new Error(`Gewerkedaten konnten nicht geladen werden (${response.status}).`);
        const seed = await response.json();
        if (seed.schemaVersion !== 2 || !Array.isArray(seed.trades)) throw new Error("Das Seed-Format wird nicht unterstützt.");
        trades = seed.trades.map(normalizeTrade);
        assignColors(trades);
    }

    function persist(notify = true) {
        localStorage.setItem(TRADE_STORAGE_KEY, JSON.stringify(trades));
        if (notify) window.dispatchEvent(new CustomEvent("trades:changed"));
    }

    async function list() { await initialize(); return clone(trades); }

    function availableColor(color, currentId = "") {
        const used = new Set(trades.filter((trade) => trade.id !== currentId).map((trade) => trade.color));
        const selected = TRADE_COLORS.includes(color) && !used.has(color) ? color : TRADE_COLORS.find((item) => !used.has(item));
        if (!selected) throw new Error("Alle 20 Gewerkfarben sind bereits vergeben.");
        return selected;
    }

    async function add(name, color) {
        await initialize();
        const normalizedName = name.trim();
        if (!normalizedName) throw new Error("Bitte einen Namen für das Gewerk eingeben.");
        if (trades.some((trade) => trade.name.localeCompare(normalizedName, "de", { sensitivity: "base" }) === 0)) {
            throw new Error("Dieses Gewerk ist bereits vorhanden.");
        }
        trades.push(normalizeTrade({ name: normalizedName, color: availableColor(color), status: "active" }));
        trades.sort((left, right) => left.name.localeCompare(right.name, "de"));
        persist();
    }

    async function setColor(id, color) {
        await initialize();
        const trade = trades.find((item) => item.id === id);
        if (!trade) throw new Error("Das Gewerk wurde nicht gefunden.");
        trade.color = availableColor(color, id);
        trade.updatedAt = now();
        persist();
    }

    async function remove(id) {
        await initialize();
        const index = trades.findIndex((item) => item.id === id);
        if (index === -1) throw new Error("Das Gewerk wurde nicht gefunden.");
        const companies = await companyStore.list();
        if (companies.some((company) => company.tradeId === id)) throw new Error("Ein verwendetes Gewerk kann nicht gelöscht werden.");
        trades.splice(index, 1);
        persist();
    }

    async function colorFor(id) { await initialize(); return trades.find((trade) => trade.id === id)?.color || "#d7ded9"; }

    async function setActive(id, active) {
        await initialize();
        const trade = trades.find((item) => item.id === id);
        if (!trade) throw new Error("Das Gewerk wurde nicht gefunden.");
        trade.status = active ? "active" : "inactive";
        trade.updatedAt = now();
        persist();
    }

    return { list, add, remove, setActive, setColor, colorFor, colors: TRADE_COLORS };
})();
