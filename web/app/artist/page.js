"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import FanMap from "../../components/FanMap";
import FitRing from "../../components/FitRing";
import MatchCharts from "../../components/MatchCharts";
import { QlooMeters } from "../../components/Meter";
import Poster from "../../components/Poster";
import RunProgress, { ARTIST_STAGES } from "../../components/RunProgress";
import Shell, { Steps } from "../../components/Shell";
import Trace from "../../components/Trace";
import { get, post, useRun } from "../../lib/api";
import { AGE_LABELS, SECTIONS, TYPE_FILTERS, genderLean, initials, peakAge, typeLabel } from "../../lib/labels";

const ROLES = [
  { id: "singer", label: "Singer" },
  { id: "band", label: "Band" },
  { id: "producer", label: "Producer" },
  { id: "composer", label: "Composer" },
  { id: "lyricist", label: "Lyricist" },
];
const SAVED_KEY = "cue.artist";
const ROUTE_TEXT = {
  spotify: "Found in Qloo from your Spotify link",
  musicbrainz: "Found through MusicBrainz",
  name: "Found by name",
  stand_in: "Matched through artists you resemble",
};

function readSaved() {
  try {
    return JSON.parse(localStorage.getItem(SAVED_KEY) || "null");
  } catch {
    return null;
  }
}

function writeSaved(value) {
  try {
    if (value) localStorage.setItem(SAVED_KEY, JSON.stringify(value));
    else localStorage.removeItem(SAVED_KEY);
  } catch {}
}

function Avatar({ name, image, small }) {
  return <span className={`avatar ${small ? "small" : ""}`}>{image ? <img src={image} alt="" /> : initials(name)}</span>;
}

