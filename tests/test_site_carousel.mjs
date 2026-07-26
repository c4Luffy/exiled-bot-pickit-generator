// Behaviour test for the landing-page carousel in docs/index.html.
//
// The hero carousel is the first thing on the site and it is driven entirely by
// one inline <script>. A single null lookup there throws during init and leaves
// a dead frame with no controls — the same failure mode app.html has, which is
// why that file has tools/check_ui.py and tests/test_ui_logic.mjs. This runs the
// REAL script (not a copy) against a small DOM stub and checks the two-game
// switch actually re-slices the slides, since PoE 2 has 14 tabs and PoE 1 has 8.
//
// Run:  node tests/test_site_carousel.mjs
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const html = fs.readFileSync(path.join(ROOT, "docs", "index.html"), "utf8");
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];

// ── the slides/switches the page really ships ────────────────────────────────
const slideData = [...html.matchAll(
  /<a class="carousel-slide[^"]*" data-game="(\w+)" data-title="([^"]+)" data-version="([^"]+)"/g)]
  .map(([, game, title, version]) => ({ game, title, version }));
const switchData = [...html.matchAll(/data-game-switch="(\w+)"/g)].map(m => m[1]);

assert.ok(slideData.length > 0, "no carousel slides found in docs/index.html");
assert.equal(switchData.length, 2, "expected exactly two game switches");

// ── minimal DOM ──────────────────────────────────────────────────────────────
class El {
  constructor(tag = "div", data = {}) {
    this.tagName = tag.toUpperCase();
    this.dataset = { ...data };
    this.attrs = {};
    this.children = [];
    this.classes = new Set();
    this._text = "";
    this.tabIndex = 0;
    this.handlers = {};
    const self = this;
    this.classList = {
      add: c => self.classes.add(c),
      remove: c => self.classes.delete(c),
      contains: c => self.classes.has(c),
      toggle: (c, on) => (on ? self.classes.add(c) : self.classes.delete(c)),
    };
  }
  // Real DOM semantics: assigning textContent replaces ALL children. The
  // carousel relies on `dotWrap.textContent=''` to drop the previous game's
  // dots, so a stub that kept them would hide a genuine leak.
  get textContent() { return this._text; }
  set textContent(v) { this._text = String(v); this.children = []; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return this.attrs[k] ?? null; }
  addEventListener(type, fn) { (this.handlers[type] ||= []).push(fn); }
  dispatch(type, ev = {}) { (this.handlers[type] || []).forEach(fn => fn(ev)); }
  click() { this.dispatch("click", {}); }
  focus() { this.focused = true; }
  appendChild(node) { this.children.push(node); return node; }
  contains() { return true; }
  matches(sel) {
    if (sel === ".carousel-slide") return this.classes.has("carousel-slide");
    const exact = sel.match(/^\[([\w-]+)="([^"]+)"\]$/);
    if (exact) return this.dataset[camel(exact[1])] === exact[2];
    const bare = sel.match(/^\[([\w-]+)\]$/);
    if (bare) return camel(bare[1]) in this.dataset;
    return false;
  }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
  querySelectorAll(sel) { return all(this).filter(n => n.matches(sel)); }
}
const camel = s => s.replace(/^data-/, "").replace(/-(\w)/g, (_, c) => c.toUpperCase());
const all = root => root.children.flatMap(c => [c, ...all(c)]);

const carousel = new El("figure", { carousel: "" });
const viewport = carousel.appendChild(new El("div"));
for (const s of slideData) {
  const a = viewport.appendChild(new El("a", { game: s.game, title: s.title, version: s.version }));
  a.classes.add("carousel-slide");
}
for (const g of switchData) carousel.appendChild(new El("button", { gameSwitch: g }));
const dotWrap = carousel.appendChild(new El("div", { carouselDots: "" }));
const titleEl = carousel.appendChild(new El("span", { carouselTitle: "" }));
const gameEl = carousel.appendChild(new El("span", { carouselGame: "" }));
const versionEl = carousel.appendChild(new El("span", { carouselVersion: "" }));
const countEl = carousel.appendChild(new El("span", { carouselCount: "" }));
const noteEl = carousel.appendChild(new El("span", { carouselNote: "" }));
carousel.appendChild(new El("button", { carouselPrev: "" }));
const nextBtn = carousel.appendChild(new El("button", { carouselNext: "" }));
carousel.appendChild(new El("button", { carouselToggle: "" }));

const document_ = {
  hidden: false,
  querySelector: sel => (sel === "[data-carousel]" ? carousel : null),
  createElement: tag => new El(tag),
  addEventListener() {},
};
const timers = [];
const sandbox = {
  document: document_,
  window: {
    setTimeout: (fn, ms) => timers.push([fn, ms]),      // never auto-advance here
    clearTimeout: () => {},
  },
  console,
};
sandbox.window.document = document_;

// ── run the page's own script ────────────────────────────────────────────────
vm.createContext(sandbox);
vm.runInContext(script, sandbox, { timeout: 5000 });

const dots = () => dotWrap.children.length;
const poe2 = slideData.filter(s => s.game === "poe2").length;
const poe1 = slideData.filter(s => s.game === "poe1").length;

// initial state: PoE 2, first slide
assert.equal(dots(), poe2, `expected ${poe2} dots for PoE 2, got ${dots()}`);
assert.equal(countEl.textContent, `1 of ${poe2}`);
assert.equal(gameEl.textContent, "Path of Exile 2");
assert.equal(noteEl.textContent, `All ${poe2} Path of Exile 2 tabs`);
assert.equal(titleEl.textContent, slideData.find(s => s.game === "poe2").title);
assert.match(versionEl.textContent, /^v\d+\.\d+\.\d+$/);

// advancing stays inside the active game
nextBtn.click();
assert.equal(countEl.textContent, `2 of ${poe2}`);

// switching games re-slices slides, dots and the note
carousel.querySelector('[data-game-switch="poe1"]').click();
assert.equal(dots(), poe1, `expected ${poe1} dots for PoE 1, got ${dots()}`);
assert.equal(countEl.textContent, `1 of ${poe1}`);
assert.equal(gameEl.textContent, "Path of Exile 1");
assert.equal(noteEl.textContent, `All ${poe1} Path of Exile 1 tabs`);

// exactly one slide is visible, and it belongs to the selected game
const active = carousel.querySelectorAll(".carousel-slide").filter(s => s.classes.has("is-active"));
assert.equal(active.length, 1, "exactly one slide must be active");
assert.equal(active[0].dataset.game, "poe1");

// and back again
carousel.querySelector('[data-game-switch="poe2"]').click();
assert.equal(dots(), poe2);
assert.equal(countEl.textContent, `1 of ${poe2}`);

console.log(`site carousel: OK (${poe2} PoE 2 + ${poe1} PoE 1 slides, switch re-slices both ways)`);
