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
  const listeners = {};
  const duaSearch = { value: '', addEventListener(type, fn) { listeners[`search:${type}`] = fn; } };
  const duaViewBody = { innerHTML: '', querySelector: () => null };
  const duaContent = {
    innerHTML: '',
    querySelector: selector => selector === '#dua-search' ? duaSearch : selector === '#dua-view-body' ? duaViewBody : null,
  };
  const savedContent = { innerHTML: '' };
  const settingsContent = { innerHTML: '' };
  const app = {
    innerHTML: '',
    querySelector(selector) {
      if (selector === '#duas-content') return duaContent;
      if (selector === '#dua-view-body') return duaViewBody;
      if (selector === '#saved-content') return savedContent;
      if (selector === '#settings-content') return settingsContent;
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
    navigator: {},     fetch: async url => {
      const parsed = new URL(url, 'https://test.invalid');
      if (parsed.pathname.endsWith('/duas/daily')) {
        return { ok: true, status: 200, headers: { get: () => 'application/json' }, json: async () => ({
          id: 'waking', title: "Du'a Upon Waking Up", category: 'Morning', arabic: 'عربي', translation: 'Translation',
          source: 'OpenDua',
        }) };
      }
      if (parsed.pathname.endsWith('/duas')) {
        const search = parsed.searchParams.get('search');
        const category = parsed.searchParams.get('category');
        const items = search
          ? search === 'resurrection'
          ? [{ id: 'waking', title: "Du'a Upon Waking Up", category: 'Morning', source_reference: 'resurrection', source: 'OpenDua' }]
          : []
          : category === 'More'
            ? [{ id: 'eating', title: "Du'a Before Eating", category: 'Food', source_reference: '2', source: 'OpenDua' }]
            : [{ id: 'waking', title: "Du'a Upon Waking Up", category: 'Morning', source_reference: '1', source: 'OpenDua' },
              { id: 'eating', title: "Du'a Before Eating", category: 'Food', source_reference: '2', source: 'OpenDua' }];
        return { ok: true, status: 200, headers: { get: () => 'application/json' }, json: async () => ({
          items, total: items.length, page: 1, limit: 20, has_more: false,
        }) };
      }
      throw new Error(`unexpected network request: ${url}`);
    },
    setTimeout, clearTimeout, URL, File: class {},
  };
  vm.createContext(sandbox);
  const source = fs.readFileSync(path.join(__dirname, '../app/static/js/app.js'), 'utf8');
  vm.runInContext(source, sandbox, { filename: 'app.js' });
  vm.runInContext('_currentUser = { id: 41, role: "user" }; todayDua = () => DUAS[0];', sandbox);
  return { sandbox, app, duaContent, duaViewBody, savedContent, settingsContent, body, storage };
}

