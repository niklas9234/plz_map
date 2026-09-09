const SELECTABLE_POSTAL_CODES = [
    "01", "02", "03", "04", "06", "07", "08", "09",
    "10", "12", "13", "14", "15", "16", "17", "18", "19",
    "20", "21", "22", "23", "24", "25", "26", "27", "28", "29",
    "30", "31", "32", "33", "34", "35", "36", "37", "38", "39",
    "40", "41", "42", "44", "45", "46", "47", "48", "49",
    "50", "51", "52", "53", "54", "55", "56", "57", "58", "59",
    "60", "61", "63", "64", "65", "66", "67", "68", "69",
    "70", "71", "72", "73", "74", "75", "76", "77", "78", "79",
    "80", "81", "82", "83", "84", "85", "86", "87", "88", "89",
    "90", "91", "92", "93", "94", "95", "96", "97", "98", "99"
];

function createPostalCodePicker(root, options = {}) {
    const roles = options.roles || [
        { value: "primary", label: "Vorzugsdienstleister", className: "is-primary" },
        { value: "alternative", label: "Alternativdienstleister", className: "is-alternative" }
    ];
    const territories = options.territories || [];
    const assignedRole = (code) => {
        const territory = territories.find((item) => (typeof item === "string" ? item : item.postalCode) === code);
        return territory ? (typeof territory === "string" ? roles[0].value : territory.role) : null;
    };
    const grid = root.querySelector(".postal-code-grid");
    const international = root.querySelector(".postal-code-international");
    const status = root.querySelector(".postal-code-selection-status");
    const clear = root.querySelector(".postal-code-clear");
    const selectable = new Set(SELECTABLE_POSTAL_CODES);
    let activePointer = null;
    let dragRole = null;

    function nextRole(role) {
        const index = roles.findIndex((item) => item.value === role);
        return index < 0 ? roles[0].value : roles[index + 1]?.value || null;
    }

    function update() {
        const counts = roles.map((role) => ({
            ...role, count: root.querySelectorAll(`.postal-code-tile[data-role="${role.value}"]:not(:disabled)`).length
        }));
        status.textContent = counts.map((role) => `${role.summary || role.label}: ${role.count}`).join(", ");
        clear.disabled = counts.every((role) => role.count === 0);
    }

    function setRole(tile, role) {
        if (tile.disabled || (tile.dataset.role || null) === role) return;
        if (role) tile.dataset.role = role;
        else delete tile.dataset.role;
        roles.forEach((item) => tile.classList.toggle(item.className, role === item.value));
        const label = roles.find((item) => item.value === role)?.label || "nicht zugewiesen";
        tile.setAttribute("aria-label", `${tile.dataset.label}, ${label}`);
        update();
        options.onChange?.();
    }

    function finishDrag(event) {
        if (event.pointerId !== activePointer) return;
        activePointer = null;
        document.removeEventListener("pointerup", finishDrag);
        document.removeEventListener("pointercancel", finishDrag);
    }

    function makeTile(code, label = `PLZ-Gebiet ${code}`, disabled = false) {
        const tile = document.createElement("button");
        tile.type = "button";
        tile.className = "postal-code-tile";
        tile.dataset.code = code;
        tile.dataset.label = label;
        tile.textContent = code;
        tile.disabled = disabled;
        if (disabled) {
            tile.setAttribute("aria-label", `${label} nicht vergeben`);
            return tile;
        }
        const role = assignedRole(code);
        if (role) tile.dataset.role = role;
        roles.forEach((item) => tile.classList.toggle(item.className, role === item.value));
        tile.setAttribute("aria-label", `${label}, ${roles.find((item) => item.value === role)?.label || "nicht zugewiesen"}`);
        tile.addEventListener("pointerdown", (event) => {
            if (event.button !== 0) return;
            activePointer = event.pointerId;
            dragRole = nextRole(tile.dataset.role);
            setRole(tile, dragRole);
            document.addEventListener("pointerup", finishDrag);
            document.addEventListener("pointercancel", finishDrag);
        });
        tile.addEventListener("pointerenter", (event) => {
            if (event.pointerId === activePointer && (event.buttons & 1) === 1) setRole(tile, dragRole);
        });
        tile.addEventListener("click", (event) => {
            if (event.detail === 0) setRole(tile, nextRole(tile.dataset.role));
        });
        return tile;
    }

    for (let first = 0; first <= 9; first += 1) {
        const row = document.createElement("div");
        row.className = "postal-code-grid__row";
        row.setAttribute("role", "row");
        for (let last = 0; last <= 9; last += 1) {
            const code = `${first}${last}`;
            const cell = document.createElement("span");
            cell.className = "postal-code-grid__cell";
            cell.setAttribute("role", "gridcell");
            cell.append(makeTile(code, `PLZ-Gebiet ${code}`, !selectable.has(code)));
            row.append(cell);
        }
        grid.append(row);
    }
    const luxemburg = makeTile("LUX", "Luxemburg");
    luxemburg.classList.add("postal-code-tile--international");
    international.append(luxemburg);
    clear.addEventListener("click", () => {
        root.querySelectorAll(".postal-code-tile[data-role]:not(:disabled)").forEach((tile) => setRole(tile, null));
    });
    update();

    return {
        assignments: () => [...root.querySelectorAll(".postal-code-tile[data-role]:not(:disabled)")]
            .map((tile) => ({ postalCode: tile.dataset.code, role: tile.dataset.role })),
        codes: () => [...root.querySelectorAll(".postal-code-tile[data-role]:not(:disabled)")]
            .map((tile) => tile.dataset.code)
    };
}

class PostalCodeSelection extends HTMLElement {
    configure(options = {}) {
        const companyMode = this.getAttribute("mode") === "company";
        const configuration = companyMode ? {
            hint: "Klicken Sie mehrfach auf ein Gebiet: Weiß = nicht zugewiesen, Grün = Vorzugsdienstleister, Gelb = Alternativdienstleister.",
            roles: [
                { value: "primary", label: "Vorzugsdienstleister", summary: "Vorzug", className: "is-primary" },
                { value: "alternative", label: "Alternativdienstleister", summary: "Alternativ", className: "is-alternative" }
            ]
        } : {
            hint: "Klicken Sie auf ein Gebiet: Weiß = nicht zugewiesen, Grün = zugewiesen.",
            roles: [{ value: "assigned", label: "zugewiesen", summary: "Zugewiesen", className: "is-primary" }]
        };
        this.className = "detail-section postal-code-section";
        this.innerHTML = `
            <h3>PLZ-Gebiete</h3>
            <p class="postal-code-section__hint"></p>
            <div class="postal-code-selection-summary">
              <p class="postal-code-selection-status" aria-live="polite" aria-atomic="true"></p>
              <button class="button button--secondary postal-code-clear" type="button">Auswahl löschen</button>
            </div>
            <div class="postal-code-picker">
              <div class="postal-code-grid" role="grid" aria-label="Deutsche PLZ-Gebiete auswählen"></div>
            </div>
            <div class="postal-code-international" aria-label="Weitere PLZ-Gebiete"></div>`;
        this.querySelector(".postal-code-section__hint").textContent = configuration.hint;
        this.picker = createPostalCodePicker(this, { ...options, roles: configuration.roles });
        return this;
    }

    assignments() {
        return this.picker?.assignments() || [];
    }

    codes() {
        return this.picker?.codes() || [];
    }
}

customElements.define("postal-code-selection", PostalCodeSelection);
