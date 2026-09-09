function initializeSiteManagerManagement() {
    const dialog = document.getElementById("master-data-management");
    const header = dialog.querySelector(".management-dialog__header");
    const tabs = dialog.querySelector(".management-tabs");
    const panels = [...dialog.querySelectorAll(".management-panel")];
    const panel = document.getElementById("site-manager-management-panel");
    const search = document.getElementById("site-manager-management-search");
    const status = document.getElementById("site-manager-management-result-status");
    const tableBody = document.getElementById("site-manager-table-body");
    const deleteDialog = document.getElementById("delete-site-manager-confirmation");
    const deleteName = document.getElementById("delete-site-manager-name");
    const confirmDelete = document.getElementById("confirm-site-manager-delete");
    let managers = [];
    let currentManager = null;
    let detailView = null;
    let postalCodeSelection = null;
    let initialState = "";
    let pointerStartedOnBackdrop = false;

    function normalized(value) { return value.trim().toLocaleLowerCase("de"); }

    function render() {
        const query = normalized(search.value);
        const matches = managers.filter((manager) => !query || normalized(manager.name).includes(query));
        status.textContent = `${matches.length} von ${managers.length} Bauleitern`;
        tableBody.replaceChildren();
        if (!matches.length) {
            const cell = tableBody.insertRow().insertCell();
            cell.colSpan = 2;
            cell.className = "company-table__empty";
            cell.textContent = "Keine Bauleiter für diese Suche gefunden.";
            return;
        }
        matches.forEach((manager) => {
            const row = tableBody.insertRow();
            row.tabIndex = 0;
            row.setAttribute("role", "button");
            row.setAttribute("aria-label", `${manager.name} öffnen`);
            row.classList.toggle("is-inactive", manager.status !== "active");
            const nameCell = row.insertCell();
            nameCell.className = "company-table__name-cell";
            const name = document.createElement("strong");
            name.textContent = manager.name;
            nameCell.append(name);
            if (manager.status !== "active") {
                const badge = document.createElement("span");
                badge.className = "status-badge";
                badge.textContent = "Inaktiv";
                nameCell.append(" ", badge);
            }
            const territories = row.insertCell();
            territories.className = "company-table__postal-codes";
            territories.textContent = siteManagerPostalCodes(manager.territories).join(", ");
            row.addEventListener("click", () => openManager(manager));
            row.addEventListener("keydown", (event) => {
                if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    openManager(manager);
                }
            });
        });
    }

    async function refresh() {
        try {
            managers = await siteManagerStore.list();
            render();
        } catch (error) {
            status.textContent = error.message;
            tableBody.replaceChildren();
        }
    }

    function formState() {
        if (!detailView) return "";
        return JSON.stringify({
            name: detailView.querySelector("#site-manager-detail-name").value.trim(),
            territories: postalCodeSelection.codes()
        });
    }

    function updateDirtyState() {
        const dirty = formState() !== initialState;
        detailView.querySelector(".detail-actions").hidden = !dirty;
        return dirty;
    }

    function showList() {
        currentManager = null;
        detailView?.remove();
        detailView = null;
        header.hidden = false;
        tabs.hidden = false;
        panels.forEach((item) => { item.hidden = item !== panel; });
        render();
    }

    function closeToMap() {
        currentManager = null;
        detailView?.remove();
        detailView = null;
        dialog.close();
    }

    async function saveManager() {
        const data = JSON.parse(formState());
        const error = detailView.querySelector(".detail-error");
        if (!data.name) {
            error.textContent = "Bitte geben Sie einen Namen ein.";
            error.hidden = false;
            return false;
        }
        if (!data.territories.length) {
            error.textContent = "Bitte wählen Sie mindestens ein PLZ-Gebiet aus.";
            error.hidden = false;
            return false;
        }
        try {
            currentManager = await siteManagerStore.save({ ...currentManager, ...data });
            error.hidden = true;
            initialState = formState();
            updateDirtyState();
            await refresh();
            return true;
        } catch (saveError) {
            error.textContent = saveError.message;
            error.hidden = false;
            return false;
        }
    }

    async function leaveDetail(destination) {
        if (updateDirtyState()) {
            const shouldSave = window.confirm("Sollen die Änderungen am Bauleiter gespeichert werden?");
            if (shouldSave && !(await saveManager())) return;
        }
        if (destination === "map") closeToMap();
        else showList();
    }

    function openManager(manager, isNew = false) {
        detailView?.remove();
        currentManager = manager;
        header.hidden = true;
        tabs.hidden = true;
        panels.forEach((item) => { item.hidden = true; });
        detailView = document.createElement("form");
        detailView.className = "company-detail site-manager-detail";
        detailView.tabIndex = -1;
        detailView.innerHTML = `
          <div class="company-detail__nav">
            <div class="company-detail__heading"><p class="eyebrow">Bauleiterdaten</p><h2 class="company-detail__company-name"></h2></div>
            <div class="company-detail__navigation-actions">
              <button class="detail-back" type="button" aria-label="Zurück zu den Bauleitern">&#8592;</button>
              <button class="icon-button detail-close" type="button" aria-label="Zurück zur Karte">&times;</button>
            </div>
          </div>
          <div class="company-detail__content">
            <div class="company-detail__master-data">
              <label class="form-field"><span>Name</span><input id="site-manager-detail-name" required maxlength="120"></label>
            </div>
            <postal-code-selection></postal-code-selection>
            <section class="company-delete-section">
              <h3>Bauleiter ${manager.status === "active" ? "deaktivieren" : "aktivieren"}</h3>
              <p>Der Bauleiter kann später jederzeit wieder ${manager.status === "active" ? "aktiviert" : "deaktiviert"} werden.</p>
              <button class="button button--secondary detail-toggle-active" type="button">Bauleiter ${manager.status === "active" ? "deaktivieren" : "aktivieren"}</button>
            </section>
            ${isNew ? "" : `<section class="company-delete-section"><h3>Bauleiter löschen</h3><p>Entfernt den Bauleiter und alle zugehörigen Daten dauerhaft.</p><button class="button button--ghost-danger detail-delete" type="button">Bauleiter löschen</button></section>`}
            <p class="form-error detail-error" role="alert" hidden></p>
            <div class="dialog-actions detail-actions" hidden><button class="button button--secondary detail-cancel" type="button">Abbrechen</button><button class="button button--primary" type="submit">Speichern</button></div>
          </div>`;
        dialog.append(detailView);
        const nameInput = detailView.querySelector("#site-manager-detail-name");
        nameInput.value = manager.name;
        detailView.querySelector(".company-detail__company-name").textContent = isNew ? "Neuer Bauleiter" : manager.name;
        postalCodeSelection = detailView.querySelector("postal-code-selection").configure({
            territories: manager.territories,
            onChange: updateDirtyState
        });
        initialState = formState();
        detailView.addEventListener("input", updateDirtyState);
        nameInput.addEventListener("input", () => {
            detailView.querySelector(".company-detail__company-name").textContent = nameInput.value || "Bauleiter ohne Namen";
        });
        detailView.addEventListener("submit", async (event) => { event.preventDefault(); await saveManager(); });
        detailView.querySelector(".detail-back").addEventListener("click", () => leaveDetail("list"));
        detailView.querySelector(".detail-close").addEventListener("click", () => leaveDetail("map"));
        detailView.querySelector(".detail-cancel").addEventListener("click", () => isNew ? showList() : openManager(managers.find((item) => item.id === manager.id) || manager));
        detailView.querySelector(".detail-toggle-active").addEventListener("click", async () => {
            const action = manager.status === "active" ? "deaktivieren" : "aktivieren";
            if (!window.confirm(`Möchten Sie den Bauleiter ${manager.name} wirklich ${action}?`)) return;
            try {
                currentManager = await siteManagerStore.setActive(manager.id, manager.status !== "active");
                await refresh();
                openManager(currentManager);
            } catch (error) {
                detailView.querySelector(".detail-error").textContent = error.message;
                detailView.querySelector(".detail-error").hidden = false;
            }
        });
        detailView.querySelector(".detail-delete")?.addEventListener("click", () => {
            deleteName.textContent = manager.name;
            deleteDialog.showModal();
            confirmDelete.focus();
        });
        detailView.querySelector(".company-delete-section").hidden = isNew;
        detailView.focus({ preventScroll: true });
        if (isNew) {
            detailView.querySelector(".detail-actions").hidden = false;
            nameInput.focus();
        }
    }

    document.addEventListener("site-manager-management:open", refresh);
    document.addEventListener("site-manager-management:create", () => openManager({ name: "", territories: [], status: "active" }, true));
    search.addEventListener("input", render);
    document.getElementById("cancel-site-manager-delete").addEventListener("click", () => deleteDialog.close());
    confirmDelete.addEventListener("click", async () => {
        if (!currentManager) return;
        confirmDelete.disabled = true;
        try {
            await siteManagerStore.remove(currentManager.id);
            deleteDialog.close();
            await refresh();
            showList();
        } catch (error) {
            deleteDialog.close();
            detailView.querySelector(".detail-error").textContent = error.message;
            detailView.querySelector(".detail-error").hidden = false;
        } finally {
            confirmDelete.disabled = false;
        }
    });
    document.getElementById("close-company-management").addEventListener("click", (event) => {
        if (!detailView) return;
        event.stopImmediatePropagation();
        leaveDetail("map");
    }, true);
    dialog.addEventListener("pointerdown", (event) => {
        if (!detailView) return;
        const bounds = dialog.getBoundingClientRect();
        pointerStartedOnBackdrop = event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom;
    }, true);
    dialog.addEventListener("click", (event) => {
        if (!detailView || !pointerStartedOnBackdrop) return;
        pointerStartedOnBackdrop = false;
        event.stopImmediatePropagation();
        leaveDetail("map");
    }, true);
    dialog.addEventListener("cancel", (event) => {
        if (!detailView) return;
        event.preventDefault();
        event.stopImmediatePropagation();
        leaveDetail("map");
    }, true);
}

document.addEventListener("DOMContentLoaded", initializeSiteManagerManagement);
