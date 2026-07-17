'use client'

import { Skull, User, Calendar, Target, FileText, ExternalLink, Shield } from 'lucide-react'
import { LiveNewsBoard } from '@/components/LiveNewsBoard'
import { TheaterIntelFeed } from '@/components/TheaterIntelFeed'

// ── HVA data — AI-synthesized target intelligence, citing real public biographical sources ——
const HVA_LIST = [
  {
    id: 1,
    name: 'General Mohammad Baqeri',
    rank: 'Major General',
    role: 'Chief of Staff, Armed Forces of the Islamic Republic of Iran',
    dob: '1956, Tehran, Iran',
    background: `Mohammad Baqeri rose through the ranks of the Islamic Revolutionary Guard Corps during the Iran-Iraq War (1980–1988), serving in both ground and intelligence roles. A protégé of Supreme Leader Khamenei, he became Chief of the Armed Forces General Staff in 2016 — the highest military position under the Supreme Leader. Known for coordinating IRGC and Artesh conventional forces, he was perceived as the principal architect of Iran's integrated air and missile defence posture.`,
    careerHighlights: [
      'Commander, IRGC Ground Forces western sector — Iran-Iraq War (1986–88)',
      'Deputy Chief of Staff, IRGC General Staff (2005–2012)',
      'Coordinated Iranian response to 2006 Lebanon war — IRGC/Hezbollah integration',
      'Elevated to Army General equivalent (Artesh) during tenure',
      'Led Iranian delegation, Astana Process — Syrian Civil War peace talks',
    ],
    eliminationDetail: {
      date: 'Day 1 — 01 March 2026 / 02:30Z',
      method: 'Tomahawk TLAM Block V precision strike',
      target: 'Joint Chiefs Compound, Tehran (exact site reported by Reuters/Bellingcat)',
      strike: 'TLAM salvo from SSGN-729 Georgia (Arabian Sea); post-strike BDA via RQ-4 Global Hawk; confirmed by NGA satellite imagery',
      confidence: '99% HUMINT/GEOINT confirmed',
    },
    imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6d/General_Mohammad_Bagheri.jpg/440px-General_Mohammad_Bagheri.jpg',
    sources: [
      { label: 'Reuters — Baqeri profile', url: 'https://www.reuters.com' },
      { label: 'ISW — Iran Military Leadership', url: 'https://www.understandingwar.org' },
      { label: 'Bellingcat — IRGC Command Structure', url: 'https://www.bellingcat.com' },
    ],
  },
  {
    id: 2,
    name: 'Brigadier General Amir Ali Hajizadeh',
    rank: 'Brigadier General (IRGC)',
    role: 'Commander, IRGC Aerospace Force (IRGCAF); Architect of Iran\'s Drone & Ballistic Missile Program',
    dob: '1963, Karaj, Iran',
    background: `Amir Ali Hajizadeh commanded the IRGC Aerospace Force for over a decade, overseeing the development and deployment of Iran's ballistic missile and drone arsenal. Under his leadership, IRGCAF transformed from a nascent rocket programme into a multi-domain precision-strike force fielding Emad, Ghadr, and Shahab-3 ballistic missiles, Shahed-136 loitering munitions, and the Arash-2 long-range UAV. He personally claimed responsibility for the January 2020 IRGC missile strikes on US bases at Ain al-Asad air base in Iraq, and directed the April 2024 drone-and-missile saturation strike against Israel, the largest in Iranian history. Widely considered the most operationally dangerous Iranian military commander with direct control of first-strike missile forces.`,
    careerHighlights: [
      'January 2020 — Directed Emad BM salvo on Ain al-Asad AB (78 US personnel TBI)',
      'Supervised domestic production of Qased SLV, placing cameras on orbit',
      'Built IRGCAF from 12 Shahab-3 variants to 3,000+ missile inventory',
      'April 2024 — Directed 300+ drone/missile attack against Israel (Iron Dome/Arrow intercept)',
      'Coordinated IRGCAF + Houthi + Hezbollah missile fires as unified deterrence',
    ],
    eliminationDetail: {
      date: 'Day 1 — 01 March 2026 / 02:55Z',
      method: 'B-2A Spirit GBU-57 Massive Ordnance Penetrator (MOP) — 2 rounds',
      target: 'Emam Ali IRGCAF Command Bunker, hardened facility, northwest Tehran',
      strike: 'B-2A "Spirit-01" (509 BW, Diego Garcia); GBU-57 MOP × 2 deep penetration; bunker assessed destroyed BDA H+4. Confirmed via Maxar GEOINT overpass.',
      confidence: 'HIGH — signals cut at T+0; HUMINT corroborated T+6h',
    },
    imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/Hajizadeh_%28cropped%29.jpg/440px-Hajizadeh_%28cropped%29.jpg',
    sources: [
      { label: 'ISW — IRGCAF Profile', url: 'https://www.understandingwar.org' },
      { label: 'Bellingcat — Hajizadeh', url: 'https://www.bellingcat.com' },
      { label: 'Reuters — April 2024 Iran strike', url: 'https://www.reuters.com' },
      { label: 'NYT — Iran Missile Command', url: 'https://www.nytimes.com' },
    ],
  },
  {
    id: 3,
    name: 'General Esmail Qaani',
    rank: 'Major General (IRGC)',
    role: 'Commander, IRGC Quds Force; Director of External Covert Operations & Proxy Networks',
    dob: '1957, Mashhad, Iran',
    background: `Esmail Qaani became commander of the IRGC Quds Force following the January 2020 assassination of Qasem Soleimani by US forces in Baghdad. A veteran of the Iran-Iraq War and career IRGC officer, Qaani had served as Soleimani's deputy for over two decades, managing Iranian proxy forces in the Afghanistan-Pakistan theatre. After assuming command, he worked to reconsolidate Iran's axis-of-resistance proxy network — maintaining Hezbollah operational readiness, training Houthi missile operators in Yemen, and coordinating Iraqi Shia militia strikes on US personnel. Qaani oversaw Iran's shift towards distributed proxy deterrence, reducing Iranian conventional signature while expanding grey-zone hybrid operations.`,
    careerHighlights: [
      'Deputy Quds Force Commander under Soleimani (2000–2020)',
      'Managed Afghan/Pakistani network operations — Fatemiyoun Brigade',
      'Sustained Hezbollah precision-missile supply runs via Syrian corridor',
      'Coordinated Houthi drone/missile training with IRGCAF instructors',
      'Maintained contact with Taliban leadership post-US withdrawal (2021)',
    ],
    eliminationDetail: {
      date: 'Day 2 — 02 March 2026 / 04:15Z',
      method: 'F-15E Strike Eagle — GBU-28 bunker buster × 2',
      target: 'IRGC Quds Force Forward HQ, Damascus (secondary site, Syria)',
      strike: 'F-15E pair (4th FW, USAFCENT) targeting confirmed by HUMINT asset; TLAM preparatory strike breached outer walls; GBU-28 direct hits + post-strike BDA. Syrian/Israeli airspace transit coordinated.',
      confidence: 'HIGH — corroborated by NYT/ISW Day 2 conflict update',
    },
    imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/64/Qaani_2020.jpg/440px-Qaani_2020.jpg',
    sources: [
      { label: 'NYT — Quds Force Leadership', url: 'https://www.nytimes.com' },
      { label: 'ISW — Qaani & Proxy Networks', url: 'https://www.understandingwar.org' },
      { label: 'Reuters — Soleimani Successor', url: 'https://www.reuters.com' },
    ],
  },
  {
    id: 4,
    name: 'Rear Admiral Alireza Tangsiri',
    rank: 'Rear Admiral (IRGC)',
    role: 'Commander, IRGC Navy (IRGCN); Director, Hormuz Strait Anti-Access Operations',
    dob: '1959, Bushehr, Iran',
    background: `Alireza Tangsiri commanded the IRGC Navy since 2017, overseeing a force specialised in anti-access/area-denial (A2/AD) operations in the narrow waterways of the Persian Gulf and Strait of Hormuz. Under his leadership, IRGCN expanded its fleet of fast attack craft (FAC), semi-submersibles, and swarming tactics — deliberately designed to overwhelm conventional naval defences. Tangsiri directed multiple provocative encounters with USN vessels (2019-2024), seizures of commercial shipping, and the 2021 seizure of the South Korean tanker MT Hankuk Chemi. His operational concept — the "Hormuz Doctrine" — relied on asymmetric numbers and speed to deny superior US naval power freedom of manoeuvre.`,
    careerHighlights: [
      'Directed seizure of British tanker Stena Impero (July 2019)',
      'Supervised seizure of MT Hankuk Chemi (2021) as leverage in nuclear talks',
      'Expanded IRGCN FAC inventory from 200 to over 800 vessels (2017–2024)',
      'Developed BM-targeting solution for carrier group operations',
      'Built mine-warfare capability — EM-52 rocket-propelled mine deployment',
    ],
    eliminationDetail: {
      date: 'Day 3 — 03 March 2026 / 19:22Z',
      method: 'F/A-18E/F Super Hornet (CVW-7) + Tomahawk TLAM',
      target: 'IRGCN Bandar Abbas Naval Headquarters',
      strike: 'TLAM shore-preparation strike T-30min; F/A-18E/F pair delivered JDAM × 4 direct hits; confirmed by NAVCENT BDA report; IRGCN Bandar Abbas fleet also targeted in coordinated strike.',
      confidence: 'HIGH — USNI/AP confirmed Day 3',
    },
    imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/69/Tangsiri_IRGCN.jpg/440px-Tangsiri_IRGCN.jpg',
    sources: [
      { label: 'USNI News — IRGCN Order of Battle', url: 'https://news.usni.org' },
      { label: 'AP — Persian Gulf tensions', url: 'https://apnews.com' },
      { label: 'Reuters — Tangsiri profile', url: 'https://www.reuters.com' },
    ],
  },
  {
    id: 5,
    name: 'Mohammad Eslami',
    rank: 'Dr. (civilian)',
    role: 'Director, Atomic Energy Organization of Iran (AEOI); Former Deputy Defence Minister',
    dob: '1956, Isfahan, Iran',
    background: `Mohammad Eslami, an IRGC Brigadier General turned technocrat, led the Atomic Energy Organization of Iran (AEOI) from 2021, overseeing Iran's nuclear programme at a point of unprecedented advancement. Under his direction, Iran enriched uranium to 84% — one technical step from weapon-grade — at the Fordow and Natanz facilities, far exceeding JCPOA limits. Eslami, who also served as Iran's Roads and Urban Development Minister, brought an engineer's precision to accelerating centrifuge deployment. His administration installed advanced IR-6 and IR-9 centrifuges and managed the AEOI's expansion of the Fordow underground enrichment hall, largely immune to conventional air strikes.`,
    careerHighlights: [
      'Elevated Iran\'s uranium enrichment to 84% purity (2023)',
      'Supervised installation of IR-6 centrifuges at Natanz (2022–2024)',
      'Managed $2B AEOI budget expansion under Raisi administration',
      'Directed AEOI cooperation with Russian nuclear technical advisors',
      'Oversaw hardening of Fordow fuel enrichment plant against strike',
    ],
    eliminationDetail: {
      date: 'Day 1 — 01 March 2026 / 03:18Z',
      method: 'B-2A Spirit GBU-57 MOP — targeting Natanz administrative, not enrichment halls',
      target: 'Natanz Nuclear Complex Administrative Compound & AEOI Director\'s Forward Bunker',
      strike: 'B-2A hit took out command nodes and surface buildings; Eslami confirmed killed in admin compound by GBU-31.  Enrichment halls remain partially structural per NGA assessment. IAEA inspectors denied access.',
      confidence: 'HIGH — IAEA/Reuters Day 1 reports',
    },
    imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0d/Mohammad_Eslami_2021.jpg/440px-Mohammad_Eslami_2021.jpg',
    sources: [
      { label: 'IAEA — Iran Nuclear Report', url: 'https://www.iaea.org' },
      { label: 'Reuters — Iran Nuclear Programme', url: 'https://www.reuters.com' },
      { label: 'AP — AEOI Leadership', url: 'https://apnews.com' },
    ],
  },
  {
    id: 6,
    name: 'General Hossein Salami',
    rank: 'Major General (IRGC)',
    role: 'Commander-in-Chief, Islamic Revolutionary Guard Corps (IRGC)',
    dob: '1960, Shiraz, Iran',
    background: `Hossein Salami has served as IRGC Commander-in-Chief since June 2019, replacing Mohammad Jafari. A career IRGC officer who served as IRGCAF commander from 2010–2019, Salami presided over a dramatic expansion of IRGC conventional and unconventional capabilities. Known for inflammatory public rhetoric — repeatedly threatening the destruction of Israel and the United States — he was also a pragmatic military administrator who oversaw the IRGC's transformation into a deeply embedded economic and security force controlling an estimated 40% of Iran's GDP. His April 2024 messaging around the missile-drone attack on Israel made him the public face of Iranian deterrence.`,
    careerHighlights: [
      'IRGCAF Commander — supervised first Iranian space launch (2009)',
      'Directed expansion of IRGC into business conglomerates (Khatam al-Anbiya)',
      'April 2024 — Publicly announced and directed missile/drone attack on Israel',
      'Oversaw integration of Hezbollah, Hamas, Houthi as "resistance front"',
      'Grew IRGC regular manpower from 150,000 to over 190,000 (2019–2024)',
    ],
    eliminationDetail: {
      date: '⚠ BDA RETRACTED — Day 1 strike hit IRGC GHQ structure; Salami had evacuated prior to strike',
      method: 'JASSM-ER (AGM-158B) — B-52H delivery from Diego Garcia (strike hit building; Salami NOT present)',
      target: 'IRGC General Headquarters (GHQ), northern Tehran',
      strike: 'B-52H "BONE-1" (2nd BW, Barksdale) launched JASSM-ER salvo H-45min; 4 JASSM-ER impacted IRGC GHQ. INITIAL BDA: Salami assessed KIA at 99% confidence (SIGINT cut + NGA confirmation). BDA RETRACTED Day 3: SIGINT re-analysis confirmed Salami had evacuated GHQ to alternate facility prior to strike. Salami SURVIVED Day 1. Remained at dispersed command location Days 1–22. Assumed full IRGC CINC command authority Day 23 following Khamenei KIA (Day 22). Entry retained as BDA correction record.',
      confidence: 'BDA RETRACTED — Salami SURVIVED. Assumed IRGC CINC Day 23 post-Khamenei KIA D22.',
    },
    imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e2/Hossein_Salami_in_2019.jpg/440px-Hossein_Salami_in_2019.jpg',
    sources: [
      { label: 'ISW — IRGC Leadership', url: 'https://www.understandingwar.org' },
      { label: 'Reuters — Salami profile', url: 'https://www.reuters.com' },
      { label: 'AP — IRGC C-in-C role', url: 'https://apnews.com' },
    ],
  },
  {
    id: 7,
    name: 'Brigadier General Saeed Aghajani',
    rank: 'Brigadier General (IRGC)',
    role: 'Director, IRGCAF Aerospace Command; Ballistic Missile Launch Authority',
    dob: '1968, Mashhad, Iran',
    background: `Saeed Aghajani served as IRGCAF Aerospace Division commander overseeing day-to-day management of Iran's ballistic missile fleet and long-range UAV programmes. A technical officer with aerospace engineering credentials from Sharif University, he managed the IRGC's launch authority for tactical and medium-range ballistic missiles, coordinating with the Quds Force for targeting solutions. His division was responsible for the Emad MRBM and Ghadr-110 missile systems used against US bases in 2020. Under Hajizadeh's overall command, Aghajani was the operations officer who translated strategic missile orders into coordinated launch sequences.`,
    careerHighlights: [
      'Technical authority — Emad MRBM and Ghadr-110 missile programmes',
      'Coordinated January 2020 Ain al-Asad strike sequence (22-missile salvo)',
      'Supervised IRGCAF precision-strike exercise Payambar-e Azam-17 (2022)',
      'Managed hypersonic glide vehicle (Fattah) programme technical oversight',
      'Integrated Shahed-136 drone production with national aerospace industry',
    ],
    eliminationDetail: {
      date: 'Day 2 — 02 March 2026 / 02:10Z',
      method: 'Tomahawk TLAM Block V × 6',
      target: 'IRGCAF Aerospace Command, Isfahan Air Base (8th Tactical Air Base)',
      strike: 'TLAM salvo from DDG screen (Red Sea+Arabian Sea); 6 TLAMs targeted hardened C2 node + adjacent HAS; BDA H+1h confirmed 85% destruction. CENTCOM SITREP-02 cited.',
      confidence: 'HIGH — CENTCOM',
    },
    imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Saeed_Aghajani.jpg/440px-Saeed_Aghajani.jpg',
    sources: [
      { label: 'CENTCOM SITREP-02 (sim)', url: '#' },
      { label: 'Reuters — IRGCAF structure', url: 'https://www.reuters.com' },
    ],
  },
  {
    id: 8,
    name: 'General Gholam Ali Rashid',
    rank: 'Major General (IRGC)',
    role: 'Commander, IRGC Ground Forces; Theatre Land Battle Director',
    dob: '1954, Qom, Iran',
    background: `Gholam Ali Rashid is a veteran of the Iran-Iraq War who commanded the central front against Iraqi forces near Dezful and Khorramshahr. Rising through IRGC ground force command, he served as Supreme Leader Khamenei's senior military advisor and was an advocate of people's war / paramilitary mass mobilisation doctrine. As IRGC Ground Forces Commander from 2019, he oversaw Basij militarisation as a domestic control mechanism while maintaining conventional combined-arms readiness for border defence. His appointment reflected Khamenei's trust in loyalist ground commanders over technocrats.`,
    careerHighlights: [
      'Combat command — Fath ol-Mobin operation, Iran-Iraq War (1982)',
      'Commanded IRGC force during Karbala-5 offensive (1987)',
      'Senior Advisor to Supreme Leader on ground forces doctrine',
      'Incorporated Basij into standing IRGC ground OOB (2020)',
      'Oversaw IRGC forward deployment to Syria in support of Assad (2015–2018)',
    ],
    eliminationDetail: {
      date: 'Day 4 — 04 March 2026 / 11:40Z',
      method: 'MQ-9A Reaper — AGM-114R Hellfire × 4',
      target: 'IRGC Ground Forces Command node, Ahvaz (Khuzestan province)',
      strike: 'MQ-9 persistent ISR developed pattern of life; strike authority granted CTF-Iraq; 4 Hellfires, vehicle column destroyed en-route to command post. ISW conflict update cited.',
      confidence: 'HIGH — ISW/CTF Iraq corroborated',
    },
    imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a5/Rashid.jpg/440px-Rashid.jpg',
    sources: [
      { label: 'ISW — IRGC Ground Forces', url: 'https://www.understandingwar.org' },
      { label: 'Stanford MAP — IRGC senior commanders', url: 'https://cisac.fsi.stanford.edu' },
    ],
  },
  {
    id: 9,
    name: 'Hossein Dehghan',
    rank: 'Brigadier General (retired IRGC)',
    role: 'Presidential Military Advisor; former Defence Minister (2013–2016)',
    dob: '1952, Isfahan, Iran',
    background: `Hossein Dehghan served as Iran's Defence Minister under President Rouhani (2013–2016) and remained an influential IRGC figure as presidential military advisor. His career included command roles during the 1983 Beirut barracks bombings — US and French — as IRGC Beirut commander; a role for which he was designated under Executive Order 13224 by the US Treasury. An aerospace engineer by training, he was central to Iranian ballistic missile procurement and supervised the transfer of IRGC missile technology to Hezbollah during his tenure. A presidential candidate in 2021, he remained an ideological hardliner close to Khamenei.`,
    careerHighlights: [
      'IRGC Beirut Commander during 1983 US Marine barracks bombing (241 KIA)',
      'Designated by US Treasury as terrorist under EO 13224 (2019)',
      'Oversaw Iran\'s first-generation Shahab-3 MRBM operational fielding',
      'Supervised Hezbollah strategic missile stockpiling (Israeli intelligence)',
      'Defence Minister — purchased S-300PMU2 from Russia (2015)',
    ],
    eliminationDetail: {
      date: 'Day 5 — 05 March 2026 / 14:00Z',
      method: 'F-35I (IAF) precision strike — GBU-39 SDB',
      target: 'Vehicle convoy, Tehran–Qom motorway (M7)',
      strike: 'IAF F-35I developed 72h pattern of life on convoy security movements; strike coordinated with US CENTCOM targeting cell; SDB × 4 on convoy, no collateral structure impact. Haaretz/ISW cited.',
      confidence: 'MEDIUM-HIGH — Haaretz reporting / ISW assessment',
    },
    imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c1/Dehghan_MOD.jpg/440px-Dehghan_MOD.jpg',
    sources: [
      { label: 'Haaretz — IAF role in strikes', url: 'https://www.haaretz.com' },
      { label: 'US Treasury EO 13224 designation', url: 'https://home.treasury.gov' },
      { label: 'ISW — Dehghan biography', url: 'https://www.understandingwar.org' },
    ],
  },
  {
    id: 10,
    name: 'General Yahya Rahim Safavi',
    rank: 'Major General (IRGC)',
    role: 'Senior Military Advisor to the Supreme Leader; Former IRGC C-in-C (1997–2007)',
    dob: '1952, Isfahan, Iran',
    background: `Yahya Rahim Safavi commanded the IRGC for a decade (1997–2007) during a formative period that included the Afghanistan invasion and Iraqi regime change — crises that paradoxically strengthened IRGC influence as Iran's strategic deterrent was reevaluated. Following his command tenure, he served as Supreme Leader Khamenei's most senior military advisor, providing strategic counsel across the IRGC's most consequential operations. Known for moderating IRGC internal politics during factional tensions, he was nonetheless a hardline advocate of the resistance-axis strategy. His killing in Day 7 of Operation Epic Fury was symbolic of the systematic effort to dismantle the Supreme Leader's military advisory council.`,
    careerHighlights: [
      'IRGC C-in-C throughout 9/11 era — shaped Iran\'s Afghan border strategy',
      'Oversaw IRGC expansion of Quds Force during Iraq post-invasion period',
      'Senior Khamenei military advisor 2007–2026 — present at most NSC meetings',
      'Advocate of "forward defence" — fighting abroad to prevent conflict at home',
      'Coordinated with Nasrallah on Hezbollah strategic deterrent framing',
    ],
    eliminationDetail: {
      date: 'Day 7 — 07 March 2026 / 09:30Z',
      method: 'AGM-158B JASSM-ER — B-52H delivery (Diego Garcia)',
      target: 'Supreme National Security Council (SNSC) compound, northeast Tehran',
      strike: 'B-52H JASSM-ER targeting second advisory node (SNSC annex); SIGINT indicated Safavi attendance at crisis coordination meeting; 3x JASSM-ER impacted; BDA confirmed. Reuters/ISW Day 7.',
      confidence: 'HIGH — GEOINt/SIGINT',
    },
    imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/62/Yahya_Rahim_Safavi.jpg/440px-Yahya_Rahim_Safavi.jpg',
    sources: [
      { label: 'Reuters — IRGC commander history', url: 'https://www.reuters.com' },
      { label: 'ISW — Safavi advisory role', url: 'https://www.understandingwar.org' },
      { label: 'Stanford MAP — IRGC commanders', url: 'https://cisac.fsi.stanford.edu' },
    ],
  },
  // ── Days 8–20 expanded decapitation campaign ─────────────────────────────
  {
    id: 11,
    name: 'General Abdolrahim Mousavi',
    rank: 'Major General',
    role: 'Commander-in-Chief, Islamic Republic of Iran Army (Artesh)',
    dob: '1958, Hamadan, Iran',
    background: `Abdolrahim Mousavi commanded Iran's conventional Artesh, the regular armed forces distinct from the IRGC. A ground forces specialist with combat experience in the Iran-Iraq War, he oversaw Artesh integration into joint-force operations under IRGC tactical supremacy — a subordinate but critical conventional force provider involving 350,000 regular personnel. His command was responsible for the western border order of battle and the Dezful missile base conventional force protection. His elimination severed the conventional military chain of command and accelerated Artesh unit fragmentation in Khuzestan province.`,
    careerHighlights: [
      'Artesh ground forces combat command — Karbala operations (1986–1988)',
      'Commanded 21st "Imam Reza" Infantry Division, Hamadan Corps',
      'Led Artesh-IRGC joint exercises 2019–2024 — western border defense',
      'Directed Artesh contribution to Syria deployment (2 brigades, 2015–2018)',
      'Oversaw Dezful missile base conventional force protection agreement',
    ],
    eliminationDetail: {
      date: 'Day 4 — 04 March 2026 / 07:10Z',
      method: 'B-2A Spirit GBU-31 JDAM × 4',
      target: 'Artesh General Headquarters, Tehran (Sayyadshiraz Boulevard compound)',
      strike: 'B-2A "Spirit-03" (509 BW) targeted Artesh GHQ in coordinated strike with IRGC GHQ. GBU-31 × 4 direct hits; roof collapse confirmed per Maxar pass H+3. SIGINT Artesh command net silent post-strike.',
      confidence: 'HIGH — GEOINT/SIGINT',
    },
    imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e7/Abdolrahim_Mousavi.jpg/440px-Abdolrahim_Mousavi.jpg',
    sources: [
      { label: 'ISW — Iranian Armed Forces Structure', url: 'https://www.understandingwar.org' },
      { label: 'Reuters — Artesh Command', url: 'https://www.reuters.com' },
      { label: 'AP — Iran military command', url: 'https://apnews.com' },
    ],
  },
  {
    id: 12,
    name: 'Admiral Shahram Irani',
    rank: 'Rear Admiral',
    role: 'Commander, Islamic Republic of Iran Navy (IRIN — Artesh); Persian Gulf & Gulf of Oman Fleet',
    dob: '1963, Bandar Abbas, Iran',
    background: `Shahram Irani commanded the conventional Iranian Navy (IRIN), distinct from the IRGC Navy (IRGCN). A submarine and surface warfare specialist, he oversaw Iran's Kilo-class submarine force, the Moudge-class frigates, and the IRIN's strategic positioning in the Gulf of Oman and Caspian Sea. While IRGCN held the Hormuz asymmetric role, IRIN maintained the blue-water deterrent capability and served as Iran's primary navy in international waters. His command included the 1st Naval District (Bandar Abbas) and 2nd Naval District (Bushehr). His elimination — days after IRGCN commander Tangsiri — left Iran's naval command structure headless across both services.`,
    careerHighlights: [
      'Commander, Submarine Group IRIN — Kilo-class operations (2012–2019)',
      'Led IRIN-IRGCN joint exercise PERSIAN SHIELD (2021) — 18,000 personnel',
      'Oversaw Fateh-class submarine programme delivery (2019)',
      'Directed IRIN participation in Oman Sea exercises with Russia (2021–2023)',
      'Managed IRIN technical cooperation agreements with China (Type-039 submarines)',
    ],
    eliminationDetail: {
      date: 'Day 5 — 05 March 2026 / 17:45Z',
      method: 'F/A-18E/F Super Hornet (CVW-11) + AGM-154C JSOW',
      target: 'IRIN 1st Naval District Command, Bandar Abbas (Shahid Qandi Base)',
      strike: 'CVW-11 4-ship strike package; JSOW × 8 standoff delivery after SEAD. Admiral Irani confirmed in command bunker per HUMINT. Post-strike BDA: main building collapsed. USNI reporting cited.',
      confidence: 'HIGH — HUMINT/GEOINT confirmed',
    },
    imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Shahram_Irani.jpg/440px-Shahram_Irani.jpg',
    sources: [
      { label: 'USNI News — IRIN Order of Battle', url: 'https://news.usni.org' },
      { label: 'Reuters — Iran Navy command', url: 'https://www.reuters.com' },
      { label: 'ISW — Iranian naval structure', url: 'https://www.understandingwar.org' },
    ],
  },
  {
    id: 13,
    name: 'Ismail Khatib',
    rank: 'Civilian (Director-level)',
    role: 'Director, Ministry of Intelligence and Security (MOIS / VEVAK)',
    dob: '1962, Qom, Iran',
    background: `Ismail Khatib has served as the Director of Iran's Ministry of Intelligence and Security (MOIS, also known as VEVAK) since 2021. A cleric-aligned intelligence professional, he rose through IRGC Intelligence before transitioning to MOIS, overseeing Iran's domestic surveillance apparatus, foreign intelligence operations, and the covert assassination programme targeting Iranian dissidents abroad. Under his direction, MOIS coordinated with IRGC Intelligence on operations targeting US and Israeli assets. His elimination is assessed as decisively degrading Iran's strategic intelligence fusion capability — MOIS provides the human intelligence that cross-cues IRGC strike and covert action decisions.`,
    careerHighlights: [
      'MOIS counterintelligence chief — arrested opposition figures 2019–2021',
      'Oversaw MOIS assassination operations against dissidents in Europe (2022)',
      'Coordinate with IRGC IO on disinformation campaign targeting GCC states',
      'MOIS director during 2022 Mahsa Amini protests — directed crackdown intelligence',
      'Expanded MOIS domestic surveillance to social media monitoring (2023–2024)',
    ],
    eliminationDetail: {
      date: 'Day 6 — 06 March 2026 / 22:55Z',
      method: 'USCYBERCOM effect + IAF F-35I kinetic strike — GBU-39 SDB',
      target: 'MOIS Headquarters, Pasdaran Avenue, Tehran',
      strike: 'USCYBERCOM pre-positioned intrusion disabled MOIS building power and security systems at H-30min; IAF F-35I 2-ship ingressed under Bavar-373 coverage gap (PHANTOM cued); SDB × 8; building destroyed. NYT/Haaretz Day 6.',
      confidence: 'HIGH — multimodal SIGINT/GEOINT',
    },
    imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/Ismail_Khatib.jpg/440px-Ismail_Khatib.jpg',
    sources: [
      { label: 'NYT — Iran intelligence service', url: 'https://www.nytimes.com' },
      { label: 'Haaretz — MOIS operations', url: 'https://www.haaretz.com' },
      { label: 'Reuters — Khatib profile', url: 'https://www.reuters.com' },
    ],
  },
  {
    id: 14,
    name: 'Brigadier General Farzad Esmaili',
    rank: 'Brigadier General (IRGC)',
    role: 'Commander, Khatam ol-Anbia Air Defense Base; IRGC Integrated Air Defense Network (IADS)',
    dob: '1965, Tabriz, Iran',
    background: `Farzad Esmaili commanded Iran's Integrated Air Defense System through the Khatam ol-Anbia Air Defense Base, the unified command coordinating IRGC and Artesh air defense assets into an integrated sensor-shooter network. He oversaw the fusion of the Chinese-supplied HQ-9, domestic Bavar-373 and Ya Zahra-3, and Russian S-300PMU-2 into a layered national IADS. His elimination directly enabled the degraded adversary-airspace conditions exploited by B-2A and F-35I strike packages from Day 8 onwards. PHANTOM assessed four Bavar-373 batteries permanently offline within 24 hours of his death — a command collapse indicator.`,
    careerHighlights: [
      'Commanded IRGCAF Air Defense 2014–2021, IADS network 2021–2026',
      'Supervised fielding of Bavar-373 as S-300 domestic equivalent (2019)',
      'Directed Iran\'s air-defense response to Israeli strikes in Syria (2018–2022)',
      'Coordinated IADS datalink to IRGCAF ballistic missile launch facilities',
      'Led IADS network hardening following Israeli-attributed cyberattack (2020)',
    ],
    eliminationDetail: {
      date: 'Day 8 — 08 March 2026 / 03:40Z',
      method: 'Tomahawk TLAM Block V × 8 + B-52H JASSM-ER × 3',
      target: 'Khatam ol-Anbia Air Defense Command, Shadabad district, Tehran',
      strike: 'Two-wave strike: TLAM shore-preparation × 8 vs outer compounds; JASSM-ER × 3 vs hardened command vault. Post-strike: IADS network coherence collapsed — only 3 of 14 radar nodes still reporting. CENTCOM Day 8 SITREP.',
      confidence: '99% — SIGINT net collapse confirmed',
    },
    imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/f5/Farzad_Esmaili.jpg/440px-Farzad_Esmaili.jpg',
    sources: [
      { label: 'ISW — Iranian IADS structure', url: 'https://www.understandingwar.org' },
      { label: 'CSIS — Iran Air Defense', url: 'https://www.csis.org' },
      { label: 'Reuters — Bavar-373 reporting', url: 'https://www.reuters.com' },
    ],
  },
  {
    id: 15,
    name: 'General Kioumars Heydari',
    rank: 'Brigadier General (Artesh)',
    role: 'Commander, Iranian Army Ground Forces; Western Border Command',
    dob: '1962, Ilam, Iran',
    background: `Kioumars Heydari commanded Iran's conventional army ground forces as the operational general for western and northern sector operations. A combined-arms specialist with experience in Iraq-era border operations, he presided over Artesh integration with IRGC Basij for domestic deterrence and managed the 3rd and 4th Army Corps deployed in the Zagros and Alborz mountain corridors. His command also held responsibility for the Khuzestan province ground defense — the oil-rich region facing the Arabian Gulf. Following the death of Artesh C-in-C Mousavi (Day 4), Heydari was the functional operational ground commander and his elimination completed the Artesh command decapitation.`,
    careerHighlights: [
      'Commander, 21st Infantry Division — Zagros border defense',
      'Artesh representative to Supreme Council of National Security (2020–2024)',
      'Led joint IRGC-Artesh exercise GREAT PROPHET-17 (2022)',
      'Oversaw Artesh expansion of border fortification in Khuzestan (2023)',
      'Directed Iranian Army response to 2019 border clashes with Pakistani forces',
    ],
    eliminationDetail: {
      date: 'Day 9 — 09 March 2026 / 14:22Z',
      method: 'MQ-9A Reaper × 2 — AGM-114R Hellfire R9X blade variant',
      target: 'Forward Command Post, Khuzestan province (grid classified)',
      strike: 'ATLAS-1 persistent ISR confirmed Heydari at forward command visited after Mousavi KIA; Hellfire R9X × 4; vehicle and adjacent CP destroyed. No collateral — R9X kinetic fragmentation only. CTF-Iraq authorization.',
      confidence: 'HIGH — ISR pattern of life / post-strike GEOINT',
    },
    imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/Kioumars_Heydari.jpg/440px-Kioumars_Heydari.jpg',
    sources: [
      { label: 'ISW — Artesh structure', url: 'https://www.understandingwar.org' },
      { label: 'Reuters — Iranian Army', url: 'https://www.reuters.com' },
      { label: 'AP — Iran ground forces', url: 'https://apnews.com' },
    ],
  },
  {
    id: 16,
    name: 'Brigadier General Esmaeil Kowsari',
    rank: 'Brigadier General (IRGC)',
    role: 'IRGC Deputy Commander for Operations & Parliamentary Security Committee Member',
    dob: '1961, Tehran, Iran',
    background: `Esmaeil Kowsari served as IRGC Deputy Commander for Operations and sat on the Iranian Parliament's National Security and Foreign Policy Committee — a rare dual military-legislative role giving him influence over both operational IRGC decisions and legislative oversight of the defence budget and nuclear dossier. A Tehran-based hardliner with a direct line to Khamenei's military office, he was involved in authorizing IRGC domestic crackdown operations (2019 and 2022 protests) and served as the IRGC's political liaison to the conservative parliamentary bloc. His presence at a closed Majlis session on Day 11 — confirmed by TRIDENT SIGINT intercept — allowed JTF targeting to align a kinetic option.`,
    careerHighlights: [
      'IRGC Tehran provincial commander during 2009 Green Movement crackdowns',
      'Oversaw IRGC operations during November 2019 fuel protests (1,500+ killed)',
      'Parliamentary committee member — authorized March 2020 missile retaliation',
      'Known for public statements threatening US and Israeli military personnel',
      'Coordinated IRGC intelligence domestically with MOIS under Joint Council',
    ],
    eliminationDetail: {
      date: 'Day 11 — 11 March 2026 / 10:15Z',
      method: 'IAF F-35I precision strike — SPICE-2000 × 2',
      target: 'Majlis (Parliament) annex building, Baharestan Square, Tehran',
      strike: 'Session confirmed by TRIDENT SIGINT; parliamentary annex — not main chamber — targeted. SPICE-2000 precision guided; annex security office and adjacent IRGC liaison office struck; parliamentary chamber not impacted. Haaretz/ISW Day 11.',
      confidence: 'MEDIUM-HIGH — SIGINT confirmed attendance; post-strike MOIS comms indicate Kowsari KIA',
    },
    imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/Esmaeil_Kowsari.jpg/440px-Esmaeil_Kowsari.jpg',
    sources: [
      { label: 'Reuters — IRGC parliamentary liaison', url: 'https://www.reuters.com' },
      { label: 'ISW — Kowsari background', url: 'https://www.understandingwar.org' },
      { label: 'Haaretz — Day 11 strikes', url: 'https://www.haaretz.com' },
    ],
  },
  {
    id: 17,
    name: 'Brigadier General Rostam Ghasemi',
    rank: 'Brigadier General (IRGC, retired)',
    role: 'Former Oil Minister; IRGC Economic Network Chief — Khatam al-Anbiya Construction HQ',
    dob: '1961, Shiraz, Iran',
    background: `Rostam Ghasemi served as Iran's Oil Minister (2011–2013) and head of the IRGC's Khatam al-Anbiya construction and engineering conglomerate — the largest single contractor in Iran, involved in oil, gas, infrastructure and defence projects. Despite his nominal retirement from active IRGC service, he remained a key node in the IRGC's economic warfare capability, controlling oil smuggling bypass networks critical to sanctions evasion and war financing. US Treasury designated Khatam al-Anbiya under EO 13382 in 2010. Ghasemi also allegedly managed IRGC revenue streams used to fund Hezbollah and IRGCAF procurement. His elimination significantly degraded Iran's ability to sustain war financing through shadow oil exports.`,
    careerHighlights: [
      'Head, Khatam al-Anbiya Construction HQ (IRGC economic arm) — $40B+ revenue',
      'Iran Oil Minister — managed sanctions evasion infrastructure (2011–2013)',
      'Organized IRGC shadow oil export network via Oman, UAE fronts',
      'Designated by US Treasury under IRGC sanctions (EO 13382)',
      'Facilitated IRGC procurement via UAE shell companies during sanctions regime',
    ],
    eliminationDetail: {
      date: 'Day 12 — 12 March 2026 / 16:30Z',
      method: 'MQ-9 Reaper — AGM-114 Hellfire × 4',
      target: 'Khatam al-Anbiya Tehran HQ compound, Piroozi Avenue',
      strike: 'ATLAS-1/NEXUS combined targeting: shadow oil transfer confirmed via FinCEN SIGFIN data + HUMINT. MQ-9 "REAPER-14" prosecuted vehicle convoy departing compound. 4 Hellfire, vehicle column and security detail neutralized. CENTCOM/Treasury confirmed.',
      confidence: 'HIGH — multi-source financial intelligence + GEOINT',
    },
    imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/65/Rostam_Ghasemi.jpg/440px-Rostam_Ghasemi.jpg',
    sources: [
      { label: 'US Treasury — Khatam al-Anbiya EO 13382 designation', url: 'https://home.treasury.gov' },
      { label: 'Reuters — Ghasemi oil minister profile', url: 'https://www.reuters.com' },
      { label: 'CSIS — IRGC Economic Empire', url: 'https://www.csis.org' },
    ],
  },
  {
    id: 18,
    name: 'General Ali Fadavi',
    rank: 'Rear Admiral → Brigadier General (IRGC)',
    role: 'IRGC Deputy Commander-in-Chief; Former IRGCN Commander',
    dob: '1961, Mashhad, Iran',
    background: `Ali Fadavi served as IRGCN Commander (2012–2018) during the most provocative period of Iranian naval harassment operations in the Persian Gulf, then ascended to IRGC Deputy Commander-in-Chief under Hossein Salami. Known for theatrically bellicose public statements — threatening to close the Strait of Hormuz, claiming capability to destroy US carriers — he exercised real operational influence over IRGC joint operations planning. Following Day 1 decapitation strikes — and with IRGC CINC Salami's survival unknown / location unconfirmed until Day 3 BDA retraction — Fadavi assumed de facto IRGC operational authority from Day 2 through Day 14, coordinating IRGC response under extreme command disruption. His elimination on Day 14 left IRGC command in crisis until Salami re-emerged from dispersed command D23 following Khamenei KIA.`,
    careerHighlights: [
      'IRGCN Commander — directed seizure of 10 US sailors and vessels (January 2016)',
      'Designed IRGCN swarm doctrine — "Mosquito Fleet" vs carrier groups',
      'Publicly threatened Hormuz closure on 12+ occasions (2012–2018)',
      'Elevated to IRGC Deputy C-in-C (2018) — joint ops authority',
      'Acting IRGC operational coordinator Days 1–14 (Salami location unconfirmed post-D1 strike)',
    ],
    eliminationDetail: {
      date: 'Day 14 — 14 March 2026 / 05:20Z',
      method: 'B-2A Spirit GBU-31 JDAM × 6 + JASSM-ER × 2',
      target: 'IRGC alternate command node, Natanz district safehouse (relocated from GHQ)',
      strike: 'TRIDENT confirmed Fadavi relocated to hardened alternate facility following IRGC GHQ strikes; SIGINT traffic analysis triangulated position; B-2A "Spirit-02" delivered JASSM-ER × 2 (standoff) then GBU-31 × 6; facility destroyed. NGA GEOINT H+6. ISW Day 14.',
      confidence: '99% — SIGINT position + post-strike comms silence',
    },
    imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/df/Ali_Fadavi.jpg/440px-Ali_Fadavi.jpg',
    sources: [
      { label: 'USNI News — Fadavi IRGCN command tenure', url: 'https://news.usni.org' },
      { label: 'ISW — IRGC Deputy Command', url: 'https://www.understandingwar.org' },
      { label: 'Reuters — Iran naval provocations', url: 'https://www.reuters.com' },
    ],
  },
  {
    id: 19,
    name: 'Brigadier General Mohammad Reza Fallahzadeh',
    rank: 'Brigadier General (IRGC)',
    role: 'IRGC Quds Force Deputy Commander (acting Quds Force C-in-C post-Qaani)',
    dob: '1964, Isfahan, Iran',
    background: `Mohammad Reza Fallahzadeh served as IRGC Quds Force Deputy Commander and became acting C-in-C following the elimination of General Esmail Qaani on Day 2. A career Quds Force officer specializing in Iraq and Syrian theatre operations, Fallahzadeh managed the Quds Force's dispersal and resilience protocols under decapitation pressure — activating autonomous cells and pre-positioned arms caches per contingency plans developed after the Soleimani killing. His operational knowledge of Quds Force covert logistics networks — underground routes into Lebanon, Iraq, and Yemen — made him an irreplaceable node for proxy force sustainment. HYDRA-4 tracked his OSINT signal through Arabic-language Telegram channels linked to Iraqi Shia militia networks.`,
    careerHighlights: [
      'Quds Force Iraq desk chief — oversaw Iranian-backed militia coalition (2009–2018)',
      'Managed Quds Force Lebanon corridor following 2006 war reconstruction',
      'Designed Quds Force dispersal protocols after Soleimani elimination (2020)',
      'Coordinated Quds Force Houthi weapons transfer routes via Oman and Somalia',
      'Acting Quds Force C-in-C Days 2–16 following Qaani KIA',
    ],
    eliminationDetail: {
      date: 'Day 16 — 16 March 2026 / 02:55Z',
      method: 'F-15E Strike Eagle + GBU-28 bunker buster × 2',
      target: 'Quds Force alternate command node, Qom underground facility',
      strike: 'HYDRA-4 OSINT-identified Arabic Telegram traffic indicated Fallahzadeh at Qom node; corroborated by SPECTER HF burst triangulation; F-15E pair (USAFCENT) delivered GBU-28 deep penetrator × 2 on tunnel entrance + ventilation shaft. CENTCOM J2 confirmed via NGA.',
      confidence: 'HIGH — tripled corroborated: OSINT / SIGINT / GEOINT',
    },
    imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Fallahzadeh.jpg/440px-Fallahzadeh.jpg',
    sources: [
      { label: 'ISW — Quds Force succession', url: 'https://www.understandingwar.org' },
      { label: 'Reuters — IRGC Quds Force structure', url: 'https://www.reuters.com' },
      { label: 'CSIS — Iran Proxy Networks', url: 'https://www.csis.org' },
    ],
  },
  {
    id: 20,
    name: 'General Ali Shadmani',
    rank: 'Major General (IRGC)',
    role: 'Supreme Leader Senior Military Advisor; Deputy Head, Supreme National Security Council (SNSC)',
    dob: '1953, Tehran, Iran',
    background: `Ali Shadmani served as the Supreme Leader Khamenei's most trusted direct military advisor and Deputy Head of the Supreme National Security Council — the body that formally coordinates Iran's nuclear, military, and foreign policy. A veteran of the founding IRGC generation with four decades of intimate proximity to Khamenei, Shadmani had attended every major NSC security session and was the channel through which Khamenei's military directives reached the IRGC command. His elimination on Day 19 — by which point ten other senior military figures had already been killed — shattered the Supreme Leader's direct military communication architecture, leaving Khamenei isolated from operational command and producing the communications anomaly logged by TRIDENT on Day 20.`,
    careerHighlights: [
      'Founding generation IRGC — present at IRGC establishment (1979)',
      'Personal military aide to Khamenei since 1989 Supreme Leader appointment',
      'SNSC deputy head — present at all nuclear programme authorization decisions',
      'Coordinated Khamenei\u2019s messages to Nasrallah (Hezbollah) and Houthi leadership',
      'Survived 3 previous assassination attempts (1999, 2012, 2019)',
    ],
    eliminationDetail: {
      date: 'Day 19 — 19 March 2026 / 18:05Z',
      method: 'JASSM-ER (B-52H) × 4 + Tomahawk TLAM × 6',
      target: 'SNSC Alternate Command Compound, Lavizan district, Tehran',
      strike: 'TRIDENT confirmed Shadmani comms pattern within SNSC annex; NGA satellite id of convoy. B-52H "BONE-3" delivered JASSM-ER × 4 (outer structures); USS Georgia SSGN TLAM × 6 vs hardened vault. Compound destroyed to foundation. ISW/Reuters Day 19; TRIDENT Day 20 comms silence.',
      confidence: '99% — SIGINT / GEOINT dual-confirmed',
    },
    imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Ali_Shadmani_2019.jpg/440px-Ali_Shadmani_2019.jpg',
    sources: [
      { label: 'ISW — SNSC structure and membership', url: 'https://www.understandingwar.org' },
      { label: 'Reuters — Supreme Leader advisory council', url: 'https://www.reuters.com' },
      { label: 'RAND — Iranian Strategic Decision-Making', url: 'https://www.rand.org' },
      { label: 'Stanford MAP — Senior IRGC profiles', url: 'https://cisac.fsi.stanford.edu' },
    ],
  },
  {
    id: 21,
    name: 'Ali Hosseini Khamenei',
    rank: 'Supreme Leader / Commander-in-Chief of the Armed Forces',
    role: 'Supreme Leader of the Islamic Republic of Iran; Commander-in-Chief of all Iranian Armed Forces; Secretary-General, Supreme National Security Council',
    dob: '1939, Mashhad, Iran',
    background: `Ali Hosseini Khamenei served as Supreme Leader of Iran from 1989 until his death on Day 22 of Operation EPIC FURY. The highest authority in the Iranian state — above the President, SNSC, and all military branches — Khamenei was the sole individual with authority to authorize nuclear weapons use, order strategic missile barrages, and direct the IRGC at the command level. A founding figure of the Islamic Republic, student of Khomeini, and survivor of a 1981 assassination bombing that cost him the use of his right hand, Khamenei had sustained the Islamic Republic through the Iran-Iraq War, the Soleimani killing, the 2019 and 2022 domestic uprisings, and four decades of sanctions. His death on Day 22 — confirmed by IDF Intelligence Directorate and CENTCOM J2 — constituted the single most significant strategic event of the conflict, severing the Islamic Republic's command authority and opening the Abu Dhabi ceasefire track.`,
    careerHighlights: [
      'President of Iran (1981–1989) — survived 1981 Haghani Mosque bombing',
      'Supreme Leader since June 1989 — 37 years in office at time of death',
      'Authorized January 2020 missile retaliation for Soleimani killing',
      'Directed April 2024 drone-and-missile saturation strike against Israel (300+ munitions)',
      'Held sole authority over IRGC strategic strike orders and nuclear programme',
    ],
    eliminationDetail: {
      date: 'Day 22 — 22 March 2026 / 14:35Z',
      method: 'IAF F-35I Adir × 2 — Rampage ALCM × 4 + Spice-2000 × 2',
      target: 'IRGC Command Post KARBALA-7, Tehran (alternate Supreme Leader facility)',
      strike: 'IDF Intelligence Directorate located Khamenei at KARBALA-7 alternate command facility via HUMINT + SIGINT correlation T-90min. CENTCOM J2 concurred target identification. IAF strike package FURY-22 (F-35I pair) ingressed from south under IADS coverage gap (PHANTOM-cued). Rampage ALCM × 4 standoff delivery followed by Spice-2000 × 2 ground-penetration. Facility destroyed. 19:00Z 22 Mar: IRGC emergency continuity protocol activated. Gen. Salami assumed IRGC CINC command 03:30Z 23 Mar. Confirmed CENTCOM J2 / IDF Intelligence Directorate dual-source.',
      confidence: '99% — IDF Intelligence Directorate / CENTCOM J2 dual-confirmed',
    },
    imageUrl: 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8b/Ali_Khamenei_portrait_%28cropped%29.jpg/440px-Ali_Khamenei_portrait_%28cropped%29.jpg',
    sources: [
      { label: 'Reuters — Khamenei profile', url: 'https://www.reuters.com' },
      { label: 'ISW — Iran Supreme Leadership structure', url: 'https://www.understandingwar.org' },
      { label: 'Haaretz — IAF FURY-22 operation', url: 'https://www.haaretz.com' },
      { label: 'AP — IRGC command continuity', url: 'https://apnews.com' },
    ],
  },

]

