"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const { createController, HIDE_DELAY_MS } = require("./titlebar.js");

class Element extends EventTarget {
    constructor() {
        super();
        this.classes = new Set();
        this.classList = {
            add: value => this.classes.add(value),
            remove: value => this.classes.delete(value),
            contains: value => this.classes.has(value),
        };
        this.inert = true;
    }
}

function fixture() {
    const titlebar = new Element();
    const trigger = new Element();
    const pending = new Map();
    let timerId = 0;
    const timers = {
        setTimeout(callback, delay) {
            const id = ++timerId;
            pending.set(id, { callback, delay });
            return id;
        },
        clearTimeout(id) {
            pending.delete(id);
        },
    };
    createController(titlebar, trigger, timers);
    return { titlebar, trigger, pending };
}

test("shows only after entering the top-edge trigger", () => {
    const { titlebar, trigger, pending } = fixture();

    assert.equal(titlebar.classList.contains("is-visible"), false);
    trigger.dispatchEvent(new Event("mouseenter"));

    assert.equal(titlebar.classList.contains("is-visible"), true);
    assert.equal(titlebar.inert, false);
    assert.equal(pending.size, 0);
});

test("stays visible for five seconds after the pointer leaves", () => {
    const { titlebar, trigger, pending } = fixture();
    trigger.dispatchEvent(new Event("mouseenter"));
    titlebar.dispatchEvent(new Event("mouseleave"));

    const timer = [...pending.values()][0];
    assert.equal(timer.delay, HIDE_DELAY_MS);
    assert.equal(titlebar.classList.contains("is-visible"), true);

    timer.callback();
    assert.equal(titlebar.classList.contains("is-visible"), false);
    assert.equal(titlebar.inert, true);
});

test("entering the titlebar again cancels pending hiding", () => {
    const { titlebar, trigger, pending } = fixture();
    trigger.dispatchEvent(new Event("mouseenter"));
    titlebar.dispatchEvent(new Event("mouseleave"));
    titlebar.dispatchEvent(new Event("mouseenter"));

    assert.equal(pending.size, 0);
    assert.equal(titlebar.classList.contains("is-visible"), true);
});
