// =============================================================================
// lib/news-fetcher.ts
// Handles RSS news aggregation and kinetic contradiction analysis.
// =============================================================================

export interface NewsItem {
  title:                string
  url:                  string
  pubDate:              string   // ISO 8601 string
  source:               string
  summary:              string
  /** Source reliability tier: 1 = wire/official, 2 = analysis/regional, 3 = commodity/alternative */
  tier:                 1 | 2 | 3
  /** How many OTHER sources are reporting a substantially similar story */
  corroborationCount:   number
  /** Which sources are reporting a similar story */
  corroborationSources: string[]
  /** Pre-analysis credibility score: tier base + corroboration bonus (0-100) */
  credibilityScore:     number
  /** True when only one source (this item's source) is reporting this story */
  singleSource:         boolean
  /** AllSides lean score: -2 Far Left → 0 Center → +2 Far Right */
  mediaBias:            number
  /** Human-readable bias label */
  biasLabel:            string
  /** True when confirmed by BOTH left-leaning AND right-leaning independent sources */
  crossIdeological:     boolean
  /** Count of left-leaning (lean ≤ -0.5) corroborating sources */
  leftSources:          number
  /** Count of right-leaning (lean ≥ +0.5) corroborating sources */
  rightSources:         number
  /**
   * TRUE when the story describes peaceful/diplomatic/monitoring activity at a
   * site confirmed to be under active kinetic bombardment.
   */
  kineticContradiction:  boolean
  /** Human-readable explanation of why the contradiction was detected */
  contradictionReason:   string
}

