const POSTAL_CODE_LAYER_IDS = [
    "plz-de-fill",
    "plz-de-border",
    "plz-de-labels",
    "plz-lux-fill",
    "plz-lux-border",
    "plz-lux-label"
];

function postalCodeFilter(postalCodes) {
    return ["in", ["get", "plz"], ["literal", postalCodes]];
}

function setVisiblePostalCodes(map, postalCodes) {
    const filter = postalCodeFilter(postalCodes);
    POSTAL_CODE_LAYER_IDS.forEach((layerId) => map.setFilter(layerId, filter));
}

function setPostalCodeColor(map, color) {
    ["plz-de-fill", "plz-lux-fill"].forEach((id) => map.setPaintProperty(id, "fill-color", color));
    ["plz-de-border", "plz-lux-border"].forEach((id) => map.setPaintProperty(id, "line-color", color));
}

function extendBoundsWithCoordinates(bounds, coordinates) {
    if (typeof coordinates[0] === "number") {
        bounds.extend(coordinates);
        return;
    }

    coordinates.forEach((coordinate) => extendBoundsWithCoordinates(bounds, coordinate));
}

function zoomToPostalCodes(map, postalCodes, postalCodeData) {
    const selectedPostalCodes = new Set(postalCodes);
    const bounds = new maplibregl.LngLatBounds();

    postalCodeData.forEach((featureCollection) => {
        featureCollection.features.forEach((feature) => {
            if (selectedPostalCodes.has(feature.properties?.plz) && feature.geometry?.coordinates) {
                extendBoundsWithCoordinates(bounds, feature.geometry.coordinates);
            }
        });
    });

    if (!bounds.isEmpty()) {
        map.fitBounds(bounds, {
            padding: 60,
            maxZoom: 9,
            duration: 900
        });
    }
}

function normalizeSearchValue(value) {
    return value.trim().toLocaleLowerCase("de-DE");
}

function createTradeBadge(tradeId) {
    const badge = document.createElement("span");
    badge.className = "company-search__trade-badge";
    tradeStore.list().then((trades) => { badge.textContent = trades.find((trade) => trade.id === tradeId)?.name || "Unbekanntes Gewerk"; });
    tradeStore.colorFor(tradeId).then((color) => { badge.style.backgroundColor = color; });
    return badge;
}

function companyPostalCodes(company) {
    return company.territories.map((territory) => territory.postalCode);
}

function formatCompanyTerritories(territories) {
    const primaryCodes = territories.filter((territory) => territory.role === "primary").map((territory) => territory.postalCode);
    const alternativeCodes = territories.filter((territory) => territory.role === "alternative").map((territory) => territory.postalCode);
    return `Vorzug: ${primaryCodes.join(", ") || "–"} · Alternative: ${alternativeCodes.join(", ") || "–"}`;
}

function findCompany(companies, searchValue) {
    const query = normalizeSearchValue(searchValue);
    if (!query) return null;

    return companies.find((company) =>
        normalizeSearchValue(company.name) === query ||
        normalizeSearchValue(company.ppsNumber) === query
    ) || companies.find((company) =>
        normalizeSearchValue(company.name).includes(query)
    );
}

function findCompanySuggestions(companies, searchValue) {
    const query = normalizeSearchValue(searchValue);
    if (!query) return [];

    return companies.filter((company) =>
        normalizeSearchValue(company.name).includes(query) ||
        normalizeSearchValue(company.ppsNumber).includes(query)
    );
}