function Connect({ onFound }) {
  const [role, setRole] = useState("singer");
  const [byName, setByName] = useState(false);
  const [link, setLink] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    if (byName ? !name.trim() : !link.trim()) {
      setError(byName ? "Type your artist name first." : "Paste your Spotify artist link first.");
      return;
    }
    setBusy(true);
    try {
      const found = byName
        ? await post("/onboarding/name", { name: name.trim(), role })
        : await post("/onboarding/spotify", { link: link.trim(), role, name: name.trim() });
      onFound({ ...found, typedName: name.trim() });
    } catch (failure) {
      setError(`Couldn't reach Cue: ${failure.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="narrow">
      <div className="stack">
        <h2>Let's find your music</h2>
        <p className="lede">{byName ? "Type your artist name. We'll look you up in Qloo." : "Paste your Spotify artist link. We use it to find you in Qloo, nothing else."}</p>
      </div>
      <form className="card stack" onSubmit={submit} noValidate>
        {byName ? (
          <label className="field" htmlFor="artist-name">
            Artist name
            <input id="artist-name" className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Prateek Kuhad" />
          </label>
        ) : (
          <label className="field" htmlFor="spotify-link">
            Spotify artist link
            <input id="spotify-link" className="input" value={link} onChange={(e) => setLink(e.target.value)} placeholder="open.spotify.com/artist/…" />
          </label>
        )}
        <div className="stack">
          <span className="field">I'm a…</span>
          <div className="chips" role="group" aria-label="Your role">
            {ROLES.map((r) => (
              <button type="button" key={r.id} className="chip" aria-pressed={role === r.id} onClick={() => setRole(r.id)}>
                {r.label}
              </button>
            ))}
          </div>
        </div>
        {!byName && role === "lyricist" && (
          <label className="field" htmlFor="lyricist-name">
            Your name <span className="muted small">(helps us find lyricists through MusicBrainz)</span>
            <input id="lyricist-name" className="input" value={name} onChange={(e) => setName(e.target.value)} />
          </label>
        )}
        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn block" disabled={busy}>
          {busy ? "Looking you up…" : "Find me →"}
        </button>
      </form>
      <p className="muted small" style={{ textAlign: "center" }}>
        {byName ? "Have a Spotify link? " : "Not on Spotify? "}
        <button type="button" className="linkish" onClick={() => setByName(!byName)}>
          {byName ? "Use your Spotify link" : "Search by name instead"}
        </button>
      </p>
    </div>
  );
}

function StandIn({ defaultName, onReady }) {
  const [name, setName] = useState(defaultName || "");
  const [names, setNames] = useState(["", "", ""]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [skipped, setSkipped] = useState([]);

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    const wanted = names.map((n) => n.trim()).filter(Boolean);
    if (!name.trim()) return setError("Add your own artist name so the pitches can use it.");
    if (!wanted.length) return setError("Name at least one artist you sound like.");
    setBusy(true);
    try {
      const found = await post("/onboarding/sounds-like", { names: wanted });
      setSkipped(found.skipped || []);
      if (!found.candidates.length) setError(found.note || "None of those artists are in Qloo. Try others.");
      else onReady(name.trim(), found.candidates);
    } catch (failure) {
      setError(`Couldn't reach Cue: ${failure.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="note stack" onSubmit={submit} noValidate>
      <div>
        <h3>Not on Qloo yet? No problem.</h3>
        <p className="small">Name up to 3 artists you sound like. We'll use their fans as a stand-in.</p>
      </div>
      <label className="field" htmlFor="own-name">
        Your artist name
        <input id="own-name" className="input" value={name} onChange={(e) => setName(e.target.value)} />
      </label>
      <div className="stack" style={{ gap: 4 }}>
        <strong style={{ color: "var(--ink)" }}>Artists you sound like</strong>
        <span className="muted small">Pick artists whose music is close to yours, not just ones you like.</span>
      </div>
      <div className="grid-3 fixed">
        {names.map((value, index) => (
          <label className="field" key={index} htmlFor={`like-${index}`}>
            <span>Sounds like {index + 1}{index > 0 && <span className="muted small"> (optional)</span>}</span>
            <input
              id={`like-${index}`}
              className="input"
              value={value}
              placeholder={["e.g. Bon Iver", "e.g. Hozier", "e.g. Prateek Kuhad"][index]}
              onChange={(e) => setNames(names.map((n, i) => (i === index ? e.target.value : n)))}
            />
          </label>
        ))}
      </div>
      {skipped.length > 0 && <p className="small">Skipped: {skipped.join(" · ")}</p>}
      {error && <p className="error" role="alert">{error}</p>}
      <div>
        <button className="btn dark small" disabled={busy}>{busy ? "Checking…" : "Use these instead"}</button>
      </div>
    </form>
  );
}

function Confirm({ found, onConfirm, onBack }) {
  const [index, setIndex] = useState(0);
  const candidates = found.candidates || [];
  const current = candidates[index];
  return (
    <div className="narrow">
      <h2>{current ? "Is this you?" : "We couldn't find you in Qloo"}</h2>
      {current ? (
        <div className="card stack">
          <div className="person">
            <Avatar name={current.name} image={current.image_url} />
            <div className="stack" style={{ gap: 4 }}>
              <h3 style={{ fontSize: "1.3rem" }}>{current.name}</h3>
              <p className="muted small">{current.description || typeLabel(current.type)}</p>
              <div className="row">
                <span className="pill good">{ROUTE_TEXT[found.route] || "Found in Qloo"}</span>
                {current.listeners ? <span className="pill plain">{current.listeners.toLocaleString()} Last.fm listeners</span> : null}
              </div>
            </div>
          </div>
          <div className="row">
            <button className="btn" style={{ flex: 1 }} onClick={() => onConfirm({ name: current.name, signal_ids: [current.entity_id], route: found.route, basis: "measured", profile_id: current.entity_id, image: current.image_url })}>
              Yes, that's me
            </button>
            <button className="btn ghost" style={{ flex: 1 }} onClick={() => (index + 1 < candidates.length ? setIndex(index + 1) : setIndex(candidates.length))}>
              Not me
            </button>
          </div>
          {candidates.length > 1 && <p className="muted small">Showing {index + 1} of {candidates.length} artists with this name.</p>}
        </div>
      ) : (
        <p className="lede">{found.note || "None of these were you."}</p>
      )}
      <StandIn
        defaultName={found.typedName || current?.name || ""}
        onReady={(name, picks) => onConfirm({ name, signal_ids: picks.map((p) => p.entity_id), route: "stand_in", basis: "projected", profile_id: picks[0].entity_id, resemble: picks.map((p) => p.name) })}
      />
      <button className="linkish" onClick={onBack}>← Start over</button>
    </div>
  );
}

const LEVELS = [
  [0.25, "Far more than average"],
  [0.05, "More than average"],
  [-0.05, "About average"],
  [-0.25, "Fewer than average"],
  [-Infinity, "Far fewer than average"],
];

function level(value) {
  return LEVELS.find(([floor]) => value >= floor)[1];
}

function compact(n) {
  if (n == null) return "—";
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${Math.round(n / 1e3)}K`;
  return String(n);
}

function distinct(list) {
  const key = (t) => t.toLowerCase().replace(/[^a-z0-9]/g, "");
  return list.filter((t, i, all) => all.findIndex((x) => key(x) === key(t)) === i);
}

function Venues({ artistId }) {
  const [city, setCity] = useState("");
  const [found, setFound] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const search = async (event) => {
    event.preventDefault();
    setError("");
    if (!city.trim()) return setError("Type a city first, such as Detroit or Mumbai.");
    setBusy(true);
    try {
      const body = await get(`/artists/${artistId}/venues?city=${encodeURIComponent(city.trim())}`);
      setFound(body);
      if (!body.venues.length) setError(`Qloo has no live-music venues for ${city.trim()} yet. Try a bigger city nearby.`);
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="card stack" onSubmit={search} noValidate>
      <div className="stack" style={{ gap: 4 }}>
        <h3>Where to play live</h3>
        <p className="muted small">Live-music venues in a city that Qloo says your fans would go to.</p>
      </div>
      <div className="row" style={{ flexWrap: "nowrap" }}>
        <label className="sr-only" htmlFor="venue-city">City</label>
        <input id="venue-city" className="input" value={city} onChange={(e) => setCity(e.target.value)} placeholder="e.g. Detroit" />
        <button className="btn small" disabled={busy}>{busy ? "Looking…" : "Find venues"}</button>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      {found && found.venues.length > 0 && (
        <div className="rank-list">
          {found.venues.map((v, index) => (
            <div key={v.id} className="rank-row" title={v.address || found.city}>
              <span className="rank-num">{index + 1}</span>
              <span className="rank-name">{v.name}<small>{v.address || found.city}</small></span>
              <span className="rank-bar"><span style={{ width: `${Math.round((v.affinity || 0) * 100)}%` }} /></span>
              <span className="rank-val">{Math.round((v.affinity || 0) * 100)}</span>
            </div>
          ))}
          <p className="muted small">The bar is how strongly your fans like each venue on Qloo.</p>
        </div>
      )}
    </form>
  );
}

function FanInsights({ run }) {
  const result = run.summary?.result;
  return (
    <section className="stack">
      <div className="stack" style={{ gap: 4 }}>
        <h3>What Qloo learned about your fans</h3>
        <p className="muted small">Cue scores shows, films, games, podcasts and brands for your fans as soon as you're confirmed.</p>
      </div>
      {run.status === "running" && <div className="card loading"><span className="spinner" /><strong>Scoring productions for your fans…</strong><span className="muted small">About 30 seconds. The charts appear here when it's done.</span></div>}
      {run.status === "error" && <p className="card error">{run.error}</p>}
      {result && <MatchCharts result={result} />}
    </section>
  );
}

function Fans({ artist, run, onStart }) {
  const [profile, setProfile] = useState(null);
  const [similar, setSimilar] = useState(null);
  const [error, setError] = useState("");
  const [brief, setBrief] = useState("");

  useEffect(() => {
    let live = true;
    get(`/artists/${artist.profile_id}/profile`)
      .then((p) => live && setProfile(p))
      .catch((failure) => live && setError(failure.message));
    get(`/artists/${artist.profile_id}/similar`)
      .then((s) => live && setSimilar(s.artists || []))
      .catch(() => live && setSimilar([]));
    return () => {
      live = false;
    };
  }, [artist.profile_id]);

  const entity = profile?.entity || {};
  const tags = profile?.tags || {};
  const genres = distinct([...(tags.genre || []), ...(tags.subgenre || [])]).slice(0, 6);
  const sound = distinct([...(tags.music || []), ...(tags.characteristic || []), ...(tags.style || []).filter((s) => !s.includes(" "))]).slice(0, 8);
  const themes = (tags.theme || []).slice(0, 6);
  const audience = tags.audience || [];
  const instruments = tags.instrument || [];
  const influences = tags.influenced_by || [];
  const age = profile?.demographics?.age || {};
  const female = profile?.demographics?.gender?.female;
  const peak = peakAge(age);
  const listeners = entity.lastfm_listeners;
  const plays = entity.lastfm_scrobbles;
  const popularity = entity.ref?.popularity;
  const backdrop = entity.image_url || artist.image;

  return (
    <>
      {error && <p className="error">Couldn't load your fan profile: {error}</p>}
      {!profile && !error && (
        <div className="loading"><span className="spinner" /><span className="muted">Reading your fans from Qloo…</span></div>
      )}
      {profile && (
        <>
          <section className="card fan-hero" style={backdrop ? { "--poster": `url("${encodeURI(backdrop)}")` } : undefined}>
            <Poster src={backdrop} name={artist.name} type="urn:entity:artist" size="xl" />
            <div className="stack" style={{ gap: 8 }}>
              <span className="fan-hi">Hi {artist.name}</span>
              <h2>Here's who loves your music</h2>
              {entity.description && <p className="fan-desc">{entity.description}</p>}
              {artist.basis === "projected" && <p className="fan-desc">Based on fans of {artist.resemble?.join(", ")}, the artists you sound like.</p>}
              {genres.length > 0 && <div className="chips">{genres.map((t) => <span className="chip" key={t}>{t}</span>)}</div>}
            </div>
            <div className="hero-stats">
              <div className="hero-stat"><strong>{compact(listeners)}</strong><span>Last.fm listeners</span></div>
              <div className="hero-stat"><strong>{compact(plays)}</strong><span>Total plays</span></div>
              <div className="hero-stat"><strong>{listeners && plays ? Math.round(plays / listeners) : "—"}</strong><span>Plays per listener</span></div>
              <div className="hero-stat"><strong>{popularity == null ? "—" : Math.round(popularity * 100)}<small>/100</small></strong><span>Popularity on Qloo</span></div>
            </div>
          </section>

          <div className="grid-2 fan-grid">
            <div className="card stack">
              <div className="between"><h3>How old your fans are</h3>{peak && <span className="pill">Biggest group: {AGE_LABELS[peak]}</span>}</div>
              <p className="muted small">Compared with the average Qloo user. Bars to the right mean more of your fans are that age.</p>
              <div className="diverge" role="list">
                {Object.entries(AGE_LABELS).map(([key, labelText]) => {
                  const value = age[key];
                  if (value == null) return null;
                  const width = `${Math.min(50, Math.abs(value) * 50)}%`;
                  return (
                    <div key={key} role="listitem" className={`diverge-row ${key === peak ? "peak" : ""}`}>
                      <span className="diverge-label">{labelText}</span>
                      <span className="diverge-track"><span className={`diverge-bar ${value >= 0 ? "up" : "down"}`} style={{ width }} /></span>
                      <span className="level">{level(value)}</span>
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="card stack">
              <h3>Women and men</h3>
              <p className="muted small">Which way your fans lean, compared with the average Qloo user.</p>
              {female == null ? (
                <p className="muted">No gender data from Qloo.</p>
              ) : (
                <>
                  <div className="meter" aria-label={genderLean(profile.demographics.gender)}>
                    <span style={{ left: `${50 - Math.max(-1, Math.min(1, female)) * 45}%` }} />
                  </div>
                  <div className="meter-labels"><span>More women</span><span>Even</span><span>More men</span></div>
                  <strong style={{ color: "var(--ink)" }}>{genderLean(profile.demographics.gender)}</strong>
                </>
              )}
              {audience.length > 0 && (
                <>
                  <p className="muted small" style={{ marginTop: 8 }}>Qloo describes your fans as</p>
                  <div className="chips">{audience.map((t) => <span className="chip gold" key={t}>{t}</span>)}</div>
                </>
              )}
            </div>
          </div>

          {(sound.length > 0 || themes.length > 0 || influences.length > 0) && (
            <div className="grid-3">
              {sound.length > 0 && (
                <div className="card stack">
                  <h3>Your sound, in Qloo's words</h3>
                  <div className="chips">{sound.map((t) => <span className="chip gold" key={t}>{t}</span>)}</div>
                  {instruments.length > 0 && <p className="muted small">Played on {instruments.join(" · ")}</p>}
                </div>
              )}
              {themes.length > 0 && (
                <div className="card stack">
                  <h3>What your songs are about</h3>
                  <div className="chips">{themes.map((t) => <span className="chip" key={t}>{t}</span>)}</div>
                </div>
              )}
              {influences.length > 0 && (
                <div className="card stack">
                  <h3>Influenced by</h3>
                  <ul className="plain-list">{influences.map((t) => <li key={t}>{t}</li>)}</ul>
                </div>
              )}
            </div>
          )}

          {similar && similar.length > 0 && (
            <div className="card stack">
              <h3>Cue compares you with fans of</h3>
              <p className="muted small">A match counts when your fans like a show, film, game, podcast or brand more than these artists' fans do. That's what keeps the list from being just "whatever is popular".</p>
              <div className="similar-row">
                {similar.map((s) => (
                  <div className="similar" key={s.id}>
                    <Poster src={s.image_url} name={s.name} type="urn:entity:artist" />
                    <span>{s.name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <FanInsights run={run} />

          <FanMap artistId={artist.profile_id} />

          <Venues artistId={artist.profile_id} />

          <form
            className="card stack brief-card"
            onSubmit={(event) => {
              event.preventDefault();
              onStart(brief.trim());
            }}
          >
            <label className="field" htmlFor="brief">
              What's the music for? <span className="muted small">(optional)</span>
              <input id="brief" className="input" maxLength={300} value={brief} onChange={(e) => setBrief(e.target.value)} placeholder="e.g. acoustic songs for a monsoon romance scene" />
            </label>
            <div><button className="btn">See where to pitch →</button></div>
          </form>
        </>
      )}
    </>
  );
}

function Matches({ run, onPitch, onRetry }) {
  const [filter, setFilter] = useState("all");
  const result = run.summary?.result;
  const types = TYPE_FILTERS.find((f) => f.id === filter)?.types;
  const keep = (item) => !types || types.includes(item.candidate.type);
  return (
    <div className="layout-run">
      <div className="stack">
        <div className="stack" style={{ gap: 6 }}>
          <h2>Your best places to pitch</h2>
          <p className="muted">Ranked by how much more your fans like each one than fans of similar artists do.</p>
        </div>
        {run.status === "running" && <RunProgress events={run.events} status={run.status} stages={ARTIST_STAGES} title="Cue is working through Qloo for you" />}
        {run.status === "error" && (
          <div className="card stack"><p className="error">{run.error}</p><div><button className="btn small" onClick={onRetry}>Try again</button></div></div>
        )}
        {result && (
          <>
            <div className="tabs" role="group" aria-label="Filter by type">
              {TYPE_FILTERS.map((f) => (
                <button key={f.id} className="chip" aria-pressed={filter === f.id} onClick={() => setFilter(f.id)}>{f.label}</button>
              ))}
            </div>
            {result.pitches.length === 0 && <p className="note">Qloo found matches, but no pitches could be written this time.</p>}
            {SECTIONS.map((section) => {
              const items = (result.sections[section.id] || []).filter(keep);
              if (!items.length) return null;
              return (
                <section key={section.id} className="stack">
                  <div className="marquee"><h3>{section.title}</h3><span>{section.hint}</span></div>
                  {items.map((item, index) => (
                    <article key={item.candidate.id} className="card match poster-card reveal" style={{ animationDelay: `${index * 70}ms` }}>
                      <Poster src={item.fit.inputs?.image_url} name={item.candidate.name} type={item.candidate.type} />
                      <div className="stack" style={{ gap: 4 }}>
                        <h3>{item.candidate.name} <span className="pill">{typeLabel(item.candidate.type)}</span>{BASIS_LABELS[item.fit.inputs?.basis] && <span className="pill warn" title="Qloo shows no taste lean toward your music here; only the audience's age and gender line up">{BASIS_LABELS[item.fit.inputs.basis]}</span>}</h3>
                        <p>{item.reason}</p>
                        <Tags inputs={item.fit.inputs} />
                        <QlooMeters inputs={item.fit.inputs} popularity={item.candidate.popularity} />
                      </div>
                      <div className="match-side">
                        <FitRing value={item.fit.value} />
                        <button className="btn small ghost" onClick={() => onPitch(item)}>Write pitch</button>
                      </div>
                    </article>
                  ))}
                </section>
              );
            })}
            <AlsoLove groups={result.also_love} keep={(row) => !types || types.includes(row.type)} />
            <p className="muted small">{result.matches_scored} productions scored with Qloo data in {run.summary.seconds} s. Pitches are drafts: Cue never sends anything.</p>
          </>
        )}
      </div>
      <Trace events={run.events} status={run.status} />
    </div>
  );
}

const BASIS_LABELS = { audience_only: "Audience match only", weak: "Weak match" };

function AlsoLove({ groups, keep }) {
  const entries = Object.entries(groups || {})
    .map(([type, rows]) => [type, rows.filter(keep)])
    .filter(([, rows]) => rows.length);
  if (!entries.length) return null;
  return (
    <section className="card stack">
      <div className="stack" style={{ gap: 4 }}>
        <h3>More your fans love</h3>
        <p className="muted small">Other productions Qloo scored for your fans, beyond the picks above. The bar is Cue's fit score; the small number is popularity on Qloo.</p>
      </div>
      <div className="grid-2">
        {entries.map(([type, rows]) => (
          <div key={type} className="stack" style={{ gap: 8 }}>
            <strong>{typeLabel(type)}</strong>
            <div className="rank-list">
              {rows.map((row, index) => (
                <div key={row.id} className="rank-row" title={`Popularity ${Math.round(row.popularity * 100)} · fit ${Math.round(row.fit * 100)}`}>
                  <span className="rank-num">{index + 1}</span>
                  <span className="rank-name">{row.name}<small>popularity {Math.round(row.popularity * 100)}</small></span>
                  <span className="rank-bar"><span style={{ width: `${Math.round(row.fit * 100)}%` }} /></span>
                  <span className="rank-val">{Math.round(row.fit * 100)}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function Tags({ inputs }) {
  const genres = inputs?.genres || [];
  const themes = inputs?.themes || [];
  if (!genres.length && !themes.length) return null;
  return (
    <div className="tags" aria-label="Qloo tags">
      {genres.map((t) => <span className="tag" key={`g-${t}`}>{t}</span>)}
      {themes.map((t) => <span className="tag theme" key={`t-${t}`}>{t}</span>)}
    </div>
  );
}

function Pitch({ item, artist, onBack }) {
  const [subject, setSubject] = useState(item.email_subject);
  const [body, setBody] = useState(item.email_body);
  const [song, setSong] = useState("");
  const [copied, setCopied] = useState("");
  const inputs = item.fit.inputs || {};
  const section = SECTIONS.find((s) => s.id === inputs.section);
  const text = `Subject: ${subject}\n\n${body}${song.trim() ? `\n\nListen: ${song.trim()}` : ""}`;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied("Copied. Paste it into your email.");
    } catch {
      setCopied("Couldn't copy automatically. Select the text and copy it.");
    }
  };

  return (
    <div className="stack">
      <button className="linkish" onClick={onBack} style={{ justifySelf: "start" }}>← Back to matches</button>
      <div className="pitch-layout">
        <aside className="card why" style={inputs.image_url ? { "--poster": `url("${encodeURI(inputs.image_url)}")` } : undefined}>
          <div className="between"><span className="pill">{typeLabel(item.candidate.type)}</span><FitRing value={item.fit.value} size={44} /></div>
          <Poster src={inputs.image_url} name={item.candidate.name} type={item.candidate.type} size="lg" />
          <h2>{item.candidate.name}</h2>
          <Tags inputs={inputs} />
          <p className="small">Why it fits</p>
          <ul className="small">
            <li>{item.reason}</li>
            {section && <li>{section.title}: {section.hint.toLowerCase()}</li>}
            {BASIS_LABELS[inputs.basis] && <li>{BASIS_LABELS[inputs.basis]}: Qloo shows no taste lean toward your music here</li>}
          </ul>
          <QlooMeters inputs={inputs} popularity={item.candidate.popularity} />
        </aside>
        <div className="card stack">
          <div className="between"><h3>Your pitch</h3><span className="pill">Draft · edit anything</span></div>
          <label className="field" htmlFor="subject">Subject<input id="subject" className="input" value={subject} onChange={(e) => setSubject(e.target.value)} /></label>
          <label className="field" htmlFor="message">Message<textarea id="message" className="input" value={body} onChange={(e) => setBody(e.target.value)} /></label>
          <label className="field" htmlFor="song">Song to share<input id="song" className="input" value={song} onChange={(e) => setSong(e.target.value)} placeholder="Spotify link to your track" /></label>
          <div className="row">
            <button className="btn" onClick={copy}>Copy pitch</button>
            <span className="muted small">{copied || `Cue never sends anything. Copy this and send it yourself, ${artist.name}.`}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ArtistPage() {
  const [step, setStep] = useState("connect");
  const [found, setFound] = useState(null);
  const [artist, setArtist] = useState(null);
  const [brief, setBrief] = useState("");
  const [pitch, setPitch] = useState(null);
  const run = useRun();

  const [trying, setTrying] = useState("");

  useEffect(() => {
    const wanted = new URLSearchParams(window.location.search).get("try");
    if (wanted) {
      writeSaved(null);
      setTrying(wanted);
      setStep("trying");
      post("/onboarding/name", { name: wanted, role: "singer" })
        .then((f) => {
          setFound({ ...f, typedName: wanted });
          setStep("confirm");
        })
        .catch(() => setStep("connect"));
      return;
    }
    const saved = readSaved();
    if (saved?.signal_ids?.length) {
      setArtist(saved);
      setStep("fans");
    }
  }, []);

  const ranFor = useRef(null);
  const launch = (text) => {
    setBrief(text);
    ranFor.current = artist.profile_id;
    run.start({ mode: "artist", signal_ids: artist.signal_ids, artist_name: artist.name, basis: artist.basis, route: artist.route, brief: text });
  };

  useEffect(() => {
    if (step === "fans" && artist && ranFor.current !== artist.profile_id) launch("");
  }, [step, artist]);

  const startRun = (text) => {
    setStep("matches");
    if (text === brief && ranFor.current === artist.profile_id && run.status !== "error") return;
    launch(text);
  };

  const stepIndex = { trying: 0, connect: 0, confirm: 1, fans: 2, matches: 2, pitch: 2 }[step];
  const nav = useMemo(
    () =>
      artist ? (
        <>
          <span className="muted small">{artist.name}</span>
          <button
            className="linkish small"
            onClick={() => {
              writeSaved(null);
              ranFor.current = null;
              setArtist(null);
              setFound(null);
              setStep("connect");
            }}
          >
            Not you?
          </button>
        </>
      ) : (
        <Steps steps={["Connect", "Confirm", "Your fans"]} current={stepIndex} />
      ),
    [artist, stepIndex]
  );

  return (
    <Shell right={nav}>
      {step === "trying" && (
        <div className="narrow"><div className="card loading"><span className="spinner" /><strong>Looking up {trying} in Qloo…</strong></div></div>
      )}
      {step === "connect" && (
        <Connect
          onFound={(f) => {
            setFound(f);
            setStep("confirm");
          }}
        />
      )}
      {step === "confirm" && found && (
        <Confirm
          found={found}
          onBack={() => setStep("connect")}
          onConfirm={(chosen) => {
            setArtist(chosen);
            writeSaved(chosen);
            setStep("fans");
          }}
        />
      )}
      {step === "fans" && artist && <Fans artist={artist} run={run} onStart={startRun} />}
      {step === "matches" && artist && <Matches run={run} onPitch={(item) => { setPitch(item); setStep("pitch"); }} onRetry={() => startRun(brief)} />}
      {step === "pitch" && pitch && <Pitch item={pitch} artist={artist} onBack={() => setStep("matches")} />}
    </Shell>
  );
}
