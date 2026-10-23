# Cue — Product Requirements Document

| | |
|---|---|
| Status | Draft v0.1 |
| Hackathon | Qloo Agentic Hackathon, deadline 30 Oct 2026, 11:45 PM ET |
| Team | Prachit (foundation and app), Vedant (agents and tools), Swara (PM, docs, demo) |
| Related | [DESIGN.md](DESIGN.md), [COMPETITION.md](COMPETITION.md), [BUILD_PROMPTS.md](BUILD_PROMPTS.md) |

## 1. Summary

Cue is an agent that matches emerging musicians with the TV shows, films, video games, podcasts and
ads whose audiences already love their sound. It works in two directions. An artist gets a ranked
list of productions to pitch and a ready-to-send pitch kit. A music supervisor gets a ranked
shortlist of emerging artists who fit their show. Qloo's taste data drives every match; plain code
scores them; an LLM plans the work and writes the output.

## 2. Problem statement

**For artists.** Sync licensing (placing songs in TV, film, games and ads) is one of the few large
income sources an independent musician can reach without a record label. But artists don't know
which productions suit them, so they mass-email music supervisors and get ignored.

**For music supervisors.** Supervisors pick songs for shows under deadline. They rely on a small
circle of labels and publishers, so emerging artists rarely get heard, and shows keep using the
same famous tracks.

**Why existing tools fall short.** Sync marketplaces let you search by genre, mood and tempo. None
of them answer the question that matters: *does this show's audience already love music like
this?* A plain LLM can't answer it either; it guesses from fame and invents shows.

**Why Qloo.** Qloo knows what people who like an artist also like across TV, film, games, podcasts
and brands. That cross-category link is the whole product.

## 3. Goals

- G-1 Ground every match in Qloo data and show the reason for each one
- G-2 Beat an LLM-only baseline on a public eval of real placements
- G-3 Produce a pitch kit or shortlist good enough to send, in under a minute
- G-4 Run live and free for judges until 16 Nov 2026
- G-5 Make the depth of Qloo use visible: every call traced and shown

## 4. Non-goals

- Licensing contracts, payments or rights management
- Sending email or contacting anyone automatically
- Audio analysis of songs (we match on audience taste, not sound waves)
- Predicting income or offering money to artists
- Accounts and logins beyond what the demo needs

## 5. Users

### 5.1 Persona A — Independent artist (primary for the demo)

Has released music, has some fans, no label. Wants to know where to pitch and what to say. Success
for them: a short list of productions that make sense, with a reason they can quote.

### 5.2 Persona B — Music supervisor

Chooses music for a show, film, game or ad. Wants fresh artists who fit the audience, fast.
Success for them: a shortlist they'd actually listen to, with nothing made up.

### 5.3 Persona C — Talent agency or label scout (pitch only)

Manages many artists. Would use both modes at scale. Not built for the hackathon; it's the business
story.

## 6. User stories