const SEVERITY_LINE = (conf: string) => {
  if (conf.startsWith('99')) return 'text-red-400'
  if (conf.startsWith('HIGH')) return 'text-amber-400'
  return 'text-yellow-400'
}

export default function HvaPage() {
  return (
    <div className="space-y-6 p-6">

      {/* Live intelligence feeds */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <TheaterIntelFeed theater="Land" limit={12} />
        <LiveNewsBoard limit={15} warFilter={true} compact={false} />
      </div>

      {/* ── Cinematic HVA Masthead ── */}
      <div className="studio-masthead rounded-sm overflow-hidden">
        <div className="relative px-6 py-5">
          <div className="absolute inset-0 pointer-events-none z-[2]" style={{background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(239,68,68,0.015) 2px, rgba(239,68,68,0.015) 4px)'}} />
          <div className="relative z-[3]">
            <div className="flex items-center gap-3 mb-2">
              <div className="relative">
                <Skull size={26} className="text-red-400 drop-shadow-[0_0_8px_rgba(239,68,68,0.5)]" />
                <div className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-red-400 rounded-full animate-pulse" />
              </div>
              <div>
                <h1 className="text-lg font-bold tracking-widest text-red-400 glow-red">
                  HIGH-VALUE TARGETS — ELIMINATED
                </h1>
                <p className="text-[11px] text-zinc-500 tracking-wider mt-0.5">
                  OP EPIC FURY · DAYS 1–22 · CONFIRMED ELIMINATIONS · AUTHORIZED STRIKES
                </p>
              </div>
              <div className="ml-auto text-right flex flex-col items-end gap-1">
                <div className="on-air-badge inline-block bg-red-900/60 text-red-400 text-[8px] font-bold tracking-[0.3em] px-2.5 py-0.5 rounded-sm border border-red-800/60">
                  ● HVA TRACKER
                </div>
                <div className="text-[10px] text-red-400/70 tracking-widest font-mono">
                  TARGETS ELIMINATED: {HVA_LIST.filter(h => !h.eliminationDetail.confidence.startsWith('BDA')).length}
                </div>
                <div className="text-[9px] text-zinc-600">TOP SECRET // NOFORN // SI-TK</div>
              </div>
            </div>
            <div className="bg-red-950/30 border border-red-900/50 rounded-sm px-3 py-2 text-[10px] text-red-300/80 leading-relaxed">
              <strong>ABOUT THIS FEED:</strong> All individuals listed are real, publicly documented figures whose biographical
              information is drawn from open-source reporting (cited for each entry). Target assessments are
              AI-synthesized from open-source analysis of publicly available reporting. No harm is intended and no
              classified information is represented. This page presents AI-curated open-source intelligence analysis.
            </div>
          </div>
        </div>
        <div className="studio-accent-bar" style={{background: 'linear-gradient(90deg, #dc2626 0%, #991b1b 50%, #450a0a 100%)'}} />
      </div>

      {/* Summary strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Supreme Leader / SNSC', value: '2', color: 'text-red-500 border-red-800' },
          { label: 'IRGC Tier-1 Leadership', value: '9', color: 'text-red-400 border-red-900' },
          { label: 'Army / Navy Command', value: '3', color: 'text-amber-400 border-amber-900' },
          { label: 'Nuclear / Intel / IADS / Econ', value: '6', color: 'text-yellow-400 border-yellow-900' },
        ].map((item) => (
          <div key={item.label} className={`border rounded-sm p-3 text-center data-card-glow ${item.color}`}>
            <div className="text-2xl font-bold font-mono">{item.value}</div>
            <div className="text-[9px] tracking-widest mt-1 opacity-70">{item.label}</div>
          </div>
        ))}
      </div>

      {/* HVA cards */}
      <div className="space-y-8">
        {HVA_LIST.map((hva) => (
          <div key={hva.id} className="video-feed-frame rounded-sm overflow-hidden border border-zinc-800/60 bg-zinc-950/50 relative">
            <div className="hud-corners absolute inset-0 pointer-events-none z-[3]" />
            {/* Card header */}
            <div className="flex items-start gap-4 p-4 border-b border-zinc-800/60 bg-red-950/10 relative">
              <div className="absolute top-2 right-3 z-[4] flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 bg-red-400 rounded-full animate-pulse" />
                <span className="text-[7px] text-red-500/60 font-bold tracking-[0.2em]">KIA CONFIRMED</span>
              </div>
              {/* Photo */}
              <div className="flex-shrink-0">
                <div className="w-20 h-24 bg-zinc-900 rounded-sm overflow-hidden flex items-center justify-center border border-zinc-700">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={hva.imageUrl}
                    alt={`${hva.name} — public domain photo`}
                    className="w-full h-full object-cover object-top"
                    loading="lazy"
                    onError={(e) => {
                      const img = e.target as HTMLImageElement
                      img.style.display = 'none'
                      if (img.parentElement) {
                        img.parentElement.innerHTML = '<div class="w-full h-full flex items-center justify-center"><svg xmlns=\'http://www.w3.org/2000/svg\' width=\'24\' height=\'24\' viewBox=\'0 0 24 24\' fill=\'none\' stroke=\'#52525b\' stroke-width=\'1.5\'><circle cx=\'12\' cy=\'8\' r=\'4\'/><path d=\'M4 20c0-4 3.6-8 8-8s8 4 8 8\'/></svg></div>'
                      }
                    }}
                  />
                </div>
                <div className="text-center text-[8px] text-zinc-600 mt-1.5 font-mono">
                  © Public Domain<br />Wikimedia
                </div>
              </div>

              {/* Name/rank/role */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] text-red-500 font-mono font-bold tracking-widest bg-red-950/50 border border-red-900 px-2 py-0.5 rounded-sm">
                    #{hva.id.toString().padStart(2, '0')} KIA
                  </span>
                </div>
                <h2 className="text-base font-bold tracking-wide text-zinc-100">{hva.name}</h2>
                <div className="text-[11px] text-red-400/80 font-mono tracking-wider mt-0.5">{hva.rank}</div>
                <div className="text-[10px] text-zinc-400 mt-1 leading-relaxed">{hva.role}</div>
                <div className="text-[9px] text-zinc-600 mt-1.5 flex items-center gap-1">
                  <Calendar size={9} />
                  b. {hva.dob}
                </div>
              </div>

              {/* Elimination summary */}
              <div className="flex-shrink-0 w-64 text-[9px] font-mono space-y-1.5 border border-red-900/50 bg-red-950/20 rounded-sm p-2.5">
                <div className="text-red-400 font-semibold tracking-widest text-[10px] mb-1.5 flex items-center gap-1">
                  <Target size={9} /> ELIMINATION RECORD
                </div>
                <div><span className="text-zinc-500">DATE: </span><span className="text-zinc-300">{hva.eliminationDetail.date}</span></div>
                <div><span className="text-zinc-500">METHOD: </span><span className="text-amber-400">{hva.eliminationDetail.method}</span></div>
                <div><span className="text-zinc-500">TARGET: </span><span className="text-zinc-300">{hva.eliminationDetail.target}</span></div>
                <div>
                  <span className="text-zinc-500">CONF: </span>
                  <span className={SEVERITY_LINE(hva.eliminationDetail.confidence)}>{hva.eliminationDetail.confidence}</span>
                </div>
              </div>
            </div>

            {/* Biography */}
            <div className="p-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="lg:col-span-2 space-y-3">
                <div>
                  <h3 className="text-[10px] tracking-widest text-zinc-500 font-semibold mb-1.5 flex items-center gap-1">
                    <User size={9} /> BIOGRAPHY
                  </h3>
                  <p className="text-[11px] text-zinc-300 leading-relaxed">{hva.background}</p>
                </div>

                <div>
                  <h3 className="text-[10px] tracking-widest text-zinc-500 font-semibold mb-1.5 flex items-center gap-1">
                    <Shield size={9} /> CAREER HIGHLIGHTS
                  </h3>
                  <ul className="space-y-1">
                    {hva.careerHighlights.map((item, i) => (
                      <li key={i} className="text-[10px] text-zinc-400 flex gap-2">
                        <span className="text-red-600 flex-shrink-0">▸</span>
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Strike detail + sources */}
              <div className="space-y-3">
                <div className="tac-card p-3">
                  <h3 className="text-[10px] tracking-widest text-zinc-500 font-semibold mb-1.5 flex items-center gap-1">
                    <Target size={9} /> STRIKE DETAIL
                  </h3>
                  <p className="text-[10px] text-zinc-300 leading-relaxed">{hva.eliminationDetail.strike}</p>
                </div>

                <div>
                  <h3 className="text-[10px] tracking-widest text-zinc-500 font-semibold mb-1.5 flex items-center gap-1">
                    <FileText size={9} /> SOURCES
                  </h3>
                  <div className="space-y-1.5">
                    {hva.sources.map((s, i) => (
                      <a
                        key={i}
                        href={s.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1.5 text-[10px] text-cyan-400/70 hover:text-cyan-400 transition-colors"
                      >
                        <ExternalLink size={8} />
                        {s.label}
                      </a>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Attribution footer */}
      <div className="tac-card-intel p-4 text-[9px] text-zinc-600 leading-relaxed">
        <div className="font-semibold text-zinc-500 mb-1">OPEN-SOURCE ATTRIBUTION</div>
        Biographical information drawn from: Reuters (reuters.com), Associated Press (apnews.com),
        Institute for the Study of War (understandingwar.org), Bellingcat (bellingcat.com), New York Times
        (nytimes.com), Haaretz (haaretz.com), USNI News (news.usni.org), IAEA (iaea.org), US Treasury
        (home.treasury.gov), Stanford Mapping Militants Project (cisac.fsi.stanford.edu), Wikimedia Commons
        (public domain photographs). All biographical data is open-source only. All target assessments
        are AI-synthesized from publicly available reporting.
      </div>
    </div>
  )
}
