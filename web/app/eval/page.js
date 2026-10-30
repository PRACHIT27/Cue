import Shell from "../../components/Shell";
import known from "../../lib/eval/known_placements.json";
import small from "../../lib/eval/small_us_artists.json";
import examples from "../../lib/eval/examples.json";

const SYSTEMS = [
  { id: "llm", label: "Claude alone" },
  { id: "cue", label: "Cue" },
];

function pct(value) {
  return value == null ? "n/a" : `${Math.round(value * 100)}%`;
}

function Compare({ title, hint, values, better, score = false }) {
  return (
    <div className="card stack">
      <div className="stack" style={{ gap: 4 }}>
        <h3>{title}</h3>
        <p className="muted small">{hint}</p>
      </div>
      <div className="bars">
        {SYSTEMS.map((s) => (
          <div className="bar-row" key={s.id}>
            <span>{s.label}</span>
            <span className="bar"><span style={{ width: `${Math.round((values[s.id] ?? 0) * 100)}%`, background: s.id === "cue" ? "var(--accent)" : "#9a97a8" }} /></span>
            <strong style={{ textAlign: "right" }}>{score ? (values[s.id] == null ? "n/a" : values[s.id].toFixed(2)) : pct(values[s.id])}</strong>
          </div>
        ))}
      </div>
      {better && <span className="pill plain" style={{ justifySelf: "start" }}>{better}</span>}
    </div>
  );
}

function pick(doc, key) {
  return { llm: doc.summary.llm?.[key], cue: doc.summary.cue?.[key] };
}

export const metadata = { title: "How Cue compares · Cue" };

export default function EvalPage() {
  const s = small.summary;
  const k = known.summary;
  return (
    <Shell>
      <section className="stack" style={{ gap: 10 }}>
        <span className="pill" style={{ justifySelf: "start" }}>Evaluation</span>
        <h1 style={{ fontSize: "clamp(1.9rem, 4.5vw, 2.8rem)" }}>How Cue compares with Claude alone</h1>
        <p className="lede" style={{ maxWidth: "70ch" }}>
          We asked both the same questions. Claude alone answers from what it remembers. Cue answers from Qloo's taste data, scores matches in code and only shows names that exist in Qloo. Both use the same Claude model, so Qloo is the difference.
        </p>
      </section>

      <section className="stack">
        <h2>1 · Smaller US artists: who should they pitch to?</h2>
        <p className="muted" style={{ maxWidth: "70ch" }}>
          {s.cue.rows} lesser-known US artists that Qloo knows, such as Major Murphy, Annie DiRusso and Babehoven. These are the artists Cue is built for. There is no single right answer for them, so we measure how specific and how reachable each system's suggestions are.
        </p>
        <div className="grid-3">
          <Compare title="Suggestions repeated for other artists" hint="Same title suggested to 3 or more different artists. Lower means answers fit the artist, not a generic list." values={pick(small, "repeat_share")} better="Lower is better" />
          <Compare title="How big the suggestions are" hint="Median popularity in Qloo of what was suggested. Lower means smaller, more realistic placements for an indie artist." values={pick(small, "median_suggestion_popularity")} better="Lower is better" score />
          <Compare title="Names not found in Qloo" hint="Suggestions Qloo has no exact match for. Not always invented, but not checkable." values={pick(small, "made_up_rate")} better="Lower is better" />
        </div>
        {examples.length > 0 && (
          <div className="stack">
            <h3>Side by side</h3>
            <p className="muted small">Three of the twelve artists, first six suggestions each. Both systems have weak spots: Cue also suggested Cyberpunk 2077 to Annie DiRusso, and repeats a few favourites such as Sandra.</p>
            {examples.map((e) => (
              <div className="card grid-2" key={e.artist}>
                <div className="stack" style={{ gap: 6 }}>
                  <strong>{e.artist} · Claude alone</strong>
                  <p className="muted small">{e.llm.join(" · ")}</p>
                </div>
                <div className="stack" style={{ gap: 6 }}>
                  <strong style={{ color: "var(--accent)" }}>{e.artist} · Cue</strong>
                  <p className="small">{e.cue.join(" · ")}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="stack">
        <h2>2 · Supervisors asking for lesser-known artists</h2>
        <p className="muted" style={{ maxWidth: "70ch" }}>
          Both were told to suggest lesser-known, still-active artists for a show, film or game. We checked every suggestion's popularity in Qloo.
        </p>
        <div className="grid-2">
          <Compare title="Suggestions that really are under the radar" hint={`At or under popularity ${Math.round(known.popularity_cap * 100)} in Qloo.`} values={pick(known, "under_the_radar_share")} better="Higher is better" />
          <Compare title="Names not found in Qloo" hint="Across all known-placement rows." values={pick(known, "made_up_rate")} better="Lower is better" />
        </div>
      </section>

      <section className="stack">
        <h2>3 · Famous placements, as a sanity check</h2>
        <p className="muted" style={{ maxWidth: "70ch" }}>
          {k.cue.hit_rows} well-documented placements, such as Kate Bush in Stranger Things. Claude alone finds {pct(k.llm.hit_rate_top10)} of them and Cue {pct(k.cue.hit_rate_top10)}. That is expected: these placements are famous, so Claude can recall them from training, while Cue matches on audience taste and doesn't know placement history. Famous artists aren't who Cue is for.
        </p>
        <div className="note stack" style={{ gap: 6 }}>
          <strong style={{ color: "var(--ink)" }}>What to keep in mind</strong>
          {known.caveats.map((c) => <span key={c}>· {c}</span>)}
          <span>· {k.llm.answers_above_cap} supervisor rows weren't scored for hits, for either system, because the known answer is above Cue's popularity cap.</span>
        </div>
      </section>

      <section className="grid-3">
        <div className="card stat"><span className="muted">Typical time per run</span><strong>{s.llm.median_seconds} s vs {s.cue.median_seconds} s</strong><span className="muted small">Claude alone vs Cue. Cue makes about 20 live Qloo calls.</span></div>
        <div className="card stat"><span className="muted">Claude cost, small-artist set</span><strong>${s.llm.total_usd} vs ${s.cue.total_usd}</strong><span className="muted small">Claude alone vs Cue, whole set</span></div>
        <div className="card stat"><span className="muted">Errors</span><strong>{(s.llm.errors || 0) + (k.llm.errors || 0)} vs {(s.cue.errors || 0) + (k.cue.errors || 0)}</strong><span className="muted small">Across {s.cue.rows + k.cue.rows} rows</span></div>
      </section>
      <p className="muted small">Scores come from python -m cue.eval in the repo. Only scores are published; raw Qloo responses never are.</p>
    </Shell>
  );
}
