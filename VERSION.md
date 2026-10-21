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
