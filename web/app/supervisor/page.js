"use client";

import { useEffect, useState } from "react";
import FitRing from "../../components/FitRing";
import Poster from "../../components/Poster";
import RunProgress, { SUPERVISOR_STAGES } from "../../components/RunProgress";
import Shell from "../../components/Shell";
import SpotifyPlayer, { spotifyArtistId } from "../../components/SpotifyPlayer";
import Trace from "../../components/Trace";
import { get, post, useRun } from "../../lib/api";
import { typeLabel } from "../../lib/labels";

const ROLES = [
  { id: "producer", title: "Producer or music supervisor", hint: "Music for TV, film, ads or games", type: "tv_show", icon: "▣" },
  { id: "creator", title: "Creator or podcaster", hint: "Music for shows, reels and videos", type: "podcast", icon: "◉" },
  { id: "games", title: "Game studio", hint: "Music for trailers and soundtracks", type: "videogame", icon: "▲" },
  { id: "brand", title: "Brand or agency", hint: "Music for campaigns and launches", type: "brand", icon: "☆" },
];
const TYPES = [
  { id: "tv_show", label: "TV show" },
  { id: "movie", label: "Film" },
  { id: "podcast", label: "Podcast" },
  { id: "videogame", label: "Game" },
  { id: "brand", label: "Brand" },
];
const VIBES = ["Dreamy", "Upbeat", "Moody", "Acoustic", "Electronic", "Desi fusion", "Hip-hop", "Jazzy", "Classical", "Folk"];

function WhatYouDo({ onNext }) {
  const [role, setRole] = useState(ROLES[0]);
  return (
    <div className="narrow" style={{ width: "min(720px, 100%)" }}>
      <div className="between"><h2>What do you do?</h2><span className="muted small">Step 1 of 2</span></div>
      <p className="lede">We'll shape your search around it.</p>
      <div className="grid-2" role="radiogroup" aria-label="What you do">
        {ROLES.map((r) => (
          <button
            key={r.id}
            role="radio"
            aria-checked={role.id === r.id}
            className="card"
            style={{ textAlign: "left", display: "flex", gap: 14, borderColor: role.id === r.id ? "var(--accent)" : undefined, background: role.id === r.id ? "var(--accent-soft)" : "#fff" }}
            onClick={() => setRole(r)}
          >
            <span className="avatar small" style={{ background: role.id === r.id ? "var(--accent)" : "#f1f0f5", color: role.id === r.id ? "#fff" : "var(--ink)" }} aria-hidden="true">{r.icon}</span>
            <span className="stack" style={{ gap: 2 }}><strong style={{ color: "var(--ink)" }}>{r.title}</strong><span className="muted small">{r.hint}</span></span>
          </button>
        ))}
      </div>
      <button className="btn block" onClick={() => onNext(role)}>Continue →</button>
    </div>
  );
}

