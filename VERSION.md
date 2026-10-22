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