test('Dua search matches English translation and provides a no-results state', async () => {
  const { sandbox, app, duaContent, duaViewBody } = createAppHarness();
  vm.runInContext('_duaSearch = "resurrection";', sandbox);
  await sandbox.renderDuas(app);
  assert.match(duaViewBody.innerHTML, /Du\'a Upon Waking Up/);
  assert.match(duaViewBody.innerHTML, /SEARCH RESULTS/);
  assert.doesNotMatch(duaContent.innerHTML, /DU'A OF THE DAY/);

  vm.runInContext('_duaSearch = "no matching phrase";', sandbox);
  await sandbox.renderDuas(app);
  assert.match(duaViewBody.innerHTML, /No Du’as found for/);
});

test('Dua search failures show an error state and pagination requests the next page', async () => {
  const { sandbox, app, duaViewBody } = createAppHarness();
  sandbox.fetch = async url => {
    const parsed = new URL(url, 'https://test.invalid');
    if (parsed.pathname.endsWith('/duas')) {
      const page = parsed.searchParams.get('page');
      return { ok: true, status: 200, headers: { get: () => 'application/json' }, json: async () => ({
        items: [{ id: `entry-${page}`, title: `Result ${page}`, category: 'General' }],
        total: 2, page: Number(page), limit: 1, has_more: page === '1',
      }) };
    }
    throw new Error('unexpected network request');
  };
  vm.runInContext('_duaSearch = "mos";', sandbox);
  await sandbox.renderDuas(app);
  assert.match(duaViewBody.innerHTML, /Result 1/);
  await sandbox.loadDuaSearch(app, 1, 'mos', 2);
  assert.match(duaViewBody.innerHTML, /Result 1/);
  assert.match(duaViewBody.innerHTML, /Result 2/);

  sandbox.fetch = async () => { throw new Error('provider unavailable'); };
  vm.runInContext('_duaSearch = "broken";', sandbox);
  await sandbox.renderDuas(app);
  assert.match(duaViewBody.innerHTML, /Unable to search Du’as right now/);
  assert.match(duaViewBody.innerHTML, /dua-search-retry/);
});

test('Clearing Dua search restores the daily card and stale results are ignored', async () => {
  const { sandbox, app, duaContent, duaViewBody } = createAppHarness();
  vm.runInContext('_duaSearch = "resurrection";', sandbox);
  await sandbox.renderDuas(app);
  vm.runInContext('_duaSearch = "";', sandbox);
  await sandbox.renderDuas(app);
  assert.match(duaContent.innerHTML, /DUA OF THE DAY|DU'A OF THE DAY/);

  let resolveOld;
  let resolveNew;
  sandbox.fetch = url => new Promise(resolve => {
    const query = new URL(url, 'https://test.invalid').searchParams.get('search');
    if (query === 'old') resolveOld = resolve;
    else resolveNew = resolve;
  });
  const generation = vm.runInContext('_duaRenderGeneration', sandbox);
  vm.runInContext('_duaSearch = "old";', sandbox);
  const oldRequest = sandbox.loadDuaSearch(app, generation, 'old', 1);
  vm.runInContext('_duaSearch = "new";', sandbox);
  const newRequest = sandbox.loadDuaSearch(app, generation, 'new', 1);
  resolveNew({ ok: true, status: 200, headers: { get: () => 'application/json' }, json: async () => ({ items: [{ id: 'new', title: 'New result', category: 'General' }], total: 1, page: 1, limit: 20, has_more: false }) });
  await newRequest;
  resolveOld({ ok: true, status: 200, headers: { get: () => 'application/json' }, json: async () => ({ items: [{ id: 'old', title: 'Old result', category: 'General' }], total: 1, page: 1, limit: 20, has_more: false }) });
  await oldRequest;
  assert.match(duaViewBody.innerHTML, /New result/);
  assert.doesNotMatch(duaViewBody.innerHTML, /Old result/);
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

test('reminder settings expose an editable time and explain browser-open delivery', async () => {
  const { sandbox, app, settingsContent } = createAppHarness();
  await sandbox.renderSettings(app);
  assert.match(settingsContent.innerHTML, /type="time"/);
  assert.match(settingsContent.innerHTML, /value="07:00"/);
  assert.match(settingsContent.innerHTML, /only while Tadabbur is open in this browser/);
});

test('reminder preferences are isolated by profile and daily notifications are sent once', () => {
  const { sandbox } = createAppHarness();
  const notifications = [];
  sandbox.Notification = class {
    static permission = 'granted';
    constructor(title, options) { this.title = title; this.options = options; notifications.push(this); }
  };
  sandbox.setSettings({ quranReminder: true, duaReminder: true, reminderTime: '07:00' });
  vm.runInContext('_currentUser = { id: 42, role: "user" };', sandbox);
  assert.equal(sandbox.getSettings().quranReminder, false);
  vm.runInContext('_currentUser = { id: 41, role: "user" };', sandbox);
  const reminderTime = new Date('2026-10-17T07:05:00');
  sandbox.checkDailyReminders(reminderTime);
  sandbox.checkDailyReminders(reminderTime);
  assert.equal(notifications.length, 2);
  assert.deepEqual(notifications.map(n => n.options.tag).sort(), [
    'tadabbur-dua-2026-10-17', 'tadabbur-quran-2026-10-17',
  ]);
});
