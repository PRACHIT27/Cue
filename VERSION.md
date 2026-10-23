# Version log

Change log for the docs and the agreed contract. Newest first.

**Governed files:** every top-level `.md`, and the contract in [DESIGN.md](DESIGN.md) §7.
Changing one needs an entry here in the same commit.

**Scheme:** MAJOR = contract change · MINOR = new requirement or scope · PATCH = clarification.

**Entry format**

```
## vX.Y.Z — DD Mon YYYY — who
What changed, written for the next person to read it.
Action required: what someone must do because of this (or "none").
```

---

## v1.4.2 — 24 Oct 2026 — Vedant

WU-08 supervisor mode (`cue/agents/supervisor_run.py`) and a sturdier writer.
- `run_supervisor(production_id, production_name, production_type, events, brief=)`: artists
  liked by the production's audience, capped at popularity 0.80 (PRD Q-5). If fewer than 8 come
  back, the cap widens to 0.85 and a `step="widen"` event says so. Lift compares with 4 similar
  productions' audiences, asked about exactly our candidates (`filter.results.entities`), so every
  artist gets a real comparison instead of a guessed baseline. Each shortlisted artist gets a
  Spotify link in `FitScore.inputs["spotify_url"]`. The writer returns a `Brief`.
- Live check, *Bandish Bandits*: 30 candidates, all ≤ 0.80, 8 on the shortlist, about 26 s,
  $0.002 of Claude on Haiku.
- **Writer failures no longer crash a run:** the run returns its scored matches with no text, and a
  `guard_drop` saying why. Writer `max_tokens` is 8000, because Haiku's thinking shares the budget.
- **Known problem: "emerging" isn't "new".** The 0.80 cap returns veteran and late classical
  artists (Bhimsen Joshi, Mehdi Hassan), and Qloo carries no birth, death or debut dates for
  artists. Needs a decision; see the PR.

Action required:
- Prachit: `run_supervisor(...)` is the entry point for `POST /runs` in supervisor mode; show
  `spotify_url` as a Listen link.
- All: decide how supervisor mode handles veteran artists before the demo.

## v1.4.1 — 24 Oct 2026 — Vedant

WU-06 writer and the artist run end to end (`cue/agents/artist_run.py`).
- One live run for Prateek Kuhad with the brief "acoustic songs for a monsoon romance scene":
  109 matches scored, 9 pitches (3 per section), about 28 s, $0.0017 of Claude on Haiku.
- **Content filter** (`cue/guards/content.py`): drops candidates whose titles contain explicit
  words, before scoring. It only checks titles; a tag-based check would be stronger.
- **Fixes from the live runs:** Insights rows carry the real type in `subtype` (`type` is just
  `urn:entity`), which broke type labels and the per-type limit. Comparison-group calls now set no
  popularity cap, because the default games cap hid mega-games from the group and inflated their
  lift. The planner now leaves out production types a brief rules out (no shooting games for a
  monsoon romance).
- DESIGN.md §4: the writer's aliases, schema and style rules.

Action required:
- Prachit: `run_artist(signal_ids, artist_name, events, brief=, basis=)` is the entry point for
  `POST /runs` in artist mode. Pass `RunEvents(run_id, sink)` and the client's `sink=events.qloo_sink`
  so every event lands in one stream.

## v1.4.0 — 24 Oct 2026 — Vedant

MINOR: WU-02 planner, WU-03 executor and WU-05 guards; the planner design changed.
- **DESIGN.md §4:** the planner outputs decisions (production types, sections, brief tags, lift
  on or off, a note), not raw calls; code builds the calls. It gets a second round after seeing a
  summary of the first. All model calls go through `cue/agents/common/llm.py`, which caches by
  `PROMPT_VERSION` and refuses calls that could pass `LLM_BUDGET_USD`.
- **New setting:** `LLM_BUDGET_USD` in `.env` (and Secret Manager). With it unset, no paid call is made.
- `anthropic>=2.1,<3` added to `requirements.txt`.
- Executor timeout is 20 s per call: with ~25 calls a run, time queued behind the rate limiter was
  hitting 10 s.
