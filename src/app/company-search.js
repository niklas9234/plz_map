const COMPANY_DATA_URL = "./companies.json";
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

function normalizeSearchValue(value) {
    return value.trim().toLocaleLowerCase("de-DE");
}

function createTradeBadge(trade) {
    const badge = document.createElement("span");
    badge.className = "company-search__trade-badge";
    badge.textContent = trade;
    return badge;
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

async function loadCompanies() {
    const response = await fetch(COMPANY_DATA_URL);
    if (!response.ok) {
        throw new Error(`Unternehmensdaten konnten nicht geladen werden (${response.status}).`);
    }
    return response.json();
}

async function initializeCompanySearch(map) {
    const input = document.getElementById("company-search-input");
    const suggestions = document.getElementById("company-suggestions");
    const status = document.getElementById("company-search-status");
    let activeSuggestionIndex = -1;

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
        input.value = "";
        closeSuggestions();
        setVisiblePostalCodes(map, company.postalCodes);

        const companyDetails = document.createElement("div");
        companyDetails.className = "company-search__company-details";

        const companyName = document.createElement("strong");
        companyName.textContent = company.name;

        const companyNumber = document.createElement("strong");
        companyNumber.textContent = company.ppsNumber;

        companyDetails.append(
            companyName,
            " · ",
            companyNumber,
            " · ",
            createTradeBadge(company.trade)
        );

        const postalCodeArea = document.createElement("div");
        postalCodeArea.className = "company-search__postal-codes";
        postalCodeArea.textContent = `PLZ-Gebiete: ${company.postalCodes.join(", ")}`;

        status.replaceChildren(companyDetails, postalCodeArea);
        input.focus();
    }

    try {
        const companies = await loadCompanies();

        status.textContent = `${companies.length} Testunternehmen verfügbar.`;

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
                button.append(companyLabel, createTradeBadge(company.trade));
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

            const activeButton = suggestionButtons()[activeSuggestionIndex];
            const company = activeButton
                ? companies.find((item) => item.ppsNumber === activeButton.dataset.ppsNumber)
                : findCompany(companies, input.value);
            if (company) {
                event.preventDefault();
                selectCompany(company);
            }
        });

        document.addEventListener("click", (event) => {
            if (!event.target.closest(".company-search__controls")) closeSuggestions();
        });

        input.focus();
    } catch (error) {
        status.textContent = error.message;
        input.disabled = true;
    }
}