async function initializeCompanySearch(map, postalCodeData) {
    const input = document.getElementById("company-search-input");
    const suggestions = document.getElementById("company-suggestions");
    const status = document.getElementById("company-search-status");
    let activeSuggestionIndex = -1;
    let selectedCompany = null;

    function suggestionButtons() {
        return [...suggestions.querySelectorAll("button")];
    }

    function highlightSuggestion(index) {
        const buttons = suggestionButtons();
        if (!buttons.length) return;

        activeSuggestionIndex = (index + buttons.length) % buttons.length;
        buttons.forEach((button, buttonIndex) => {
            const isActive = buttonIndex === activeSuggestionIndex;
            button.classList.toggle("is-active", isActive);
            button.setAttribute("aria-selected", String(isActive));
        });

        const activeButton = buttons[activeSuggestionIndex];
        input.setAttribute("aria-activedescendant", activeButton.id);
        activeButton.scrollIntoView({ block: "nearest" });
    }

    function closeSuggestions() {
        suggestions.replaceChildren();
        suggestions.hidden = true;
        activeSuggestionIndex = -1;
        input.setAttribute("aria-expanded", "false");
        input.removeAttribute("aria-activedescendant");
    }

    function selectCompany(company) {
        selectedCompany = company;
        input.value = "";
        closeSuggestions();
        setVisiblePostalCodes(map, companyPostalCodes(company));
        tradeStore.colorFor(company.tradeId).then((color) => setPostalCodeColor(map, color));
        zoomToPostalCodes(map, companyPostalCodes(company), postalCodeData);

        const companyDetails = document.createElement("div");
        companyDetails.className = "company-search__company-details";

        const companySummary = document.createElement("div");
        companySummary.className = "company-search__company-summary";

        const companyIdentity = document.createElement("div");
        companyIdentity.className = "company-search__company-identity";

        const companyName = document.createElement("strong");
        companyName.textContent = company.name;

        const companyNumber = document.createElement("strong");
        companyNumber.textContent = company.ppsNumber;

        companyIdentity.append(
            companyName,
            " · ",
            companyNumber,
            " · ",
            createTradeBadge(company.tradeId)
        );

        const centerButton = document.createElement("button");
        centerButton.type = "button";
        centerButton.className = "company-search__action company-search__center";
        centerButton.setAttribute("aria-label", `${company.name} auf der Karte zentrieren`);
        centerButton.title = "Auf der Karte zentrieren";
        centerButton.innerHTML = `
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="12" cy="12" r="7"></circle>
              <path d="M12 2v3M12 19v3M2 12h3M19 12h3"></path>
            </svg>`;
        centerButton.addEventListener("click", () => zoomToPostalCodes(map, companyPostalCodes(company), postalCodeData));

        const detailsId = `company-search-details-${company.id}`;
        const detailsButton = document.createElement("button");
        detailsButton.type = "button";
        detailsButton.className = "company-search__action company-search__details-toggle";
        detailsButton.setAttribute("aria-label", `Details zu ${company.name} anzeigen`);
        detailsButton.setAttribute("aria-expanded", "false");
        detailsButton.setAttribute("aria-controls", detailsId);
        detailsButton.title = "Details anzeigen";
        detailsButton.innerHTML = `
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="m5 9 7 7 7-7"></path>
            </svg>`;

        const postalCodeArea = document.createElement("div");
        postalCodeArea.className = "company-search__postal-codes";
        postalCodeArea.id = detailsId;
        postalCodeArea.hidden = true;
        postalCodeArea.textContent = formatCompanyTerritories(company.territories);

        detailsButton.addEventListener("click", () => {
            const isOpen = detailsButton.getAttribute("aria-expanded") === "true";
            detailsButton.setAttribute("aria-expanded", String(!isOpen));
            detailsButton.setAttribute("aria-label", `Details zu ${company.name} ${isOpen ? "anzeigen" : "ausblenden"}`);
            detailsButton.title = isOpen ? "Details anzeigen" : "Details ausblenden";
            postalCodeArea.hidden = isOpen;
        });

        companySummary.append(companyIdentity, centerButton, detailsButton);
        companyDetails.append(companySummary, postalCodeArea);
        status.replaceChildren(companyDetails);
        input.focus();
    }

    try {
        let activeTrades = new Set((await tradeStore.list()).filter((trade) => trade.status === "active").map((trade) => trade.id));
        let companies = (await companyStore.list()).filter((company) => company.status === "active" && activeTrades.has(company.tradeId));

        status.replaceChildren();

        input.addEventListener("input", () => {
            closeSuggestions();
            const matches = findCompanySuggestions(companies, input.value);
            if (!matches.length) {
                return;
            }

            matches.forEach((company, index) => {
                const item = document.createElement("li");
                const button = document.createElement("button");
                button.type = "button";
                button.id = `company-suggestion-${index}`;
                button.dataset.ppsNumber = company.ppsNumber;
                button.setAttribute("role", "option");
                button.setAttribute("aria-selected", "false");
                const companyLabel = document.createElement("span");
                companyLabel.textContent = `${company.name} · ${company.ppsNumber} · `;
                button.append(companyLabel, createTradeBadge(company.tradeId));
                button.addEventListener("click", () => selectCompany(company));
                item.append(button);
                suggestions.append(item);
            });
            suggestions.hidden = false;
            input.setAttribute("aria-expanded", "true");
        });

        input.addEventListener("keydown", (event) => {
            if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                if (suggestions.hidden) return;
                event.preventDefault();
                const direction = event.key === "ArrowDown" ? 1 : -1;
                const startIndex = activeSuggestionIndex === -1
                    ? (direction === 1 ? 0 : suggestionButtons().length - 1)
                    : activeSuggestionIndex + direction;
                highlightSuggestion(startIndex);
                return;
            }
            if (event.key === "Escape") {
                closeSuggestions();
                return;
            }
            if (event.key !== "Enter") return;

            const selectedButton = suggestionButtons()[activeSuggestionIndex] || suggestionButtons()[0];
            const company = selectedButton
                ? companies.find((item) => item.ppsNumber === selectedButton.dataset.ppsNumber)
                : findCompany(companies, input.value);
            if (company) {
                event.preventDefault();
                selectCompany(company);
            }
        });

        document.addEventListener("click", (event) => {
            if (!event.target.closest(".company-search__controls")) closeSuggestions();
        });

        window.addEventListener("companies:changed", async () => {
            activeTrades = new Set((await tradeStore.list()).filter((trade) => trade.status === "active").map((trade) => trade.id));
            companies = (await companyStore.list()).filter((company) => company.status === "active" && activeTrades.has(company.tradeId));
            const updatedSelection = selectedCompany && companies.find((company) => company.id === selectedCompany.id);
            if (updatedSelection) selectCompany(updatedSelection);
            else {
                selectedCompany = null;
                status.replaceChildren();
            }
            closeSuggestions();
        });

        window.addEventListener("trades:changed", async () => {
            activeTrades = new Set((await tradeStore.list()).filter((trade) => trade.status === "active").map((trade) => trade.id));
            companies = (await companyStore.list()).filter((company) => company.status === "active" && activeTrades.has(company.tradeId));
            const updatedSelection = selectedCompany && companies.find((company) => company.id === selectedCompany.id);
            if (updatedSelection) selectCompany(updatedSelection);
            else {
                selectedCompany = null;
                status.replaceChildren();
            }
            closeSuggestions();
        });

        input.focus();
    } catch (error) {
        status.textContent = error.message;
        input.disabled = true;
    }
}
