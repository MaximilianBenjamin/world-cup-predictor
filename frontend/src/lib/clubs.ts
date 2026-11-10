// Club colours and three-letter codes, keyed by the names the API uses
// (football-data.co.uk's spellings). Badges are drawn from these two colours;
// no club crests are used.

interface Club { code: string; name: string; a: string; b: string }

const CLUBS: Record<string, Club> = {
  "Arsenal":          { code: "ARS", name: "Arsenal",           a: "#ef0107", b: "#ffffff" },
  "Aston Villa":      { code: "AVL", name: "Aston Villa",       a: "#670e36", b: "#95bfe5" },
  "Bournemouth":      { code: "BOU", name: "Bournemouth",       a: "#da291c", b: "#111111" },
  "Brentford":        { code: "BRE", name: "Brentford",         a: "#e30613", b: "#ffffff" },
  "Brighton":         { code: "BHA", name: "Brighton",          a: "#0057b8", b: "#ffffff" },
  "Burnley":          { code: "BUR", name: "Burnley",           a: "#6c1d45", b: "#99d6ea" },
  "Chelsea":          { code: "CHE", name: "Chelsea",           a: "#034694", b: "#ffffff" },
  "Coventry":         { code: "COV", name: "Coventry City",     a: "#6cabdd", b: "#ffffff" },
  "Crystal Palace":   { code: "CRY", name: "Crystal Palace",    a: "#1b458f", b: "#c4122e" },
  "Everton":          { code: "EVE", name: "Everton",           a: "#003399", b: "#ffffff" },
  "Fulham":           { code: "FUL", name: "Fulham",            a: "#ffffff", b: "#111111" },
  "Hull":             { code: "HUL", name: "Hull City",         a: "#f5a12d", b: "#111111" },
  "Ipswich":          { code: "IPS", name: "Ipswich Town",      a: "#0044a9", b: "#ffffff" },
  "Leeds":            { code: "LEE", name: "Leeds United",      a: "#ffffff", b: "#1d428a" },
  "Leicester":        { code: "LEI", name: "Leicester City",    a: "#003090", b: "#fdbe11" },
  "Liverpool":        { code: "LIV", name: "Liverpool",         a: "#c8102e", b: "#00b2a9" },
  "Luton":            { code: "LUT", name: "Luton Town",        a: "#f78f1e", b: "#002d62" },
  "Man City":         { code: "MCI", name: "Manchester City",   a: "#6cabdd", b: "#1c2c5b" },
  "Man United":       { code: "MUN", name: "Manchester United", a: "#da291c", b: "#fbe122" },
  "Middlesbrough":    { code: "MID", name: "Middlesbrough",     a: "#e11b22", b: "#ffffff" },
  "Newcastle":        { code: "NEW", name: "Newcastle United",  a: "#111111", b: "#ffffff" },
  "Norwich":          { code: "NOR", name: "Norwich City",      a: "#fff200", b: "#00a650" },
  "Nott'm Forest":    { code: "NFO", name: "Nottingham Forest", a: "#dd0000", b: "#ffffff" },
  "Sheffield United": { code: "SHU", name: "Sheffield United",  a: "#ee2737", b: "#111111" },
  "Southampton":      { code: "SOU", name: "Southampton",       a: "#d71920", b: "#ffffff" },
  "Sunderland":       { code: "SUN", name: "Sunderland",        a: "#eb172b", b: "#ffffff" },
  "Tottenham":        { code: "TOT", name: "Tottenham Hotspur", a: "#ffffff", b: "#132257" },
  "Watford":          { code: "WAT", name: "Watford",           a: "#fbee23", b: "#ed2127" },
  "West Brom":        { code: "WBA", name: "West Bromwich Albion", a: "#122f67", b: "#ffffff" },
  "West Ham":         { code: "WHU", name: "West Ham United",   a: "#7a263a", b: "#1bb1e7" },
  "Wolves":           { code: "WOL", name: "Wolves",            a: "#fdb913", b: "#231f20" },
};

export function club(team: string): Club {
  const known = CLUBS[team];
  if (known) return known;
  // An unlisted team gets a colour derived from its name, so it is at least
  // always the same colour.
  let h = 0;
  for (let i = 0; i < team.length; i++) h = (h * 31 + team.charCodeAt(i)) % 360;
  return {
    code: team.replace(/[^A-Za-z]/g, "").slice(0, 3).toUpperCase(),
    name: team,
    a: `hsl(${h} 60% 38%)`,
    b: "#ffffff",
  };
}

/** Is a hex colour light enough to need dark text on top? */
export function isLight(hex: string): boolean {
  if (!hex.startsWith("#") || hex.length !== 7) return false;
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
  return 0.299 * r + 0.587 * g + 0.114 * b > 160;
}
