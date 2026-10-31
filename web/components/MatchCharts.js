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

function SweetSpot({ data }) {
  if (data.length < 3) return null;
  const W = 760, H = 340, L = 44, R = 16, T = 14, B = 40;
  const maxLift = Math.max(...data.map((d) => d.lift), 0.001);
  const minLift = Math.min(0, ...data.map((d) => d.lift));
  const pops = data.map((d) => d.popularity).sort((a, b) => a - b);
  const lo = Math.max(0, Math.floor((pops[0] - 0.05) * 20) / 20);
  const split = pops[Math.floor(pops.length / 2)];
  const x = (p) => L + ((p - lo) / (1 - lo || 1)) * (W - L - R);
  const y = (l) => T + (1 - (l - minLift) / (maxLift - minLift || 1)) * (H - T - B);
  const midX = x(split);
  const midY = y(minLift + (maxLift - minLift) / 2);
  const sweet = data
    .filter((d) => d.popularity < split && d.lift >= minLift + (maxLift - minLift) / 2)
    .sort((a, b) => b.lift - a.lift)
    .slice(0, 4);
  const types = [...new Set(data.map((d) => d.type))];
  return (
    <div className="card stack">
      <div className="stack" style={{ gap: 4 }}>
        <h3>Your sweet spot</h3>
        <p className="muted small">Every match Qloo scored. Further left is smaller and easier to reach; higher means your fans like it more than fans of similar artists.</p>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Scatter of matches by Qloo popularity and how much more your fans like them">
        <rect x={L} y={T} width={midX - L} height={midY - T} fill="var(--accent-soft)" rx="6" />
        <text x={L + 8} y={T + 18} fontSize="13" fill="var(--accent)" fontWeight="600">Sweet spot: smaller, and your fans love it</text>
        <line x1={L} y1={H - B} x2={W - R} y2={H - B} stroke="var(--line)" />
        <line x1={L} y1={T} x2={L} y2={H - B} stroke="var(--line)" />
        {[lo, (lo + 1) / 2, 1].map((p) => (
          <text key={p} x={x(p)} y={H - B + 16} fontSize="11" textAnchor="middle" fill="var(--muted)">{Math.round(p * 100)}</text>
        ))}
        <text x={(L + W - R) / 2} y={H - 4} fontSize="11" textAnchor="middle" fill="var(--muted)">Qloo popularity (0 to 100)</text>
        <text x={12} y={(T + H - B) / 2} fontSize="11" textAnchor="middle" fill="var(--muted)" transform={`rotate(-90 12 ${(T + H - B) / 2})`}>Fans prefer it more</text>
        {data.map((d) => (
          <circle key={`${d.id}-${d.pitched}`} cx={x(d.popularity)} cy={y(d.lift)} r={d.pitched ? 7 : 4.5} fill={TYPE_COLORS[d.type] || "var(--accent)"} fillOpacity={d.pitched ? 0.95 : 0.55} stroke="#fff" strokeWidth="1">
            <title>{`${d.name} · ${typeLabel(d.type)} · popularity ${Math.round(d.popularity * 100)} · +${Math.round(d.lift * 1000) / 10}`}</title>
          </circle>
        ))}
      </svg>
      <div className="chips small">
        {types.map((t) => (
          <span key={t} className="row" style={{ gap: 6 }}><span style={{ width: 10, height: 10, borderRadius: 99, background: TYPE_COLORS[t] || "var(--accent)", display: "inline-block" }} />{typeLabel(t)}</span>
        ))}
        <span className="muted">Big dots are your picks</span>
      </div>
      {sweet.length > 0 && (
        <p className="insight">Pitch first: {sweet.map((s, i) => <span key={s.id}>{i > 0 && ", "}<strong>{s.name}</strong></span>)}.</p>
      )}
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
