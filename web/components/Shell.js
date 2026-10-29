import Link from "next/link";
import Logo from "./Logo";

export default function Shell({ tone = "artist", right = null, children }) {
  return (
    <div className={`shell tone-${tone}`}>
      <div className="backdrop" aria-hidden="true">
        <span className="spot" />
        <span className="staff" />
        <span className="vinyl" />
        <span className="grain" />
      </div>
      <header className="topbar">
        <Link href="/" className="home-link">
          <Logo />
        </Link>
        <div className="topbar-right">{right}</div>
      </header>
      <main className="page">{children}</main>
    </div>
  );
}

export function Steps({ steps, current }) {
  return (
    <ol className="steps" aria-label="Progress">
      {steps.map((label, index) => (
        <li key={label} className={index < current ? "done" : index === current ? "now" : ""}>
          <span className="step-dot">{index < current ? "✓" : index + 1}</span>
          {label}
        </li>
      ))}
    </ol>
  );
}
