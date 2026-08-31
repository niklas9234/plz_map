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

async function loadCompanies() {
    const response = await fetch(COMPANY_DATA_URL);
    if (!response.ok) {
        throw new Error(`Unternehmensdaten konnten nicht geladen werden (${response.status}).`);
    }
    return response.json();
}

async function initializeCompanySearch(map) {
    const form = document.getElementById("company-search-form");
    const input = document.getElementById("company-search-input");
    const resetButton = document.getElementById("company-search-reset");
    const suggestions = document.getElementById("company-suggestions");
    const status = document.getElementById("company-search-status");

    try {
        const companies = await loadCompanies();

        companies.forEach((company) => {
            const option = document.createElement("option");
            option.value = company.name;
            option.label = company.ppsNumber;
            suggestions.append(option);
        });
        status.textContent = `${companies.length} Testunternehmen verfügbar.`;

        form.addEventListener("submit", (event) => {
            event.preventDefault();
            const company = findCompany(companies, input.value);

            if (!company) {
                setVisiblePostalCodes(map, []);
                status.textContent = "Kein Unternehmen mit diesem Namen oder dieser PPS-Nummer gefunden.";
                return;
            }

            setVisiblePostalCodes(map, company.postalCodes);
            status.textContent = `${company.name} (${company.ppsNumber}): ${company.postalCodes.join(", ")}`;
        });

        resetButton.addEventListener("click", () => {
            form.reset();
            setVisiblePostalCodes(map, []);
            status.textContent = `${companies.length} Testunternehmen verfügbar.`;
            input.focus();
        });
    } catch (error) {
        status.textContent = error.message;
        input.disabled = true;
        form.querySelector("button[type='submit']").disabled = true;
    }
}