const RSS_FEEDS: { name: string; url: string; tier: 1 | 2 | 3 }[] = [
  { tier: 1, name: 'Reuters — World',           url: 'https://feeds.reuters.com/reuters/worldNews' },
  { tier: 1, name: 'Reuters — Middle East',     url: 'https://feeds.reuters.com/reuters/MENTTopNews' },
  { tier: 1, name: 'AP — Top Headlines',        url: 'https://feeds.apnews.com/rss/apf-topnews' },
  { tier: 1, name: 'AP — World News',           url: 'https://feeds.apnews.com/rss/apf-WorldNews' },
  { tier: 1, name: 'BBC — World',               url: 'https://feeds.bbci.co.uk/news/world/rss.xml' },
  { tier: 1, name: 'BBC — Middle East',         url: 'https://feeds.bbci.co.uk/news/world/middle_east/rss.xml' },
  { tier: 1, name: 'Fox News',                  url: 'https://moxie.foxnews.com/google-publisher/latest.xml' },
  { tier: 1, name: 'Fox Business',              url: 'https://feeds.foxbusiness.com/foxbusiness/latest' },
  { tier: 1, name: 'NBC News',                  url: 'https://feeds.nbcnews.com/nbcnews/public/news' },
  { tier: 1, name: 'ABC News',                  url: 'https://abcnews.go.com/abcnews/topstories' },
  { tier: 1, name: 'CBS News',                  url: 'https://www.cbsnews.com/latest/rss/main' },
  { tier: 1, name: 'NPR News',                  url: 'https://feeds.npr.org/1001/rss.xml' },
  { tier: 1, name: 'PBS NewsHour',              url: 'https://www.pbs.org/newshour/feeds/rss/headlines' },
  { tier: 1, name: 'USA Today',                 url: 'https://rssfeeds.usatoday.com/usatoday-NewsTopStories' },
  { tier: 1, name: 'USNI News',                 url: 'https://news.usni.org/feed' },
  { tier: 1, name: 'Defense News',              url: 'https://www.defensenews.com/arc/outboundfeeds/rss/?outputType=xml' },
  { tier: 1, name: 'Breaking Defense',          url: 'https://breakingdefense.com/feed/' },
  { tier: 1, name: 'War on the Rocks',          url: 'https://warontherocks.com/feed/' },
  { tier: 1, name: 'The Drive — War Zone',      url: 'https://www.thedrive.com/feed/the-war-zone' },
  { tier: 1, name: 'Military Times',            url: 'https://www.militarytimes.com/arc/outboundfeeds/rss/?outputType=xml' },
  { tier: 1, name: 'Defense One',               url: 'https://www.defenseone.com/rss/all/' },
  { tier: 1, name: 'Stars and Stripes',         url: 'https://www.stripes.com/arc/outboundfeeds/rss/?outputType=xml' },
  { tier: 1, name: 'The Guardian — World',      url: 'https://www.theguardian.com/world/rss' },
  { tier: 1, name: 'Sky News — World',          url: 'https://feeds.skynews.com/feeds/rss/world.xml' },
  { tier: 1, name: 'France 24 — Middle East',   url: 'https://www.france24.com/en/middle-east/rss' },
  { tier: 1, name: 'VOA — Middle East',         url: 'https://www.voanews.com/api/zyqkpqymii' },
  { tier: 1, name: 'Haaretz — English',         url: 'https://www.haaretz.com/cmlink/1.628765' },
  { tier: 2, name: 'Politico',                  url: 'https://www.politico.com/rss/politics08.xml' },
  { tier: 2, name: 'Axios',                     url: 'https://api.axios.com/feed/' },
  { tier: 2, name: 'The Hill',                  url: 'https://thehill.com/feed/' },
  { tier: 2, name: 'Newsweek',                  url: 'https://www.newsweek.com/rss' },
  { tier: 2, name: 'New York Post',             url: 'https://nypost.com/feed/' },
  { tier: 2, name: 'Washington Times',          url: 'https://www.washingtontimes.com/rss/headlines/news/front-page/' },
  { tier: 2, name: 'Washington Examiner',       url: 'https://www.washingtonexaminer.com/feed/' },
  { tier: 2, name: 'The Guardian — US',         url: 'https://www.theguardian.com/us-news/rss' },
  { tier: 2, name: 'ISW — Institute for the Study of War', url: 'https://www.understandingwar.org/aggregator/rss' },
  { tier: 2, name: 'RAND — Commentary',         url: 'https://www.rand.org/pubs/commentary.xml' },
  { tier: 2, name: 'Foreign Policy',            url: 'https://foreignpolicy.com/feed/' },
  { tier: 2, name: 'Middle East Eye',           url: 'https://www.middleeasteye.net/rss' },
  { tier: 2, name: 'Atlantic Council',          url: 'https://www.atlanticcouncil.org/feed/' },
  { tier: 2, name: 'Radio Free Europe — Iran',  url: 'https://www.rferl.org/api/eqpmgyiuqo' },
  { tier: 2, name: 'Al Jazeera — World',        url: 'https://www.aljazeera.com/xml/rss/all.xml' },
  { tier: 2, name: 'Iran International',        url: 'https://www.iranintl.com/en/rss' },
  { tier: 2, name: 'Times of Israel',           url: 'https://www.timesofisrael.com/feed/' },
  { tier: 2, name: 'Jerusalem Post',            url: 'https://www.jpost.com/Rss/RssFeedsHeadlines.aspx' },
  { tier: 2, name: 'Al-Monitor',               url: 'https://www.al-monitor.com/rss' },
  { tier: 2, name: 'Arab News',                 url: 'https://www.arabnews.com/rss.xml' },
  { tier: 2, name: 'The National — UAE',        url: 'https://www.thenationalnews.com/rss' },
  { tier: 2, name: 'Rudaw',                     url: 'https://www.rudaw.net/english/rss.xml' },
  { tier: 2, name: 'Middle East Monitor',       url: 'https://www.middleeastmonitor.com/feed/' },
  { tier: 2, name: 'Kurdistan 24',              url: 'https://www.kurdistan24.net/en/rss.xml' },
  { tier: 2, name: 'i24 News',                  url: 'https://www.i24news.tv/en/rss' },
  { tier: 3, name: 'Oilprice.com',              url: 'https://oilprice.com/rss/main' },
  { tier: 3, name: 'EIA — Today in Energy',     url: 'https://www.eia.gov/rss/todayinenergy.xml' },
  { tier: 3, name: 'S&P Global — Commodities',  url: 'https://www.spglobal.com/commodityinsights/rss/news-and-analysis' },
];

