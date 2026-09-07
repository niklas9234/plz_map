const COMPANY_API_URL = "/api/companies";
const INFORMATION_CATEGORIES = ["address", "phone", "contact", "other"];

const companyStore = (() => {
    async function request(path = "", options = {}) {
        const response = await fetch(`${COMPANY_API_URL}${path}`, {
            ...options,
            headers: options.body ? { "Content-Type": "application/json", ...(options.headers || {}) } : options.headers
        });
        if (response.status === 204) return null;
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.message || `Unternehmensdaten konnten nicht verarbeitet werden (${response.status}).`);
        return data;
    }

    async function list(filters = {}) {
        const query = new URLSearchParams(Object.entries(filters).filter(([, value]) => value !== undefined && value !== null && value !== ""));
        return request(query.size ? `?${query}` : "");
    }

    async function save(company) {
        const fields = (({ name, ppsNumber, tradeId, territories, information, status }) =>
            ({ name, ppsNumber, tradeId, territories, information, status }))(company);
        const existing = Boolean(company.id);
        const result = await request(existing ? `/${company.id}` : "", {
            method: existing ? "PATCH" : "POST", body: JSON.stringify(fields)
        });
        window.dispatchEvent(new CustomEvent("companies:changed"));
        return result;
    }

    async function remove(id) {
        await request(`/${id}`, { method: "DELETE" });
        window.dispatchEvent(new CustomEvent("companies:changed"));
    }

    async function setActive(id, active) {
        const result = await request(`/${id}/${active ? "activate" : "deactivate"}`, { method: "POST" });
        window.dispatchEvent(new CustomEvent("companies:changed"));
        return result;
    }

    async function exportData() {
        const response = await fetch("/api/admin/export");
        if (!response.ok) throw new Error(`Datenexport fehlgeschlagen (${response.status}).`);
        return response.json();
    }

    return { list, save, remove, setActive, exportData, informationCategories: INFORMATION_CATEGORIES };
})();
