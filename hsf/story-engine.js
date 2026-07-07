/*!
 * HSF Story Engine — story-engine.js
 * Hoch Storybook Factory · part of the Hoch Agent Swarm
 *
 * Pure vanilla JS. No build step, no deps, no network.
 * Usage:  <script src="story-engine.js"></script>  then  buildStory(spec)
 *
 * buildStory(spec) -> Array<Scene>  (8–10 scenes)
 *   spec = { who, oneLiner, journey, moments:[...], tone, ending, extras }
 *   Scene = { id, kicker, heading, body, chips:[], layout, accent }
 *
 * Design intent: generate cinematic on-screen COPY from the user's inputs.
 * Where a fact is missing we stay evocative but GENERIC — we never fabricate
 * specific names, dates, numbers, or events the user did not provide.
 */
(function (global) {
  'use strict';

  // ---- tone → accent palette -------------------------------------------
  var PALETTES = {
    Cinematic: { primary: '#22d3ee', secondary: '#a78bfa', warm: '#fbbf24', cool: '#34d399' },
    Warm:      { primary: '#fbbf24', secondary: '#34d399', warm: '#fbbf24', cool: '#22d3ee' },
    Epic:      { primary: '#a78bfa', secondary: '#22d3ee', warm: '#fbbf24', cool: '#34d399' },
    Minimal:   { primary: '#e6edf6', secondary: '#8b98ad', warm: '#e6edf6', cool: '#8b98ad' }
  };

  // ---- small helpers ---------------------------------------------------
  function clean(s) {
    return (s == null ? '' : String(s)).replace(/\s+/g, ' ').trim();
  }
  function fallback(s, alt) {
    var v = clean(s);
    return v ? v : alt;
  }
  // Lowercase the first char (for mid-sentence stitching) without touching acronyms.
  function lowerLead(s) {
    s = clean(s);
    if (!s) return s;
    if (s.length > 1 && s[1] === s[1].toUpperCase() && /[A-Z]/.test(s[1])) return s; // e.g. "AI first"
    return s.charAt(0).toLowerCase() + s.slice(1);
  }
  function stripEndPunct(s) {
    return clean(s).replace(/[.。!?…]+$/, '');
  }
  // Split a moment "Title — detail" or "Title: detail" into {title, detail}.
  function splitMoment(m) {
    var raw = clean(m);
    var parts = raw.split(/\s*(?:—|--|–|:|\|)\s*/);
    if (parts.length >= 2 && parts[0]) {
      return { title: parts[0], detail: parts.slice(1).join(' — ') };
    }
    return { title: raw, detail: '' };
  }
  // A few short evocative fragments keyed off tone, used only to color GENERIC
  // connective copy — never presented as a specific fact.
  var TONE_TEXTURE = {
    Cinematic: ['the frame widens', 'the light shifts', 'the score swells low'],
    Warm:      ['the room softens', 'a quiet warmth settles', 'the day leans golden'],
    Epic:      ['the horizon tilts', 'the ground trembles', 'the odds stack high'],
    Minimal:   ['everything goes still', 'the noise falls away', 'one line remains']
  };
  function texture(tone, i) {
    var arr = TONE_TEXTURE[tone] || TONE_TEXTURE.Cinematic;
    return arr[i % arr.length];
  }

  // ---- the builder -----------------------------------------------------
  function buildStory(spec) {
    spec = spec || {};
    var tone = fallback(spec.tone, 'Cinematic');
    if (!PALETTES[tone]) tone = 'Cinematic';
    var pal = PALETTES[tone];

    var who     = fallback(spec.who, 'This Story');
    var oneLiner= fallback(spec.oneLiner, 'a journey worth telling');
    var journey = fallback(spec.journey, 'A long road of building, breaking, and building again — the kind that only makes sense looking back.');
    var ending  = fallback(spec.ending, 'The mission continues.');
    var extras  = clean(spec.extras);

    // Normalize moments: accept array or newline-joined string.
    var rawMoments = spec.moments;
    if (typeof rawMoments === 'string') rawMoments = rawMoments.split(/\r?\n/);
    if (!Array.isArray(rawMoments)) rawMoments = [];
    var moments = rawMoments.map(clean).filter(Boolean).map(splitMoment);

    var whoShort = stripEndPunct(who);
    var scenes = [];
    var seq = 0;
    function push(scene) {
      scene.id = 'scene-' + (++seq);
      if (!scene.accent) scene.accent = pal.primary;
      if (!scene.chips) scene.chips = [];
      scenes.push(scene);
    }

    // 1) PROLOGUE — set the frame. Uses only who + oneLiner.
    push({
      kicker: 'Prologue',
      heading: whoShort,
      body: capFirst(oneLiner) + '. Before the milestones, before the ending — a person, and a spark worth following.',
      chips: [],
      layout: 'center',
      accent: pal.primary
    });

    // 2) THE CALL — the pull to begin. Generic but tone-colored.
    push({
      kicker: 'The Call',
      heading: 'Something started pulling.',
      body: 'Every story has a moment where staying the same stops being an option. For ' + whoShort +
            ', ' + texture(tone, 0) + ' — and the work began.',
      chips: [],
      layout: 'split',
      accent: pal.secondary
    });

    // 3) THE JOURNEY — the user's own words carry this scene.
    push({
      kicker: 'The Journey',
      heading: 'What they set out to build.',
      body: capFirst(journey),
      chips: [],
      layout: 'split',
      accent: pal.primary
    });

    // 4..) TURNING POINTS — one scene per moment. Capped at 2 so the finished
    // storybook stays inside the 8–10 scene target (8 fixed scenes + up to 2).
    var turningAccents = [pal.warm, pal.cool, pal.secondary];
    var turningLayouts = ['grid', 'quote', 'split'];
    var used = moments.slice(0, 2);
    if (used.length === 0) {
      // No moments given — one honest, generic turning-point scene.
      push({
        kicker: 'Turning Point',
        heading: 'Then everything pivoted.',
        body: 'A decision, a door, a moment that split the timeline into before and after. This is where the shape of the story changed.',
        chips: [],
        layout: 'grid',
        accent: pal.warm
      });
    } else {
      used.forEach(function (m, i) {
        var layout = turningLayouts[i % turningLayouts.length];
        var accent = turningAccents[i % turningAccents.length];
        var heading = capFirst(m.title);
        var body;
        if (m.detail) {
          body = capFirst(m.detail);
        } else {
          // No detail supplied — frame it without inventing specifics.
          body = 'A moment that mattered — the kind that only reveals its weight later, once ' + texture(tone, i + 1) + '.';
        }
        var kicker = used.length > 1 ? ('Turning Point ' + (i + 1)) : 'Turning Point';
        // Quote layout reframes the line as a pulled quote.
        push({
          kicker: kicker,
          heading: layout === 'quote' ? '' : heading,
          body: layout === 'quote' ? '“' + stripEndPunct(m.detail || m.title) + '.”' : body,
          chips: layout === 'quote' && m.detail ? [heading] : [],
          layout: layout,
          accent: accent
        });
      });
    }

    // 5) THE STRUGGLE — honest low point. Generic, tasteful.
    push({
      kicker: 'The Struggle',
      heading: 'It got hard. That part is real.',
      body: 'Progress is never a straight line. There were nights the whole thing felt impossible — and ' +
            (used.length ? whoShort + ' kept going anyway.' : 'the only way through was forward.'),
      chips: [],
      layout: 'center',
      accent: pal.warm
    });

    // 6) THE DOCTRINE — the lesson distilled. This is the "patch" moment.
    push({
      kicker: 'The Doctrine',
      heading: 'What the road taught.',
      body: 'Every hard thing leaves a rule behind. The lesson here isn\'t loud — it\'s the quiet discipline of ' +
            'showing up, telling the truth about the work, and refusing to quit before it was done.',
      chips: distillChips(moments, tone),
      layout: 'patch',
      accent: pal.cool
    });

    // 7) THE RECOVERY — momentum returns.
    push({
      kicker: 'The Recovery',
      heading: 'Then it started to work.',
      body: 'Slowly, then all at once, the pieces began to hold. What looked like failure turned out to be groundwork — and ' + texture(tone, 2) + '.',
      chips: [],
      layout: 'split',
      accent: pal.secondary
    });

    // 8) THE NEXT LAUNCH — the ending the user gave us.
    push({
      kicker: 'The Next Launch',
      heading: capFirst(ending),
      body: extras
        ? capFirst(extras)
        : 'The story isn\'t finished — it\'s launching. Whatever comes next starts from everything that came before.',
      chips: [],
      layout: 'center',
      accent: pal.primary
    });

    // 9) CLOSING PATCH — the mission-patch signature. Always last.
    push({
      kicker: 'Mission Patch',
      heading: whoShort,
      body: 'Produced by the Hoch Storybook Factory — honest, animated, yours.',
      chips: buildPatchChips(who, tone),
      layout: 'patch',
      accent: pal.primary
    });

    return scenes;
  }

  // ---- copy helpers ----------------------------------------------------
  function capFirst(s) {
    s = clean(s);
    if (!s) return s;
    return s.charAt(0).toUpperCase() + s.slice(1);
  }

  // Turn moment titles into short chips for the doctrine scene (max 4).
  function distillChips(moments, tone) {
    var chips = moments.slice(0, 4).map(function (m) {
      return capFirst(stripEndPunct(m.title)).slice(0, 40);
    }).filter(Boolean);
    if (chips.length === 0) {
      chips = ['Show up', 'Tell the truth', 'Finish the work'];
    }
    return chips;
  }

  function buildPatchChips(who, tone) {
    var year = new Date().getFullYear();
    return [String(year), tone, 'Chronicle'];
  }

  // ---- export ----------------------------------------------------------
  var api = { buildStory: buildStory, PALETTES: PALETTES };
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
  global.buildStory = buildStory;
  global.HSFStoryEngine = api;

})(typeof window !== 'undefined' ? window : this);