export const RSS_FEEDS_LIST = RSS_FEEDS;

const WIRE_FAMILIES: Record<string, string> = {
  'Reuters — World':       'Reuters',
  'Reuters — Middle East': 'Reuters',
  'AP — Top Headlines':    'AP',
  'AP — World News':       'AP',
  'ABC News':              'US-Broadcast',
  'NBC News':              'US-Broadcast',
  'CBS News':              'US-Broadcast',
  'PBS NewsHour':          'US-Broadcast',
  'NPR News':              'US-Broadcast',
  'USA Today':             'US-Broadcast',
  'Fox News':              'Fox',
  'Fox Business':          'Fox',
  'Washington Times':      'Washington-Times-Group',
  'Washington Examiner':   'Washington-Times-Group',
  'Times of Israel':       'Israeli-Press',
  'Jerusalem Post':        'Israeli-Press',
  'Haaretz — English':     'Israeli-Press',
  'The Guardian — World':  'Guardian',
  'The Guardian — US':     'Guardian',
  'Military Times':        'Defense-Trade-Press',
  'Defense One':           'Defense-Trade-Press',
  'Arab News':             'Gulf-Press',
  'The National — UAE':    'Gulf-Press',
  'Rudaw':                 'Kurdish-Press',
  'Kurdistan 24':          'Kurdish-Press',
};

function sourceFamily(sourceName: string): string {
  return WIRE_FAMILIES[sourceName] ?? sourceName;
}

const MEDIA_BIAS: Record<string, { lean: number; label: string; color: string }> = {
  'Reuters — World':       { lean: 0,    label: 'CENTER',      color: '#94a3b8' },
  'Reuters — Middle East': { lean: 0,    label: 'CENTER',      color: '#94a3b8' },
  'AP — Top Headlines':    { lean: 0,    label: 'CENTER',      color: '#94a3b8' },
  'AP — World News':       { lean: 0,    label: 'CENTER',      color: '#94a3b8' },
  'BBC — World':           { lean: -0.5, label: 'LEAN LEFT',   color: '#93c5fd' },
  'BBC — Middle East':     { lean: -0.5, label: 'LEAN LEFT',   color: '#93c5fd' },
  'Fox News':              { lean: 1,    label: 'RIGHT',       color: '#f87171' },
  'Fox Business':          { lean: 1,    label: 'RIGHT',       color: '#f87171' },
  'NBC News':              { lean: -0.5, label: 'LEAN LEFT',   color: '#93c5fd' },
  'ABC News':              { lean: -0.5, label: 'LEAN LEFT',   color: '#93c5fd' },
  'CBS News':              { lean: -0.5, label: 'LEAN LEFT',   color: '#93c5fd' },
  'NPR News':              { lean: -0.5, label: 'LEAN LEFT',   color: '#93c5fd' },
  'PBS NewsHour':          { lean: -0.5, label: 'LEAN LEFT',   color: '#93c5fd' },
  'USA Today':             { lean: 0,    label: 'CENTER',      color: '#94a3b8' },
  'USNI News':             { lean: 0,    label: 'CENTER',      color: '#94a3b8' },
  'Defense News':          { lean: 0,    label: 'CENTER',      color: '#94a3b8' },
  'Breaking Defense':      { lean: 0,    label: 'CENTER',      color: '#94a3b8' },
  'War on the Rocks':      { lean: 0,    label: 'CENTER',      color: '#94a3b8' },
  'The Drive — War Zone':  { lean: 0,    label: 'CENTER',      color: '#94a3b8' },
  'Military Times':        { lean: 0,    label: 'CENTER',      color: '#94a3b8' },
  'Defense One':           { lean: 0,    label: 'CENTER',      color: '#94a3b8' },
  'Stars and Stripes':     { lean: 0,    label: 'CENTER',      color: '#94a3b8' },
  'The Guardian — US':     { lean: -1,   label: 'LEFT',        color: '#60a5fa' },
  'The Guardian — World':  { lean: -1,   label: 'LEFT',        color: '#60a5fa' },
  'Sky News — World':      { lean: 0,    label: 'CENTER',      color: '#94a3b8' },
  'France 24 — Middle East': { lean: 0,  label: 'CENTER',      color: '#94a3b8' },
  'VOA — Middle East':     { lean: 0,    label: 'CENTER',      color: '#94a3b8' },
  'Haaretz — English':     { lean: -0.5, label: 'LEAN LEFT',   color: '#93c5fd' },
  'ISW — Institute for the Study of War': { lean: 0, label: 'CENTER', color: '#94a3b8' },
  'RAND — Commentary':     { lean: 0,    label: 'CENTER',      color: '#94a3b8' },
  'Foreign Policy':        { lean: -0.5, label: 'LEAN LEFT',   color: '#93c5fd' },
  'Middle East Eye':       { lean: -1,   label: 'LEFT',        color: '#60a5fa' },
  'Atlantic Council':      { lean: 0,    label: 'CENTER',      color: '#94a3b8' },
  'Radio Free Europe — Iran': { lean: 0, label: 'CENTER',      color: '#94a3b8' },
  'Al Jazeera — World':    { lean: -0.5, label: 'LEAN LEFT',   color: '#93c5fd' },
  'Iran International':    { lean: 0,    label: 'CENTER',      color: '#94a3b8' },
  'Times of Israel':       { lean: 0.5,  label: 'LEAN RIGHT',  color: '#fca5a5' },
  'Jerusalem Post':        { lean: 0.5,  label: 'LEAN RIGHT',  color: '#fca5a5' },
  'Al-Monitor':            { lean: 0,    label: 'CENTER',      color: '#94a3b8' },
  'Arab News':             { lean: 0.5,  label: 'LEAN RIGHT',  color: '#fca5a5' },
  'The National — UAE':    { lean: 0,    label: 'CENTER',      color: '#94a3b8' },
  'Rudaw':                 { lean: 0,    label: 'CENTER',      color: '#94a3b8' },
  'Middle East Monitor':   { lean: -0.5, label: 'LEAN LEFT',   color: '#93c5fd' },
  'Kurdistan 24':          { lean: 0,    label: 'CENTER',      color: '#94a3b8' },
  'i24 News':              { lean: 0.5,  label: 'LEAN RIGHT',  color: '#fca5a5' },
  'Oilprice.com':          { lean: 0,    label: 'CENTER',      color: '#94a3b8' },
  'EIA — Today in Energy': { lean: 0,    label: 'CENTER',      color: '#94a3b8' },
  'S&P Global — Commodities': { lean: 0, label: 'CENTER',      color: '#94a3b8' },
};

