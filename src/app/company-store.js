const COMPANY_DATA_URL = "./companies.json";
const COMPANY_STORAGE_KEY = "plz-map.companies.v2";
const LEGACY_COMPANY_STORAGE_KEY = "plz-map.companies.v1";
const INFORMATION_CATEGORIES = ["address", "phone", "contact", "other"];
const LEGACY_INFORMATION_CATEGORIES = { Adresse: "address", Telefon: "phone", Ansprechpartner: "contact", Sonstiges: "other" };

const companyStore = (() => {
    let companies;
    const clone = (value) => JSON.parse(JSON.stringify(value));
    const now = () => new Date().toISOString();
    const isUuid = (value) => /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value || "");

    function normalizeInformation(information) {
        if (!Array.isArray(information)) throw new Error("Informationen müssen als Liste angegeben werden.");
        return information.map((item) => {
            if (!item || typeof item !== "object" || Object.keys(item).some((key) => !["category", "value"].includes(key))) {
                throw new Error("Informationseinträge dürfen nur Kategorie und Wert enthalten.");
            }
            const category = LEGACY_INFORMATION_CATEGORIES[item.category] || item.category;
            const value = String(item.value || "").trim();
            if (!INFORMATION_CATEGORIES.includes(category)) throw new Error(`Unbekannte Informationskategorie: ${item.category}`);
            if (!value) throw new Error("Informationswerte dürfen nicht leer sein.");
            return { category, value };
        });
    }

    function normalizeCompany(company, tradeByName = new Map()) {
        const timestamp = now();
        const territories = Array.isArray(company.territories)
            ? company.territories
            : (company.postalCodes || []).map((postalCode) => ({ postalCode, role: "primary" }));
        const normalizedTerritories = [...new Map(territories.map((territory) => {
            const postalCode = String(territory.postalCode);
            if (!/^\d{2}$/.test(postalCode)) throw new Error(`Ungültiges PLZ-Gebiet: ${postalCode}`);
            if (!["primary", "alternative"].includes(territory.role)) throw new Error(`Ungültige Gebietsrolle: ${territory.role}`);
            return [postalCode, { postalCode, role: territory.role }];
        })).values()].sort((a, b) => a.postalCode.localeCompare(b.postalCode));
        if (!normalizedTerritories.length) throw new Error("Mindestens ein PLZ-Gebiet ist erforderlich.");
        const tradeId = company.tradeId || tradeByName.get(String(company.trade || "").toLocaleLowerCase("de-DE"));
        if (!tradeId) throw new Error(`Gewerk konnte nicht zugeordnet werden: ${company.trade || "ohne Angabe"}`);
        const name = String(company.name || "").trim();
        const ppsNumber = String(company.ppsNumber || "").trim();
        if (!name || !ppsNumber) throw new Error("Name und PPS-Nummer sind Pflichtfelder.");
        return {
            id: isUuid(company.id) ? company.id : crypto.randomUUID(), name, ppsNumber, tradeId,
            territories: normalizedTerritories,
            information: normalizeInformation(company.information || []),
            status: company.status === "inactive" || company.active === false ? "inactive" : "active",
            createdAt: company.createdAt || timestamp,
            updatedAt: company.updatedAt || timestamp
        };
    }

    async function initialize() {
        if (companies) return;
        const trades = await tradeStore.list();
        const tradeByName = new Map(trades.map((trade) => [trade.name.toLocaleLowerCase("de-DE"), trade.id]));
        const stored = localStorage.getItem(COMPANY_STORAGE_KEY);
        const legacy = localStorage.getItem(LEGACY_COMPANY_STORAGE_KEY);
        if (stored || legacy) {
            companies = JSON.parse(stored || legacy).map((company) => normalizeCompany(company, tradeByName));
            if (!stored) persist(false);
            return;
        }
        const response = await fetch(COMPANY_DATA_URL);
        if (!response.ok) throw new Error(`Unternehmensdaten konnten nicht geladen werden (${response.status}).`);
        const seed = await response.json();
        if (seed.schemaVersion !== 2 || !Array.isArray(seed.companies)) throw new Error("Das Seed-Format wird nicht unterstützt.");
        companies = seed.companies.map((company) => normalizeCompany(company, tradeByName));
    }

    function persist(notify = true) {
        localStorage.setItem(COMPANY_STORAGE_KEY, JSON.stringify(companies));
        if (notify) window.dispatchEvent(new CustomEvent("companies:changed"));
    }

    async function list() { await initialize(); return clone(companies); }

    async function save(company) {
        await initialize();
        const trades = await tradeStore.list();
        if (!trades.some((trade) => trade.id === company.tradeId)) throw new Error("Das ausgewählte Gewerk existiert nicht.");
        const duplicate = companies.find((item) => item.ppsNumber.toLocaleLowerCase("de-DE") === company.ppsNumber.trim().toLocaleLowerCase("de-DE") && item.id !== company.id);
        if (duplicate) throw new Error("Diese PPS-Nummer wird bereits verwendet.");
        const existingIndex = companies.findIndex((item) => item.id === company.id);
        const existing = existingIndex === -1 ? {} : companies[existingIndex];
        const candidate = normalizeCompany({ ...existing, ...company, id: company.id || crypto.randomUUID(), createdAt: existing.createdAt, updatedAt: now() });
        const conflict = candidate.territories.find((territory) => territory.role === "primary" && companies.some((item) =>
            item.id !== candidate.id && item.tradeId === candidate.tradeId && item.territories.some((entry) => entry.postalCode === territory.postalCode && entry.role === "primary")
        ));
        if (conflict) throw new Error(`Für das PLZ-Gebiet ${conflict.postalCode} und das ausgewählte Gewerk ist bereits ein Vorzugsdienstleister eingetragen.`);
        if (existingIndex === -1) companies.push(candidate); else companies[existingIndex] = candidate;
        persist();
        return clone(candidate);
    }

    async function remove(id) { await initialize(); companies = companies.filter((company) => company.id !== id); persist(); }

    async function setActive(id, active) {
        await initialize();
        const company = companies.find((item) => item.id === id);
        if (!company) throw new Error("Das Unternehmen wurde nicht gefunden.");
        company.status = active ? "active" : "inactive";
        company.updatedAt = now();
        persist();
        return clone(company);
    }

    async function exportData() {
        await initialize();
        return { schemaVersion: 2, exportedAt: now(), trades: await tradeStore.list(), companies: clone(companies) };
    }

    return { list, save, remove, setActive, exportData, informationCategories: INFORMATION_CATEGORIES };
})();
