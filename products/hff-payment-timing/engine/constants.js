// engine/constants.js
//
// HFF — Getting-Paid Speed Report. Shared constants.
'use strict';

const PRODUCT_NAME = 'Getting-Paid Speed Report';
const PRODUCT_SLUG = 'hff-payment-timing';

// Mandatory disclaimer, rendered on every artifact (XLSX Summary, PDF, JSON).
// Fragments of this wording are allowlisted in engine/advice_linter.js so the
// banner can never trip its own guardrail.
const DISCLAIMER =
  'This report is organizational tooling only. It describes the invoices recorded in the file you ' +
  'uploaded and the payment timing those invoices arithmetically produce, exactly as the file states ' +
  'them. It is not financial, tax, legal, or collections advice, it does not tell you which clients to ' +
  'chase or how to collect, and it does not judge any client. Where the file gives no due date or ' +
  'terms, on-time is measured against an assumed net-30 and that assumption is disclosed. Verify every ' +
  'line against your own records before acting.';

// Corporate suffixes stripped when grouping two spellings of the same client.
// This is STRING normalization only — there is no client database behind it,
// and every merge is disclosed in the report.
const CLIENT_SUFFIXES = [
  'INCORPORATED', 'INC', 'LLC', 'L L C', 'LLP', 'LP', 'LTD', 'LIMITED', 'CORP',
  'CORPORATION', 'COMPANY', 'CO', 'PLC', 'GMBH', 'PTY', 'SA', 'NV', 'BV', 'AB', 'AS',
];

// A single invoice above this absolute amount is flagged, not counted.
const MAX_LINE_AMOUNT = 100000000; // $100M

// When the file gives neither a due-date column nor parseable terms for a row,
// on-time is measured against this many days after the issue date, and the
// assumption is disclosed prominently.
const DEFAULT_NET_DAYS = 30;

module.exports = {
  PRODUCT_NAME,
  PRODUCT_SLUG,
  DISCLAIMER,
  CLIENT_SUFFIXES,
  MAX_LINE_AMOUNT,
  DEFAULT_NET_DAYS,
};
