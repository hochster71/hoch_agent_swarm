// engine/constants.js
//
// HFF — Invoice Aging Snapshot engine constants. Deterministic tables only.
// GUARDRAIL: organizational tooling ONLY. No financial/collections advice anywhere.

'use strict';

// The non-advice banner that MUST appear on every rendered artifact.
const DISCLAIMER =
  'Organizational summary of your own accounts-receivable data. ' +
  'Not financial, collections, or legal advice. ' +
  'It shows which invoices are outstanding and how old they are, with labeled inputs; ' +
  'it does not tell you what to do, whom to pursue, or how. Verify all figures against your records.';

// Aging buckets, measured by days past the invoice DUE date (as of the report date).
// A bucket matches when: lowerInclusive <= daysPastDue <= upperInclusive.
// "Current" means not yet due (daysPastDue <= 0).
const AGING_BUCKETS = [
  { key: 'current', label: 'Current (not due)', lower: -Infinity, upper: 0 },
  { key: 'd1_30', label: '1–30 days', lower: 1, upper: 30 },
  { key: 'd31_60', label: '31–60 days', lower: 31, upper: 60 },
  { key: 'd61_90', label: '61–90 days', lower: 61, upper: 90 },
  { key: 'd90_plus', label: '90+ days', lower: 91, upper: Infinity },
];

// A row is treated as OUTSTANDING (owed) when its balance is > this epsilon.
const PAID_EPSILON = 0.005;

module.exports = { DISCLAIMER, AGING_BUCKETS, PAID_EPSILON };