- Fixed: the default games cap (0.90) no longer clashes with the big-screen section's 0.90 floor.

Action required:
- Prachit: set `LLM_BUDGET_USD` with the deploy key. Run events now include planner steps
  (`step="planner"`, with `note`) for the trace panel.
- All: Qloo returns adult titles (one podcast in a live run). A content filter is needed before the
  writer can pitch anything; Vedant adds it with WU-06.

## v1.3.0 — 24 Oct 2026 — Vedant

MINOR: PRD Q-7 and Q-9 settled from live calls; the fit score is redefined.
- **DESIGN.md §6:** productions split into three popularity sections (big screen ≥ 0.90, prime
  time 0.70–0.90, indie gems < 0.70), each its own Insights call. Inside a section they rank by
  `match = 0.70 × lift_rank + 0.30 × audience`. **Lift** = how much more this artist's fans like a
  production than a comparison group of 4 similar artists' fans do, from one extra Insights call
  per production type. Compare overlap, reverse affinity and trend are dropped from the score.
- **No contract change:** `lift`, `lift_rank`, `audience` and `section` go in `FitScore.inputs`;
  `Match.overlap` and `Match.trend` stay `None`.
- **PRD Q-9:** artist trending needs a window longer than about 13 weeks (the tool now fetches 16),
  but Qloo's trending data stopped changing around Dec 2025 for every entity checked. Cue doesn't
  use or show trend. PRD FR-3 and FR-4 updated to match.

Action required:
- Prachit: group result cards by `FitScore.inputs["section"]`, and drop the "as of July 2026" trend
  label from `web/`, since no trend is shown.
- Swara: the demo script and write-up should explain lift ("your fans over-index on X compared with
  fans of similar artists") and say plainly that trend isn't shown because Qloo's data is static.

## v1.2.2 — 23 Oct 2026 — Vedant

WU-01: the nine Qloo tools in `cue/tools/`, with the §7.1 signatures, all through the WU-00 client.
Every tool ran live once (15 calls, 0 errors); tests use fake values only.
- **Reaching the client:** wrap a run in `with use_client(client, run_id=...)`. Tools pick the
  client up from a context variable, so the §7.1 signatures stay as agreed.
- **`find_entity`:** keeps only exact matches after `normalise_name` (case, accents, punctuation,
  `&`→`and`, leading "the"), checking akas too. For artists it never searches `urn:entity:person`.
  Results sharing a Spotify or MusicBrainz ID merge into one. `[]` means not found.
- **`insights`:** always sends `feature.explainability=true`. Each item carries `rank` (affinity is
  flat, so rank carries more information), Qloo's per-input explanation shares, and
  `duplicate_ids` when the same title came back more than once. Games default to
  `filter.popularity.max=0.90`. `InsightsRequest.popularity_min/max` give the three popularity
  bands. `filter.type` `urn:demographics`, `urn:heatmap` and `urn:tag` fill
  `InsightsResult.demographics`, `.heatmap` and `.tags` instead of `.items`.
- **`compare`:** returns shared tags plus each side's own tags (`a_tags`, `b_tags`), so WU-04 can
  still work with them when `shared` is empty for artist vs show.
- **`trending`:** fetches 16 weeks up to 31 Jul 2026 (`DATA_ENDS` in `cue/tools/trending.py`) and
  keeps the latest 12. A window shorter than about 13 weeks returns nothing for artists, which is
  why artist trending looked empty (PRD Q-9). **But the data is frozen:** every week since about
  Dec 2025 repeats the same rank and percentile, for artists and shows alike, so `trend_score` is
  0.5 for everything. See PRD Q-9.
  **Which field feeds `trend`:** `trend_score(series)` uses `population_percentile`, the change from
  the first to the last week, mapped so no change is 0.5 and a swing of ±0.10 or more is 1 or 0.
  It returns `None`, not 0, when there are fewer than two weeks; WU-04 decides how to treat that.
- `python -m cue.tools.smoke "Artist name"` runs every tool once live and prints a summary. Nothing
  it receives is saved.

Action required:
- Prachit: `InsightsResult` and the other tool-only records are in `cue/tools/records.py`; the
  §7.2 records the website uses (`Match`, `FitScore`, …) come with WU-04.
- Vedant: settle Q-7 and Q-9 before WU-04. Per v1.2.0, fan profiles use the artist entry's own
  tags (`get_entities(...)[0].tags`), not raw `urn:tag` results; the harness builds profiles that
  way in WU-02/WU-03.

## v1.2.1 — 22 Oct 2026 — Prachit

PATCH: heatmap corrected from a live retry. It needs an area (`filter.location.query`), and only
the default geohash boundary returns data; `urn:entity:locality` gave nothing. It maps
neighbourhoods within one city, not cities. DESIGN.md §2 Extra row, §3 and the WU-15 prompt
updated. Pushed straight to `main`.
Action required: Prachit, the `params.py` boundary check should allow `urn:geohash` only for now,
and require `filter.location` or `filter.location.query` for `urn:heatmap`.

## v1.2.0 — 22 Oct 2026 — Prachit

MINOR: onboarding becomes three routes, plus more live findings. Pushed straight to `main` at
Prachit's call, without a PR.
- PRD FR-1: we ask for the Spotify link and the artist's role, then try **Route 1** (Qloo by
  Spotify ID), **Route 2** (Spotify link → MusicBrainz MBID → Qloo by MBID, for lyricists stored
  only as person entries), **Route 3** (taste stand-in). Entries sharing an MBID merge into one
  card with the artist entry as the signal. Name search without a Spotify link searches by role.
  Flow in DESIGN.md §2.1, including the MusicBrainz helper (`cue/identity/musicbrainz.py`).
