// engine/checks.js
//
// The heuristic checks. Every finding is phrased as an OBSERVATION about the
// text of the headers — never as a verdict, an instruction, or a claim about
// what the message "is". Severity is a weighting input to the score, not a
// judgement about the message.
'use strict';

const { parseAddressList, firstAddress, registrableDomain } = require('./addresses');
const { analyzeDomain } = require('./lookalike');
const { dkimAlignment } = require('./auth_results');

function f(id, title, severity, detail) {
  return { id, title, severity, detail };
}

// ---------------------------------------------------------------------------
// 1. Structural completeness
// ---------------------------------------------------------------------------
function checkStructure(ctx) {
  const out = [];
  const { headerIndex } = ctx;

  if (!headerIndex.from) {
    out.push(f('no_from', 'No From header present', 'medium',
      'The pasted block contains no From header. Either the paste is partial, or the message omitted it.'));
  }
  if (!headerIndex.date) {
    out.push(f('no_date', 'No Date header present', 'low',
      'The pasted block contains no Date header. Most legitimate mail carries one; partial pastes also lack it.'));
  }
  if (!headerIndex.messageId) {
    out.push(f('no_message_id', 'No Message-ID header present', 'low',
      'No Message-ID was found. Most mail systems add one; some bulk senders and partial pastes do not.'));
  }
  if (ctx.chain.count === 0) {
    out.push(f('no_received', 'No Received headers present', 'medium',
      'No Received hops were found, so the path the message took cannot be read at all. This is normal for a partial paste and unusual for a delivered message.'));
  }
  if (ctx.parsed.malformed.length > 0) {
    out.push(f('malformed_lines', `${ctx.parsed.malformed.length} line(s) could not be read as headers`, 'low',
      'Lines that do not parse as "Name: value" were skipped and are listed in the report. This usually means the paste included body text or was reflowed by an editor.'));
  }
  return out;
}

// ---------------------------------------------------------------------------
// 2. Authentication as REPORTED (never re-verified)
// ---------------------------------------------------------------------------
function checkAuth(ctx) {
  const out = [];
  const { auth, fromAddr } = ctx;

  if (!auth.present) {
    out.push(f('no_auth_results', 'No authentication results reported in the headers', 'medium',
      'No Authentication-Results or Received-SPF header was found, so this block records no SPF/DKIM/DMARC outcome at all. Absence is not itself a signal about the sender — many partial pastes drop it.'));
    return out;
  }

  const sev = { fail: 'high', softfail: 'medium', none: 'medium', neutral: 'low', permerror: 'low', temperror: 'low', policy: 'medium' };

  for (const method of ['spf', 'dkim', 'dmarc']) {
    const r = auth.byMethod[method];
    if (!r) {
      out.push(f(`auth_${method}_absent`, `${method.toUpperCase()} result not reported`, 'low',
        `The nearest Authentication-Results header records no ${method.toUpperCase()} outcome.`));
      continue;
    }
    const res = String(r.result || '').toLowerCase();
    if (res === 'pass') {
      out.push(f(`auth_${method}_pass`, `${method.toUpperCase()} reported as pass`, 'info',
        `A server reported ${method.toUpperCase()}=pass. This is only as trustworthy as the server that wrote the line, which this offline tool cannot identify or re-check.`));
    } else if (sev[res]) {
      out.push(f(`auth_${method}_${res}`, `${method.toUpperCase()} reported as ${res}`, sev[res],
        `A server reported ${method.toUpperCase()}=${res}. Reported failures also occur for benign reasons such as forwarding and mailing lists.`));
    } else {
      out.push(f(`auth_${method}_other`, `${method.toUpperCase()} reported as ${res || 'unrecognized'}`, 'low',
        `The recorded ${method.toUpperCase()} outcome ("${res}") is not one this tool recognizes.`));
    }
  }

  if (auth.authservIds.length > 1) {
    out.push(f('multiple_authserv', `Authentication results reported by ${auth.authservIds.length} different servers`, 'medium',
      `More than one system stamped an Authentication-Results header (${auth.authservIds.join(', ')}). Only the one added by your own receiving system carries weight; earlier ones can be forged or simply relayed.`));
  }

  const align = dkimAlignment(auth.byMethod, fromAddr && fromAddr.domain);
  if (align && !align.aligned) {
    out.push(f('dkim_not_aligned', 'DKIM signing domain differs from the From domain', 'medium',
      `The reported DKIM signature is from "${align.signingDomain}" while the From address is at "${align.fromDomain}". Legitimate senders using a mail vendor commonly sign with the vendor's domain, so this alone is not conclusive.`));
  }
  return out;
}

