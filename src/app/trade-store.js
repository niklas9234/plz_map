const TRADE_STORAGE_KEY = "plz-map.trades.v1";

// Bewusst helle, leicht entsättigte Farben: dunkler Text und die PLZ-Zahlen
// bleiben sowohl in Badges als auch auf der Karte gut lesbar.
const TRADE_COLORS = [
    "#b8d8c0", "#b9d7d9", "#b8cde0", "#c5c3df", "#d4bfda",
    "#dfbfd0", "#e2c1bd", "#e3c9ad", "#e4d5aa", "#d9dcae",
    "#c9dcb2", "#b9d9cb", "#b7d4df", "#c2cde2", "#cec4dc",
    "#ddc3d9", "#e0c5c9", "#dfccb9", "#d8d4b7", "#c4d5bd"
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
            trades.forEach((trade, index) => {
                if (!trade.color) trade.color = TRADE_COLORS[index % TRADE_COLORS.length];
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
        trades.push({ name: normalizedName, active: true, color: normalizeColor(color) });
        trades.sort((left, right) => left.name.localeCompare(right.name, "de"));
        persist();
    }

    function normalizeColor(color) {
        return TRADE_COLORS.includes(color) ? color : TRADE_COLORS[trades.length % TRADE_COLORS.length];
    }

    async function setColor(name, color) {
        await initialize();
        const trade = trades.find((item) => item.name === name);
        if (!trade) throw new Error("Das Gewerk wurde nicht gefunden.");
        trade.color = normalizeColor(color);
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