- DESIGN.md §3 findings: MBID lookup returns every entry for one person; lyricists are usually
  person-only; names collide ("Divine"); shows carry no music credits; artist-vs-artist Compare
  doesn't separate shows; the same popular shows top every Indian artist's list; reverse affinity
  works; fan taste tags from `urn:tag` are noisy; artist trending came back empty; heatmap
  boundary must be `urn:geohash` or `urn:entity:locality`, not `city`; explainability with one
  input is trivial.
- DESIGN.md §6: Q-7 options, led by lift over a comparison group of similar artists.
- PRD: Q-7 updated, Q-8 now covers `find_by_spotify` and `find_by_musicbrainz`, new Q-9 (artist
  trending). BUILD_PROMPTS WU-15 uses `urn:entity:locality`.

Action required:
- Vedant: settle Q-7 and Q-9 before WU-04. WU-01 fan profiles use the artist entry's own tags,
  not raw `urn:tag` results.
- All three: agree on Q-8 (now two lookup tools).
- Prachit: build `cue/identity/musicbrainz.py`, and add a check in `cue/qloo/params.py` that
  `output.heatmap.boundary` is `urn:geohash` or `urn:entity:locality`.

## v1.1.0 — 22 Oct 2026 — Prachit

MINOR: new onboarding requirement and live findings.
- PRD FR-1 is now **Artist onboarding** with three paths: Spotify ID first, then a name search
  limited to `urn:entity:artist`, then a taste stand-in (sounds-like artists, genre tags, song
  artists) for artists Qloo doesn't know. Duplicates are merged when they share a Spotify or
  MusicBrainz ID; otherwise the artist picks. Flow in DESIGN.md §2.1. US-1 updated.
- DESIGN.md §3: artists also exist as `urn:entity:person` entries, and signalling with those gives
  different results and empty demographics, so always search with `types=urn:entity:artist`.
  Spotify lookup via `/entities?external.spotify.ids=` is exact. Compare's shared-tag list is
  empty for artist vs TV show. Affinity is nearly flat across top results.
- New open questions: Q-7 (the fit formula's overlap and affinity inputs are weak), Q-8 (add
  `find_by_spotify` to the contract).

