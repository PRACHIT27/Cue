"use client";

import { useEffect, useState } from "react";

const RESULT = (events) => events.some((e) => e.kind === "result");

export const ARTIST_STAGES = [
  { label: "Planning where to look", match: (s) => s === "planner" },
  { label: "Reading your fans' taste", match: (s) => s === "profile" },
  { label: "Finding artists who sound like you", match: (s) => s === "similar" },
  { label: "Searching shows, films, games, podcasts and brands", match: (s) => s.startsWith("match_") || s.startsWith("group_") },
  { label: "Comparing each audience's age and gender with your fans", match: (s) => s.startsWith("audience_") },
  { label: "Reading each pick's Qloo genres and themes", match: (s) => s === "pick_tags" },
  { label: "Writing your pitches", match: (s) => s === "writer" },
  { label: "Checking every sentence against the data", final: true },
];

export const SUPERVISOR_STAGES = [
  { label: "Reading your audience's taste", match: (s) => s === "profile" },
  { label: "Finding productions with a similar audience", match: (s) => s === "similar" },
  { label: "Finding lesser-known artists they love", match: (s) => s === "artists" || s === "artists_wide" },
  { label: "Comparing with fans of similar productions", match: (s) => s === "audiences" || s === "profiles" || s === "group" },
  { label: "Checking each artist is still active on MusicBrainz", match: (s) => s.startsWith("life_") },
  { label: "Writing the shortlist", match: (s) => s === "writer" },
  { label: "Checking every sentence against the data", final: true },
];

export default function RunProgress({ events, status, stages, title }) {
  const [started] = useState(() => Date.now());
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (status !== "running") return undefined;
    const timer = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(timer);
  }, [status]);

  const begun = new Set();
  const ended = new Set();
  for (const event of events) {
    if (event.kind === "step_start") begun.add(event.step);
    if (event.kind === "step_end") ended.add(event.step);
  }
  const writerDone = ended.has("writer");
  const states = stages.map((stage) => {
    if (stage.final) return RESULT(events) ? "done" : writerDone ? "active" : "todo";
    const mine = [...begun].filter(stage.match);
    if (!mine.length) return "todo";
    return mine.every((step) => ended.has(step)) ? "done" : "active";
  });
  const calls = events.filter((e) => e.kind === "qloo_call").length;
  const done = states.filter((s) => s === "done").length;

  return (
    <div className="card progress" aria-live="polite">
      <div className="between">
        <strong>{title}</strong>
        <span className="progress-clock">{Math.round((now - started) / 1000)} s · {calls} Qloo calls</span>
      </div>
      <div className="progress-bar" aria-hidden="true"><span style={{ width: `${Math.max(6, (done / stages.length) * 100)}%` }} /></div>
      <ol className="progress-list">
        {stages.map((stage, index) => (
          <li key={stage.label} className={`progress-${states[index]}`}>
            <span className="progress-mark" aria-hidden="true">{states[index] === "done" ? "✓" : ""}</span>
            {stage.label}
          </li>
        ))}
      </ol>
    </div>
  );
}
