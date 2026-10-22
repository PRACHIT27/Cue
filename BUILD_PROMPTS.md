# Build prompts

One ready-to-paste prompt per work unit. Start a fresh Claude Code session, paste the prompt for
your work unit, and let it read the linked docs itself. Swara owns this file.

Every prompt assumes the session has read [CLAUDE.md](CLAUDE.md) first.

## Day plan (dates in ET)

| Day | Prachit | Vedant | Swara |
|---|---|---|---|
| Wed 21 Oct | Request API keys · WU-00 start | Request key · read Qloo docs, settle Q-1, Q-3 | Request key · WU-11 sources (Q-4) |
| Thu 22 Oct | WU-00 | WU-01 against recorded shapes | WU-11 · WU-12 scorers against fake runs |
| Fri 23 Oct | WU-00 done · data check (Q-2) | WU-01 · WU-02 | WU-11 · WU-12 · demo script draft |
| Sat 24 Oct | WU-07 | WU-03 · WU-04 | WU-11 done (dev split) · WU-12 systems A and B |
| Sun 25 Oct | WU-09 | WU-05 · WU-06 · **artist mode end to end** | WU-12 hooks in Cue as system C · write-up draft |
| Mon 26 Oct | WU-10 · WU-13 first deploy | WU-08 | WU-12 dev-split run · test the live app, file bugs |
| Tue 27 Oct | WU-13 | Fix what the dev run finds | WU-11 test split · WU-12 smoke eval in CI |
| Wed 28 Oct | Eval page | WU-15 if time | WU-12 full run · screenshots |
| Thu 29 Oct | Polish, pre-warm cache | Fix eval findings | WU-14 write-up final |
| Fri 30 Oct | Freeze at noon · submit by 6 PM | Freeze at noon | Submission checklist · submit |

## Cut order

If we run late, cut from the bottom up. Never cut anything above the line.

1. WU-15 heatmap extra
2. Full 300-sample eval (keep the 60-sample dev set and publish that)
3. Supervisor-mode web view (keep the API)
4. Redis (keep the in-memory cache)

---- never cut ----

Qloo client with param checker · artist mode end to end · grounding guard · trace panel · live
deploy · eval page with at least the dev set · license · write-up

## Ticket index

| WU | What | Owner | Epic | PRD |
|---|---|---|---|---|
| WU-00 | Qloo client | Prachit | 0 | NF-4 |
| WU-01 | Qloo tools | Vedant | 0 | FR-1–FR-4 |
| WU-02 | Planner | Vedant | 1 | FR-3 |
| WU-03 | Executor | Vedant | 1 | FR-3 |
| WU-04 | Fit score | Vedant | 1 | FR-5 |
| WU-05 | Grounding and pitch-claim guards | Vedant | 1 | FR-6, FR-7 |
| WU-06 | Writer | Vedant | 1 | FR-7 |
| WU-07 | API and run streaming | Prachit | 2 | FR-9 |
| WU-08 | Supervisor mode | Vedant | 2 | FR-8 |
| WU-09 | Website | Prachit | 3 | US-1–US-4 |
| WU-10 | Trace panel | Prachit | 3 | FR-9 |
| WU-11 | Eval test set | Swara | 4 | US-6 |
| WU-12 | Eval runner and scorers | Swara | 4 | US-6 |
| WU-13 | Deploy | Prachit | 5 | NF-3, NF-6 |
| WU-14 | Devpost write-up and submission | Swara | 5 | — |
| WU-15 | Heatmap extra | Vedant | 6 | — |

---

# Epic 0 — Qloo client — BUILD THIS FIRST

## WU-00 · Qloo client · Prachit · blocks everything

```
Read CLAUDE.md, then DESIGN.md §3, §5 and §7. Build cue/qloo/: an async client that is the only
code allowed to talk to Qloo. It must: send X-Api-Key from settings to the hackathon base URL;
run every request through the param checker in cue/qloo/params.py (a table of which parameters
each filter.type accepts, copied from Qloo's Entity Type Parameter Guide, rejecting anything else
with a clear reason); check a Cache interface first (in-memory implementation now, keyed by
endpoint plus sorted normalised params); apply a token-bucket rate limiter; retry 429 and 5xx up
to 3 times with jittered backoff; and emit a run event (DESIGN §7.3) for every call with endpoint,
params, ms, cache hit or miss and status. DEMO_MODE=true must serve from cache only and fail loudly
on a miss. Write pytest tests with a fake transport: cache hit and miss, rejected params, retry on
429, no retry on 400, demo mode. Done when tests pass and one real Search call works with a key.
```

## WU-01 · Qloo tools · Vedant

```
Read CLAUDE.md, then DESIGN.md §3 and §7.1. Build one module per tool in cue/tools/ with the exact
signatures in DESIGN §7.1, all calling the WU-00 client. Verify every endpoint path and parameter
against the live Qloo reference and fix DESIGN.md §3 if it is wrong (VERSION.md entry). Normalise
results into the §7.2 records, including affinity, overlap and popularity as 0–1 values, and write
down in VERSION.md which response fields feed each one. Insights always sets
feature.explainability=true and keeps the explanation on each Match. Tests use recorded response
shapes with fake values, never real Qloo data. Done when each tool has a passing test and a working
live call.
```

---

# Epic 1 — Harness

## WU-02 · Planner · Vedant

```
Read CLAUDE.md, DESIGN.md §2 and §4, PRD FR-1 to FR-4. Build cue/agents/planner/ (agent.py,
guardrail.py, instructions.py with PROMPT_VERSION). Small model, temperature 0, structured output:
given the mode and input, return every Qloo tool call for the run with dependencies. The input is
data in a delimited field, never instructions. On a param-checker rejection, replan with the reason,
at most twice. Tests: artist mode plan, supervisor mode plan, a rejected param leads to a fixed
plan, an injection attempt in the artist name doesn't change the tool list.
```

