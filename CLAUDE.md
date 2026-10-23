# Cue — read this first

This file is the hub. Three people build this in parallel with separate Claude Code sessions that
cannot see each other, so everything we need to stay consistent lives here or is linked from here.

## What we're building

> **Cue matches emerging musicians with the TV shows, films, games and ads whose audiences already
> love their sound.**

One engine, two directions:

- **Artist mode:** an artist goes in, a ranked list of productions and a pitch kit come out.
- **Supervisor mode:** a show, film, game or brand goes in, a ranked shortlist of under-the-radar
  artists comes out.

Both modes share one harness, one set of Qloo tools and one scoring function. Qloo is the engine:
if a feature would work the same without Qloo, we are building the wrong thing.

Qloo Agentic Hackathon ("Agents, but with taste"). Deadline **30 Oct 2026, 11:45 PM ET**. We submit
by **30 Oct, 6:00 PM ET**.

Stack: Python 3.11+ · FastAPI · async `httpx` · Qloo API · Claude Haiku 5.5 (planner) and
Claude Opus 5.5 (writer), via the `anthropic` SDK · Redis (Upstash) behind `Cache` · Supabase
Postgres · Next.js on Vercel · Cloud Run.

## Canonical external references — check these, don't trust our summaries

Our docs summarise these pages, and **the organisers can change them at any time**. For anything
about rules, eligibility, submission or what the API supports, read the live page.

| Source | URL | Ours that summarises it |
|---|---|---|
| **Rules** | https://qloo.devpost.com/rules | [COMPETITION.md](COMPETITION.md) |
| Overview | https://qloo.devpost.com/ | [COMPETITION.md](COMPETITION.md) |
| **Hackathon developer guide** | https://docs.qloo.com/reference/qloo-llm-hackathon-developer-guide | [DESIGN.md](DESIGN.md) §3 |
| Parameter reference | https://docs.qloo.com/reference/parameters | [DESIGN.md](DESIGN.md) §3 |
| Qloo Discord, `#api-help` | linked from the developer guide | — |

If a live page contradicts one of our docs, **the live page wins**. Fix our doc and log it in
[VERSION.md](VERSION.md).

Some endpoint paths in [DESIGN.md](DESIGN.md) were written from the docs' page titles, not tested.
Verify each against the live reference before building on it.

---

## Document map

Seven docs, deliberately. If you want an eighth, extend one of these instead.

| Doc | What's in it | Read it when |
|---|---|---|
| [BUILD_PROMPTS.md](BUILD_PROMPTS.md) | A ready-to-paste prompt per work unit, the day plan and the cut order | **Start here every session** |
| [VERSION.md](VERSION.md) | Change log for the docs and the agreed contract | **Second thing you read** — what moved, and any *Action required* |
| [PRD.md](PRD.md) | Problem, users, requirements FR-1…FR-9 with acceptance criteria, non-goals, risks | Before building a feature — find its requirement |
| [DESIGN.md](DESIGN.md) | Architecture diagrams, the Qloo client, harness, guardrails, caching, scoring, eval, the agreed contract | Before writing a tool, a model call, or anything touching Qloo |
| [COMPETITION.md](COMPETITION.md) | Rules, judging criteria, submission checklist | Before adding a dependency or preparing the submission |
| [README.md](README.md) | Public pitch, how it works, setup | When editing anything a judge will read |

---

## Hard rules — do not break

These carry the product's core claims. Reasons are in [DESIGN.md](DESIGN.md).

1. **Qloo data never goes in the repo.** No raw Qloo responses in commits, fixtures, eval sets or
   logs we publish. Qloo's terms allow private server-side caching only. Eval sets store our inputs,
   the known answers and our scores.
2. **The model never decides a score.** Fit scores come from plain code over Qloo's numbers. The
   model explains scores; it never invents or changes them.
3. **Every name we show is a real Qloo entity.** The grounding guard drops any show, film, game,
   brand or artist that doesn't resolve to a Qloo ID. Zero made-up names is a claim we publish.
4. **Every Qloo request passes the param checker.** Qloo silently ignores parameters that don't fit
   the `filter.type`, which returns empty or wrong results with no error. We reject those requests
   before sending them.
5. **Every Qloo request goes through the Qloo client.** Cache, rate limiter and retries live there.
   No direct `httpx` calls to Qloo anywhere else.
6. **No outward action is automatic.** Pitch kits and briefs are drafts. Cue never sends email.
7. **Never claim a placement that didn't happen.** Pitch text may not say a song was used somewhere
   unless our data says so.
8. **Cache keys include `prompt_version`** for model calls and the full normalised parameter set for
   Qloo calls.
9. **Fail toward "not enough data", never toward a confident match.** An error or an empty Qloo
   answer shows as `insufficient_data`, never as a low or high score.
10. **Every Qloo call is traced.** Endpoint, parameters, time taken, cache hit or miss. The trace
    panel is how judges see how deeply we use Qloo.
11. **The repo is public. Never commit a key.** If one lands in history, rotate it.
12. **No AI attribution in commits.** No `Co-Authored-By` lines for AI tools.

---

