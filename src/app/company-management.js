function initializeCompanyManagement() {
    const dialog = document.getElementById("company-management");
    const tableBody = document.getElementById("company-table-body");
    const searchInput = document.getElementById("management-search");
    const tradeFilter = document.getElementById("management-trade-filter");
    const resultStatus = document.getElementById("management-result-status");
    const header = dialog.querySelector(".management-dialog__header");
    const listElements = [dialog.querySelector(".management-toolbar"), resultStatus, dialog.querySelector(".company-table-wrapper")];
    let companies = [];
    let trades = [];
    let currentCompany = null;
    let initialState = "";
    let detailView = null;
    let pointerStartedOnBackdrop = false;

    function isOutsideDialog(event) {
        const bounds = dialog.getBoundingClientRect();
        return event.clientX < bounds.left || event.clientX > bounds.right ||
            event.clientY < bounds.top || event.clientY > bounds.bottom;
    }

    function filteredCompanies() {
        const query = normalizeSearchValue(searchInput.value);
        return companies.filter((company) => (!query ||
            normalizeSearchValue(company.name).includes(query) ||
            normalizeSearchValue(company.ppsNumber).includes(query)) &&
            (!tradeFilter.value || company.trade === tradeFilter.value));
    }

    function populateTradeOptions() {
        const current = tradeFilter.value;
        tradeFilter.replaceChildren(new Option("Alle Gewerke", ""));
        trades.filter((trade) => trade.active).forEach((trade) => tradeFilter.add(new Option(trade.name, trade.name)));
        if ([...tradeFilter.options].some((option) => option.value === current)) tradeFilter.value = current;
    }

    function renderCompanies() {
        const matches = filteredCompanies();
        tableBody.replaceChildren();
        resultStatus.textContent = `${matches.length} von ${companies.length} Unternehmen`;
        if (!matches.length) {
            const cell = tableBody.insertRow().insertCell();
            cell.colSpan = 4;
            cell.className = "company-table__empty";
            cell.textContent = "Keine Unternehmen für diese Filter gefunden.";
            return;
        }
        matches.forEach((company) => {
            const row = tableBody.insertRow();
            row.tabIndex = 0;
            row.setAttribute("role", "button");
            row.setAttribute("aria-label", `${company.name} öffnen`);
            row.classList.toggle("is-inactive", !company.active);
            const nameCell = row.insertCell();
            nameCell.className = "company-table__name-cell";
            const name = document.createElement("strong");
            name.textContent = company.name;
            nameCell.append(name);
            if (!company.active) {
                const status = document.createElement("span");
                status.className = "status-badge";
                status.textContent = "Inaktiv";
                nameCell.append(" ", status);
            }
            row.insertCell().append(createTradeBadge(company.trade));
            row.insertCell().textContent = company.ppsNumber;
            const postalCodes = row.insertCell();
            postalCodes.className = "company-table__postal-codes";
            postalCodes.textContent = company.postalCodes.join(", ");
            row.addEventListener("click", () => openCompany(company));
            row.addEventListener("keydown", (event) => {
                if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    openCompany(company);
                }
            });
        });
    }

    async function refresh() {
        [companies, trades] = await Promise.all([companyStore.list(), tradeStore.list()]);
        populateTradeOptions();
        renderCompanies();
    }

    function formState() {
        if (!detailView) return "";
        const information = [...detailView.querySelectorAll(".information-row")].map((row) => ({
            category: row.querySelector("select").value,
            value: row.querySelector("input").value
        }));
        return JSON.stringify({
            name: detailView.querySelector("#detail-name").value,
            ppsNumber: detailView.querySelector("#detail-pps").value,
            trade: detailView.querySelector("#detail-trade").value,
            postalCodes: [...detailView.querySelectorAll(".postal-code-tile.is-selected")].map((tile) => tile.dataset.code),
            information
        });
    }

    function updateDirtyState() {
        const dirty = formState() !== initialState;
        detailView.querySelector(".detail-actions").hidden = !dirty;
        return dirty;
    }

    async function leaveDetail(destination) {
        if (updateDirtyState()) {
            const shouldSave = window.confirm("Sollen die Änderungen gespeichert werden?");
            if (shouldSave && !(await saveCompany())) return;
        }
        if (destination === "map") closeToMap();
        else showList();
    }

    function closeToMap() {
        currentCompany = null;
        detailView?.remove();
        detailView = null;
        dialog.close();
    }

    function addInformationRow(information = { category: "Adresse", value: "" }) {
        const row = document.createElement("div");
        row.className = "information-row";
        const select = document.createElement("select");
        select.setAttribute("aria-label", "Informationskategorie");
        ["Adresse", "Telefon", "Ansprechpartner", "Sonstiges"].forEach((category) => select.add(new Option(category, category)));
        select.value = information.category;
        const input = document.createElement("input");
        input.type = "text";
        input.value = information.value;
        input.placeholder = "Information eingeben";
        input.setAttribute("aria-label", `Information für ${information.category}`);
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "information-delete";
        remove.innerHTML = "&#128465;";
        remove.setAttribute("aria-label", "Information löschen");
        remove.addEventListener("click", () => { row.remove(); updateInformationEmptyState(); updateDirtyState(); });
        row.append(select, input, remove);
        detailView.querySelector(".information-list").append(row);
        updateInformationEmptyState();
    }

    function updateInformationEmptyState() {
        const empty = !detailView.querySelector(".information-row");
        detailView.querySelector(".information-empty").hidden = !empty;
    }

    function openCompany(company, isNew = false) {
        detailView?.remove();
        currentCompany = company;
        listElements.forEach((element) => { element.hidden = true; });
        header.hidden = true;
        detailView = document.createElement("form");
        detailView.className = "company-detail";
        detailView.tabIndex = -1;
        detailView.innerHTML = `
            <div class="company-detail__nav">
              <div class="company-detail__heading">
                <p class="eyebrow">Unternehmensdaten</p>
                <h2 class="company-detail__company-name"></h2>
              </div>
              <div class="company-detail__navigation-actions">
                <button class="detail-back" type="button" aria-label="Zurück zu den Stammdaten">&#8592;</button>
                <button class="icon-button detail-close" type="button" aria-label="Zurück zur Karte">&times;</button>
              </div>
            </div>
            <div class="company-detail__content">
              <div class="company-detail__master-data">
                <label class="form-field"><span>Unternehmensname</span><input id="detail-name" required maxlength="120"></label>
                <label class="form-field"><span>PPS-Nummer</span><input id="detail-pps" required maxlength="40"></label>
                <label class="form-field"><span>Gewerk</span><select id="detail-trade" required></select></label>
              </div>
              <section class="detail-section"><h3>PLZ-Gebiete</h3><div class="postal-code-grid" aria-label="PLZ-Gebiete auswählen"></div></section>
              <section class="detail-section information-section">
                <h3>Informationen</h3>
                <p class="information-empty">Fügen Sie hier weitere Informationen über das Unternehmen hinzu.</p>
                <div class="information-list"></div>
                <button class="information-add" type="button" aria-label="Information hinzufügen">+</button>
              </section>
              <p class="form-error detail-error" role="alert" hidden></p>
              <div class="dialog-actions detail-actions" hidden>
                <button class="button button--secondary detail-cancel" type="button">Abbrechen</button>
                <button class="button button--primary" type="submit">Speichern</button>
              </div>
            </div>`;
        dialog.append(detailView);
        detailView.querySelector("#detail-name").value = company.name;
        detailView.querySelector(".company-detail__company-name").textContent = isNew ? "Neues Unternehmen" : company.name;
        detailView.querySelector("#detail-pps").value = company.ppsNumber;
        const tradeSelect = detailView.querySelector("#detail-trade");
        trades.filter((trade) => trade.active || trade.name === company.trade).forEach((trade) => tradeSelect.add(new Option(trade.name, trade.name)));
        tradeSelect.value = company.trade;
        const grid = detailView.querySelector(".postal-code-grid");
        const selectablePostalCodes = [
            ...Array.from({ length: 99 }, (_, index) => String(index + 1).padStart(2, "0")),
            "LUX"
        ];
        selectablePostalCodes.forEach((code) => {
            const tile = document.createElement("button");
            tile.type = "button";
            tile.className = "postal-code-tile";
            tile.dataset.code = code;
            tile.textContent = code;
            tile.classList.toggle("is-selected", company.postalCodes.includes(code));
            tile.setAttribute("aria-pressed", String(company.postalCodes.includes(code)));
            tile.addEventListener("click", () => {
                tile.classList.toggle("is-selected");
                tile.setAttribute("aria-pressed", String(tile.classList.contains("is-selected")));
                updateDirtyState();
            });
            grid.append(tile);
        });
        (company.information || []).forEach(addInformationRow);
        updateInformationEmptyState();
        initialState = formState();
        detailView.addEventListener("input", updateDirtyState);
        detailView.addEventListener("change", updateDirtyState);
        if (!isNew) {
            detailView.querySelector("#detail-name").addEventListener("input", (event) => {
                detailView.querySelector(".company-detail__company-name").textContent = event.target.value || "Unternehmen ohne Namen";
            });
        }
        detailView.addEventListener("submit", async (event) => { event.preventDefault(); await saveCompany(); });
        detailView.querySelector(".detail-back").addEventListener("click", () => leaveDetail("list"));
        detailView.querySelector(".detail-close").addEventListener("click", () => leaveDetail("map"));
        detailView.querySelector(".detail-cancel").addEventListener("click", () => {
            if (isNew) {
                showList();
                return;
            }
            const original = companies.find((item) => item.id === currentCompany.id) || currentCompany;
            openCompany(original);
        });
        detailView.querySelector(".information-add").addEventListener("click", () => { addInformationRow(); updateDirtyState(); });
        detailView.focus({ preventScroll: true });
        if (isNew) detailView.querySelector("#detail-name").focus();
    }

    function openNewCompany() {
        const firstActiveTrade = trades.find((trade) => trade.active)?.name || "";
        openCompany({
            name: "",
            ppsNumber: "",
            trade: firstActiveTrade,
            postalCodes: [],
            information: [],
            active: true
        }, true);
        // Beim Anlegen muss die primäre Aktion von Anfang an sichtbar sein.
        detailView.querySelector(".detail-actions").hidden = false;
    }

    async function saveCompany() {
        const data = JSON.parse(formState());
        const error = detailView.querySelector(".detail-error");
        if (!data.postalCodes.length) {
            error.textContent = "Bitte wählen Sie mindestens ein PLZ-Gebiet aus.";
            error.hidden = false;
            return false;
        }
        try {
            currentCompany = await companyStore.save({ ...currentCompany, ...data });
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

    function showList() {
        currentCompany = null;
        detailView?.remove();
        detailView = null;
        header.hidden = false;
        listElements.forEach((element) => { element.hidden = false; });
        renderCompanies();
    }

    document.getElementById("open-company-management").addEventListener("click", async () => {
        await refresh();
        showList();
        dialog.showModal();
        searchInput.focus();
    });
    document.getElementById("close-company-management").addEventListener("click", closeToMap);
    document.getElementById("create-company").addEventListener("click", openNewCompany);
    searchInput.addEventListener("input", renderCompanies);
    tradeFilter.addEventListener("change", renderCompanies);
    window.addEventListener("trades:changed", refresh);
    dialog.addEventListener("pointerdown", (event) => {
        pointerStartedOnBackdrop = isOutsideDialog(event);
    });
    dialog.addEventListener("pointercancel", () => {
        pointerStartedOnBackdrop = false;
    });
    dialog.addEventListener("click", (event) => {
        const clickedBackdrop = pointerStartedOnBackdrop && isOutsideDialog(event);
        pointerStartedOnBackdrop = false;
        if (!clickedBackdrop) return;
        if (detailView) leaveDetail("map");
        else closeToMap();
    });
    dialog.addEventListener("cancel", (event) => {
        if (!detailView) return;
        event.preventDefault();
        leaveDetail("map");
    });
}

document.addEventListener("DOMContentLoaded", initializeCompanyManagement);

function initializeTradeManagement() {
    const dialog = document.getElementById("trade-management");
    const form = document.getElementById("trade-form");
    const nameInput = document.getElementById("trade-name");
    const list = document.getElementById("trade-list");
    const error = document.getElementById("trade-error");
    const newColorPicker = document.getElementById("new-trade-color-picker");
    let trades = [];

    function createColorPicker(selected, currentTrade = "") {
        const picker = document.createElement("div");
        picker.className = "color-picker__control";
        picker.dataset.color = selected;
        const button = document.createElement("button");
        button.type = "button";
        button.className = "color-picker__button";
        button.innerHTML = '<span class="color-picker__swatch"></span> Farbe';
        button.querySelector("span").style.backgroundColor = selected;
        button.setAttribute("aria-expanded", "false");
        const overlay = document.createElement("div");
        overlay.className = "color-picker__overlay";
        overlay.hidden = true;
        const usedColors = new Set(trades.filter((trade) => trade.name !== currentTrade).map((trade) => trade.color));
        tradeStore.colors.forEach((color, index) => {
            const option = document.createElement("button");
            option.type = "button";
            option.className = "color-option";
            option.style.backgroundColor = color;
            option.disabled = usedColors.has(color);
            option.classList.toggle("is-selected", color === selected);
            option.setAttribute("aria-label", option.disabled ? `Farbe ${index + 1}, bereits vergeben` : `Farbe ${index + 1}`);
            option.addEventListener("click", () => {
                picker.dataset.color = color;
                button.querySelector("span").style.backgroundColor = color;
                overlay.hidden = true;
                button.setAttribute("aria-expanded", "false");
                picker.dispatchEvent(new CustomEvent("colorchange", { bubbles: true, detail: { color } }));
            });
            overlay.append(option);
        });
        button.addEventListener("click", () => {
            document.querySelectorAll(".color-picker__overlay:not([hidden])").forEach((element) => {
                if (element !== overlay) element.hidden = true;
            });
            overlay.hidden = !overlay.hidden;
            button.setAttribute("aria-expanded", String(!overlay.hidden));
        });
        picker.append(button, overlay);
        return picker;
    }

    async function render() {
        trades = await tradeStore.list();
        const firstAvailableColor = tradeStore.colors.find((color) => !trades.some((trade) => trade.color === color));
        newColorPicker.replaceChildren(createColorPicker(firstAvailableColor || tradeStore.colors[0]));
        list.replaceChildren();
        trades.forEach((trade) => {
            const item = document.createElement("li");
            item.classList.toggle("is-inactive", !trade.active);
            const name = document.createElement("strong");
            name.textContent = trade.name;
            const colors = createColorPicker(trade.color, trade.name);
            colors.addEventListener("colorchange", async (event) => {
                await tradeStore.setColor(trade.name, event.detail.color);
                await render();
            });
            const activeLabel = document.createElement("label");
            activeLabel.className = "trade-active";
            const active = document.createElement("input");
            active.type = "checkbox";
            active.checked = trade.active;
            active.addEventListener("change", () => tradeStore.setActive(trade.name, active.checked));
            activeLabel.append(active, " Aktiv");
            const remove = document.createElement("button");
            remove.type = "button";
            remove.className = "table-action table-action--delete";
            remove.textContent = "×";
            remove.setAttribute("aria-label", `${trade.name} löschen`);
            remove.addEventListener("click", async () => {
                if (!window.confirm(`Gewerk „${trade.name}“ wirklich löschen?`)) return;
                await tradeStore.remove(trade.name);
                await render();
            });
            const actions = document.createElement("div");
            actions.className = "trade-list__actions";
            actions.append(activeLabel, remove);
            item.append(name, colors, actions);
            list.append(item);
        });
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        try {
            const selectedColor = newColorPicker.querySelector(".color-picker__control").dataset.color;
            await tradeStore.add(nameInput.value, selectedColor);
            nameInput.value = "";
            error.hidden = true;
            await render();
        } catch (addError) {
            error.textContent = addError.message;
            error.hidden = false;
        }
    });
    document.getElementById("open-trade-management").addEventListener("click", async () => {
        await render();
        dialog.showModal();
        nameInput.focus();
    });
    document.getElementById("close-trade-management").addEventListener("click", () => dialog.close());
    document.addEventListener("click", (event) => {
        if (event.target.closest(".color-picker__control")) return;
        document.querySelectorAll(".color-picker__overlay:not([hidden])").forEach((overlay) => {
            overlay.hidden = true;
            overlay.previousElementSibling?.setAttribute("aria-expanded", "false");
        });
    });
}

document.addEventListener("DOMContentLoaded", initializeTradeManagement);