// ---------------------------------------------------------------------------
// 3. Sender identity alignment
// ---------------------------------------------------------------------------
function checkIdentity(ctx) {
  const out = [];
  const { fromAddr, headerIndex } = ctx;
  if (!fromAddr || !fromAddr.valid) {
    if (headerIndex.from) {
      out.push(f('from_unparseable', 'From header does not contain a readable address', 'medium',
        'The From header is present but no valid address could be read from it.'));
    }
    return out;
  }

  const fromReg = registrableDomain(fromAddr.domain);

  // Display name that itself contains a different email address or domain.
  const display = fromAddr.display || '';
  const displayAddr = /[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}/.exec(display);
  if (displayAddr) {
    const shown = displayAddr[0].toLowerCase();
    if (shown !== fromAddr.address.toLowerCase()) {
      out.push(f('display_name_address', 'Display name shows a different address than the actual sender', 'high',
        `The name shown to the reader contains "${shown}", but the message is actually from "${fromAddr.address}". Most mail clients show only the name.`));
    }
  } else if (display) {
    const dom = analyzeDomain(display.toLowerCase().replace(/\s+/g, ''));
    for (const b of dom.brandAdjacent) {
      out.push(f('display_name_brand', 'Display name references a brand that is not the sending domain', 'medium',
        `The display name "${display}" references ${b.brand}, but the message was sent from "${fromAddr.domain}".`));
      break;
    }
  }

  // Reply-To / Return-Path divergence.
  const replyTo = firstAddress(headerIndex.replyTo || '');
  if (replyTo && replyTo.valid && registrableDomain(replyTo.domain) !== fromReg) {
    out.push(f('replyto_mismatch', 'Reply-To points to a different domain than From', 'medium',
      `Replies would go to "${replyTo.address}" (${replyTo.domain}) rather than the From domain "${fromAddr.domain}". This is normal for ticketing systems and newsletters, and is also how reply-interception is set up.`));
  }

  const returnPath = firstAddress(headerIndex.returnPath || '');
  if (returnPath && returnPath.valid && registrableDomain(returnPath.domain) !== fromReg) {
    out.push(f('returnpath_mismatch', 'Return-Path domain differs from the From domain', 'low',
      `The bounce address is at "${returnPath.domain}" while From is at "${fromAddr.domain}". Bulk-mail vendors legitimately produce this pattern.`));
  }

  // Message-ID domain divergence.
  if (headerIndex.messageId) {
    const midDomain = (/@([^>\s]+)>?\s*$/.exec(headerIndex.messageId) || [null, ''])[1].toLowerCase().replace(/>$/, '');
    if (midDomain && registrableDomain(midDomain) !== fromReg) {
      out.push(f('messageid_mismatch', 'Message-ID domain differs from the From domain', 'low',
        `The Message-ID was generated at "${midDomain}" while From is at "${fromAddr.domain}". Vendor-sent mail routinely shows this.`));
    }
  }

  // Multiple From addresses.
  const fromList = parseAddressList(headerIndex.from || '');
  if (fromList.length > 1) {
    out.push(f('multiple_from', 'From header lists more than one address', 'medium',
      `The From header contains ${fromList.length} addresses. This is legal but rare, and clients differ in which one they display.`));
  }
  return out;
}

