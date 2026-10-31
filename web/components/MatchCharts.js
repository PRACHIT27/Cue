import { typeLabel } from "../lib/labels";

const TYPE_COLORS = {
  "urn:entity:tv_show": "#4f3cf0",
  "urn:entity:movie": "#c8441c",
  "urn:entity:videogame": "#1f8a5b",
  "urn:entity:podcast": "#b26b00",
  "urn:entity:brand": "#c2378a",
};

function rows(result) {
  const pitched = (result.pitches || []).map((p) => ({
    id: p.candidate.id,
    name: p.candidate.name,
    type: p.candidate.type,
    popularity: p.candidate.popularity,
    lift: p.fit.inputs?.lift,
    pitched: true,
  }));
  const extra = Object.values(result.also_love || {}).flat().map((r) => ({ ...r, pitched: false }));
  return [...pitched, ...extra].filter((r) => typeof r.lift === "number" && typeof r.popularity === "number");
}

function TypeLean({ data }) {
  const byType = {};
  data.forEach((r) => {
    (byType[r.type] ||= []).push(r.lift);
  });
  const bars = Object.entries(byType)
    .map(([type, lifts]) => ({ type, lift: lifts.reduce((a, b) => a + b, 0) / lifts.length, count: lifts.length }))
    .sort((a, b) => b.lift - a.lift);
  if (!bars.length) return null;
  const top = Math.max(...bars.map((b) => Math.abs(b.lift)), 0.0001);
  const lead = bars[0];
  return (
    <div className="card stack">
      <div className="stack" style={{ gap: 4 }}>
        <h3>What your fans lean toward</h3>
        <p className="muted small">How much more your fans like each kind of production than fans of similar artists, averaged over its top matches.</p>
      </div>
      <p className="insight">Your fans lean most toward <strong>{typeLabel(lead.type).toLowerCase()}s</strong>.</p>
      <div className="bars">
        {bars.map((b) => (
          <div className="bar-row" key={b.type} title={`${b.count} matches`}>
            <span>{typeLabel(b.type)}</span>
            <span className="bar"><span style={{ width: `${Math.max(4, (Math.abs(b.lift) / top) * 100)}%`, background: TYPE_COLORS[b.type] || "var(--accent)" }} /></span>
            <strong style={{ textAlign: "right" }}>{b.lift >= 0 ? "+" : ""}{Math.round(b.lift * 1000) / 10}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

const BOXES = [
  { id: "first", icon: "🎯", title: "Pitch first", hint: "Smaller productions your fans love. Your best odds.", tone: "var(--good)", soft: "var(--good-soft)" },
  { id: "dream", icon: "🚀", title: "Dream pitches", hint: "Big productions your fans love. Harder to land, worth a try.", tone: "var(--accent)", soft: "var(--accent-soft)" },
  { id: "easy", icon: "🌱", title: "Easy wins", hint: "Smaller and easier to reach, but your fans are less keen.", tone: "#9a5b06", soft: "var(--warn-soft)" },
  { id: "skip", icon: "⏸", title: "Skip for now", hint: "Big and your fans are less keen. Leave these for later.", tone: "var(--muted)", soft: "#f1f0f5" },
];

function SweetSpot({ data }) {
  if (data.length < 3) return null;
  const pops = data.map((d) => d.popularity).sort((a, b) => a - b);
  const lifts = data.map((d) => d.lift).sort((a, b) => a - b);
  const bigFrom = pops[Math.floor(pops.length / 2)];
  const loveFrom = lifts[Math.floor(lifts.length / 2)];
  const groups = { first: [], dream: [], easy: [], skip: [] };
  data.forEach((d) => {
    const big = d.popularity >= bigFrom;
    const loved = d.lift >= loveFrom;
    groups[loved ? (big ? "dream" : "first") : big ? "skip" : "easy"].push(d);
  });
  Object.values(groups).forEach((g) => g.sort((a, b) => b.lift - a.lift));
  return (
    <div className="card stack">
      <div className="stack" style={{ gap: 4 }}>
        <h3>Where to pitch first</h3>
        <p className="muted small">Every match Qloo scored for you, sorted by two questions: how much do your fans love it, and how easy is it to reach?</p>
      </div>
      <div className="sweet-grid">
        {BOXES.map((box) => (
          <div key={box.id} className="sweet-box" style={{ background: box.soft, borderColor: box.tone }}>
            <div className="between" style={{ gap: 8 }}>
              <strong style={{ color: box.tone }}><span aria-hidden="true">{box.icon}</span> {box.title}</strong>
              <span className="pill plain">{groups[box.id].length}</span>
            </div>
            <span className="muted small">{box.hint}</span>
            <ul className="sweet-list">
              {groups[box.id].slice(0, 4).map((d) => (
                <li key={`${d.id}-${d.pitched}`}>
                  <span className="sweet-dot" style={{ background: TYPE_COLORS[d.type] || "var(--accent)" }} />
                  <span className="rank-name">{d.name}</span>
                  <span className="muted small">{typeLabel(d.type)}</span>
                </li>
              ))}
              {groups[box.id].length === 0 && <li className="muted small">Nothing here</li>}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function MatchCharts({ result }) {
  const data = rows(result);
  if (!data.length) return null;
  return (
    <section className="stack">
      <TypeLean data={data} />
      <SweetSpot data={data} />
    </section>
  );
}