export const MEDIA_BIAS_MAP = MEDIA_BIAS;

const ACTIVE_STRIKE_TARGETS: { name: string; aliases: string[] }[] = [
  { name: 'Fordow', aliases: ['fordow', 'fordo', 'fordow centrifuge', 'fordow fuel enrichment'] },
  { name: 'Natanz', aliases: ['natanz', 'natanz facility', 'natanz hall'] },
  { name: 'Arak Heavy Water', aliases: ['arak', 'ir-40', 'heavy water reactor'] },
  { name: 'Isfahan / Esfahan', aliases: ['isfahan', 'esfahan', 'ucf', 'uranium conversion facility'] },
  { name: 'Parchin', aliases: ['parchin'] },
];

const DIPLOMATIC_PROCESS_PATTERNS: RegExp[] = [
  /\biaea\b/i,
  /\binspect(or|ion|ors|ions)?\b/i,
  /\bsafeguards\b/i,
  /\bverification\b/i,
  /\benrichment activity\b/i,
  /\benrichment (resumed|reported|detected|ongoing|underway|continues)\b/i,
  /\b(resume[sd]?|restart(ed)?) (enrich|centrifuge)/i,
  /\bcentrifuge[s]? (operational|spinning|active|running|installed)\b/i,
  /\b(access denied|denied access|inspectors barred|agency barred)\b/i,
  /\bjcpoa\b/i,
  /\bnpt (compliance|obligations|protocol)\b/i,
  /\bdirector general (report|says|warns|notes)\b/i,
  /\brafael grossi\b/i,
  /\binternational atomic energy\b/i,
  /\bnuclear (deal|agreement|talks|negotiations)\b/i,
];

