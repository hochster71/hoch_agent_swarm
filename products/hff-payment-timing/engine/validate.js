// engine/validate.js
//
// HFF — Getting-Paid Speed Report — input validation gate.
// Fails CLOSED with machine-readable codes so the API can map them to honest
// HTTP statuses instead of returning a half-built report.
'use strict';

const MAX_BYTES = 8 * 1024 * 1024; // 8 MB
const MAX_ROWS = 50000;

function validateCsvInput(text) {
  if (typeof text !== 'string') {
    const e = new Error('Expected the CSV file contents as text.'); e.code = 'BAD_INPUT_TYPE'; throw e;
  }
  if (text.trim() === '') {
    const e = new Error('The uploaded file is empty.'); e.code = 'EMPTY_FILE'; throw e;
  }
  const bytes = Buffer.byteLength(text, 'utf8');
  if (bytes > MAX_BYTES) {
    const e = new Error(`File is ${(bytes / 1048576).toFixed(1)} MB; the limit is ${MAX_BYTES / 1048576} MB.`);
    e.code = 'FILE_TOO_LARGE'; throw e;
  }
  const lines = text.split('\n').length;
  if (lines > MAX_ROWS) {
    const e = new Error(`File has about ${lines} lines; the limit is ${MAX_ROWS}.`);
    e.code = 'TOO_MANY_ROWS'; throw e;
  }
  return true;
}

module.exports = { validateCsvInput, MAX_BYTES, MAX_ROWS };
