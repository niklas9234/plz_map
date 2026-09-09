(function initializeAdministrationMenu() {
    const menu = document.querySelector(".administration-menu");
    const toggle = document.getElementById("administration-menu-toggle");
    const panel = document.getElementById("administration-menu-panel");
    const pageDialog = document.getElementById("administration-page");
    const pageTitle = document.getElementById("administration-page-title");
    const pageContents = [...pageDialog.querySelectorAll("[data-page-content]")];

    function setMenuOpen(open) {
        panel.hidden = !open;
        toggle.setAttribute("aria-expanded", String(open));
        toggle.setAttribute("aria-label", open ? "Verwaltungsmenü schließen" : "Verwaltungsmenü öffnen");
    }

    toggle.addEventListener("click", () => {
        setMenuOpen(toggle.getAttribute("aria-expanded") !== "true");
    });

    panel.addEventListener("click", (event) => {
        const pageButton = event.target.closest("[data-administration-page]");
        setMenuOpen(false);
        if (!pageButton) return;

        const page = pageButton.dataset.administrationPage;
        pageTitle.textContent = page === "settings" ? "Einstellungen" : "Info";
        pageContents.forEach((content) => {
            content.hidden = content.dataset.pageContent !== page;
        });
        pageDialog.showModal();
    });

    document.getElementById("close-administration-page").addEventListener("click", () => pageDialog.close());
    pageDialog.addEventListener("click", (event) => {
        if (event.target === pageDialog) pageDialog.close();
    });

    document.addEventListener("pointerdown", (event) => {
        if (!menu.contains(event.target)) setMenuOpen(false);
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && toggle.getAttribute("aria-expanded") === "true") {
            setMenuOpen(false);
            toggle.focus();
        }
    });
})();
