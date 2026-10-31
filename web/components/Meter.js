export function Meter({ label, value, display, hint, color = "var(--accent)" }) {
  if (typeof value !== "number" || Number.isNaN(value)) return null;
  const width = Math.max(3, Math.min(100, value * 100));
  return (
    <div className="qmeter" title={hint || label}>
      <span className="qmeter-label">{label}</span>
      <span className="qmeter-track"><span style={{ width: `${width}%`, background: color }} /></span>
      <span className="qmeter-value">{display ?? Math.round(value * 100)}</span>
    </div>
  );
}

export function liftShare(lift, scale = 0.08) {
  return typeof lift === "number" ? Math.max(0, Math.min(1, lift / scale)) : null;
}

export function liftLabel(lift) {
  if (typeof lift !== "number") return null;
  const points = Math.round(lift * 1000) / 10;
  return `${points >= 0 ? "+" : ""}${points}`;
}

export function QlooMeters({ inputs, popularity }) {
  const lift = inputs?.lift;
  const audience = inputs?.audience;
  if (typeof lift !== "number" && typeof audience !== "number" && typeof popularity !== "number") return null;
  return (
    <div className="qmeters" aria-label="Qloo numbers">
      <Meter label="Fan preference" value={liftShare(lift)} display={liftLabel(lift)} hint="How much more your fans like it than fans of similar artists" />
      <Meter label="Audience match" value={audience} display={typeof audience === "number" ? `${Math.round(audience * 100)}%` : null} hint="How closely its audience's age and gender match your fans" color="#1f8a5b" />
      <Meter label="Popularity" value={popularity} display={typeof popularity === "number" ? `${Math.round(popularity * 100)}` : null} hint="How big it is on Qloo, out of 100. Lower is easier to reach" color="#9a97a8" />
    </div>
  );
}
