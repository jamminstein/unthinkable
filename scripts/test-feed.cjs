const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const source = fs.readFileSync(path.join(__dirname, '../feed.js'), 'utf8');
const data = JSON.parse(fs.readFileSync(path.join(__dirname, '../posts.json'), 'utf8'));

// Exercise the shipped loader and renderer without a browser dependency.
class Element {
  constructor(tag) {
    this.tag = tag;
    this.children = [];
    this.events = {};
    this.style = { setProperty() {} };
  }
  append(...nodes) {
    for (const node of nodes) {
      this.children.push(...(node?.tag === 'fragment' ? node.children : [node]));
    }
  }
  replaceChildren(...nodes) {
    this.children = [];
    this.append(...nodes);
  }
  addEventListener(event, handler) { this.events[event] = handler; }
}

const success = () => ({ ok: true, json: async () => data });

async function load(responses) {
  const feed = new Element('main');
  const state = { calls: 0, reloads: 0, errors: [] };
  vm.runInNewContext(source, {
    document: {
      querySelector: () => feed,
      createElement: (tag) => new Element(tag),
      createDocumentFragment: () => new Element('fragment'),
    },
    fetch: async () => {
      const response = responses[state.calls++];
      if (response instanceof Error) throw response;
      if (!response) throw new Error('unexpected extra request');
      return response;
    },
    setTimeout: (callback) => setImmediate(callback),
    console: { error: (...args) => state.errors.push(args) },
    window: { location: { reload: () => { state.reloads += 1; } } },
  });
  for (let tick = 0; tick < 20 && !feed.children.length; tick += 1) {
    await new Promise(setImmediate);
  }
  assert.ok(feed.children.length, 'the loader must render posts or a recoverable error');
  return { feed, state };
}

test('renders the complete published feed on the first successful request', async () => {
  const { feed, state } = await load([success()]);
  assert.equal(feed.children.length, data.posts.length);
  assert.equal(feed.children[0].id, data.posts[0].id);
  assert.equal(feed.children.at(-1).id, data.posts.at(-1).id);
  assert.equal(state.calls, 1);
  assert.equal(state.errors.length, 0);
});

test('recovers after a network failure and a temporary HTTP error', async () => {
  const { feed, state } = await load([new TypeError('Failed to fetch'), { ok: false, status: 503 }, success()]);
  assert.equal(feed.children.length, data.posts.length);
  assert.equal(state.calls, 3);
  assert.equal(state.errors.length, 0);
});

test('retries an invalid response instead of leaving a blank feed', async () => {
  const { feed, state } = await load([{ ok: true, json: async () => ({}) }, success()]);
  assert.equal(feed.children.length, data.posts.length);
  assert.equal(state.calls, 2);
});

test('stops retrying after persistent failure and lets the visitor reload', async () => {
  const { feed, state } = await load(Array.from({ length: 3 }, () => new TypeError('offline')));
  assert.equal(state.calls, 3);
  assert.equal(state.errors.length, 1);
  const retry = feed.children[0].children.find((node) => node.tag === 'button');
  assert.equal(retry.textContent, 'try again');
  retry.events.click();
  assert.equal(state.reloads, 1);
});
