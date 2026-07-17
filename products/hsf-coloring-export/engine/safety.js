// engine/safety.js
//
// HSF — Coloring Book Export — CHILD-SAFE content gate (FAIL-CLOSED).
//
// This product renders a child-facing printable. Every piece of text that will
// reach the page (title, kickers, headings, bodies, chips) passes through this
// gate BEFORE rendering. If ANY blocked category matches, the whole export is
// refused with SAFETY_GATE_FAILED — we never render a "partially safe" book.
//
// HONESTY NOTE: this is a deterministic keyword/pattern gate, not a semantic
// classifier. It fails closed on clear signals; it cannot judge nuance. The
// README documents this limit.

'use strict';

// Word-boundary patterns per category. Kept intentionally conservative and
// clearly-unsafe-only so ordinary storybook copy ("the battle with homework
// felt epic") isn't nuked — but real weapons/violence/adult content is.
const BLOCKLIST = [
  { category: 'violence_gore', re: /\b(kill(?:s|ed|ing)?|murder(?:s|ed|er)?|stab(?:s|bed|bing)?|behead|strangle[sd]?|torture[sd]?|massacre[sd]?|slaughter(?:s|ed)?|gor(?:e|y)|blood(?:y|bath)|corpse[s]?|mutilat\w*)\b/i },
  { category: 'weapons', re: /\b(gun[s]?|pistol[s]?|rifle[s]?|shotgun[s]?|firearm[s]?|ammo|ammunition|grenade[s]?|bomb[s]?|explosive[s]?|landmine[s]?|switchblade[s]?|machete[s]?)\b/i },
  { category: 'adult_content', re: /\b(sex(?:ual|y)?|porn\w*|nude[s]?|naked|erotic\w*|xxx|fetish\w*|orgasm\w*)\b/i },
  { category: 'drugs_alcohol', re: /\b(cocaine|heroin|meth(?:amphetamine)?|fentanyl|opioid[s]?|marijuana|cannabis|vap(?:e|ing)|cigarette[s]?|drunk|vodka|whiskey|beer[s]?)\b/i },
  { category: 'profanity', re: /\b(fuck\w*|shit\w*|bitch\w*|asshole[s]?|bastard[s]?|cunt[s]?|dick(?:head)?[s]?|damn(?:ed|it)?)\b/i },
  { category: 'self_harm', re: /\b(suicide|suicidal|self[- ]harm\w*|cut(?:s|ting)? (?:myself|himself|herself|themselves)|overdose[sd]?)\b/i },
  { category: 'hate', re: /\b(nazi[s]?|kkk|white power|ethnic cleansing|genocide)\b/i },
];

const MAX_FIELD_CHARS = 2000;

function collectTexts(pagesInput) {
  const texts = [];
  const push = (v) => { if (v != null && String(v).trim() !== '') texts.push(String(v)); };
  push(pagesInput.title);
  for (const s of pagesInput.scenes || []) {
    push(s.kicker); push(s.heading); push(s.body);
    for (const c of s.chips || []) push(c);
  }
  return texts;
}

// Throws { code:'SAFETY_GATE_FAILED', category } on any hit. Returns { ok:true, checked }.
function assertChildSafe(pagesInput) {
  const texts = collectTexts(pagesInput);
  for (const t of texts) {
    if (t.length > MAX_FIELD_CHARS) {
      const err = new Error(`Safety gate: a text field exceeds ${MAX_FIELD_CHARS} characters.`);
      err.code = 'SAFETY_GATE_FAILED';
      err.category = 'oversize_field';
      throw err;
    }
    for (const rule of BLOCKLIST) {
      if (rule.re.test(t)) {
        const err = new Error(
          `Safety gate: blocked category "${rule.category}" detected in story text. ` +
          'This is a child-facing coloring book; the export was refused (fail-closed).'
        );
        err.code = 'SAFETY_GATE_FAILED';
        err.category = rule.category;
        throw err;
      }
    }
  }
  return { ok: true, checked: texts.length };
}

module.exports = { assertChildSafe, BLOCKLIST, MAX_FIELD_CHARS };
