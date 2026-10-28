export const TYPE_LABELS = {
  "urn:entity:tv_show": "TV series",
  "urn:entity:movie": "Film",
  "urn:entity:videogame": "Game",
  "urn:entity:podcast": "Podcast",
  "urn:entity:brand": "Brand",
  "urn:entity:artist": "Artist",
  "urn:entity:person": "Person",
  "urn:entity:author": "Author",
};

export const TYPE_FILTERS = [
  { id: "all", label: "All", types: null },
  { id: "screen", label: "TV & film", types: ["urn:entity:tv_show", "urn:entity:movie"] },
  { id: "podcast", label: "Podcasts", types: ["urn:entity:podcast"] },
  { id: "game", label: "Games", types: ["urn:entity:videogame"] },
  { id: "brand", label: "Brands", types: ["urn:entity:brand"] },
];

export const SECTIONS = [
  { id: "big_screen", title: "Big screen", hint: "The most popular productions" },
  { id: "prime_time", title: "Prime time", hint: "Well known, easier to reach" },
  { id: "indie_gems", title: "Indie gems", hint: "Smaller, often the most realistic placements" },
];

export const AGE_LABELS = {
  "24_and_younger": "Under 25",
  "25_to_29": "25–29",
  "30_to_34": "30–34",
  "35_to_44": "35–44",
  "45_to_54": "45–54",
  "55_and_older": "55+",
};

export function typeLabel(type) {
  return TYPE_LABELS[type] || (type || "").split(":").pop();
}

export function initials(name) {
  return (name || "?")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");
}

export function peakAge(age) {
  const entries = Object.entries(age || {});
  if (!entries.length) return null;
  return entries.sort((a, b) => b[1] - a[1])[0][0];
}

export function genderLean(gender) {
  if (!gender) return null;
  const women = gender.female ?? 0;
  if (Math.abs(women) < 0.05) return "Even split of women and men";
  const side = women > 0 ? "women" : "men";
  return Math.abs(women) > 0.3 ? `Leans clearly toward ${side}` : `Leans slightly toward ${side}`;
}
