const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const mp4Bytes = Uint8Array.from([
  0, 0, 0, 24, 0x66, 0x74, 0x79, 0x70, 0x69, 0x73, 0x6f, 0x6d,
  0, 0, 0, 0, 0x69, 0x73, 0x6f, 0x6d, 0, 0, 0, 8,
]);

class TestFile extends Blob {
  constructor(parts, name, options = {}) {
    super(parts, options);
    this.name = name;
    this.lastModified = options.lastModified || 0;
  }
}

function createHarness({ fetchImpl, navigator = {} } = {}) {
  const fetchCalls = [];
  const calls = [];
  const elements = [];
  const status = {
    textContent: '', classList: { toggle() {} },
    setAttribute() {},
  };
  const host = {
    querySelector(selector) { return selector === '.video-share-status' ? status : null; },
    appendChild() {},
  };
  const button = {
    disabled: false,
    textContent: 'Share video',
    dataset: {},
    closest(selector) { return selector === '.video-actions' ? host : null; },
    parentElement: host,
  };
  const document = {
    createElement(tag) {
      const element = { tagName: tag, setAttribute() {}, clicked: false, click() { this.clicked = true; }, classList: { toggle() {} } };
      elements.push(element);
      return element;
    },
  };
  const sandbox = {
    Blob, File: TestFile, Date, URL,
    console: { error() {} }, document, navigator,
    window: { location: { origin: 'https://tadabbur.test' }, addEventListener() {} },
    setTimeout: callback => { callback(); return 0; }, clearTimeout() {},
    fetch: async (...args) => {
      fetchCalls.push(args);
      if (fetchImpl) return fetchImpl(...args);
      calls.push(args[0]);
      return { ok: true, status: 201, headers: { get: () => 'application/json' }, json: async () => ({}) };
    },
  };
  vm.createContext(sandbox);
  const source = fs.readFileSync(path.join(__dirname, '../app/static/js/app.js'), 'utf8');
  vm.runInContext(source, sandbox, { filename: 'app.js' });
  return { sandbox, button, status, fetchCalls, calls, elements };
}

function videoResponse({ status = 200, contentType = 'video/mp4', bytes = mp4Bytes } = {}) {
  let delivered = false;
  return {
    ok: status >= 200 && status < 300,
    status,
    redirected: false,
    headers: { get: name => name.toLowerCase() === 'content-type' ? contentType : name.toLowerCase() === 'content-length' ? String(bytes.byteLength) : null },
    body: {
      getReader: () => ({
        async read() {
          if (delivered) return { done: true };
          delivered = true;
          return { done: false, value: bytes };
        },
        async cancel() {},
      }),
    },
  };
}

test('valid MP4 is prepared as a video/mp4 File and requires a second tap to share', async () => {
  let sharePayload;
  let shareCalls = 0;
  const h = createHarness({
    fetchImpl: async () => videoResponse(),
    navigator: {
      canShare: ({ files }) => files.length === 1 && files[0].type === 'video/mp4',
      share(payload) { shareCalls += 1; sharePayload = payload; return Promise.resolve(); },
    },
  });

  await h.sandbox.shareVideoFile(12, 'A Reminder', h.button);
  assert.equal(shareCalls, 0, 'preparation must not auto-open the share sheet');
  assert.equal(h.button.textContent, 'Share video now');
  assert.match(h.status.textContent, /Video ready/);

  const sharePromise = h.sandbox.shareVideoFile(12, 'A Reminder', h.button);
  assert.equal(shareCalls, 1, 'share is invoked synchronously on the second tap');
  assert.deepEqual(Object.keys(sharePayload), ['files']);
  assert.equal(sharePayload.files[0].name, 'A_Reminder.mp4');
  assert.equal(sharePayload.files[0].type, 'video/mp4');
  assert.equal(await sharePayload.files[0].slice(0, 12).text(), String.fromCharCode(...mp4Bytes.slice(0, 12)));
  await sharePromise;
  assert.deepEqual(h.fetchCalls.map(call => call[0]), ['/api/v1/videos/12/stream', '/api/v1/videos/12/share']);
});

test('HTTP, non-video, and malformed MP4 responses fail visibly without invoking native share', async t => {
  const notAnMp4 = Uint8Array.from(Buffer.from('<html>error response</html>'));
  for (const response of [
    videoResponse({ status: 502 }),
    videoResponse({ contentType: 'text/html' }),
    videoResponse({ bytes: notAnMp4 }),
  ]) {
    await t.test(`rejects HTTP ${response.status} ${response.headers.get('content-type')}`, async () => {
      let shares = 0;
      const h = createHarness({ fetchImpl: async () => response, navigator: { share() { shares += 1; } } });
      await h.sandbox.shareVideoFile(4, 'Reminder', h.button);
      assert.equal(shares, 0);
      assert.match(h.status.textContent, /HTTP 502|did not return an MP4|not a valid MP4/);
      assert.equal(h.button.disabled, false);
    });
  }
});

test('NotAllowedError is recoverable and never opens a link fallback', async () => {
  let opened = false;
  const h = createHarness({ navigator: {
    canShare: () => true,
    share: () => Promise.reject(Object.assign(new Error('activation expired'), { name: 'NotAllowedError' })),
  } });
  h.sandbox.window.open = () => { opened = true; };
  vm.runInContext('_videoCache.set(8, { file: new File([new Blob(["valid video"])], "cached.mp4", { type: "video/mp4" }), preparedAt: Date.now() });', h.sandbox);
  await h.sandbox.shareVideoFile(8, 'Reminder', h.button);
  assert.equal(opened, false);
  assert.equal(h.fetchCalls.length, 0);
  assert.match(h.status.textContent, /Tap “Share video now” to try again/);
});

test('cancelling native share does not record share or posted activity', async () => {
  const h = createHarness({ navigator: {
    canShare: () => true,
    share: () => Promise.reject(Object.assign(new Error('cancelled'), { name: 'AbortError' })),
  } });
  vm.runInContext('_videoCache.set(9, { file: new File([new Blob(["valid video"])], "cached.mp4", { type: "video/mp4" }), preparedAt: Date.now() });', h.sandbox);
  await h.sandbox.shareVideoFile(9, 'Reminder', h.button);
  assert.equal(h.fetchCalls.length, 0);
  assert.match(h.status.textContent, /Share cancelled/);
});

test('unsupported file sharing offers the actual MP4 download alternative', async () => {
  const h = createHarness({ fetchImpl: async () => videoResponse(), navigator: {} });
  h.sandbox.URL = { createObjectURL: () => 'blob:prepared-video', revokeObjectURL() {} };
  await h.sandbox.shareVideoFile(14, 'Reminder', h.button);
  assert.equal(h.button.textContent, 'Download video');
  assert.equal(h.button.dataset.shareDownload, 'true');
  assert.match(h.status.textContent, /cannot share video files.*Download video/s);
  h.sandbox.shareVideoFile(14, 'Reminder', h.button);
  const download = h.elements.find(element => element.tagName === 'a');
  assert.equal(download.href, 'blob:prepared-video');
  assert.equal(download.download, 'Reminder.mp4');
  assert.equal(download.clicked, true);
});
