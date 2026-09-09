function initializeSearchTabs() {
    const tabList = document.querySelector(".search-tabs");
    const tabs = [...tabList.querySelectorAll('[role="tab"]')];

    function activateTab(activeTab, focusPanel = true) {
        tabs.forEach((tab) => {
            const isActive = tab === activeTab;
            const panel = document.getElementById(tab.getAttribute("aria-controls"));
            tab.classList.toggle("is-active", isActive);
            tab.setAttribute("aria-selected", String(isActive));
            tab.tabIndex = isActive ? 0 : -1;
            panel.hidden = !isActive;
        });

        if (focusPanel) {
            document.getElementById(activeTab.getAttribute("aria-controls"))
                .querySelector("input, select, button")?.focus();
        }
    }

    tabs.forEach((tab, index) => {
        tab.addEventListener("click", () => activateTab(tab));
        tab.addEventListener("keydown", (event) => {
            let targetIndex;
            if (event.key === "ArrowLeft") targetIndex = (index - 1 + tabs.length) % tabs.length;
            else if (event.key === "ArrowRight") targetIndex = (index + 1) % tabs.length;
            else if (event.key === "Home") targetIndex = 0;
            else if (event.key === "End") targetIndex = tabs.length - 1;
            else return;

            event.preventDefault();
            activateTab(tabs[targetIndex]);
            tabs[targetIndex].focus();
        });
    });
}

initializeSearchTabs();
