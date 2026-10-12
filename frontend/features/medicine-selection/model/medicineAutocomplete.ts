export interface MedicineEntry {
  n: string; // Formal drug name (e.g. "ツムラ葛根湯エキス顆粒（医療用）")
  k: string; // Katakana reading (e.g. "ツムラカッコントウエキスカリュウ")
  h: string; // Hiragana reading (e.g. "つむらかっことうえきすかりゅう")
  y: string; // YJ code (12 digits, e.g. "5200013D1026")
  g: string; // Generic standard name (e.g. "グリメピリド錠１ｍｇ")
  c: string; // Category (内用, 外用, 注射, 歯科, 他)
}

export interface AutocompleteMatch {
  entry: MedicineEntry;
  score: number;
}

// Map for Hepburn/Kunrei Romaji to Hiragana
const ROMAJI_TABLE: Record<string, string> = {
  kya: "きゃ",
  kyu: "きゅ",
  kyo: "きょ",
  sha: "しゃ",
  shu: "しゅ",
  sho: "しょ",
  cha: "ちゃ",
  chu: "ちゅ",
  cho: "ちょ",
  nya: "にゃ",
  nyu: "にゅ",
  nyo: "にょ",
  hya: "ひゃ",
  hyu: "ひゅ",
  hyo: "ひょ",
  mya: "みゃ",
  myu: "みゅ",
  myo: "みょ",
  rya: "りゃ",
  ryu: "りゅ",
  ryo: "りょ",
  gya: "ぎゃ",
  gyu: "ぎゅ",
  gyo: "ぎょ",
  ja: "じゃ",
  ju: "じゅ",
  jo: "じょ",
  bya: "びゃ",
  byu: "びゅ",
  byo: "びょ",
  pya: "ぴゃ",
  pyu: "ぴゅ",
  pyo: "ぴょ",
  shi: "し",
  chi: "ち",
  tsu: "つ",
  fu: "ふ",
  ka: "か",
  ki: "き",
  ku: "く",
  ke: "け",
  ko: "こ",
  sa: "さ",
  si: "し",
  su: "す",
  se: "せ",
  so: "そ",
  ta: "た",
  ti: "ち",
  tu: "つ",
  te: "て",
  to: "と",
  na: "な",
  ni: "に",
  nu: "ぬ",
  ne: "ね",
  no: "の",
  ha: "は",
  hi: "ひ",
  hu: "ふ",
  he: "へ",
  ho: "ほ",
  ma: "ま",
  mi: "み",
  mu: "む",
  me: "め",
  mo: "も",
  ya: "や",
  yu: "ゆ",
  yo: "よ",
  ra: "ら",
  ri: "り",
  ru: "る",
  re: "れ",
  ro: "ろ",
  wa: "わ",
  wo: "を",
  nn: "ん",
  ga: "が",
  gi: "ぎ",
  gu: "ぐ",
  ge: "げ",
  go: "ご",
  za: "ざ",
  zi: "じ",
  zu: "ず",
  ze: "ぜ",
  zo: "ぞ",
  da: "だ",
  di: "ぢ",
  du: "づ",
  de: "de",
  do: "ど",
  ba: "ば",
  bi: "び",
  bu: "ぶ",
  be: "べ",
  bo: "ぼ",
  pa: "ぱ",
  pi: "ぴ",
  pu: "ぷ",
  pe: "ぺ",
  po: "ぽ",
  a: "あ",
  i: "い",
  u: "う",
  e: "え",
  o: "お",
  "-": "ー",
};

/**
 * Convert Romaji input string to Hiragana.
 * e.g. "kakkon" -> "かっこん", "amari" -> "あまり"
 */
