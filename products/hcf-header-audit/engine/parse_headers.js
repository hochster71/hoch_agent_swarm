// engine/parse_headers.js
//
// RFC 5322 header-block parsing (offline, deterministic).
//
// Handles: CRLF and LF line endings, a leading UTF-8 BOM, folded (continued)
// header lines, duplicate header names (ORDER IS PRESERVED — the Received chain
// depends on it), the blank line that ends the header block, and RFC 2047
// encoded-words in display text.
//
// Anything that is not a valid header line is recorded in `malformed` with its
// line number rather than silently dropped.
'use strict';

const { MAX_INPUT_BYTES } = require('./constants');

class HeaderParseError extends Error {
  constructor(message, code) {
    super(message);
    this.name = 'HeaderParseError';
    this.code = code || 'HEADER_PARSE_FAILED';
  }
}

function validateInput(text) {
  if (typeof text !== 'string' || text.trim() === '') {
    throw new HeaderParseError('No headers provided. Paste the raw header block of the email.', 'EMPTY_INPUT');
  }
  if (Buffer.byteLength(text, 'utf8') > MAX_INPUT_BYTES) {
    throw new HeaderParseError(
      `Header block is larger than the ${Math.floor(MAX_INPUT_BYTES / 1024)} KB limit.`,
      'INPUT_TOO_LARGE'
    );
  }
  return true;
}

// RFC 2047 encoded-word decoding, limited to the two defined encodings.
// Unknown charsets are decoded as latin1/utf8 best-effort; failures return the
// original token untouched (never throws — decoding is cosmetic).
function decodeEncodedWords(value) {
  if (!value || value.indexOf('=?') === -1) return value;
  return value.replace(/=\?([^?]+)\?([BbQq])\?([^?]*)\?=/g, (match, charset, enc, payload) => {
    try {
      const cs = String(charset).toLowerCase().split('*')[0];
      const nodeCharset = /utf-?8/.test(cs) ? 'utf8' : (/iso-8859-1|latin1|windows-1252|us-ascii|ascii/.test(cs) ? 'latin1' : 'utf8');
      if (enc.toUpperCase() === 'B') {
        return Buffer.from(payload, 'base64').toString(nodeCharset);
      }
      const q = payload
        .replace(/_/g, ' ')
        .replace(/=([0-9A-Fa-f]{2})/g, (m, hex) => String.fromCharCode(parseInt(hex, 16)));
      return Buffer.from(q, 'binary').toString(nodeCharset);
    } catch (e) {
      return match;
    }
  });
}

// Returns { headers: [{name, nameLower, value, line}], malformed: [{line, text, reason}], truncatedAtBody }
function parseHeaderBlock(text) {
  validateInput(text);

  let src = String(text);
  if (src.charCodeAt(0) === 0xfeff) src = src.slice(1); // strip BOM
  const lines = src.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');

  const headers = [];
  const malformed = [];
  let current = null;
  let truncatedAtBody = false;

  const flush = () => {
    if (!current) return;
    const value = decodeEncodedWords(current.rawValue.replace(/\s+/g, ' ').trim());
    headers.push({
      name: current.name,
      nameLower: current.name.toLowerCase(),
      value,
      raw: current.rawValue.trim(),
      line: current.line,
    });
    current = null;
  };

  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];
    const lineNo = i + 1;

    // A blank line terminates the header block; everything after is body.
    if (line.trim() === '') {
      // Leading blank lines before any header are ignored, not treated as body.
      if (headers.length === 0 && !current) continue;
      flush();
      // Only mark truncation if there is actual content after the blank line.
      for (let j = i + 1; j < lines.length; j += 1) {
        if (lines[j].trim() !== '') { truncatedAtBody = true; break; }
      }
      break;
    }

    // Folded continuation: line begins with SP or HTAB.
    if (/^[ \t]/.test(line)) {
      if (current) {
        current.rawValue += ' ' + line.trim();
      } else {
        malformed.push({ line: lineNo, text: line.slice(0, 200), reason: 'continuation line with no preceding header' });
      }
      continue;
    }

    // Some clients prefix the block with a Unix "From " envelope line.
    if (/^From /.test(line) && headers.length === 0 && !current) continue;

    const m = /^([!-9;-~]+)[ \t]*:(.*)$/.exec(line);
    if (!m) {
      malformed.push({ line: lineNo, text: line.slice(0, 200), reason: 'not a valid "Name: value" header line' });
      continue;
    }
    flush();
    current = { name: m[1], rawValue: m[2], line: lineNo };
  }
  flush();

  if (headers.length === 0) {
    throw new HeaderParseError(
      'No readable headers found. Paste the raw header block (e.g. Gmail: "Show original"; Outlook: "View message source").',
      'NO_HEADERS'
    );
  }

  return { headers, malformed, truncatedAtBody };
}

// All values for a header name, in the order they appeared.
function getAll(headers, name) {
  const n = String(name).toLowerCase();
  return headers.filter((h) => h.nameLower === n).map((h) => h.value);
}

// The FIRST occurrence of a header (topmost = most recently added by the
// receiving infrastructure), or null.
function getOne(headers, name) {
  const all = getAll(headers, name);
  return all.length ? all[0] : null;
}

module.exports = {
  parseHeaderBlock,
  getAll,
  getOne,
  decodeEncodedWords,
  validateInput,
  HeaderParseError,
};
