function initializeDataImport() {
    const chooseButton = document.getElementById('import-master-data');
    const fileInput = document.getElementById('import-master-data-file');
    const exportButton = document.getElementById('export-master-data');
    const dialog = document.getElementById('import-master-data-confirmation');
    const status = document.getElementById('import-master-data-status');
    const errors = document.getElementById('import-master-data-errors');
    const warning = document.getElementById('import-master-data-warning');
    const confirmButton = document.getElementById('confirm-master-data-import');
    const cancelButton = document.getElementById('cancel-master-data-import');
    let pendingDocument = null;
    let busy = false;

    function setBusy(value) {
        busy = value;
        chooseButton.disabled = value;
        fileInput.disabled = value;
        confirmButton.disabled = value;
        cancelButton.disabled = value;
        exportButton.classList.toggle('is-disabled', value);
        exportButton.setAttribute('aria-disabled', String(value));
    }

    function showErrors(message, fields = []) {
        status.textContent = message;
        errors.replaceChildren();
        fields.forEach((field) => {
            const item = document.createElement('li');
            item.textContent = String(field);
            errors.append(item);
        });
        errors.hidden = fields.length === 0;
        warning.hidden = true;
        confirmButton.hidden = true;
    }

    function resetSelection() {
        pendingDocument = null;
        fileInput.value = '';
    }

    chooseButton.addEventListener('click', () => { if (!busy) fileInput.click(); });
    exportButton.addEventListener('click', (event) => { if (busy) event.preventDefault(); });
    cancelButton.addEventListener('click', () => { resetSelection(); dialog.close(); });
    dialog.addEventListener('cancel', (event) => {
        if (busy) event.preventDefault();
        else resetSelection();
    });

    fileInput.addEventListener('change', async () => {
        const file = fileInput.files?.[0];
        if (!file || busy) return;
        dialog.showModal();
        showErrors('Datei wird gelesen und validiert …');
        setBusy(true);
        try {
            try {
                pendingDocument = JSON.parse(await file.text());
            } catch (error) {
                pendingDocument = null;
                showErrors('Die ausgewählte Datei enthält kein gültiges JSON.');
                return;
            }
            const result = await companyStore.importData(pendingDocument, 'validate');
            status.textContent = `Validierung erfolgreich: ${result.trades} Gewerke, ${result.companies} Unternehmen und ${result.siteManagers} Bauleiter.`;
            errors.hidden = true;
            warning.hidden = false;
            confirmButton.hidden = false;
        } catch (error) {
            const schemaError = error.fields?.some((field) => String(field).includes('schemaVersion'));
            const message = error.code === 'network_error'
                ? error.message
                : schemaError
                    ? 'Die schemaVersion der Datei ist mit dieser Installation nicht kompatibel.'
                    : 'Die Datei konnte nicht validiert werden.';
            showErrors(message, error.fields || []);
        } finally {
            setBusy(false);
        }
    });

    confirmButton.addEventListener('click', async () => {
        if (!pendingDocument || busy) return;
        setBusy(true);
        status.textContent = 'Daten werden importiert …';
        errors.hidden = true;
        try {
            const result = await companyStore.importData(pendingDocument, 'empty');
            status.textContent = `Import erfolgreich: ${result.trades} Gewerke, ${result.companies} Unternehmen und ${result.siteManagers} Bauleiter.`;
            warning.hidden = true;
            confirmButton.hidden = true;
            pendingDocument = null;
            document.dispatchEvent(new CustomEvent('site-manager-management:open'));
            document.dispatchEvent(new CustomEvent('trade-management:open'));
        } catch (error) {
            showErrors(error.code === 'network_error' ? error.message : (error.message || 'Der Import ist fehlgeschlagen.'), error.fields || []);
        } finally {
            resetSelection();
            setBusy(false);
        }
    });
}

document.addEventListener('DOMContentLoaded', initializeDataImport);