interface KineticCheckResult {
  contradiction: boolean
  reason: string
}

function kineticRealityCheck(item: NewsItem): KineticCheckResult {
  const text = `${item.title} ${item.summary}`.toLowerCase();
  const targetHit = ACTIVE_STRIKE_TARGETS.find(t =>
    t.aliases.some(alias => text.includes(alias.toLowerCase()))
  );
  if (!targetHit) return { contradiction: false, reason: '' };

  const patternHit = DIPLOMATIC_PROCESS_PATTERNS.find(p => p.test(text));
  if (!patternHit) return { contradiction: false, reason: '' };

  return {
    contradiction: true,
    reason: (
      `${targetHit.name} is confirmed under active kinetic bombardment. ` +
      `Diplomatic/inspection process language in this headline is inconsistent ` +
      `with an active warzone. Likely recycled pre-war content or disinformation. ` +
      `Credibility hard-capped at 25.`
    ),
  };
}

function extractItems(xml: string, sourceName: string): NewsItem[] {
  const items: NewsItem[] = [];
  const itemRegex = /<(?:item|entry)[^>]*>([\s\S]*?)<\/(?:item|entry)>/gi;
  let match: RegExpExecArray | null;

  while ((match = itemRegex.exec(xml)) !== null) {
    const block = match[1];
    const title   = stripTags(extract(block, 'title'));
    const link    = extract(block, 'link') || extractAttr(block, 'link', 'href');
    const pubDate = normaliseDate(
      extract(block, 'pubDate') ||
      extract(block, 'published') ||
      extract(block, 'updated')
    );
    const summary = stripTags(
      extract(block, 'description') ||
      extract(block, 'summary') ||
      extract(block, 'content')
    ).slice(0, 240);

    if (title && link) {
      items.push({
        title, url: link.trim(), pubDate, source: sourceName, summary, tier: 1,
        corroborationCount: 0, corroborationSources: [], credibilityScore: 0, singleSource: true,
        mediaBias: 0, biasLabel: 'CENTER', crossIdeological: false, leftSources: 0, rightSources: 0,
        kineticContradiction: false, contradictionReason: '',
      });
    }
  }
  return items;
}

function extract(text: string, tag: string): string {
  const re = new RegExp(`<${tag}(?:[^>]*)>([\\s\\S]*?)<\\/${tag}>`, 'i');
  const m  = re.exec(text);
  if (!m) return '';
  return m[1].replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, '$1').trim();
}

function extractAttr(text: string, tag: string, attr: string): string {
  const re = new RegExp(`<${tag}[^>]+${attr}="([^"]+)"`, 'i');
  const m  = re.exec(text);
  return m ? m[1].trim() : '';
}

function stripTags(html: string): string {
  return html.replace(/<[^>]+>/g, '').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&nbsp;/g, ' ').trim();
}

function normaliseDate(raw: string): string {
  if (!raw) return new Date().toISOString();
  try { return new Date(raw).toISOString() } catch { return new Date().toISOString() }
}

const STOP_WORDS = new Set([
  'the','a','an','of','in','on','at','to','for','and','or','but','is','was','are','were',
  'has','had','have','be','been','by','as','with','from','that','this','it','its','not',
  'after','before','over','under','now','new','say','says','said','would','could','will',
  'may','up','out','into','than','then','when','who','what','which','where','how','all',
  'more','any','other','some','also','about','against','during','through','while','its',
  'their','they','we','our','us','him','her','his','she','he','you','your','they','them',
  'been','into','only','just','most','over','such','than','both','each','further',
  'once','same','so','still','between','since','off','own','down','back','again',
]);

function titleFingerprint(title: string): string[] {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter(w => w.length >= 4 && !STOP_WORDS.has(w));
}

function titleSimilarity(kw1: string[], kw2: string[]): number {
  const set2 = new Set(kw2);
  return kw1.filter(w => set2.has(w)).length;
}

const CORROBORATION_MIN_SHARED = 3;