Action required:
- Vedant: settle Q-7 before WU-04. In WU-01, `find_entity` for artists always passes
  `types=urn:entity:artist`.
- All three: agree on Q-8. If yes, it goes in its own contract PR with a MAJOR bump.
- Swara: demo picks should be checked with the artist entry, not the person entry.

## v1.0.1 — 22 Oct 2026 — Prachit

Swara now owns the LLM eval end to end: `evalsets/`, `cue/eval/` runner and scorers, the CI smoke
eval and the eval results (CLAUDE.md file ownership, BUILD_PROMPTS.md WU-12). Vedant's part is
hooking Cue in as system C. The day plan's weekdays were off by one; 22 Oct is a Thursday and the
deadline, 30 Oct, is a **Friday**.
Action required: Swara, pick up WU-12. Vedant, drop `cue/eval/` from your list.

## v1.0.0 — 22 Oct 2026 — Prachit

MAJOR: contract change agreed by all three (PRD Q-6), plus Q-5 confirmed.
- DESIGN.md §7.1: `trending(entity_type, take) -> list[TrendingItem]` is now
  `trending(entity_id, entity_type) -> TrendSeries`, returning that entity's latest 12 weeks.
- DESIGN.md §7.2: new `TrendSeries` (entity_id, as_of, weeks) and `TrendWeek` (week_start,
  percentile, rank, rank_velocity, velocity_fold_change). `Match` gains `trend_as_of`.
- DESIGN.md §6: `trend` comes from the candidate's latest week, scaled to 0–1 (0 if no data).
- Trend is labelled "as of July 2026" everywhere it's shown (PRD FR-4, DESIGN §6, WU-09, README),
  because Qloo's hackathon data ends about 30 Jul 2026.
- Emerging cap stays at 0.80, tuned on the dev split only.

Action required:
- Vedant: build `trending` in WU-01 to the new signature, and log in VERSION.md which weekly field
  and scaling feed `trend`.
- Prachit: show the "as of July 2026" label wherever trend appears in `web/`.

## v0.2.0 — 22 Oct 2026 — Vedant

Checked every Qloo endpoint against the live API and settled PRD Q-1, Q-2, Q-3 and Q-5.
- DESIGN.md §3 now has the real path for every endpoint and a "What the live API actually
  returns" section. Build WU-00 and WU-01 against it.
- Games are `urn:entity:videogame`; `video_game` returns a 400.
- `filter.latest_known_year.min` (TV) and `filter.popularity.max` both work and are needed.
- LLM provider is Claude: Haiku 5.5 plans, Opus 5.5 writes. Neither accepts `temperature`, so the
  "temperature 0" convention in CLAUDE.md and DESIGN.md §4 is replaced.
- New open question Q-6: `/v2/trending` needs a signal entity and returns a weekly series for that
  one entity, and the hackathon data ends around 30 Jul 2026. The `trending(entity_type, take)`
  signature in §7.1 can't work as written. Proposed: `trending(entity_id, entity_type)` returning
  that entity's latest 12 weeks. That is a contract change, so it needs all three of us to agree
  and its own PR.

Action required:
- Prachit: in `cue/qloo/params.py`, allow `filter.latest_known_year.min/max` for `tv_show`,
  `filter.release_year.min/max` for `movie`, and `filter.popularity.max` for every entity type we
  query. Use `videogame`.
- Swara: BUILD_PROMPTS.md WU-02 still says "temperature 0"; change it to "effort low". Pick demo
  artists from ones that resolve in Qloo (PRD Q-2).
- All three: agree on Q-6 before WU-04 uses `trend`.

## v0.1.0 — 21 Oct 2026 — Prachit

First doc set: CLAUDE.md, PRD.md, DESIGN.md (with the agreed contract in §7), COMPETITION.md,
BUILD_PROMPTS.md, README.md, LICENSE.
Action required: everyone request a Qloo API key today. Vedant: settle PRD Q-1 and Q-3 and fix any
wrong endpoint paths in DESIGN.md §3.
