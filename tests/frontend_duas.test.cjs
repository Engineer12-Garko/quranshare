const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

function createAppHarness() {
  const storage = new Map();
  const localStorage = {
    getItem: key => storage.has(key) ? storage.get(key) : null,
    setItem: (key, value) => storage.set(key, String(value)),
    removeItem: key => storage.delete(key),
  };
  const duaSearch = { addEventListener() {} };
  const duaContent = { innerHTML: '', querySelector: () => duaSearch };
  const savedContent = { innerHTML: '' };
  const app = {
    innerHTML: '',
    querySelector(selector) {
      if (selector === '#duas-content') return duaContent;
      if (selector === '#saved-content') return savedContent;
      return null;
    },
  };
  const body = { lastChild: null, appendChild(node) { this.lastChild = node; } };
  const document = {
    body,
    getElementById: id => id === 'app' ? app : null,
    createElement: () => ({ addEventListener() {}, remove() {} }),
  };
  const fixedNow = new Date('2026-10-17T12:00:00Z');
  class FixedDate extends Date {
    constructor(...args) { super(...(args.length ? args : [fixedNow])); }
    static UTC(...args) { return Date.UTC(...args); }
  }
  const window = { location: { hash: '#/duas' }, addEventListener() {} };
  const sandbox = {
    Date: FixedDate, console, document, localStorage, window,
    navigator: {}, fetch: async () => { throw new Error('unexpected network request'); },
    setTimeout, clearTimeout, URL, File: class {},
  };
  vm.createContext(sandbox);
  const source = fs.readFileSync(path.join(__dirname, '../app/static/js/app.js'), 'utf8');
  vm.runInContext(source, sandbox, { filename: 'app.js' });
  vm.runInContext('_currentUser = { id: 41, role: "user" }; todayDua = () => DUAS[0];', sandbox);
  return { sandbox, app, duaContent, savedContent, body, storage };
}

test('Dua search matches English translation and provides a no-results state', async () => {
  const { sandbox, app, duaContent } = createAppHarness();
  vm.runInContext('_duaSearch = "resurrection";', sandbox);
  await sandbox.renderDuas(app);
  assert.match(duaContent.innerHTML, /Du\'a Upon Waking Up/);
  assert.doesNotMatch(duaContent.innerHTML, /Du\'a Before Eating/);

  vm.runInContext('_duaSearch = "no matching phrase";', sandbox);
  await sandbox.renderDuas(app);
  assert.match(duaContent.innerHTML, /No du\'as match this search or category/);
});

test('More category uses explicit categories outside Morning, Evening, and Sleep', async () => {
  const { sandbox, app, duaContent } = createAppHarness();
  await sandbox.setDuaCategory('More');
  assert.match(duaContent.innerHTML, /Du\'a Before Eating/);
  assert.doesNotMatch(duaContent.innerHTML, /dua-list-title">Du\'a Upon Waking Up/);
});

test('Dua details render Arabic RTL and existing English translation without invented source', () => {
  const { sandbox, body } = createAppHarness();
  sandbox.openDuaDetails('sleeping');
  assert.match(body.lastChild.innerHTML, /dir="rtl" lang="ar"/);
  assert.match(body.lastChild.innerHTML, /In Your name, O Allah, I die and I live\./);
  assert.match(body.lastChild.innerHTML, /Source details are not available/);
});

test('Dua saves persist per profile and render in the Saved screen', async () => {
  const { sandbox, app, savedContent, storage } = createAppHarness();
  sandbox.toggleSaved('dua', 'sleeping', "Du'a Before Sleeping");
  assert.ok(storage.has('tadabbur_saved_41'));

  vm.runInContext('_currentUser = { id: 42, role: "user" };', sandbox);
  assert.equal(sandbox.getSaved().length, 0);
  vm.runInContext('_currentUser = { id: 41, role: "user" };', sandbox);
  await sandbox.renderSaved(app);
  assert.match(savedContent.innerHTML, /SAVED DU\'AS/);
  assert.match(savedContent.innerHTML, /Du\'a Before Sleeping/);
});

test('Daily Dua selection is stable during repeated reads on the same date', () => {
  const { sandbox } = createAppHarness();
  const first = sandbox.todayDua().id;
  const second = sandbox.todayDua().id;
  assert.equal(first, second);
});
