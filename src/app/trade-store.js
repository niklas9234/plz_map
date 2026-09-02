const TRADE_STORAGE_KEY = "plz-map.trades.v1";

// Gut unterscheidbare, etwas entsättigte Farben: kräftig genug für die Karte,
// aber bei der transparenten Flächendarstellung weiterhin hell genug, damit
// Ortsnamen und PLZ lesbar bleiben. Jede Reihe des Farbwählers bildet eine
// eigenständige Farbfamilie ohne Wiederholungen aus anderen Reihen.
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

    async function initialize() {
        if (trades) return;
        const storedTrades = localStorage.getItem(TRADE_STORAGE_KEY);
        if (storedTrades) {
            trades = JSON.parse(storedTrades);
            const assignedColors = new Set();
            trades.forEach((trade) => {
                if (!TRADE_COLORS.includes(trade.color) || assignedColors.has(trade.color)) {
                    trade.color = TRADE_COLORS.find((color) => !assignedColors.has(color));
                }
                if (trade.color) assignedColors.add(trade.color);
            });
            return;
        }
        const companies = await companyStore.list();
        trades = [...new Set(companies.map((company) => company.trade))]
            .sort((left, right) => left.localeCompare(right, "de"))
            .map((name, index) => ({ name, active: true, color: TRADE_COLORS[index % TRADE_COLORS.length] }));
    }

    function persist() {
        localStorage.setItem(TRADE_STORAGE_KEY, JSON.stringify(trades));
        window.dispatchEvent(new CustomEvent("trades:changed"));
    }

    async function list() {
        await initialize();
        return clone(trades);
    }

    async function add(name, color) {
        await initialize();
        const normalizedName = name.trim();
        if (!normalizedName) throw new Error("Bitte einen Namen für das Gewerk eingeben.");
        if (trades.some((trade) => trade.name.localeCompare(normalizedName, "de", { sensitivity: "base" }) === 0)) {
            throw new Error("Dieses Gewerk ist bereits vorhanden.");
        }
        trades.push({ name: normalizedName, active: true, color: availableColor(color) });
        trades.sort((left, right) => left.name.localeCompare(right.name, "de"));
        persist();
    }

    function availableColor(color, currentName = "") {
        const usedColors = new Set(trades.filter((trade) => trade.name !== currentName).map((trade) => trade.color));
        const selectedColor = TRADE_COLORS.includes(color) && !usedColors.has(color)
            ? color
            : TRADE_COLORS.find((candidate) => !usedColors.has(candidate));
        if (!selectedColor) throw new Error("Alle 20 Gewerkfarben sind bereits vergeben.");
        return selectedColor;
    }

    async function setColor(name, color) {
        await initialize();
        const trade = trades.find((item) => item.name === name);
        if (!trade) throw new Error("Das Gewerk wurde nicht gefunden.");
        if (trades.some((item) => item.name !== name && item.color === color)) {
            throw new Error("Diese Farbe wird bereits von einem anderen Gewerk verwendet.");
        }
        trade.color = availableColor(color, name);
        persist();
    }

    async function remove(name) {
        await initialize();
        const index = trades.findIndex((item) => item.name === name);
        if (index === -1) throw new Error("Das Gewerk wurde nicht gefunden.");
        trades.splice(index, 1);
        persist();
    }

    async function colorFor(name) {
        await initialize();
        return trades.find((trade) => trade.name === name)?.color || "#d7ded9";
    }

    async function setActive(name, active) {
        await initialize();
        const trade = trades.find((item) => item.name === name);
        if (!trade) throw new Error("Das Gewerk wurde nicht gefunden.");
        trade.active = active;
        persist();
    }

    return { list, add, remove, setActive, setColor, colorFor, colors: TRADE_COLORS };
})();
