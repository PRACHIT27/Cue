export default function FitRing({ value, size = 48 }) {
  const score = value == null ? null : Math.round(value * 100);
  const radius = 20;
  const length = 2 * Math.PI * radius;
  const filled = score == null ? 0 : (length * score) / 100;
  return (
    <span className="fit-ring" style={{ width: size, height: size }} title={score == null ? "Not enough data" : `Fit ${score} out of 100`}>
      <svg viewBox="0 0 48 48" width={size} height={size} aria-hidden="true">
        <circle cx="24" cy="24" r={radius} className="ring-track" />
        <circle cx="24" cy="24" r={radius} className="ring-fill" strokeDasharray={`${filled} ${length}`} transform="rotate(-90 24 24)" />
      </svg>
      <span className="ring-value">{score ?? "–"}</span>
    </span>
  );
}
