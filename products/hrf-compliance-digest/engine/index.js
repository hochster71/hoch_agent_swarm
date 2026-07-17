// engine/index.js
//
// HRF — Compliance Change Digest — engine entry point.

'use strict';

const { generateDigest, DigestLintError } = require('./engine');
const { renderMarkdown } = require('./render');
const { lintDigest, summarize } = require('./linter');
const { DISCLAIMER } = require('./schemas');

// Convenience: produce a digest AND its rendered markdown in one call.
function buildDigest(request) {
  const digest = generateDigest(request);
  const markdown = renderMarkdown(digest);
  return { digest, markdown };
}

module.exports = { generateDigest, buildDigest, renderMarkdown, lintDigest, summarize, DigestLintError, DISCLAIMER };