## WU-03 · Executor · Vedant

```
Read CLAUDE.md and DESIGN.md §4. Build the executor: run the planner's calls as asyncio tasks in
dependency order, independent calls in parallel, 10 s timeout each, max 40 calls per run, run
events for step start and end. A failed call marks its outputs insufficient_data and the run
continues. Test that the five production Insights calls start together, and that a timeout
doesn't crash the run.
```

## WU-04 · Fit score · Vedant

```
Read CLAUDE.md, DESIGN.md §6, PRD FR-5. Build cue/scoring/fit.py as a pure function from a Match to
a FitScore using the §6 formula. Missing affinity or overlap returns status insufficient_data with
value None. Unit tests: normal case, each missing input, all zeros, all ones, same input twice gives
the same result.
```

## WU-05 · Guards · Vedant

```
Read CLAUDE.md, DESIGN.md §5, PRD FR-6 and FR-7. Build cue/guards/grounding.py: drop any named
entity in writer output that isn't a Qloo ID returned earlier in the run, emitting a guard_drop
event. Build the pitch-claim guard: drop or rewrite any sentence claiming a past placement unless
the run's data shows it. Tests include a planted made-up show name and a planted "your song was
featured in" claim.
```

## WU-06 · Writer · Vedant

```
Read CLAUDE.md, DESIGN.md §4 and §5, PRD FR-7. Build cue/agents/writer/: large model, structured
output into PitchKit (artist mode) or Brief (supervisor mode). The model gets only scored, grounded
matches and their Qloo explanations. Its schema has no score field; scores are joined in by code
afterwards. Run both guards on the output. No send capability anywhere. Test with fixed inputs that
the output parses, has no score field from the model, and passes both guards.
```

---

# Epic 2 — Modes

## WU-07 · API and run streaming · Prachit

```
Read CLAUDE.md, DESIGN.md §4 and §7.3. Build cue/api/ with FastAPI: POST /runs starts a run
(mode, input) and returns a run id; GET /runs/{id}/events streams run events over server-sent
events; GET /runs/{id} returns the final PitchKit or Brief. Store runs and results in Supabase
through a Store interface. Stateless: nothing kept in process memory between requests except the
cache. Test with the harness faked.
```

## WU-08 · Supervisor mode · Vedant

```
Read CLAUDE.md, DESIGN.md §2, PRD FR-8. Add supervisor mode: resolve the production, profile its
audience, run Insights for urn:entity:artist with filter.popularity.max set to the cap agreed in
PRD Q-5, then reuse the same compare, trending, scorer, guards and writer. Test that no returned
artist is above the cap.
```

---

# Epic 3 — Website

## WU-09 · Website · Prachit

```
Read CLAUDE.md and PRD §6. Build web/ in Next.js: a home page with the two modes, an input form per
mode (artist name plus optional three sounds-like artists; or a production), a results view with
ranked cards (name, type, fit score, Qloo's reason, pitch email with a copy button, and any trend
labelled "as of July 2026", never as current), and an about
section explaining how Qloo is used. Opens with a pre-warmed example so the first view shows real
output. Works at phone width.
```

## WU-10 · Trace panel · Prachit

```
Read CLAUDE.md and DESIGN.md §7.3. Add a trace panel beside results that fills live from the run's
event stream: each Qloo call with endpoint, key params, ms and a cache hit or miss chip; guard drops
highlighted; parallel calls shown as starting together. A count at the top: "N Qloo calls across M
endpoints."
```

---

# Epic 4 — Eval

## WU-11 · Eval test set · Swara

```
Read CLAUDE.md, DESIGN.md §7.4 and §8, PRD Q-4. Build evalsets/placements.jsonl: about 300 known
real placements (an artist whose song was used in a TV show, film, game or ad), each with a source
noting where we learned it. Use only sources whose terms allow it; record the source per row. Split
60 dev and 240 test, fixed, so nobody tunes on test. No Qloo data in this file.
```

## WU-12 · Eval runner and scorers · Swara

```
Read CLAUDE.md and DESIGN.md §8. Build cue/eval/: run systems A (LLM alone), B (LLM plus web
search) and C (Cue) on a split; score hit rate in top 10, made-up names via Qloo Search, emerging
share, consistency over 3 runs, and time and cost. Write results to eval/results.json with our
scores only. Add a GitHub Actions job that runs a 30-sample smoke eval on every push and fails if
Cue's hit rate drops more than 5 points.
```

---

# Epic 5 — Ship

## WU-13 · Deploy · Prachit

```
Read CLAUDE.md and DESIGN.md §9. Deploy the API to Cloud Run (min 1 instance during judging),
the website to Vercel, cache to Upstash Redis, secrets in Secret Manager. Add a health check.
Pre-warm the cache for the demo examples. Confirm the live app works from a fresh browser with no
login.
```

## WU-14 · Devpost write-up and submission · Swara

```
Read COMPETITION.md and the live rules page. Write the Devpost description: the problem in plain
words, who it's for, how it works, a table of every Qloo endpoint and the step it powers, the eval
results, and what we don't claim. Add screenshots of both modes and the trace panel. Run the
COMPETITION.md §3 checklist. Submit by 30 Oct, 6 PM ET.
```

---

# Epic 6 — Extras

## WU-15 · Heatmap extra · Vedant

```
Read DESIGN.md §2 (Extra row). Add an optional step: Insights heatmap with
output.heatmap.boundary=city for the artist's fans, shown as "your fans cluster in…" with local ad
and radio pitch ideas. Off by default if it slows the main run.
```
