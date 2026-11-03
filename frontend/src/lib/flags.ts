// National-team → flag emoji. World Cup is national teams, so a flag next to
// every name gives the board instant identity. Keys are matched case- and
// punctuation-insensitively (see `flag()`), and many naming variants (ESPN vs
// our DB vs common usage) point at the same flag, so every country resolves.
const FLAGS: Record<string, string> = {
  afghanistan: "🇦🇫", albania: "🇦🇱", algeria: "🇩🇿", angola: "🇦🇴",
  argentina: "🇦🇷", armenia: "🇦🇲", australia: "🇦🇺", austria: "🇦🇹",
  azerbaijan: "🇦🇿", bahrain: "🇧🇭", bangladesh: "🇧🇩", belgium: "🇧🇪",
  benin: "🇧🇯", bolivia: "🇧🇴", "bosnia and herzegovina": "🇧🇦",
  "bosnia herzegovina": "🇧🇦", bosnia: "🇧🇦", botswana: "🇧🇼", brazil: "🇧🇷",
  bulgaria: "🇧🇬", "burkina faso": "🇧🇫", burundi: "🇧🇮", cameroon: "🇨🇲",
  canada: "🇨🇦", "cape verde": "🇨🇻", "cabo verde": "🇨🇻", chile: "🇨🇱",
  china: "🇨🇳", "china pr": "🇨🇳", colombia: "🇨🇴", comoros: "🇰🇲",
  congo: "🇨🇬", "congo dr": "🇨🇩", "dr congo": "🇨🇩",
  "democratic republic of congo": "🇨🇩", "costa rica": "🇨🇷",
  "ivory coast": "🇨🇮", "cote d'ivoire": "🇨🇮", "côte d'ivoire": "🇨🇮",
  croatia: "🇭🇷", cuba: "🇨🇺", curacao: "🇨🇼", "curaçao": "🇨🇼",
  cyprus: "🇨🇾", czechia: "🇨🇿", "czech republic": "🇨🇿", denmark: "🇩🇰",
  "dominican republic": "🇩🇴", ecuador: "🇪🇨", egypt: "🇪🇬",
  "el salvador": "🇸🇻", england: "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "equatorial guinea": "🇬🇶",
  estonia: "🇪🇪", eswatini: "🇸🇿", ethiopia: "🇪🇹", finland: "🇫🇮",
  france: "🇫🇷", gabon: "🇬🇦", gambia: "🇬🇲", "the gambia": "🇬🇲",
  georgia: "🇬🇪", germany: "🇩🇪", ghana: "🇬🇭", greece: "🇬🇷",
  guatemala: "🇬🇹", guinea: "🇬🇳", "guinea-bissau": "🇬🇼", haiti: "🇭🇹",
  honduras: "🇭🇳", "hong kong": "🇭🇰", hungary: "🇭🇺", iceland: "🇮🇸",
  india: "🇮🇳", indonesia: "🇮🇩", iran: "🇮🇷", "ir iran": "🇮🇷",
  iraq: "🇮🇶", "republic of ireland": "🇮🇪", ireland: "🇮🇪", israel: "🇮🇱",
  italy: "🇮🇹", jamaica: "🇯🇲", japan: "🇯🇵", jordan: "🇯🇴",
  kazakhstan: "🇰🇿", kenya: "🇰🇪", kosovo: "🇽🇰", kuwait: "🇰🇼",
  "kyrgyz republic": "🇰🇬", kyrgyzstan: "🇰🇬", latvia: "🇱🇻", lebanon: "🇱🇧",
  liberia: "🇱🇷", libya: "🇱🇾", lithuania: "🇱🇹", luxembourg: "🇱🇺",
  madagascar: "🇲🇬", malawi: "🇲🇼", malaysia: "🇲🇾", mali: "🇲🇱",
  malta: "🇲🇹", mauritania: "🇲🇷", mexico: "🇲🇽", moldova: "🇲🇩",
  montenegro: "🇲🇪", morocco: "🇲🇦", mozambique: "🇲🇿", namibia: "🇳🇦",
  netherlands: "🇳🇱", "new caledonia": "🇳🇨", "new zealand": "🇳🇿",
  nicaragua: "🇳🇮", niger: "🇳🇪", nigeria: "🇳🇬", "north korea": "🇰🇵",
  "korea dpr": "🇰🇵", "north macedonia": "🇲🇰", norway: "🇳🇴", oman: "🇴🇲",
  pakistan: "🇵🇰", palestine: "🇵🇸", panama: "🇵🇦", "papua new guinea": "🇵🇬",
  paraguay: "🇵🇾", peru: "🇵🇪", philippines: "🇵🇭", poland: "🇵🇱",
  portugal: "🇵🇹", qatar: "🇶🇦", romania: "🇷🇴", russia: "🇷🇺",
  rwanda: "🇷🇼", "saudi arabia": "🇸🇦", scotland: "🏴󠁧󠁢󠁳󠁣󠁴󠁿", senegal: "🇸🇳",
  serbia: "🇷🇸", "sierra leone": "🇸🇱", singapore: "🇸🇬", slovakia: "🇸🇰",
  slovenia: "🇸🇮", "south africa": "🇿🇦", "south korea": "🇰🇷",
  "korea republic": "🇰🇷", spain: "🇪🇸", "sri lanka": "🇱🇰", sudan: "🇸🇩",
  suriname: "🇸🇷", sweden: "🇸🇪", switzerland: "🇨🇭", syria: "🇸🇾",
  tanzania: "🇹🇿", thailand: "🇹🇭", togo: "🇹🇬", "trinidad and tobago": "🇹🇹",
  tunisia: "🇹🇳", turkey: "🇹🇷", "türkiye": "🇹🇷", turkmenistan: "🇹🇲",
  uganda: "🇺🇬", ukraine: "🇺🇦", "united arab emirates": "🇦🇪", uae: "🇦🇪",
  "united states": "🇺🇸", usa: "🇺🇸", "united states of america": "🇺🇸",
  uruguay: "🇺🇾", uzbekistan: "🇺🇿", venezuela: "🇻🇪", vietnam: "🇻🇳",
  wales: "🏴󠁧󠁢󠁷󠁬󠁳󠁿", yemen: "🇾🇪", zambia: "🇿🇲", zimbabwe: "🇿🇼",
};

// Normalise a team name to a lookup key: lower-case, strip accents, collapse
// punctuation/whitespace. Lets "Côte d'Ivoire", "Bosnia-Herzegovina" etc. hit.
function norm(s: string): string {
  return s
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[.\-_]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

const NORMALISED: Record<string, string> = Object.fromEntries(
  Object.entries(FLAGS).map(([k, v]) => [norm(k), v]),
);

export function flag(team: string): string | null {
  if (!team) return null;
  const key = norm(team);
  if (NORMALISED[key]) return NORMALISED[key];
  // Drop a leading article / trailing qualifier and retry once.
  const stripped = key.replace(/\b(the|fr|republic of)\b/g, "").replace(/\s+/g, " ").trim();
  return NORMALISED[stripped] ?? null;
}

/** Up-to-3-char monogram for the rare unmapped team. */
export function monogram(team: string): string {
  const words = team.split(/\s+/).filter(Boolean);
  if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase();
  return team.slice(0, 3).toUpperCase();
}
