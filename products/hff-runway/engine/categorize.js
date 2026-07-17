// engine/categorize.js
//
// Stage 2: Deterministic, auditable, rules-based categorization.
// Keyword -> category map (constants.CATEGORY_RULES), user-overridable via
// profile.category_overrides (case-insensitive substring -> category).
// No black-box guessing: every categorization is traceable to a rule or an override.

'use strict';

const {
  CATEGORY_RULES,
  INCOME_CATEGORY,
  UNCATEGORIZED_OUTFLOW,
  UNCATEGORIZED_INFLOW,
} = require('./constants');

function categorizeOne(tx, overrides) {
  const desc = tx.description.toLowerCase();

  // 1) User overrides win (deterministic, auditable).
  for (const ov of overrides) {
    if (desc.includes(ov.match)) {
      return { category: ov.category, rule: `override:"${ov.match}"` };
    }
  }

  // 2) If the CSV already carried a category, respect it as a labeled input.
  if (tx.rawCategory) {
    return { category: tx.rawCategory, rule: 'from-csv' };
  }

  // 3) Inflows default to Income unless a keyword says otherwise.
  const isInflow = tx.amount > 0;

  // 4) Keyword rules (first match wins, in declared order).
  for (const rule of CATEGORY_RULES) {
    for (const kw of rule.keywords) {
      if (desc.includes(kw)) {
        return { category: rule.category, rule: `keyword:"${kw}"` };
      }
    }
  }

  if (isInflow) return { category: INCOME_CATEGORY, rule: 'default-inflow' };
  return { category: UNCATEGORIZED_OUTFLOW, rule: 'default-outflow' };
}

// categorize(transactions, profile) -> { categorized: [...], rollup: [...] }
// categorized: each tx with { category, rule }
// rollup: [{ category, inflow, outflow, net, count, pctOfOutflow }]
function categorize(transactions, profile) {
  const overrides = normalizeOverrides(profile && profile.category_overrides);

  const categorized = transactions.map((tx) => {
    const { category, rule } = categorizeOne(tx, overrides);
    // Normalize: an inflow landing in a plain outflow bucket "Uncategorized" is an inflow bucket.
    let cat = category;
    if (tx.amount > 0 && cat === UNCATEGORIZED_OUTFLOW) cat = UNCATEGORIZED_INFLOW;
    return Object.assign({}, tx, { category: cat, rule });
  });

  // Build rollup.
  const byCat = new Map();
  for (const tx of categorized) {
    if (!byCat.has(tx.category)) {
      byCat.set(tx.category, { category: tx.category, inflow: 0, outflow: 0, net: 0, count: 0 });
    }
    const b = byCat.get(tx.category);
    if (tx.amount >= 0) b.inflow += tx.amount;
    else b.outflow += -tx.amount; // store outflow as a positive magnitude
    b.net += tx.amount;
    b.count += 1;
  }

  const totalOutflow = Array.from(byCat.values()).reduce((s, b) => s + b.outflow, 0);

  const rollup = Array.from(byCat.values())
    .map((b) => ({
      category: b.category,
      inflow: round2(b.inflow),
      outflow: round2(b.outflow),
      net: round2(b.net),
      count: b.count,
      pctOfOutflow: totalOutflow > 0 ? round2((b.outflow / totalOutflow) * 100) : 0,
    }))
    .sort((a, b) => b.outflow - a.outflow || b.inflow - a.inflow);

  return { categorized, rollup, totalOutflow: round2(totalOutflow) };
}

function normalizeOverrides(raw) {
  if (!raw) return [];
  // Accept { "substring": "Category" } or [{ match, category }]
  if (Array.isArray(raw)) {
    return raw
      .filter((o) => o && o.match && o.category)
      .map((o) => ({ match: String(o.match).toLowerCase(), category: String(o.category) }));
  }
  return Object.keys(raw).map((k) => ({ match: k.toLowerCase(), category: String(raw[k]) }));
}

function round2(n) {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

module.exports = { categorize };
