function findAreaPartners(companies, postalCode, trade) {
    return companies.reduce((partners, company) => {
        if (!company.active || company.trade !== trade) return partners;
        const assignment = company.territories.find((territory) => territory.postalCode === postalCode);
        if (assignment) partners[assignment.role].push(company);
        return partners;
    }, { primary: [], alternative: [] });
}

function createAreaPartnerCard(company) {
    const card = document.createElement("article");
    card.className = "area-search__partner";

    const name = document.createElement("strong");
    name.textContent = company.name;
    const number = document.createElement("span");
    number.textContent = company.ppsNumber;
    card.append(name, number);
    return card;
}

async function initializeAreaSearch(map, postalCodeData) {
    const companyTab = document.getElementById("company-search-tab");
    const areaTab = document.getElementById("area-search-tab");
    const companyPanel = document.getElementById("company-search-panel");
    const areaPanel = document.getElementById("area-search-panel");
    const companyInput = document.getElementById("company-search-input");
    const postalCodeInput = document.getElementById("area-postal-code");
    const tradeSelect = document.getElementById("area-trade");
    const results = document.getElementById("area-search-results");
    let companies = [];
    let trades = [];

    function activateTab(tab) {
        const showAreaSearch = tab === areaTab;
        companyTab.classList.toggle("is-active", !showAreaSearch);
        areaTab.classList.toggle("is-active", showAreaSearch);
        companyTab.setAttribute("aria-selected", String(!showAreaSearch));
        areaTab.setAttribute("aria-selected", String(showAreaSearch));
        companyPanel.hidden = showAreaSearch;
        areaPanel.hidden = !showAreaSearch;
        (showAreaSearch ? postalCodeInput : companyInput).focus();
    }

    function renderPartnerGroup(title, partners, emptyText) {
        const section = document.createElement("section");
        section.className = "area-search__group";
        const heading = document.createElement("h2");
        heading.textContent = title;
        section.append(heading);
        if (partners.length) partners.forEach((company) => section.append(createAreaPartnerCard(company)));
        else {
            const empty = document.createElement("p");
            empty.className = "area-search__empty";
            empty.textContent = emptyText;
            section.append(empty);
        }
        return section;
    }

    async function search() {
        const postalCode = postalCodeInput.value.trim();
        const trade = tradeSelect.value;
        results.replaceChildren();
        if (!/^\d{2}$/.test(postalCode) || !trade) return;

        const partners = findAreaPartners(companies, postalCode, trade);
        results.append(
            renderPartnerGroup("Vorzugspartner", partners.primary, "Kein Vorzugspartner hinterlegt."),
            renderPartnerGroup("Alternativpartner", partners.alternative, "Keine Alternativpartner hinterlegt.")
        );
        setVisiblePostalCodes(map, [postalCode]);
        setPostalCodeColor(map, await tradeStore.colorFor(trade));
        zoomToPostalCodes(map, [postalCode], postalCodeData);
    }

    async function refreshData() {
        trades = (await tradeStore.list()).filter((trade) => trade.active);
        const activeTradeNames = new Set(trades.map((trade) => trade.name));
        companies = (await companyStore.list()).filter((company) => company.active && activeTradeNames.has(company.trade));
        const selectedTrade = tradeSelect.value;
        tradeSelect.replaceChildren(new Option("Gewerk auswählen", ""));
        trades.forEach((trade) => tradeSelect.add(new Option(trade.name, trade.name)));
        if (activeTradeNames.has(selectedTrade)) tradeSelect.value = selectedTrade;
        await search();
    }

    companyTab.addEventListener("click", () => activateTab(companyTab));
    areaTab.addEventListener("click", () => activateTab(areaTab));
    [companyTab, areaTab].forEach((tab) => tab.addEventListener("keydown", (event) => {
        if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
        event.preventDefault();
        activateTab(tab === companyTab ? areaTab : companyTab);
    }));
    postalCodeInput.addEventListener("input", () => {
        postalCodeInput.value = postalCodeInput.value.replace(/\D/g, "").slice(0, 2);
        search();
    });
    tradeSelect.addEventListener("change", search);
    window.addEventListener("companies:changed", refreshData);
    window.addEventListener("trades:changed", refreshData);

    try {
        await refreshData();
    } catch (error) {
        results.textContent = error.message;
        postalCodeInput.disabled = true;
        tradeSelect.disabled = true;
    }
}
