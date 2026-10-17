const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

function makeVideo(id) {
  return {
    id, title: `Video ${id}`, description: null, duration_seconds: null,
    is_active: true, category_id: null,
  };
}

function createHarness() {
  const requests = [];
  const listeners = {};
  let contentHtml = '';
  const search = { addEventListener(type, fn) { listeners[`search:${type}`] = fn; } };
  const list = { html: '', insertAdjacentHTML(_position, html) { this.html += html; } };
  const pagination = { set outerHTML(value) { this.html = value; }, html: '' };
  const loadMore = {
    disabled: false, textContent: 'Load more videos',
    addEventListener(type, fn) { listeners[`load-more:${type}`] = fn; },
  };
  const content = {
    querySelector(selector) {
      if (selector === '#video-search') return search;
      if (selector === '#video-list') return list;
      if (selector === '#video-pagination') return pagination;
      if (selector === '#load-more-videos' && contentHtml.includes('id="load-more-videos"')) return loadMore;
      return null;
    },
  };
  Object.defineProperty(content, 'innerHTML', {
    get() { return contentHtml; },
    set(value) { contentHtml = value; list.html = value.match(/<div id="video-list">([\s\S]*?)<\/div>/)?.[1] || ''; },
  });
  const app = { innerHTML: '', querySelector: selector => selector === '#videos-content' ? content : null };
  const localStorage = { getItem() { return null; }, setItem() {} };
  const window = { location: { hash: '#/videos' }, addEventListener() {} };
  const sandbox = {
    console, document: { getElementById: id => id === 'app' ? app : null }, localStorage,
    window, navigator: {}, setTimeout, clearTimeout, URLSearchParams,
    fetch: async url => {
      requests.push(url);
      let payload;
      if (url.endsWith('/categories')) payload = [];
      else if (url.includes('/videos?')) {
        const skip = Number(new URL(url, 'https://test.invalid').searchParams.get('skip'));
        payload = { items: skip === 0 ? Array.from({ length: 100 }, (_, i) => makeVideo(i + 1)) : [makeVideo(101)], total: 101, skip, limit: 100 };
      } else throw new Error(`Unexpected request: ${url}`);
      return { ok: true, status: 200, headers: { get: () => 'application/json' }, json: async () => payload };
    },
  };
  vm.createContext(sandbox);
  const source = fs.readFileSync(path.join(__dirname, '../app/static/js/app.js'), 'utf8');
  vm.runInContext(source, sandbox, { filename: 'app.js' });
  vm.runInContext('_currentUser = { id: 41, role: "user" };', sandbox);
  return { sandbox, app, content, list, listeners, requests, loadMore };
}

test('video library loads results beyond the first 100 on request', async () => {
  const { sandbox, app, requests, loadMore, listeners, list } = createHarness();
  await sandbox.renderVideos(app);
  assert.equal(requests.filter(url => url.includes('/videos?')).length, 1);
  assert.match(app.innerHTML, /videos-content/);
  await listeners['load-more:click']({ currentTarget: loadMore });
  assert.ok(requests.some(url => url.includes('skip=100')));
  assert.match(list.html, /Video 101/);
});
