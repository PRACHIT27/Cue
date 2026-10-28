export default function Logo({ size = 32, word = true }) {
  return (
    <span className="logo" aria-label="Cue">
      <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
        <defs>
          <linearGradient id="cueGradient" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#6d4bff" />
            <stop offset="1" stopColor="#e2458f" />
          </linearGradient>
        </defs>
        <rect width="64" height="64" rx="16" fill="url(#cueGradient)" />
        <path d="M43 21.5a15 15 0 1 0 0 21" fill="none" stroke="#fff" strokeWidth="6" strokeLinecap="round" />
        <path d="M29 24.5v15l12-7.5z" fill="#fff" />
      </svg>
      {word && <span className="logo-word">cue</span>}
    </span>
  );
}
