// engine/constants.js
//
// HFF — Runway engine constants. Deterministic tables only.
// GUARDRAIL: organizational tooling ONLY. No advice language anywhere.

'use strict';

// The non-advice banner that MUST appear on every rendered artifact (spec §Guardrail).
const DISCLAIMER =
  'Prepared for your accountant. Not financial or tax advice. ' +
  'This is an organizational worksheet that shows arithmetic with labeled inputs; ' +
  'it does not tell you what to do. Verify all figures with a qualified professional.';

// 2024 self-employment tax parameters (labeled, published IRS figures — used as arithmetic
// inputs the user's accountant can verify; NOT tax advice).
const SE = {
  NET_EARNINGS_FACTOR: 0.9235, // net profit is multiplied by this before SE tax
  SS_RATE: 0.124, // Social Security portion (12.4%)
  MEDICARE_RATE: 0.029, // Medicare portion (2.9%)
  SS_WAGE_BASE: 168600, // 2024 Social Security wage base cap for the 12.4% portion
};

// 2024 standard deduction by filing type (labeled input to the income-tax estimate).
const STANDARD_DEDUCTION = {
  single: 14600,
  married_joint: 29200,
  married_separate: 14600,
  head_of_household: 21900,
};

// 2024 federal ordinary-income brackets (single & married_joint shown; others fall back to single).
// Each entry: [upTo, rate]. Used to compute a simplified progressive income-tax estimate.
const BRACKETS = {
  single: [
    [11600, 0.1],
    [47150, 0.12],
    [100525, 0.22],
    [191950, 0.24],
    [243725, 0.32],
    [609350, 0.35],
    [Infinity, 0.37],
  ],
  married_joint: [
    [23200, 0.1],
    [94300, 0.12],
    [201050, 0.22],
    [383900, 0.24],
    [487450, 0.32],
    [731200, 0.35],
    [Infinity, 0.37],
  ],
};

// Deterministic keyword -> category map. First matching keyword wins (checked in order).
// Categories are ORGANIZATIONAL buckets, not tax determinations.
const CATEGORY_RULES = [
  { category: 'Contractors', keywords: ['upwork', 'fiverr', 'contractor', 'freelance', '1099', 'consult'] },
  { category: 'Software/SaaS', keywords: ['github', 'aws', 'google cloud', 'gcp', 'vercel', 'notion', 'slack', 'zoom', 'adobe', 'figma', 'openai', 'anthropic', 'saas', 'subscription', 'software', 'hosting', 'domain'] },
  { category: 'Advertising', keywords: ['facebook ads', 'google ads', 'meta ads', 'linkedin ads', 'advertis', 'marketing'] },
  { category: 'Meals', keywords: ['restaurant', 'coffee', 'cafe', 'starbucks', 'doordash', 'ubereats', 'grubhub', 'meal'] },
  { category: 'Travel', keywords: ['airline', 'delta', 'united air', 'american air', 'uber', 'lyft', 'hotel', 'airbnb', 'flight', 'travel'] },
  { category: 'Office', keywords: ['staples', 'office depot', 'amazon', 'supplies', 'wework', 'rent', 'office'] },
  { category: 'Utilities', keywords: ['comcast', 'verizon', 'at&t', 'internet', 'phone', 'electric', 'utility', 'utilities'] },
  { category: 'Bank Fees', keywords: ['fee', 'interest charge', 'service charge', 'overdraft'] },
  { category: 'Taxes', keywords: ['irs', 'franchise tax', 'estimated tax', 'tax payment'] },
  { category: 'Owner Draw', keywords: ['owner draw', 'transfer to', 'atm withdrawal', 'personal', 'venmo'] },
];

// Categories that are business-deductible for the estimated-tax worksheet's expense total.
// Owner Draw and Taxes are NOT operating expenses; income is handled separately.
const NON_EXPENSE_CATEGORIES = new Set(['Income', 'Owner Draw', 'Taxes', 'Uncategorized-Inflow']);

const INCOME_CATEGORY = 'Income';
const CONTRACTOR_CATEGORY = 'Contractors';
const UNCATEGORIZED_OUTFLOW = 'Uncategorized';
const UNCATEGORIZED_INFLOW = 'Uncategorized-Inflow';

// 1099-NEC candidate threshold (organizational flag, per the >$600 rule).
const THRESHOLD_1099 = 600;

module.exports = {
  DISCLAIMER,
  SE,
  STANDARD_DEDUCTION,
  BRACKETS,
  CATEGORY_RULES,
  NON_EXPENSE_CATEGORIES,
  INCOME_CATEGORY,
  CONTRACTOR_CATEGORY,
  UNCATEGORIZED_OUTFLOW,
  UNCATEGORIZED_INFLOW,
  THRESHOLD_1099,
};
