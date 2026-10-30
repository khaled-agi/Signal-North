"use strict";
const assert = require("node:assert/strict");
const { sections, select, sourceUrl } = require("../supporting_intelligence.js");
const now = Date.parse("2026-10-30T18:00:00Z");
const article = (id, title, date = "2026-10-30T12:00:00Z", extras = {}) =>
  ({ id, title, url: "https://example.org/" + id, published_at: date, ...extras });

const customer = article("c", "Toronto customer loses $25,000 in bank impersonation scam");
const verdict = article("v", "Toronto crypto fraud suspect found guilty in court");
const fine = article("e", "FINTRAC fines bank $2 million for money laundering violations");
const rules = article("r", "FCAC publishes proposed new consumer protection guidance");
const phishing = article("t", "Police warn about widespread phishing scam in Ontario");
const stale = article("old", "Customer loses savings in Canada fraud", "2025-01-01T12:00:00Z");
const invalid = article("bad", "Victim scammed in Ontario", "2026-10-30T09:00:00Z", { url: "javascript:alert(1)" });
const items = [stale, customer, fine, rules, phishing, invalid, verdict];

assert.deepEqual(sections(customer), ["incidents", "fraud"]);
assert.deepEqual(sections(fine), ["enforcement", "regulatory"]);
assert.deepEqual(sections(rules), ["regulatory"]);
assert.deepEqual(sections(phishing), ["fraud"]);
assert.ok(sections(verdict).includes("incidents"));
assert.ok(!sections(fine).includes("incidents"), "penalties must not be presented as victim cases");
assert.deepEqual(select(items, "enforcement", 4, now).map(x => x.id), ["e"]);
assert.deepEqual(select(items, "regulatory", 4, now).map(x => x.id), ["e", "r"]);
assert.deepEqual(select(items, "incidents", 4, now).map(x => x.id), ["c", "v"]);
assert.deepEqual(select(items, "fraud", 4, now).map(x => x.id), ["c", "t", "v"]);
assert.equal(sourceUrl(invalid), "");
assert.equal(select([stale], "incidents", 4, now).length, 0);
assert.equal(select([article("future", customer.title, "2030-01-01")], "incidents", 4, now).length, 0);
assert.equal(select([article("a", customer.title, undefined, { headline_variations: [{title:"Other phrasing"}] })], "incidents", 4, now).length, 1);
assert.deepEqual(select([customer, customer], "incidents", 4, now).map(x => x.id), ["c"]);
console.log("Supporting intelligence routing tests passed");
