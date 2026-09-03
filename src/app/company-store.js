const COMPANY_API_URL = "/api/companies";
const LEGACY_COMPANY_STORAGE_KEY = "plz-map.companies.v1";

const companyStore = (() => {
    let companies;

    function clone(value) {
        return JSON.parse(JSON.stringify(value));
    }

    function normalizeCompany(company, index = 0) {
        const territories = Array.isArray(company.territories)
            ? company.territories
            : (company.postalCodes || []).map((postalCode) => ({ postalCode, role: "primary" }));
        const normalizedTerritories = [...new Map(territories.map((territory) => {
            const postalCode = String(territory.postalCode);
            const role = territory.role === "alternative" ? "alternative" : "primary";
            return [postalCode, { postalCode, role }];
        })).values()].sort((first, second) => first.postalCode.localeCompare(second.postalCode));

        return {
            id: String(company.id || company.ppsNumber || `company-${index}`),
            name: String(company.name || "").trim(),
            ppsNumber: String(company.ppsNumber || "").trim(),
            trade: String(company.trade || "").trim(),
            territories: normalizedTerritories,
            information: Array.isArray(company.information)
                ? company.information.map((item) => ({ category: String(item.category), value: String(item.value) }))
                : [],
            active: company.active !== undefined ? company.active !== false : company.status !== "inactive"
        };
    }

    function errorMessage(status, details) {
        const suffix = details?.message ? ` ${details.message}` : "";
        if (status === 400 || status === 422) return `Die Unternehmensdaten sind ungültig.${suffix}`;
        if (status === 409) return `Konflikt beim Speichern der Unternehmensdaten.${suffix}`;
        if (status === 404) return `Das Unternehmen wurde nicht gefunden.${suffix}`;
        return `Das Backend konnte die Unternehmensanfrage nicht verarbeiten (${status}).${suffix}`;
    }

    async function request(path = "", options = {}) {
        let response;
        try {
            response = await fetch(`${COMPANY_API_URL}${path}`, {
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

    function clearLegacyData() {
        // Erst nach einer erfolgreichen Backend-Antwort löschen. Die alten Daten
        // werden nie als Fallback verwendet; ab jetzt ist ausschließlich die API maßgeblich.
        try { localStorage.removeItem(LEGACY_COMPANY_STORAGE_KEY); } catch (_) { /* Storage kann gesperrt sein. */ }
    }

    async function initialize() {
        if (companies) return;
        const result = await request();
        const items = Array.isArray(result) ? result : result?.items;
        if (!Array.isArray(items)) throw new Error("Das Backend hat ungültige Unternehmensdaten geliefert.");
        companies = items.map(normalizeCompany);
        clearLegacyData();
    }

    function changed() {
        window.dispatchEvent(new CustomEvent("companies:changed"));
    }

    async function list() {
        await initialize();
        return clone(companies);
    }

    async function save(company) {
        await initialize();
        const isExisting = Boolean(company.id && companies.some((item) => item.id === company.id));
        const candidate = normalizeCompany(company);
        const payload = {
            name: candidate.name,
            ppsNumber: candidate.ppsNumber,
            trade: candidate.trade,
            territories: candidate.territories,
            information: candidate.information
        };
        const saved = await request(isExisting ? `/${encodeURIComponent(company.id)}` : "", {
            method: isExisting ? "PATCH" : "POST",
            body: JSON.stringify(payload)
        });
        if (!saved) throw new Error("Das Backend hat das gespeicherte Unternehmen nicht zurückgegeben.");
        const normalized = normalizeCompany(saved);
        const existingIndex = companies.findIndex((item) => item.id === normalized.id);
        if (existingIndex === -1) companies.push(normalized);
        else companies[existingIndex] = normalized;
        changed();
        return clone(normalized);
    }

    async function remove(id) {
        await initialize();
        await request(`/${encodeURIComponent(id)}`, { method: "DELETE" });
        companies = companies.filter((company) => company.id !== id);
        changed();
    }

    async function setActive(id, active) {
        await initialize();
        const updated = await request(`/${encodeURIComponent(id)}/${active ? "activate" : "deactivate"}`, { method: "POST" });
        const normalized = normalizeCompany(updated || { ...companies.find((item) => item.id === id), active });
        const index = companies.findIndex((item) => item.id === id);
        if (index !== -1) companies[index] = normalized;
        changed();
        return clone(normalized);
    }

    return { list, save, remove, setActive };
})();
