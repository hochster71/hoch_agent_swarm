// engine/constants.js
//
// HFF — Vendor Spend Rollup. Shared constants.
'use strict';

const PRODUCT_NAME = 'Vendor Spend Rollup';
const PRODUCT_SLUG = 'hff-vendor-spend';

// Mandatory disclaimer, rendered on every artifact (XLSX Summary, PDF, JSON).
// Fragments of this wording are allowlisted in engine/advice_linter.js so the
// banner can never trip its own guardrail.
const DISCLAIMER =
  'This report is organizational tooling only. It describes the vendor payments recorded in the ' +
  'file you uploaded, exactly as that file states them. It is not financial, tax, or legal ' +
  'advice, it does not tell you which vendors to cut, keep, or renegotiate, and it does not ' +
  'judge whether any amount is reasonable. Verify every line against your own records before ' +
  'acting.';

// Corporate suffixes stripped when grouping two spellings of the same vendor.
const VENDOR_SUFFIXES = [
  'INCORPORATED', 'INC', 'LLC', 'L L C', 'LLP', 'LP', 'LTD', 'LIMITED', 'CORP',
  'CORPORATION', 'COMPANY', 'CO', 'PLC', 'GMBH', 'PTY', 'SA', 'NV', 'BV', 'AB', 'AS',
];

// Payment-processor noise commonly prefixed onto a vendor string by bank exports.
// Stripped only from the GROUPING KEY — the label always shows what the file said.
const PROCESSOR_PREFIXES = [
  'SQ ', 'SQUARE ', 'TST ', 'PAYPAL ', 'PP ', 'IC ', 'POS ', 'ACH ', 'EFT ',
  'DEBIT CARD PURCHASE ', 'CARD PURCHASE ', 'RECURRING PAYMENT ', 'PURCHASE AUTHORIZED ON ',
];

// A single line item above this absolute amount is flagged, not counted.
const MAX_LINE_AMOUNT = 100000000; // $100M

// A vendor whose gap since its last payment exceeds this multiple of its OWN
// median gap is described as dormant relative to its own rhythm.
const DORMANCY_MULTIPLE = 2.5;

// Minimum payments a vendor needs before a median gap is meaningful.
const MIN_PAYMENTS_FOR_CADENCE = 3;

module.exports = {
  PRODUCT_NAME,
  PRODUCT_SLUG,
  DISCLAIMER,
  VENDOR_SUFFIXES,
  PROCESSOR_PREFIXES,
  MAX_LINE_AMOUNT,
  DORMANCY_MULTIPLE,
  MIN_PAYMENTS_FOR_CADENCE,
};
