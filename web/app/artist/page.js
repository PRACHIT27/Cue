"use client";

import { useEffect, useMemo, useState } from "react";
import FitRing from "../../components/FitRing";
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
      <div className="grid-3 fixed">
        {names.map((value, index) => (
          <label className="field" key={index} htmlFor={`like-${index}`}>
            Artist {index + 1}
            <input
              id={`like-${index}`}
              className="input"
              value={value}
              placeholder={index === 0 ? "e.g. an artist you love" : "Optional"}
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

function Fans({ artist, onStart }) {
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState("");
  const [brief, setBrief] = useState("");

  useEffect(() => {
    let live = true;
    get(`/artists/${artist.profile_id}/profile`)
      .then((p) => live && setProfile(p))
      .catch((failure) => live && setError(failure.message));
    return () => {
      live = false;
    };
  }, [artist.profile_id]);

  const age = profile?.demographics?.age || {};
  const peak = peakAge(age);
  const tags = profile?.tags || {};
  const interests = [...(tags.genre || []), ...(tags.style || []), ...(tags.subgenre || [])].filter((t, i, all) => all.indexOf(t) === i).slice(0, 8);
  const moods = [...(tags.music || []), ...(tags.characteristic || [])].filter((t, i, all) => all.indexOf(t) === i).slice(0, 6);
  const audience = tags.audience || [];
  const ageValues = Object.values(age);
  const maxAge = Math.max(0.0001, ...ageValues.map((v) => v + 1));

  return (
    <>
      <div className="between">
        <div className="stack" style={{ gap: 4 }}>
          <span className="muted">Hi {artist.name}</span>
          <h2>Here's who loves your music</h2>
          {artist.basis === "projected" && <p className="muted small">Based on fans of {artist.resemble?.join(", ")}, the artists you resemble.</p>}
        </div>
      </div>
      {error && <p className="error">Couldn't load your fan profile: {error}</p>}
      {!profile && !error && (
        <div className="loading"><span className="spinner" /><span className="muted">Reading your fans from Qloo…</span></div>
      )}
      {profile && (
        <>
          <div className="grid-3">
            <div className="card stat dark"><span>Fans' top taste</span><strong>{interests[0] || "—"}</strong></div>
            <div className="card stat"><span className="muted">Mostly aged</span><strong>{peak ? AGE_LABELS[peak] : "—"}</strong></div>
            <div className="card stat"><span className="muted">Last.fm listeners</span><strong>{profile.entity.lastfm_listeners ? profile.entity.lastfm_listeners.toLocaleString() : "—"}</strong></div>
          </div>
          <div className="grid-3">
            <div className="card stack">
              <h3>What your fans are into</h3>
              <p className="muted small">Genres and styles Qloo links to your music.</p>
              <div className="chips">{interests.map((t) => <span className="chip" key={t}>{t}</span>)}</div>
              {moods.length > 0 && <><p className="muted small">The sound</p><div className="chips">{moods.map((t) => <span className="chip" key={t}>{t}</span>)}</div></>}
            </div>
            <div className="card stack">
              <h3>Age of your fans</h3>
              <p className="muted small">Taller means more of your fans than average are this age.</p>
              <div className="age-chart" role="img" aria-label={`Fans peak at ${peak ? AGE_LABELS[peak] : "unknown"}`}>
                {Object.entries(AGE_LABELS).map(([key, labelText]) => (
                  <div key={key} className={`age-col ${key === peak ? "peak" : ""}`}>
                    <span className="col" style={{ height: `${Math.max(6, (((age[key] ?? -1) + 1) / maxAge) * 110)}px` }} />
                    <span>{labelText}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="card stack">
              <h3>Who they are</h3>
              <p>{genderLean(profile.demographics?.gender) || "No gender data"}</p>
              {audience.length > 0 && <><p className="muted small">Qloo describes your audience as</p><div className="chips">{audience.map((t) => <span className="chip" key={t}>{t}</span>)}</div></>}
              {(tags.influenced_by || []).length > 0 && <p className="muted small">Influences: {tags.influenced_by.join(", ")}</p>}
            </div>
          </div>
          <form
            className="card stack"
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
        {run.status === "running" && (
          <div className="card loading"><span className="spinner" /><strong>Asking Qloo about your fans…</strong><span className="muted small">This takes about 30 seconds. Watch every call in the trace.</span></div>
        )}
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
                  <div className="section-head"><h3>{section.title}</h3><span>{section.hint}</span></div>
                  {items.map((item) => (
                    <article key={item.candidate.id} className="card match">
                      <FitRing value={item.fit.value} />
                      <div className="stack" style={{ gap: 4 }}>
                        <h3>{item.candidate.name} <span className="pill">{typeLabel(item.candidate.type)}</span>{BASIS_LABELS[item.fit.inputs?.basis] && <span className="pill warn" title="Qloo shows no taste lean toward your music here; only the audience's age and gender line up">{BASIS_LABELS[item.fit.inputs.basis]}</span>}</h3>
                        <p>{item.reason}</p>
                      </div>
                      <button className="btn small ghost" onClick={() => onPitch(item)}>Write pitch</button>
                    </article>
                  ))}
                </section>
              );
            })}
            <p className="muted small">{result.matches_scored} productions scored with Qloo data in {run.summary.seconds} s. Pitches are drafts: Cue never sends anything.</p>
          </>
        )}
      </div>
      <Trace events={run.events} status={run.status} />
    </div>
  );
}

const BASIS_LABELS = { audience_only: "Audience match only", weak: "Weak match" };

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
        <aside className="card why">
          <div className="between"><span className="pill">{typeLabel(item.candidate.type)}</span><FitRing value={item.fit.value} size={44} /></div>
          <h2>{item.candidate.name}</h2>
          <p className="small">Why it fits</p>
          <ul className="small">
            <li>{item.reason}</li>
            {section && <li>{section.title}: {section.hint.toLowerCase()}</li>}
            {typeof inputs.audience === "number" && <li>Audience age and gender match: {Math.round(inputs.audience * 100)}%</li>}
            {BASIS_LABELS[inputs.basis] && <li>{BASIS_LABELS[inputs.basis]}: Qloo shows no taste lean toward your music here</li>}
          </ul>
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

  useEffect(() => {
    const saved = readSaved();
    if (saved?.signal_ids?.length) {
      setArtist(saved);
      setStep("fans");
    }
  }, []);

  const startRun = (text) => {
    setBrief(text);
    setStep("matches");
    run.start({ mode: "artist", signal_ids: artist.signal_ids, artist_name: artist.name, basis: artist.basis, route: artist.route, brief: text });
  };

  const stepIndex = { connect: 0, confirm: 1, fans: 2, matches: 2, pitch: 2 }[step];
  const nav = useMemo(
    () =>
      artist ? (
        <>
          <span className="muted small">{artist.name}</span>
          <button
            className="linkish small"
            onClick={() => {
              writeSaved(null);
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
      {step === "fans" && artist && <Fans artist={artist} onStart={startRun} />}
      {step === "matches" && artist && <Matches run={run} onPitch={(item) => { setPitch(item); setStep("pitch"); }} onRetry={() => startRun(brief)} />}
      {step === "pitch" && pitch && <Pitch item={pitch} artist={artist} onBack={() => setStep("matches")} />}
    </Shell>
  );
}
