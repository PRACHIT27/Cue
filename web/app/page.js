import Link from "next/link";
import Shell from "../components/Shell";

const BARS = Array.from({ length: 28 }, (_, i) => i);
const TRIES = [
  { href: "/artist?try=Phoebe%20Bridgers", icon: "♪", title: "Phoebe Bridgers", hint: "See where an indie artist should pitch" },
  { href: "/supervisor?try=The%20Bear&type=tv_show", icon: "▣", title: "The Bear", hint: "Find under-the-radar artists for a show" },
  { href: "/artist?try=Ved%20and%20the%20Monsoons", icon: "?", title: "An unknown artist", hint: "Not in Qloo? Match through artists you sound like" },
];

export default function Welcome() {
  return (
    <Shell tone="home">
      <div className="stage">
        <span className="beam left" aria-hidden="true" />
        <span className="beam right" aria-hidden="true" />
        <span className="stage-bulbs top" aria-hidden="true" />
        <section className="hero cinema">
          <span className="marquee-badge">★ Powered by Qloo taste data ★</span>
          <h1>
            Get your music where your
            <br />
            <em>fans already are.</em>
          </h1>
          <p className="lede">Cue matches artists with the shows, films, games, podcasts and brands whose audiences already love their sound.</p>
          <div className="equalizer" aria-hidden="true">
            {BARS.map((i) => (
              <span key={i} style={{ animationDelay: `${(i * 137) % 900}ms`, animationDuration: `${900 + ((i * 211) % 700)}ms` }} />
            ))}
          </div>
        </section>
        <div className="filmstrip" aria-hidden="true" />
      </div>
      <section className="choices">
        <Link href="/artist" className="choice dark">
          <span className="choice-icon" style={{ background: "#4f3cf0", color: "#fff" }} aria-hidden="true">♪</span>
          <h2>I make music</h2>
          <p>See who your fans are, find where to pitch, and get a ready-made pitch to send yourself.</p>
          <span className="choice-cta">Start as an artist →</span>
        </Link>
        <Link href="/supervisor" className="choice">
          <span className="choice-icon" style={{ background: "#fdeee6", color: "#c8441c" }} aria-hidden="true">⌕</span>
          <h2>I'm looking for artists</h2>
          <p>For music supervisors, producers and brands. Tell us what it's for and get lesser-known artists whose fans match your audience.</p>
          <span className="choice-cta" style={{ color: "#c8441c" }}>Find artists →</span>
        </Link>
      </section>
      <section className="try" aria-label="Try an example">
        <span className="try-label">Or try it in one click</span>
        <div className="try-row">
          {TRIES.map((t) => (
            <Link key={t.href} href={t.href} className="try-card">
              <span className="try-icon" aria-hidden="true">{t.icon}</span>
              <span><strong>{t.title}</strong><span className="muted small">{t.hint}</span></span>
            </Link>
          ))}
        </div>
      </section>
      <div className="how">
        <span>1 · Connect</span>
        <span>2 · See the match</span>
        <span>3 · Pitch</span>
      </div>
    </Shell>
  );
}
