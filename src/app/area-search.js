function findAreaPartners(companies, postalCode, tradeId) {
    return companies.reduce((partners, company) => {
        if (company.status !== "active" || company.tradeId !== tradeId) return partners;
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
    const postalCodeInput = document.getElementById("area-postal-code");
    const tradeSelect = document.getElementById("area-trade");
    const results = document.getElementById("area-search-results");
    let companies = [];
    let trades = [];

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
        const postalCode = postalCodeInput.value.trim().toUpperCase();
        const trade = tradeSelect.value;
        results.replaceChildren();
        if (!/^(?:\d{2}|LUX)$/.test(postalCode) || !trade) return;

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
        trades = (await tradeStore.list()).filter((trade) => trade.status === "active");
        const activeTradeIds = new Set(trades.map((trade) => trade.id));
        companies = (await companyStore.list()).filter((company) => company.status === "active" && activeTradeIds.has(company.tradeId));
        const selectedTrade = tradeSelect.value;
        tradeSelect.replaceChildren(new Option("Gewerk auswählen", ""));
        trades.forEach((trade) => tradeSelect.add(new Option(trade.name, trade.id)));
        if (activeTradeIds.has(selectedTrade)) tradeSelect.value = selectedTrade;
        await search();
    }

    postalCodeInput.addEventListener("input", () => {
        const value = postalCodeInput.value.replace(/[^a-z\d]/gi, "").toUpperCase();
        postalCodeInput.value = /^\d/.test(value)
            ? value.replace(/\D/g, "").slice(0, 2)
            : value.replace(/[^A-Z]/g, "").slice(0, 3);
        search();
    });
    tradeSelect.addEventListener("change", search);
    window.addEventListener("companies:changed", refreshData);
    window.addEventListener("trades:changed", refreshData);

    await refreshData();
}