## Branching and pull requests

**One branch and one PR per epic**, not per work unit.

```
epic/0-qloo-client      WU-00, WU-01
epic/1-harness          WU-02, WU-03, WU-04, WU-05, WU-06
epic/2-modes            WU-07, WU-08
epic/3-web              WU-09, WU-10
epic/4-eval             WU-11, WU-12
epic/5-ship             WU-13, WU-14
epic/6-extras           WU-15
```

- Branch from up-to-date `main`. `git pull` first, every time
- Commit per work unit
- **Push early.** An open PR is how the others see a file is being worked on
- Tests pass before you push: `python -m pytest tests/ -q`
- Squash-merge to `main`, then delete the branch
- Don't merge your own PR if a teammate is awake to review it

A PR body says which work units it closes, the test count, and what the reviewer should push back
on. Not a restatement of the diff.

**Contract changes never travel in an epic PR.** See below.

## Versioning

Changing a **governed file** (any top-level `.md`, or anything in the contract below) needs a
[VERSION.md](VERSION.md) entry in the same commit. Write it for whoever reads it next: "renamed
`fit.score` to `fit.value`, update the scorer and the web table" helps; "renamed a field" doesn't.

MAJOR = contract change · MINOR = new requirement or scope · PATCH = clarification.

## The agreed contract

Defined in [DESIGN.md](DESIGN.md) §7: the Qloo tool signatures, the `Match` and `FitScore` shapes,
the run event format the web app streams, and the eval record format. **Do not change a field or a
signature alone.** The other half of the build is coded against it. Say so in chat, agree, then
change it in its own small PR with a MAJOR bump.

---

## File ownership

Stay in your lane to avoid merge conflicts. Swapping is fine; edit this section if you do.

**Prachit — foundation and app**
- `cue/qloo/` (client, cache, rate limiter, retry, param checker)
- `cue/api/` (FastAPI app, run streaming)
- `cue/store/` (Supabase)
- `web/` (Next.js app, trace panel, eval page)
- Cloud Run and Vercel deployment

**Vedant — agents and tools**
- `cue/tools/` (one module per Qloo tool)
- `cue/agents/` (planner, writer)
- `cue/scoring/` (fit score)
- `cue/guards/` (grounding guard, pitch-claim guard)

**Swara — PM, LLM eval, docs and demo**
- [BUILD_PROMPTS.md](BUILD_PROMPTS.md) and the **Status** section of this file
- **LLM eval, end to end:** `evalsets/` (the known placements), `cue/eval/` runner and scorers,
  the GitHub Actions smoke eval, and the eval results the eval page shows
- Demo script, Devpost write-up, screenshots, submission checklist

**Shared — pull first, edit with care:** `README.md`, `CLAUDE.md`, `requirements.txt`, the docs.

## Code layout

```
cue/qloo/client.py          the only place that talks to Qloo
cue/qloo/params.py          which parameters each filter.type accepts
cue/tools/<tool>.py         one Qloo tool each, typed inputs and outputs
cue/agents/common/llm.py    the only place we call a model
cue/agents/<agent>/
    agent.py                the steps
    guardrail.py            what can reject an answer
    instructions.py         the prompt, the output schema, PROMPT_VERSION
cue/scoring/fit.py          the fit score, plain code
cue/guards/grounding.py     every name resolves to a Qloo ID
```

Bump `PROMPT_VERSION` whenever a prompt's words change, or the cache serves answers from a prompt
you deleted.

## Conventions

- Type hints everywhere; dataclasses or Pydantic models for records
- No code comments; explanations go in docs, PR bodies or chat
- No sampling parameters: Claude Opus 5.5 and Haiku 5.5 reject `temperature`. Determinism comes
  from structured outputs, code-only scoring and caching by `PROMPT_VERSION`
- Structured output for every model call
- Plan all Qloo calls up front, then run independent ones in parallel
- Every Insights call sets `feature.explainability=true`
- Secrets from `.env` locally, Secret Manager in deploy

---

## Session start ritual

1. `git pull`
2. Read the newest entries in [VERSION.md](VERSION.md)
3. Pick your next work unit from [BUILD_PROMPTS.md](BUILD_PROMPTS.md); check **Status** below
4. Check **Open questions** in [PRD.md](PRD.md) §15
5. Find the requirement in [PRD.md](PRD.md) and read its acceptance criterion
6. Build, commit small, push. Governed file? Add a VERSION.md entry in the same commit
7. **Update Status before you finish**

**WU-00, the Qloo client, blocks every other work unit.** Whoever starts first builds it.

## Demo safety

`DEMO_MODE=true` runs the full pipeline from the private cache with zero external calls, so the
demo can't die on a rate limit. Demo examples use real public artists and shows (that's what Qloo
knows), but we never claim a real artist endorsed Cue or that a placement happened when it didn't.

---

## Status

- [ ] Qloo API keys requested for all three of us
- [ ] Data check: the artists and shows we plan to demo return useful Insights results
- [ ] WU-00 Qloo client
- [ ] Everything else: see [BUILD_PROMPTS.md](BUILD_PROMPTS.md)