function Brief({ role, preset, onFind }) {
  const [type, setType] = useState(preset?.type || role.type);
  const [project, setProject] = useState("");
  const [query, setQuery] = useState(preset?.query || "");
  const [vibes, setVibes] = useState([]);
  const [groups, setGroups] = useState([]);
  const [audiences, setAudiences] = useState([]);
  const [candidates, setCandidates] = useState(null);
  const [picked, setPicked] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const lookUp = async (name = query) => {
    setError("");
    setPicked(null);
    if (!name.trim()) return setError("Type a show, film, podcast, game or brand your audience loves.");
    setBusy(true);
    try {
      const found = await post("/productions/search", { name: name.trim(), type });
      setCandidates(found.candidates);
      if (found.candidates.length >= 1) setPicked(found.candidates[0]);
      if (!found.candidates.length) setError(`Qloo has no ${TYPES.find((t) => t.id === type).label.toLowerCase()} called "${name.trim()}". Check the spelling or the type.`);
    } catch (failure) {
      setError(`Couldn't reach Cue: ${failure.message}`);
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    get("/audiences").then((d) => setGroups(d.groups || [])).catch(() => setGroups([]));
  }, []);

  useEffect(() => {
    if (preset?.query) lookUp(preset.query);
  }, []);

  const submit = (event) => {
    event.preventDefault();
    if (!picked) return setError("Look up the show or brand your audience loves first.");
    const parts = [];
    if (project.trim()) parts.push(`for ${project.trim()}`);
    if (vibes.length) parts.push(`vibe: ${vibes.join(", ").toLowerCase()}`);
    onFind({ production: picked, type, project: project.trim(), vibes, audiences, brief: parts.join("; ") });
  };

  return (
    <div className="narrow">
      <div className="between"><h2>What are you looking for?</h2><span className="muted small">Step 2 of 2</span></div>
      <p className="lede">A few quick answers. Qloo does the rest.</p>
      <form className="card stack" onSubmit={submit} noValidate>
        <div className="stack">
          <span className="field">Your audience is like fans of a…</span>
          <div className="chips" role="group" aria-label="Type">
            {TYPES.map((t) => (
              <button type="button" key={t.id} className="chip" aria-pressed={type === t.id} onClick={() => { setType(t.id); setCandidates(null); setPicked(null); }}>{t.label}</button>
            ))}
          </div>
        </div>
        <label className="field" htmlFor="audience-like">
          Which one? <span className="muted small">We look it up in Qloo</span>
          <div className="row" style={{ flexWrap: "nowrap" }}>
            <input id="audience-like" className="input" value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); lookUp(); } }} placeholder="e.g. Bandish Bandits" />
            <button type="button" className="btn ghost small" onClick={() => lookUp()} disabled={busy}>{busy ? "…" : "Look up"}</button>
          </div>
        </label>
        {candidates && candidates.length > 1 && (
          <div className="chips" role="group" aria-label="Pick the right one">
            {candidates.map((c) => (
              <button type="button" key={c.id} className="chip" aria-pressed={picked?.id === c.id} onClick={() => setPicked(c)}>{c.name} · popularity {Math.round(c.popularity * 100)}</button>
            ))}
          </div>
        )}
        {picked && <p className="pill good" style={{ justifySelf: "start" }}>Using {picked.name} ({typeLabel(picked.type)})</p>}
        <label className="field" htmlFor="project">Name your project <span className="muted small">(optional)</span><input id="project" className="input" value={project} onChange={(e) => setProject(e.target.value)} placeholder="e.g. Sunset rooftop series" /></label>
        <div className="stack">
          <span className="field">The vibe <span className="muted small">pick any</span></span>
          <div className="chips">
            {VIBES.map((v) => (
              <button type="button" key={v} className="chip" aria-pressed={vibes.includes(v)} onClick={() => setVibes(vibes.includes(v) ? vibes.filter((x) => x !== v) : [...vibes, v])}>{v}</button>
            ))}
          </div>
        </div>
        {groups.length > 0 && (
          <div className="stack">
            <label className="field" htmlFor="viewers">Your viewers are <span className="muted small">optional, up to 2 Qloo audiences</span></label>
            <select id="viewers" className="input" value="" disabled={audiences.length >= 2} onChange={(e) => { const a = groups.flatMap((g) => g.audiences).find((x) => x.id === e.target.value); if (a && !audiences.some((x) => x.id === a.id)) setAudiences([...audiences, a]); }}>
              <option value="">{audiences.length >= 2 ? "Two picked" : "Pick an audience…"}</option>
              {groups.map((g) => (
                <optgroup key={g.type} label={g.label}>
                  {g.audiences.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
                </optgroup>
              ))}
            </select>
            {audiences.length > 0 && (
              <div className="chips">
                {audiences.map((a) => <button type="button" key={a.id} className="chip" aria-pressed="true" onClick={() => setAudiences(audiences.filter((x) => x.id !== a.id))}>{a.name} ×</button>)}
              </div>
            )}
            <p className="muted small">Cue asks Qloo to lean the artist search toward what this group likes.</p>
          </div>
        )}
        <p className="note">Under-the-radar artists only: big names are left out, and artists who have died or disbanded are dropped. Lesser-known doesn't always mean new.</p>
        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn block">Find artists →</button>
      </form>
    </div>
  );
}

