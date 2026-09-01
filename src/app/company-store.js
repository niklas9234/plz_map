const COMPANY_DATA_URL = "./companies.json";
const COMPANY_STORAGE_KEY = "plz-map.companies.v1";

const companyStore = (() => {
    let companies;

    function clone(value) {
        return JSON.parse(JSON.stringify(value));
    }

    function normalizeCompany(company, index = 0) {
        return {
            id: String(company.id || company.ppsNumber || `company-${index}`),
            name: company.name.trim(),
            ppsNumber: company.ppsNumber.trim(),
            trade: company.trade.trim(),
            postalCodes: [...new Set(company.postalCodes.map(String))].sort()
        };
    }

    async function initialize() {
        if (companies) return;

        const storedCompanies = localStorage.getItem(COMPANY_STORAGE_KEY);
        if (storedCompanies) {
            companies = JSON.parse(storedCompanies).map(normalizeCompany);
            return;
        }

        const response = await fetch(COMPANY_DATA_URL);
        if (!response.ok) {
            throw new Error(`Unternehmensdaten konnten nicht geladen werden (${response.status}).`);
        }
        companies = (await response.json()).map(normalizeCompany);
    }

    function persist() {
        localStorage.setItem(COMPANY_STORAGE_KEY, JSON.stringify(companies));
        window.dispatchEvent(new CustomEvent("companies:changed"));
    }

    async function list() {
        await initialize();
        return clone(companies);
    }

    async function save(company) {
        await initialize();
        const duplicate = companies.find((item) =>
            item.ppsNumber.toLocaleLowerCase("de-DE") === company.ppsNumber.trim().toLocaleLowerCase("de-DE") &&
            item.id !== company.id
        );
        if (duplicate) throw new Error("Diese PPS-Nummer wird bereits verwendet.");

        const existingIndex = companies.findIndex((item) => item.id === company.id);
        const normalized = normalizeCompany({
            ...company,
            id: company.id || (crypto.randomUUID ? crypto.randomUUID() : `company-${Date.now()}`)
        });

        if (existingIndex === -1) companies.push(normalized);
        else companies[existingIndex] = normalized;
        persist();
        return clone(normalized);
    }

    async function remove(id) {
        await initialize();
        companies = companies.filter((company) => company.id !== id);
        persist();
    }

    return { list, save, remove };
})();
