function normalizeSiteManagerSearchValue(value) {
    return value.trim().toLocaleLowerCase("de-DE");
}

function findSiteManagerSuggestions(siteManagers, searchValue) {
    const query = normalizeSiteManagerSearchValue(searchValue);
    if (!query) return siteManagers;
    return siteManagers.filter((siteManager) =>
        normalizeSiteManagerSearchValue(siteManager.name).includes(query)
    );
}

async function initializeSiteManagerSearch(map, postalCodeData) {
    const input = document.getElementById("site-manager-search-input");
    const suggestions = document.getElementById("site-manager-suggestions");
    const status = document.getElementById("site-manager-search-status");
    let siteManagers = [];
    let selectedSiteManager = null;
    let activeSuggestionIndex = -1;
    let loadFailed = false;

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

    function selectSiteManager(siteManager) {
        const postalCodes = siteManagerPostalCodes(siteManager.territories);
        selectedSiteManager = siteManager;
        input.value = "";
        setVisiblePostalCodes(map, postalCodes);
        zoomToPostalCodes(map, postalCodes, postalCodeData);

        const siteManagerDetails = document.createElement("div");
        siteManagerDetails.className = "company-search__company-details";

        const siteManagerSummary = document.createElement("div");
        siteManagerSummary.className = "company-search__company-summary";

        const siteManagerName = document.createElement("strong");
        siteManagerName.className = "company-search__company-identity";
        siteManagerName.textContent = siteManager.name;

        const postalCodeArea = document.createElement("div");
        postalCodeArea.className = "company-search__postal-codes";
        postalCodeArea.textContent = `PLZ-Gebiete: ${postalCodes.join(", ") || "Keine"}`;

        siteManagerSummary.append(siteManagerName);
        siteManagerDetails.append(siteManagerSummary, postalCodeArea);
        status.replaceChildren(siteManagerDetails);
        input.focus();
        closeSuggestions();
    }

    function renderSuggestions() {
        closeSuggestions();
        if (loadFailed) return;

        if (!siteManagers.length) {
            if (!selectedSiteManager) status.textContent = "Keine aktiven Bauleiter verfügbar.";
            return;
        }

        const matches = findSiteManagerSuggestions(siteManagers, input.value);
        if (!matches.length) {
            status.textContent = "Keine aktiven Bauleiter für diese Suche gefunden.";
            return;
        }

        if (!selectedSiteManager) status.replaceChildren();
        matches.forEach((siteManager, index) => {
            const item = document.createElement("li");
            const button = document.createElement("button");
            button.type = "button";
            button.id = `site-manager-suggestion-${index}`;
            button.dataset.siteManagerId = siteManager.id;
            button.setAttribute("role", "option");
            button.setAttribute("aria-selected", "false");
            button.textContent = siteManager.name;
            button.addEventListener("click", () => selectSiteManager(siteManager));
            item.append(button);
            suggestions.append(item);
        });
        suggestions.hidden = false;
        input.setAttribute("aria-expanded", "true");
    }

    async function refreshSiteManagers() {
        try {
            siteManagers = await siteManagerStore.listActive();
            loadFailed = false;
            input.disabled = false;

            const updatedSelection = selectedSiteManager &&
                siteManagers.find((siteManager) => siteManager.id === selectedSiteManager.id);
            if (updatedSelection) selectSiteManager(updatedSelection);
            else if (selectedSiteManager) {
                selectedSiteManager = null;
                status.textContent = "Der ausgewählte Bauleiter ist nicht mehr aktiv.";
            }
            renderSuggestions();
        } catch (error) {
            siteManagers = [];
            loadFailed = true;
            closeSuggestions();
            status.textContent = `Aktive Bauleiter konnten nicht geladen werden: ${error.message}`;
            input.disabled = false;
        }
    }

    input.disabled = true;
    status.textContent = "Aktive Bauleiter werden geladen …";
    input.addEventListener("input", () => {
        selectedSiteManager = null;
        renderSuggestions();
    });
    input.addEventListener("focus", renderSuggestions);
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
        const siteManager = selectedButton && siteManagers.find((item) => item.id === selectedButton.dataset.siteManagerId);
        if (siteManager) {
            event.preventDefault();
            selectSiteManager(siteManager);
        }
    });
    document.addEventListener("click", (event) => {
        if (!event.target.closest(".site-manager-search__controls")) closeSuggestions();
    });
    window.addEventListener("site-managers:changed", refreshSiteManagers);

    await refreshSiteManagers();
}