// ---------------------------------------------------------------------------
// 4. Lookalike sender domain
// ---------------------------------------------------------------------------
function checkLookalike(ctx) {
  const out = [];
  const { fromAddr } = ctx;
  if (!fromAddr || !fromAddr.valid || !fromAddr.domain) return out;

  const a = analyzeDomain(fromAddr.domain);

  if (a.punycode) {
    out.push(f('sender_punycode', 'Sender domain uses punycode (an internationalized domain)', 'high',
      `"${fromAddr.domain}" is an IDN encoded form. IDNs are legitimate worldwide, and they are also the standard way to register a domain that renders identically to a familiar one.`));
  } else if (a.nonAscii) {
    out.push(f('sender_non_ascii', 'Sender domain contains non-ASCII characters', 'high',
      `"${fromAddr.domain}" contains characters outside ASCII, which can render identically to a familiar domain.`));
  }
  for (const c of a.confusable) {
    out.push(f('sender_confusable', `Sender domain closely resembles ${c.target}`, 'high',
      `After folding visually similar characters, "${fromAddr.domain}" collapses onto "${c.target}" without being it. Brand list is a fixed set in this tool, not an exhaustive one.`));
    break;
  }
  for (const b of a.brandAdjacent) {
    out.push(f('sender_brand_adjacent', `Sender hostname contains "${b.brand.split('.')[0]}" but the domain is not ${b.brand}`, 'high',
      `The hostname "${fromAddr.domain}" includes a well-known brand name, but the registered domain (approximately "${registrableDomain(fromAddr.domain)}") belongs to someone else.`));
    break;
  }
  return out;
}

// ---------------------------------------------------------------------------
// 5. Routing / transport observations
// ---------------------------------------------------------------------------
function checkRouting(ctx) {
  const out = [];
  const { chain } = ctx;
  if (chain.count === 0) return out;

  if (chain.outOfOrder > 0) {
    out.push(f('hops_out_of_order', 'Received timestamps do not run forward in time', 'medium',
      `${chain.outOfOrder} hop(s) carry a timestamp earlier than the hop before them. Clock skew between mail servers produces this routinely; so does hand-edited header text.`));
  }
  if (chain.maxGapMs > 6 * 60 * 60 * 1000 && chain.maxGapBetween) {
    const hours = (chain.maxGapMs / 3600000).toFixed(1);
    out.push(f('hops_large_gap', `A ${hours}-hour gap sits between two hops`, 'low',
      `Hops ${chain.maxGapBetween[0]} and ${chain.maxGapBetween[1]} are ${hours} hours apart. Queue retries after a temporary failure are the usual cause.`));
  }
  if (chain.origin && chain.origin.publicIps.length === 0 && chain.count > 1) {
    out.push(f('origin_no_public_ip', 'The earliest hop records no public IP address', 'low',
      'The first recorded hop carries no routable IP, so the origin cannot be located from this text. Internal relays and stripped headers both produce this.'));
  }
  if (!chain.anyTls && chain.count > 0) {
    out.push(f('no_tls_recorded', 'No hop records a TLS-protected transfer', 'low',
      'None of the Received headers mention TLS/ESMTPS. Not every relay records the transport it used, so this is an absence of evidence rather than evidence of absence.'));
  }
  if (chain.count === 1) {
    out.push(f('single_hop', 'Only one Received hop is present', 'low',
      'A single hop means either direct submission or a partial paste; the earlier path cannot be read.'));
  }
  return out;
}

function runAllChecks(ctx) {
  return []
    .concat(checkStructure(ctx))
    .concat(checkAuth(ctx))
    .concat(checkIdentity(ctx))
    .concat(checkLookalike(ctx))
    .concat(checkRouting(ctx));
}

module.exports = { runAllChecks, checkStructure, checkAuth, checkIdentity, checkLookalike, checkRouting };
