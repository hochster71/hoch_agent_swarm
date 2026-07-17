/**
 * VerseOfDay — Server Component
 * Daily rotating Scripture verse rendered as a subtle banner below the TopBar.
 * Day index rotates through 7 passages selected for courage, peace, and hope
 * during times of conflict and uncertainty.
 */

const VERSES = [
  {
    ref: 'Isaiah 41:10',
    text: 'Fear not, for I am with you; be not dismayed, for I am your God; I will strengthen you, I will help you, I will uphold you.',
  },
  {
    ref: 'Psalm 46:1',
    text: 'God is our refuge and strength, a very present help in trouble. Therefore we will not fear.',
  },
  {
    ref: 'John 14:27',
    text: 'Peace I leave with you; my peace I give to you. Not as the world gives do I give to you. Let not your hearts be troubled.',
  },
  {
    ref: 'Philippians 4:6-7',
    text: 'Do not be anxious about anything. And the peace of God, which surpasses all understanding, will guard your hearts and minds.',
  },
  {
    ref: 'Psalm 23:4',
    text: 'Even though I walk through the valley of the shadow of death, I will fear no evil, for you are with me.',
  },
  {
    ref: 'Romans 8:28',
    text: 'We know that for those who love God all things work together for good, for those who are called according to his purpose.',
  },
  {
    ref: 'Proverbs 3:5-6',
    text: 'Trust in the Lord with all your heart and do not lean on your own understanding. In all your ways acknowledge him, and he will make straight your paths.',
  },
] as const

function getTodayVerse() {
  // Rotate by UTC day — no JS client needed, deterministic on server
  const dayIndex = Math.floor(Date.now() / 86_400_000)
  return VERSES[dayIndex % VERSES.length]
}

export function VerseOfDay() {
  const verse = getTodayVerse()
  // Trim text to ~110 chars for a single-line display
  const display =
    verse.text.length > 110 ? verse.text.slice(0, 107) + '…' : verse.text

  return (
    <div className="verse-strip shrink-0 flex items-center justify-center gap-3 px-4 py-1.5 animate-verse-fade">
      {/* Cross symbol */}
      <span className="text-amber-600/40 text-[11px] shrink-0" aria-hidden>✝</span>

      {/* Scripture text */}
      <p className="text-[9px] italic text-amber-500/50 tracking-wider leading-none truncate">
        &ldquo;{display}&rdquo;
      </p>

      {/* Reference */}
      <span className="text-[9px] text-amber-600/55 tracking-[0.18em] uppercase font-bold whitespace-nowrap shrink-0">
        {verse.ref}
      </span>

      {/* Cross symbol */}
      <span className="text-amber-600/40 text-[11px] shrink-0" aria-hidden>✝</span>
    </div>
  )
}
