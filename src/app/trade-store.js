const TRADE_STORAGE_KEY = "plz-map.trades.v1";

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
            return;
        }
        const companies = await companyStore.list();
        trades = [...new Set(companies.map((company) => company.trade))]
            .sort((left, right) => left.localeCompare(right, "de"))
            .map((name) => ({ name, active: true }));
    }

    function persist() {
        localStorage.setItem(TRADE_STORAGE_KEY, JSON.stringify(trades));
        window.dispatchEvent(new CustomEvent("trades:changed"));
    }

    async function list() {
        await initialize();
        return clone(trades);
    }

    async function add(name) {
        await initialize();
        const normalizedName = name.trim();
        if (!normalizedName) throw new Error("Bitte einen Namen für das Gewerk eingeben.");
        if (trades.some((trade) => trade.name.localeCompare(normalizedName, "de", { sensitivity: "base" }) === 0)) {
            throw new Error("Dieses Gewerk ist bereits vorhanden.");
        }
        trades.push({ name: normalizedName, active: true });
        trades.sort((left, right) => left.name.localeCompare(right.name, "de"));
        persist();
    }

    async function setActive(name, active) {
        await initialize();
        const trade = trades.find((item) => item.name === name);
        if (!trade) throw new Error("Das Gewerk wurde nicht gefunden.");
        trade.active = active;
        persist();
    }

    return { list, add, setActive };
})();