function addCorroborationMetadata(items: NewsItem[]): NewsItem[] {
  const fingerprints = items.map(item => titleFingerprint(item.title));
  const now = Date.now();

  return items.map((item, i) => {
    const corrobFamilies = new Set<string>();
    const corroborationSources: string[] = [];

    for (let j = 0; j < items.length; j++) {
      if (i === j) continue;
      if (items[j].source === item.source) continue;

      const shared = titleSimilarity(fingerprints[i], fingerprints[j]);
      if (shared < CORROBORATION_MIN_SHARED) continue;

      const family = sourceFamily(items[j].source);
      const itemFamily = sourceFamily(item.source);
      if (family === itemFamily) continue;

      if (!corrobFamilies.has(family)) {
        corrobFamilies.add(family);
        corroborationSources.push(items[j].source);
      }
    }

    const corroborationCount = corrobFamilies.size;
    const leftSources  = corroborationSources.filter(s => (MEDIA_BIAS[s]?.lean ?? 0) <= -0.5).length;
    const rightSources = corroborationSources.filter(s => (MEDIA_BIAS[s]?.lean ?? 0) >= 0.5).length;
    const crossIdeological = leftSources > 0 && rightSources > 0;

    let stalenessPenalty = 0;
    try {
      const ageMs = now - new Date(item.pubDate).getTime();
      const ageH  = ageMs / 3_600_000;
      if (ageH > 48) stalenessPenalty = 20;
      else if (ageH > 24) stalenessPenalty = 10;
    } catch { /* ignore bad dates */ }

    const tierBase     = item.tier === 1 ? 78 : item.tier === 2 ? 58 : 38;
    const crossBonus   = crossIdeological ? 12 : 0;
    const credibilityScore = Math.max(
      10,
      Math.min(100, tierBase + Math.min(20, corroborationCount * 4) + crossBonus - stalenessPenalty)
    );

    return {
      ...item,
      corroborationCount,
      corroborationSources: corroborationSources.slice(0, 8),
      credibilityScore,
      singleSource: corroborationCount === 0,
      leftSources,
      rightSources,
      crossIdeological,
    };
  });
}

async function fetchFeed(feed: { name: string; url: string; tier: 1 | 2 | 3 }): Promise<NewsItem[]> {
  const controller = new AbortController();
  const timer      = setTimeout(() => controller.abort(), 8_000);

  try {
    const res = await fetch(feed.url, {
      signal:  controller.signal,
      headers: {
        'User-Agent':      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Accept':          'application/rss+xml, application/xml, text/xml, application/atom+xml, */*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control':   'no-cache',
        'Pragma':          'no-cache',
      },
      next:    { revalidate: 300 },
    });

    if (!res.ok) return [];
    const xml = await res.text();
    if (xml.length > 2_000_000) return [];
    const bias = MEDIA_BIAS[feed.name] ?? { lean: 0, label: 'CENTER', color: '#94a3b8' };
    return extractItems(xml, feed.name).map(item => ({
      ...item,
      tier:      feed.tier,
      mediaBias: bias.lean,
      biasLabel: bias.label,
    }));
  } catch {
    return [];
  } finally {
    clearTimeout(timer);
  }
}

export async function fetchAllNews(): Promise<NewsItem[]> {
  const results = await Promise.allSettled(RSS_FEEDS.map(fetchFeed));
  const allItems: NewsItem[] = [];
  for (const r of results) {
    if (r.status === 'fulfilled') allItems.push(...r.value);
  }

  const seen = new Set<string>();
  const dedupedItems = allItems
    .sort((a, b) => new Date(b.pubDate).getTime() - new Date(a.pubDate).getTime())
    .filter((item) => {
      if (seen.has(item.url)) return false;
      seen.add(item.url);
      return true;
    })
    .slice(0, 120);

  const corrobItems = addCorroborationMetadata(dedupedItems);

  return corrobItems.map(item => {
    const check = kineticRealityCheck(item);
    if (!check.contradiction) return item;
    return {
      ...item,
      kineticContradiction: true,
      contradictionReason:  check.reason,
      credibilityScore: Math.min(item.credibilityScore, 25),
    };
  });
}
