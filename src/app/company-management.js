function initializeCompanyManagement() {
    const managementDialog = document.getElementById("company-management");
    const editorDialog = document.getElementById("company-editor");
    const deleteDialog = document.getElementById("company-delete-dialog");
    const tableBody = document.getElementById("company-table-body");
    const searchInput = document.getElementById("management-search");
    const tradeFilter = document.getElementById("management-trade-filter");
    const editorTrade = document.getElementById("company-trade");
    const form = document.getElementById("company-form");
    const formError = document.getElementById("company-form-error");
    const resultStatus = document.getElementById("management-result-status");
    let companies = [];
    let pendingDeleteId = null;

    function closeDialog(dialog) {
        if (dialog.open) dialog.close();
    }

    function filteredCompanies() {
        const query = normalizeSearchValue(searchInput.value);
        return companies.filter((company) => {
            const matchesQuery = !query ||
                normalizeSearchValue(company.name).includes(query) ||
                normalizeSearchValue(company.ppsNumber).includes(query);
            return matchesQuery && (!tradeFilter.value || company.trade === tradeFilter.value);
        });
    }

    function populateTradeOptions() {
        const currentFilter = tradeFilter.value;
        const trades = [...new Set(companies.map((company) => company.trade))]
            .sort((left, right) => left.localeCompare(right, "de"));
        tradeFilter.replaceChildren(new Option("Alle Gewerke", ""));
        editorTrade.replaceChildren(new Option("Gewerk auswählen", ""));
        trades.forEach((trade) => {
            tradeFilter.add(new Option(trade, trade));
            editorTrade.add(new Option(trade, trade));
        });
        if (trades.includes(currentFilter)) tradeFilter.value = currentFilter;
    }

    function actionButton(label, className, handler) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = `button button--small ${className}`;
        button.textContent = label;
        button.addEventListener("click", handler);
        return button;
    }

    function openEditor(company = null) {
        form.reset();
        formError.hidden = true;
        document.getElementById("company-editor-title").textContent = company
            ? "Unternehmen bearbeiten"
            : "Unternehmen anlegen";
        document.getElementById("company-id").value = company?.id || "";
        document.getElementById("company-name").value = company?.name || "";
        document.getElementById("company-pps-number").value = company?.ppsNumber || "";
        editorTrade.value = company?.trade || "";
        document.getElementById("company-postal-codes").value = company?.postalCodes.join(", ") || "";
        editorDialog.showModal();
        document.getElementById("company-name").focus();
    }

    function requestDelete(company) {
        pendingDeleteId = company.id;
        document.getElementById("company-delete-message").textContent =
            `„${company.name}“ (${company.ppsNumber}) wirklich löschen?`;
        deleteDialog.showModal();
    }

    function renderCompanies() {
        const matches = filteredCompanies();
        tableBody.replaceChildren();
        resultStatus.textContent = `${matches.length} von ${companies.length} Unternehmen`;

        if (!matches.length) {
            const row = tableBody.insertRow();
            const cell = row.insertCell();
            cell.colSpan = 5;
            cell.className = "company-table__empty";
            cell.textContent = "Keine Unternehmen für diese Filter gefunden.";
            return;
        }

        matches.forEach((company) => {
            const row = tableBody.insertRow();
            const nameCell = row.insertCell();
            nameCell.innerHTML = `<strong></strong>`;
            nameCell.querySelector("strong").textContent = company.name;
            row.insertCell().append(createTradeBadge(company.trade));
            row.insertCell().textContent = company.ppsNumber;
            const postalCodes = row.insertCell();
            postalCodes.className = "company-table__postal-codes";
            postalCodes.textContent = company.postalCodes.join(", ");
            const actions = row.insertCell();
            actions.className = "company-table__actions";
            actions.append(
                actionButton("Bearbeiten", "button--secondary", () => openEditor(company)),
                actionButton("Löschen", "button--ghost-danger", () => requestDelete(company))
            );
        });
    }

    async function refresh() {
        companies = await companyStore.list();
        populateTradeOptions();
        renderCompanies();
    }

    document.getElementById("open-company-management").addEventListener("click", async () => {
        await refresh();
        managementDialog.showModal();
        searchInput.focus();
    });
    document.getElementById("close-company-management").addEventListener("click", () => closeDialog(managementDialog));
    document.getElementById("add-company").addEventListener("click", () => openEditor());
    document.getElementById("close-company-editor").addEventListener("click", () => closeDialog(editorDialog));
    document.getElementById("cancel-company-editor").addEventListener("click", () => closeDialog(editorDialog));
    document.getElementById("cancel-company-delete").addEventListener("click", () => closeDialog(deleteDialog));
    searchInput.addEventListener("input", renderCompanies);
    tradeFilter.addEventListener("change", renderCompanies);
    document.getElementById("reset-management-filter").addEventListener("click", () => {
        searchInput.value = "";
        tradeFilter.value = "";
        renderCompanies();
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const postalCodes = document.getElementById("company-postal-codes").value
            .split(",")
            .map((postalCode) => postalCode.trim())
            .filter(Boolean);
        if (!postalCodes.length || postalCodes.some((postalCode) => !/^\d{2}$/.test(postalCode))) {
            formError.textContent = "Bitte zweistellige PLZ-Gebiete durch Kommas getrennt eingeben.";
            formError.hidden = false;
            return;
        }

        try {
            await companyStore.save({
                id: document.getElementById("company-id").value,
                name: document.getElementById("company-name").value,
                ppsNumber: document.getElementById("company-pps-number").value,
                trade: editorTrade.value,
                postalCodes
            });
            closeDialog(editorDialog);
            await refresh();
        } catch (error) {
            formError.textContent = error.message;
            formError.hidden = false;
        }
    });

    document.getElementById("confirm-company-delete").addEventListener("click", async () => {
        await companyStore.remove(pendingDeleteId);
        pendingDeleteId = null;
        closeDialog(deleteDialog);
        await refresh();
    });
}

document.addEventListener("DOMContentLoaded", initializeCompanyManagement);
