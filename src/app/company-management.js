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
    const tradeDialog = document.getElementById("trade-management");
    const tradeForm = document.getElementById("trade-form");
    const tradeFormError = document.getElementById("trade-form-error");
    const tradeList = document.getElementById("trade-list");
    let companies = [];
    let trades = [];
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
        const tradeNames = trades.map((trade) => trade.name);
        tradeFilter.replaceChildren(new Option("Alle Gewerke", ""));
        editorTrade.replaceChildren(new Option("Gewerk auswählen", ""));
        trades.forEach((trade) => {
            tradeFilter.add(new Option(trade.name, trade.name));
            if (trade.active) editorTrade.add(new Option(trade.name, trade.name));
        });
        if (tradeNames.includes(currentFilter)) tradeFilter.value = currentFilter;
    }

    function actionButton(symbol, label, className, handler) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = `table-action ${className}`;
        button.textContent = symbol;
        button.title = label;
        button.setAttribute("aria-label", label);
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
        if (company && ![...editorTrade.options].some((option) => option.value === company.trade)) {
            editorTrade.add(new Option(`${company.trade} (inaktiv)`, company.trade));
        }
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
            row.classList.toggle("is-inactive", !company.active);
            const nameCell = row.insertCell();
            nameCell.className = "company-table__name-cell";
            const nameContent = document.createElement("div");
            nameContent.className = "company-table__name-content";
            const companyName = document.createElement("strong");
            companyName.className = "company-table__name";
            companyName.textContent = company.name;
            companyName.title = company.name;
            nameContent.append(companyName);
            if (!company.active) {
                const status = document.createElement("span");
                status.className = "status-badge";
                status.textContent = "Inaktiv";
                nameContent.append(status);
            }
            nameCell.append(nameContent);
            row.insertCell().append(createTradeBadge(company.trade));
            row.insertCell().textContent = company.ppsNumber;
            const postalCodes = row.insertCell();
            postalCodes.className = "company-table__postal-codes";
            postalCodes.textContent = company.postalCodes.join(", ");
            const actions = row.insertCell();
            actions.className = "company-table__actions";
            actions.append(
                actionButton("✎", "Unternehmen bearbeiten", "table-action--edit", () => openEditor(company)),
                actionButton(
                    company.active ? "⏸" : "▶",
                    company.active ? "Unternehmen deaktivieren" : "Unternehmen reaktivieren",
                    "table-action--status",
                    async () => {
                        await companyStore.setActive(company.id, !company.active);
                        await refresh();
                    }
                ),
                actionButton("🗑", "Unternehmen endgültig löschen", "table-action--delete", () => requestDelete(company))
            );
        });
    }

    function renderTrades() {
        tradeList.replaceChildren();
        trades.forEach((trade) => {
            const item = document.createElement("li");
            const name = document.createElement("span");
            name.textContent = trade.name;
            const button = actionButton(
                trade.active ? "⏸" : "▶",
                trade.active ? `Gewerk ${trade.name} deaktivieren` : `Gewerk ${trade.name} reaktivieren`,
                "table-action--status",
                async () => {
                    await tradeStore.setActive(trade.name, !trade.active);
                    await refresh();
                    renderTrades();
                }
            );
            if (!trade.active) item.classList.add("is-inactive");
            item.append(name, button);
            tradeList.append(item);
        });
    }

    async function refresh() {
        [companies, trades] = await Promise.all([companyStore.list(), tradeStore.list()]);
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
    document.getElementById("open-trade-management").addEventListener("click", () => {
        renderTrades();
        tradeFormError.hidden = true;
        tradeDialog.showModal();
        document.getElementById("trade-name").focus();
    });
    document.getElementById("close-trade-management").addEventListener("click", () => closeDialog(tradeDialog));
    document.getElementById("close-company-editor").addEventListener("click", () => closeDialog(editorDialog));
    document.getElementById("cancel-company-editor").addEventListener("click", () => closeDialog(editorDialog));
    document.getElementById("cancel-company-delete").addEventListener("click", () => closeDialog(deleteDialog));
    searchInput.addEventListener("input", renderCompanies);
    tradeFilter.addEventListener("change", renderCompanies);
    tradeForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        try {
            await tradeStore.add(document.getElementById("trade-name").value);
            tradeForm.reset();
            tradeFormError.hidden = true;
            await refresh();
            renderTrades();
        } catch (error) {
            tradeFormError.textContent = error.message;
            tradeFormError.hidden = false;
        }
    });
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