function Shortlist({ search, run }) {
  const [profile, setProfile] = useState(null);
  const result = run.summary?.result;
  useEffect(() => {
    get(`/artists/${search.production.id}/profile`).then(setProfile).catch(() => setProfile(null));
  }, [search.production.id]);
  const tags = profile?.tags || {};
  const loves = [...(tags.genre || []), ...(tags.subgenre || []), ...(tags.theme || [])].filter((t, i, all) => all.indexOf(t) === i).slice(0, 8);

  return (
    <div className="layout-run">
      <div className="stack">
        <div className="stack" style={{ gap: 8 }}>
          <h2>{result ? `${result.artists.length} ${result.label.toLowerCase()} ` : "Finding artists "}for {search.project || search.production.name}</h2>
          <div className="chips">
            <span className="chip">Audience like {search.production.name}</span>
            {search.vibes.length > 0 && <span className="chip">{search.vibes.join(" · ")}</span>}
            {search.audiences?.length > 0 && <span className="chip">Viewers: {search.audiences.map((a) => a.name).join(", ")}</span>}
            <span className="chip" style={{ color: "var(--accent)" }}>Under-the-radar only</span>
          </div>
        </div>
        {loves.length > 0 && (
          <div className="card stack">
            <h3>Your audience loves</h3>
            <p className="muted small">From Qloo, based on {search.production.name}</p>
            <div className="chips">{loves.map((t) => <span className="chip" key={t}>{t}</span>)}</div>
          </div>
        )}
        {run.status === "running" && <RunProgress events={run.events} status={run.status} stages={SUPERVISOR_STAGES} title="Cue is finding artists this audience loves" />}
        {run.status === "error" && <p className="card error">{run.error}</p>}
        {result && result.artists.length === 0 && <p className="note">No under-the-radar artists came back for this audience. Try a different show or brand.</p>}
        {result && result.artists.map((item, index) => <ArtistCard key={item.candidate.id} item={item} index={index} />)}
        {result && <p className="muted small">{result.matches_scored} artists scored with Qloo data in {run.summary.seconds} s. Popularity capped at {Math.round(result.cap * 100)}.</p>}
      </div>
      <Trace events={run.events} status={run.status} />
    </div>
  );
}

function ArtistCard({ item, index }) {
  const [playing, setPlaying] = useState(false);
  const inputs = item.fit.inputs || {};
  const spotifyId = spotifyArtistId(inputs.spotify_url);
  const genres = inputs.genres || [];
  const styles = inputs.styles || [];
  return (
    <article className="card match poster-card reveal" style={{ animationDelay: `${index * 70}ms` }}>
      <Poster src={inputs.image_url} name={item.candidate.name} type="urn:entity:artist" />
      <div className="stack" style={{ gap: 4 }}>
        <h3>
          {item.candidate.name}
          {inputs.life_span === "unverified" && <span className="pill warn" title="MusicBrainz had no record, so we couldn't confirm they're still active">Unverified</span>}
        </h3>
        <p>{item.reason}</p>
        {(genres.length > 0 || styles.length > 0) && (
          <div className="tags" aria-label="Qloo tags">
            {genres.map((t) => <span className="tag" key={`g-${t}`}>{t}</span>)}
            {styles.map((t) => <span className="tag theme" key={`s-${t}`}>{t}</span>)}
          </div>
        )}
      </div>
      <div className="match-side">
        <FitRing value={item.fit.value} size={44} />
        {spotifyId ? (
          <button className="btn small" aria-expanded={playing} onClick={() => setPlaying(!playing)}>{playing ? "Hide player" : "▶ Listen"}</button>
        ) : (
          <span className="muted small">No Spotify link</span>
        )}
      </div>
      {playing && spotifyId && <SpotifyPlayer id={spotifyId} name={item.candidate.name} />}
    </article>
  );
}

export default function SupervisorPage() {
  const [step, setStep] = useState("role");
  const [role, setRole] = useState(null);
  const [search, setSearch] = useState(null);
  const [preset, setPreset] = useState(null);
  const run = useRun();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const wanted = params.get("try");
    if (!wanted) return;
    const type = params.get("type") || "tv_show";
    setRole(ROLES.find((r) => r.type === type) || ROLES[0]);
    setPreset({ query: wanted, type });
    setStep("brief");
  }, []);

  return (
    <Shell tone="supervisor" right={step === "shortlist" ? <button className="btn ghost small" onClick={() => setStep("brief")}>Edit brief</button> : null}>
      {step === "role" && <WhatYouDo onNext={(r) => { setRole(r); setStep("brief"); }} />}
      {step === "brief" && role && (
        <Brief
          role={role}
          preset={preset}
          onFind={(s) => {
            setSearch(s);
            setStep("shortlist");
            run.start({ mode: "supervisor", production_id: s.production.id, production_name: s.production.name, production_type: s.type, brief: s.brief, audiences: (s.audiences || []).map((a) => a.id) });
          }}
        />
      )}
      {step === "shortlist" && search && <Shortlist search={search} run={run} />}
    </Shell>
  );
}
