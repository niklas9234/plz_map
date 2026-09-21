const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const test = require('node:test');
const vm = require('node:vm');

const context = {
    HTMLElement: class {},
    customElements: { define() {} }
};
const source = `${readFileSync(`${__dirname}/postal-code-selection.js`, 'utf8')}\nthis.postalCodeRole = postalCodeRole;`;
vm.runInNewContext(source, context);

const roles = [{ value: 'assigned' }];

test('Bauleitergebiete aus der API verwenden die zugewiesene Darstellung', () => {
    assert.equal(context.postalCodeRole([{ postalCode: '72' }], roles, '72'), 'assigned');
    assert.equal(context.postalCodeRole([{ postalCode: '72' }], roles, '75'), null);
});

test('einfache Gebietscodes bleiben mit Importdaten kompatibel', () => {
    assert.equal(context.postalCodeRole(['75'], roles, '75'), 'assigned');
});

test('explizite Rollen der Unternehmensgebiete bleiben erhalten', () => {
    const companyRoles = [{ value: 'primary' }, { value: 'alternative' }];
    assert.equal(context.postalCodeRole([{ postalCode: '78', role: 'alternative' }], companyRoles, '78'), 'alternative');
});