export function romajiToHiragana(romaji: string): string {
  const lower = romaji.toLowerCase();
  let result = "";
  let i = 0;

  while (i < lower.length) {
    // Sokuon (double consonant like kk, tt, pp, ss)
    if (
      i + 1 < lower.length &&
      lower[i] === lower[i + 1] &&
      /[b-df-hj-np-tv-z]/.test(lower[i]) &&
      lower[i] !== "n"
    ) {
      result += "っ";
      i += 1;
      continue;
    }

    // Single 'n' before consonants or end of word
    if (lower[i] === "n" && (i + 1 === lower.length || !/[aiueoy]/.test(lower[i + 1]))) {
      result += "ん";
      i += 1;
      continue;
    }

    // Try 3-char match
    const c3 = lower.slice(i, i + 3);
    if (ROMAJI_TABLE[c3]) {
      result += ROMAJI_TABLE[c3];
      i += 3;
      continue;
    }

    // Try 2-char match
    const c2 = lower.slice(i, i + 2);
    if (ROMAJI_TABLE[c2]) {
      result += ROMAJI_TABLE[c2];
      i += 2;
      continue;
    }

    // Try 1-char match
    const c1 = lower[i];
    if (ROMAJI_TABLE[c1]) {
      result += ROMAJI_TABLE[c1];
      i += 1;
      continue;
    }

    result += c1;
    i += 1;
  }

  return result;
}

/**
 * Convert Katakana to Hiragana.
 */
export function katakanaToHiragana(text: string): string {
  return text.replace(/[\u30a1-\u30f6]/g, (match) =>
    String.fromCharCode(match.charCodeAt(0) - 0x60),
  );
}

/**
 * Convert Hiragana to Katakana.
 */
export function hiraganaToKatakana(text: string): string {
  return text.replace(/[\u3041-\u3096]/g, (match) =>
    String.fromCharCode(match.charCodeAt(0) + 0x60),
  );
}

/**
 * Normalize search string (Zen-kaku to Han-kaku for alphanumeric, normalize spaces).
 */
export function normalizeQuery(query: string): string {
  return query.normalize("NFKC").trim().toLowerCase();
}

/**
 * Perform high-speed fuzzy/prefix search across medicine entries.
 * Returns up to `limit` entries sorted by match quality.
 */
export function searchMedicines(
  rawQuery: string,
  entries: MedicineEntry[],
  limit = 8,
): MedicineEntry[] {
  const q = normalizeQuery(rawQuery);
  if (!q) return [];

  // Generate Hiragana, Katakana, and Romaji-converted variants
  const qHira = katakanaToHiragana(q);
  const qKata = hiraganaToKatakana(q);
  const qFromRomaji = romajiToHiragana(q);
  const qRomajiKata = hiraganaToKatakana(qFromRomaji);

  const scored: AutocompleteMatch[] = [];

  for (let i = 0; i < entries.length; i++) {
    const entry = entries[i];
    let score = 0;

    const nameLower = entry.n.toLowerCase();
    const hira = entry.h;
    const kata = entry.k;
    const genericLower = entry.g.toLowerCase();

    // 1. Direct name match
    if (nameLower.startsWith(q)) {
      score = 200;
    } else if (hira.startsWith(qHira) || hira.startsWith(qFromRomaji)) {
      score = 180;
    } else if (kata.startsWith(qKata) || kata.startsWith(qRomajiKata)) {
      score = 170;
    } else if (nameLower.includes(q)) {
      score = 100;
    } else if (
      hira.includes(qHira) ||
      (qFromRomaji.length >= 2 && hira.includes(qFromRomaji))
    ) {
      score = 90;
    } else if (
      kata.includes(qKata) ||
      (qRomajiKata.length >= 2 && kata.includes(qRomajiKata))
    ) {
      score = 80;
    } else if (
      genericLower &&
      (genericLower.startsWith(q) ||
        genericLower.includes(q) ||
        genericLower.includes(qKata))
    ) {
      score = 60;
    }

    if (score > 0) {
      // Prioritize shorter, cleaner brand names
      const lengthPenalty = Math.min(entry.n.length * 0.5, 20);
      scored.push({ entry, score: score - lengthPenalty });
    }
  }

  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, limit).map((m) => m.entry);
}
