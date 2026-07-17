// engine/index.js
//
// HSF — Coloring Book Export — engine entry point.
//
//   generateColoringBook({ story, watermarkFree }) ->
//     { pages, title, safety, files: { pdfName, pdf } }
//
// INPUT (either shape):
//   story.scenes : Array<{kicker, heading, body, chips}>  (from the in-browser
//                  Story Studio, same Scene shape story-engine.js produces), OR
//   story.spec   : { who, oneLiner, journey, moments, tone, ending, extras }
//                  -> run through the VENDORED story engine (identical arc to
//                  the live studio) to produce the scenes.
//
// PIPELINE (fail-closed at every step):
//   1. normalize + validate input,
//   2. CHILD-SAFETY GATE (engine/safety.js) over every string that will render,
//   3. deterministic motif selection per scene (engine/motifs.js),
//   4. multi-page line-art PDF (engine/render_pdf.js) — watermark ALWAYS on
//      unless watermarkFree === true (only the entitlement-gated endpoint sets it).
//
// GUARDRAIL: child-facing content -> safety gate is mandatory and cannot be
// skipped; watermark-free is a paid outcome, the engine defaults to watermarked.

'use strict';

const { buildStory } = require('./story-engine');
const { assertChildSafe } = require('./safety');
const { motifForScene, cover } = require('./motifs');
const { renderColoringPdf, coverPage, scenePage, backPage } = require('./render_pdf');

const MAX_SCENES = 12;

function clean(s) { return (s == null ? '' : String(s)).replace(/\s+/g, ' ').trim(); }

function normalizeStory(story) {
  if (!story || typeof story !== 'object') {
    const err = new Error('Provide a story: either { scenes: [...] } or { spec: {...} }.');
    err.code = 'BAD_INPUT';
    throw err;
  }

  let scenes = null;
  let title = clean(story.title);

  if (Array.isArray(story.scenes) && story.scenes.length > 0) {
    scenes = story.scenes.map((s) => ({
      kicker: clean(s && s.kicker),
      heading: clean(s && s.heading),
      body: clean(s && s.body),
      chips: Array.isArray(s && s.chips) ? s.chips.map(clean).filter(Boolean).slice(0, 4) : [],
    }));
  } else if (story.spec && typeof story.spec === 'object') {
    scenes = buildStory(story.spec).map((s) => ({
      kicker: clean(s.kicker), heading: clean(s.heading), body: clean(s.body),
      chips: (s.chips || []).map(clean).filter(Boolean).slice(0, 4),
    }));
    if (!title) title = clean(story.spec.who);
  }

  if (!scenes || scenes.length === 0) {
    const err = new Error('Story has no scenes. Provide { scenes: [...] } or { spec: {...} }.');
    err.code = 'BAD_INPUT';
    throw err;
  }

  const dropped = Math.max(0, scenes.length - MAX_SCENES);
  scenes = scenes.slice(0, MAX_SCENES);

  // Every scene must have SOMETHING to say; refuse fully-empty scenes rather
  // than render blank pages (fail-closed on garbage input).
  for (const s of scenes) {
    if (!s.kicker && !s.heading && !s.body) {
      const err = new Error('A scene with no kicker, heading, or body was provided.');
      err.code = 'BAD_INPUT';
      throw err;
    }
  }

  if (!title) title = scenes[0].heading || scenes[0].kicker || 'My Story';
  return { title, scenes, dropped };
}

function generateColoringBook(opts) {
  opts = opts || {};
  const watermarkFree = opts.watermarkFree === true; // strictly boolean true
  const { title, scenes, dropped } = normalizeStory(opts.story);

  // CHILD-SAFETY GATE — throws SAFETY_GATE_FAILED on any hit. Mandatory.
  const safety = assertChildSafe({ title, scenes });

  const pages = [];
  pages.push(coverPage(title, 'A Story Studio Coloring Book', cover));
  scenes.forEach((scene, i) => {
    pages.push(scenePage(scene, i, scenes.length, motifForScene(scene, i)));
  });
  pages.push(backPage(title));

  const pdf = renderColoringPdf(pages, watermarkFree);
  const slugTitle = title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40) || 'story';

  return {
    title,
    pages: pages.length,
    scenes: scenes.length,
    droppedScenes: dropped,
    watermarked: !watermarkFree,
    safety,
    files: {
      pdfName: `coloring-book-${slugTitle}${watermarkFree ? '' : '-preview'}.pdf`,
      pdf,
    },
  };
}

module.exports = { generateColoringBook, normalizeStory, MAX_SCENES };
