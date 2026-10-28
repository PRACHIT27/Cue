import Link from "next/link";
import Shell from "../components/Shell";

export default function Welcome() {
  return (
    <Shell>
      <section className="hero">
        <span className="pill">Powered by Qloo taste data</span>
        <h1>
          Get your music where your
          <br />
          fans already are.
        </h1>
        <p className="lede">Cue matches artists with the shows, films, games, podcasts and brands whose audiences already love their sound.</p>
      </section>
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
      <div className="how">
        <span>1 · Connect</span>
        <span>2 · See the match</span>
        <span>3 · Pitch</span>
      </div>
    </Shell>
  );
}
