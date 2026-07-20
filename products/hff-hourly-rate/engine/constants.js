// engine/constants.js
//
// HFF — Effective Hourly Rate Report. Shared constants.
'use strict';

const PRODUCT_NAME = 'Effective Hourly Rate Report';
const PRODUCT_SLUG = 'hff-hourly-rate';

// Mandatory disclaimer, rendered on every artifact (XLSX Summary, PDF, JSON).
// Fragments of this wording are allowlisted in engine/advice_linter.js so the
// banner can never trip its own guardrail.
const DISCLAIMER =
  'This report is organizational tooling only. It describes the hours, billing figures and ' +
  'arithmetic rates observed in the file you uploaded, exactly as that file states them. It is ' +
  'not financial, tax, or legal advice, it does not tell you what to charge, and it does not ' +
  'tell you which clients or projects to keep or drop. Verify every line against your own ' +
  'records before acting.';

// Corporate suffixes stripped when grouping two spellings of the same client.
const CLIENT_SUFFIXES = [
  'INCORPORATED', 'INC', 'LLC', 'L L C', 'LLP', 'LP', 'LTD', 'LIMITED', 'CORP',
  'CORPORATION', 'COMPANY', 'CO', 'PLC', 'GMBH', 'PTY', 'SA', 'NV', 'BV', 'AB', 'AS',
];

// A single time entry longer than this many hours is flagged, not counted.
const MAX_ENTRY_HOURS = 24;

const WEEKDAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

module.exports = {
  PRODUCT_NAME,
  PRODUCT_SLUG,
  DISCLAIMER,
  CLIENT_SUFFIXES,
  MAX_ENTRY_HOURS,
  WEEKDAY_NAMES,
};
