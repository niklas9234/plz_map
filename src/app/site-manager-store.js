const SITE_MANAGER_API_URL = "/api/site-managers";

const siteManagerStore = (() => {
    async function request(url = SITE_MANAGER_API_URL, options = {}) {
        const response = await fetch(url, {
            headers: { "Content-Type": "application/json", ...options.headers },
            ...options
        });
        const data = response.status === 204 ? null : await response.json();
        if (!response.ok) throw new Error(data?.message || `Bauleiterdaten konnten nicht verarbeitet werden (${response.status}).`);
        return data;
    }

    function list() { return request(); }
    function listActive() { return request(`${SITE_MANAGER_API_URL}?status=active`); }
    function save(manager) {
        const fields = (({ name, territories, status }) => ({ name, territories, status }))(manager);
        return request(manager.id ? `${SITE_MANAGER_API_URL}/${manager.id}` : SITE_MANAGER_API_URL, {
            method: manager.id ? "PATCH" : "POST",
            body: JSON.stringify(fields)
        }).then((result) => {
            window.dispatchEvent(new CustomEvent("site-managers:changed"));
            return result;
        });
    }

    function remove(id) {
        return request(`${SITE_MANAGER_API_URL}/${id}`, { method: "DELETE" }).then(() => {
            window.dispatchEvent(new CustomEvent("site-managers:changed"));
        });
    }

    function setActive(id, active) {
        return request(`${SITE_MANAGER_API_URL}/${id}/${active ? "activate" : "deactivate"}`, { method: "POST" })
            .then((result) => {
                window.dispatchEvent(new CustomEvent("site-managers:changed"));
                return result;
            });
    }

    return { list, listActive, save, remove, setActive };
})();
