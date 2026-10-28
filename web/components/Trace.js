const ROUTES = {
  spotify: "Found via Spotify",
  musicbrainz: "Found via MusicBrainz",
  name: "Found by name",
  stand_in: "Matched as a mix of similar artists",
};

function label(event) {
  if (event.kind === "onboarding") return ROUTES[event.route] || "Onboarding";
  if (event.kind === "step_start") return `Started ${event.step}`;
  if (event.kind === "step_end") return event.note || `Finished ${event.step}`;
  if (event.kind === "guard_drop") return `Removed "${event.text}": ${event.reason}`;
  if (event.kind === "result") return "Result ready";
  if (event.kind === "error") return event.error;
  if (event.kind === "run_end") return `Run ${event.status}`;
  return event.kind;
}

export default function Trace({ events, status }) {
  const calls = events.filter((e) => e.kind === "qloo_call");
  const endpoints = new Set(calls.map((e) => e.endpoint));
  const hits = calls.filter((e) => e.cache === "hit").length;
  const removed = events.filter((e) => e.kind === "guard_drop").length;
  const steps = events.filter((e) => e.kind !== "qloo_call" && !(e.kind === "step_start" && e.step !== "planner" && e.step !== "writer"));
  return (
    <aside className="trace card" aria-live="polite">
      <div className="trace-head">
        <h3>Live trace</h3>
        <span className={`pill ${status === "running" ? "pill-live" : ""}`}>{status === "running" ? "Running" : status === "done" ? "Done" : status === "error" ? "Stopped" : "Waiting"}</span>
      </div>
      <p className="trace-count">
        <strong>{calls.length}</strong> Qloo calls across <strong>{endpoints.size}</strong> endpoints · {hits} from cache
      </p>
      {removed > 0 && <span className="pill guard" style={{ justifySelf: "start" }}>{removed} removed by Cue's guards</span>}
      <ol className="trace-list">
        {events.length === 0 && <li className="muted">Steps and every Qloo call show up here as they happen.</li>}
        {events.map((event) =>
          event.kind === "qloo_call" ? (
            <li key={event.seq} className="trace-call">
              <code>{event.endpoint}</code>
              <span className="trace-type">{event.params?.["filter.type"]?.replace("urn:entity:", "").replace("urn:", "") || ""}</span>
              <span className={`chip-mini ${event.cache === "hit" ? "chip-hit" : ""}`}>{event.cache}</span>
              <span className="trace-ms">{event.ms} ms</span>
            </li>
          ) : event.kind === "guard_drop" ? (
            <li key={event.seq} className="trace-step trace-guard_drop">
              <span className="removed">{event.text}</span> {event.reason}
            </li>
          ) : steps.includes(event) ? (
            <li key={event.seq} className={`trace-step trace-${event.kind}`}>
              {label(event)}
            </li>
          ) : null
        )}
      </ol>
    </aside>
  );
}