| ID | Story |
|---|---|
| US-1 | As an artist, I paste my Spotify link or type my name (or, if Qloo doesn't know me yet, describe my music) and see who my fans are |
| US-2 | As an artist, I see a ranked list of shows, films, games, podcasts and brands that fit my fans, each with a reason |
| US-3 | As an artist, I get a pitch email per production that I can edit and send myself |
| US-4 | As a supervisor, I enter a show, film, game or brand and get a ranked shortlist of emerging artists |
| US-5 | As anyone, I watch the agent work step by step and see every Qloo call it made |
| US-6 | As a judge, I see an eval page comparing Cue with an LLM alone and an LLM with web search |

## 7. Functional requirements

### FR-1 Artist onboarding (US-1)

Onboarding links the artist (singer, band, composer, producer or lyricist) to the Qloo entities
that stand for them. We ask for their **Spotify artist link** and their **role**, then try three
routes in order; each runs only if the one before it found nothing. Flow and rules are in
[DESIGN.md](DESIGN.md) §2.1.

**Route 1 — Qloo knows the Spotify ID (happy path).** `/entities?external.spotify.ids=` returns
their entry. Typical for singers, bands and composers who release music. If it returns more than
one entry, prefer the `urn:entity:artist` one.

**Route 2 — Qloo doesn't know the Spotify ID, but knows the person.** Turn the Spotify ID into a
MusicBrainz ID (MBID) through MusicBrainz, then look the MBID up in Qloo with
`/entities?external.musicbrainz.ids=`. Typical for lyricists, whom Qloo often stores only as
`urn:entity:person` with no Spotify ID. MusicBrainz's direct Spotify-link lookup missed 2 of 3
lyricists we tested, so the backup is: search MusicBrainz by name and keep only the result whose
Spotify link matches theirs.

**Route 3 — Qloo doesn't know them at all.** Build a taste stand-in from a short profile:

| Question | Used for |
|---|---|
| Artists you sound like (3–5) | Main signal, each resolved in Qloo by exact match |
| Your genre | Tags via `/v2/tags`, second signal |
| Five songs you love | The agent names each song's artist, then resolves them in Qloo |
| Instagram and Spotify followers | Confirms "emerging"; pitch text only, not a Qloo signal |
| Previous work | Pitch text; the only placement claims the claim guard allows |
| Career goal | Which production types to search first (e.g. ads puts brands first) |

The agent turns the answers into Qloo artist IDs and tag IDs. Any suggestion that doesn't resolve
to an exact Qloo match is dropped. The artist sees the stand-in ("we'll match you as a mix of A, B
and C, plus these tags") and can edit it before the run.

**Same person, several entries.** One human can have an artist, a person and an author entry
(Prateek Kuhad has artist + person; Vishal Bhardwaj has all three). Whichever route found them,
look their MBID up in Qloo: it returns every entry for that person. Show one card. The artist entry
is the main signal; the others count as theirs for the grounding guard.

**No Spotify link.** Search by name with an exact-name match (singers, bands, composers:
`urn:entity:artist`; lyricists: `urn:entity:person`, then `urn:entity:author`), narrow by the genre
and country they gave, and show up to three cards plus "None of these is me", which goes to Route
3. Names collide: "Divine" matched a different artist than the Mumbai rapper, which is why the
Spotify link comes first.

Whichever route succeeds, show an "Is this you?" card (name, image, short description, listener
count), and on confirm save the user-to-entity link so they are never asked again. The trace panel
shows which route was used.

*Acceptance:*
- A Spotify link Qloo knows resolves in Route 1 with no other questions
- A lyricist whose Qloo entry has no Spotify ID resolves in Route 2 through their MBID
- Entries sharing an MBID show as one card, with the artist entry as the signal
- A name search never accepts a fuzzy near-match ("Aditi Ramesh" → "Ramesh")
- An unknown artist with at least one resolvable sounds-like artist gets a fan profile; with none,
  `insufficient_data`
- Every artist the agent suggests in Route 3 is a real Qloo entity, and the user saw and confirmed
  the stand-in
- Output from a Route 3 run says matches are based on artists the user resembles
- A confirmed choice is reused on the next visit without asking again

### FR-2 Fan profile (US-1)

Build a profile from Qloo: taste tags (Insights with tag results), age and gender lean (demographic
signals), and audience groups (Audiences).

*Acceptance:* profile shows at least five tags, an age and gender lean, and at least one audience,
each traced to a Qloo call.

### FR-3 Production matching (US-2)

Run Insights for TV shows, movies, video games, podcasts and brands **in parallel**, with
`feature.explainability=true`, once per popularity section (big screen, prime time, indie gems;
[DESIGN.md](DESIGN.md) §6).

*Acceptance:* the calls start together, not one after another (visible in the trace); each result
carries Qloo's explanation; every section that Qloo has data for shows its own matches.

### FR-4 Fit check (US-2)

For each production type, run the same Insights call for a comparison group of similar artists,
and score every production by **lift**: how much more this artist's fans like it than the group's
fans do ([DESIGN.md](DESIGN.md) §6). Add the demographic match between fans and viewers.

*Acceptance:* every ranked production has a lift value, or is marked `insufficient_data`. Trend is
not shown: Qloo's hackathon trending data stopped changing around Dec 2025 (Q-9).

### FR-5 Fit score (US-2, US-4)

A deterministic function turns Qloo's numbers into one fit score per match. Defined in
[DESIGN.md](DESIGN.md) §6.

*Acceptance:* same inputs always give the same score; the model never writes a score; unit tests
cover the edge cases.

### FR-6 Grounding guard (US-2, US-3, US-4)

Every name in the output must resolve to a Qloo ID returned earlier in the run.

*Acceptance:* a planted made-up name in model output is removed and logged; the published eval
reports the made-up-name rate.

### FR-7 Pitch kit and shortlist (US-3, US-4)

The writer produces a pitch email per production (artist mode) or a shortlist brief (supervisor
mode) from checked, scored data only.

*Acceptance:* output never claims a past placement unless our data shows one; output never contains
a send action.

### FR-8 Supervisor mode (US-4)

Same pipeline, reversed: resolve the production, profile its audience, run Insights for artists
with a popularity cap so results are emerging artists.

*Acceptance:* no artist above the popularity cap appears; results reuse the same scorer and guard.

### FR-9 Trace and eval (US-5, US-6)

Stream each step and each Qloo call to the web app. Publish an eval page from the eval runner's
results.

*Acceptance:* the trace shows endpoint, key parameters, time and cache hit for every call; the eval
page shows all three systems on the same test set.

## 8. Data model

Defined in [DESIGN.md](DESIGN.md) §7 (the agreed contract). Stored: runs, matches, fit scores,
pitch kits, briefs, eval results. **Not stored in the repo or public tables:** raw Qloo responses.

## 9. Architecture

See [DESIGN.md](DESIGN.md) §1–2. In one line: the LLM plans and writes, Qloo supplies the facts,
plain code checks and scores, and every Qloo call goes through one client with a cache, a rate
limiter and retries.

## 10. Non-functional requirements

| ID | Requirement |
|---|---|
| NF-1 | First results on screen in under 5 seconds; full run in under 60 seconds |
| NF-2 | A cached demo run finishes in under 5 seconds |
| NF-3 | The app survives a burst of judges: stateless API, autoscaling |
| NF-4 | Qloo rate limits are never exceeded; errors retry with backoff |
| NF-5 | `DEMO_MODE` runs with zero external calls |
| NF-6 | Live and free to use until 16 Nov 2026 |

## 11. Trust and safety

- No made-up names (FR-6)
- No claimed placements that didn't happen (FR-7)
- No automatic sending (FR-7)
- Inputs are data, never instructions; prompt injection in an artist name or brief can't change the
  agent's tools or rules
- Popularity cap in supervisor mode keeps the product honest about "emerging"

## 12. Legal and data constraints

- Qloo responses stay in our private cache; never in the public repo
- Public artists and shows appear only as Qloo returns them; we don't imply endorsement
- Open-source license (MIT) visible in the repo's About section, as the rules require

## 13. Success criteria

| Measure | Target |
|---|---|
| Hit rate in top 10, Cue vs LLM alone | Cue clearly higher |
| Made-up names in Cue output | 0% |
| Share of emerging artists in supervisor mode | 100% under the popularity cap |
| Full run time | Under 60 s, cached under 5 s |
| Live demo uptime through judging | No outages |

## 14. Milestones

See the day plan in [BUILD_PROMPTS.md](BUILD_PROMPTS.md). Key dates: Qloo client by 23 Oct, artist
mode end to end by 25 Oct, supervisor mode and eval by 28 Oct, submitted by 30 Oct 6 PM ET.

## 15. Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| Q-4 | Where do we get ~300 known placements, and are we allowed to use that source? | Swara | WU-11 |
| Q-8 | Onboarding needs lookups by external ID. Add `find_by_spotify(spotify_id)` and `find_by_musicbrainz(mbid)`, both `-> list[EntityRef]`, to the contract (§7.1)? | all three | WU-01, FR-1 |

### Answered — 24 Oct 2026, from live API calls

**Q-7 — the fit score: lift inside three popularity sections.** Productions are split by their own
popularity into big screen (≥ 0.90), prime time (0.70–0.90) and indie gems (< 0.70), each its own
Insights call. Inside a section they rank by `0.70 × lift_rank + 0.30 × audience`, where lift is
how much more this artist's fans like the production than fans of four similar artists do. For
Prateek Kuhad this drops *Panchayat* and *Kota Factory* (everyone's shows) and lifts
*Masaba Masaba*, *Decoupled* and *Ray*. One combined call for the comparison group gives nearly the
same order as four separate calls. Compare overlap and reverse affinity are dropped: the first is
empty between an artist and a show, the second barely varies. Full rule in
[DESIGN.md](DESIGN.md) §6.

**Q-9 — artist trending: it exists, but it is frozen.** Artist series come back only when the window
is longer than about 13 weeks, which is why it looked empty. But for every entity checked, the
weekly rank and percentile have not changed since about Dec 2025 (*Panchayat* last moved on
19 Dec 2025; Prateek Kuhad never moved). So trend can't say what is rising, and Cue doesn't use or
show it. The `trending` tool still works if Qloo's data starts moving.

### Answered — 22 Oct 2026, agreed by the team

**Q-6 — trending signature: changed.** `trending(entity_id, entity_type)` returns that entity's
latest 12 weeks as a `TrendSeries` with an `as_of` date ([DESIGN.md](DESIGN.md) §7). Because the
data ends about 30 Jul 2026, trend is always labelled "as of July 2026".

**Q-5 — "emerging" cap: 0.80 confirmed** as the starting value, still tuned on the dev split only.

### Answered — 21 Oct 2026, from live API calls

**Q-1 — LLM provider: Anthropic Claude.** Planner: Claude Haiku 5.5 (`claude-haiku-5-5`), effort
`low`. Writer: Claude Opus 5.5 (`claude-opus-5-5`). The eval's LLM-alone and LLM-with-web-search
baselines use Claude Opus 5.5 too, so the comparison is fair. These models reject `temperature`,
so determinism comes from structured outputs, code-only scoring and caching by `PROMPT_VERSION`.
Forced `tool_choice` is also rejected; use structured outputs for the planner's call list.

**Q-2 — data for emerging artists: yes, for most.** Indian indie artists resolve, including very
small ones (Dhruv Visvanath, popularity 0.06), and still return specific, sensible TV matches.
Prateek Kuhad's top TV match is *Bandish Bandits*, a series about musicians. Some artists are
missing (Aditi Ramesh, Ramya Pothuri); for those, search returns a wrong near-match, which
`find_entity` must reject. Demo picks still to be chosen from artists that resolve.

**Q-3 — paths and parameters: settled.** All paths are in [DESIGN.md](DESIGN.md) §3. Compare is
`/v2/analysis/compare`; Trending is `/v2/trending` and needs a signal entity and a date window.

**Q-5 — "emerging" cap: start at 0.80, tune on the dev split.** Observed popularity: small indie
artists 0.06–0.70, Prateek Kuhad 0.86, international stars 0.97 and above.

## 16. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| API key arrives late | Can't build against real data | Request today; build the client against recorded shapes |
| Thin Qloo data for small artists | Weak matches | Sounds-like fallback (FR-1) |
| Rate limits during eval | Eval can't finish | Cache everything; ask in Discord for a higher limit |
| Looks like a generic recommender | Low idea score | Lead with sync licensing and the eval results |
| Running out of time | Missing pieces | Cut order in [BUILD_PROMPTS.md](BUILD_PROMPTS.md) |

## 17. After the hackathon

Agency dashboard for many artists, pairing with likeness protection (Consentinel) as a talent-agency
bundle, and a paid Qloo plan.
