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
| US-1 | As an artist, I enter my name (or three artists I sound like) and see who my fans are |
| US-2 | As an artist, I see a ranked list of shows, films, games, podcasts and brands that fit my fans, each with a reason |
| US-3 | As an artist, I get a pitch email per production that I can edit and send myself |
| US-4 | As a supervisor, I enter a show, film, game or brand and get a ranked shortlist of emerging artists |
| US-5 | As anyone, I watch the agent work step by step and see every Qloo call it made |
| US-6 | As a judge, I see an eval page comparing Cue with an LLM alone and an LLM with web search |

## 7. Functional requirements

### FR-1 Artist lookup (US-1)

Resolve an artist name to a Qloo entity with Search. If not found, accept up to three "sounds like"
artists and use them as the signal.

*Acceptance:* a known artist resolves to one Qloo ID; an unknown artist with three sounds-like
artists still produces a fan profile; an unknown artist with none returns `insufficient_data`.

### FR-2 Fan profile (US-1)

Build a profile from Qloo: taste tags (Insights with tag results), age and gender lean (demographic
signals), and audience groups (Audiences).

*Acceptance:* profile shows at least five tags, an age and gender lean, and at least one audience,
each traced to a Qloo call.

### FR-3 Production matching (US-2)

Run Insights for TV shows, movies, video games, podcasts and brands **in parallel**, with
`feature.explainability=true`.

*Acceptance:* the five calls start together, not one after another (visible in the trace); each
result carries Qloo's explanation.

### FR-4 Fit check (US-2)

For the top candidates, run Compare (artist vs production) and Trending (is the production rising).

*Acceptance:* every ranked production has a compare result and a trending flag, or is marked
`insufficient_data`.

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
| Q-1 | Which LLM provider for the planner and writer? | Vedant | WU-02, WU-06 |
| Q-2 | Do emerging artists we want to demo exist in Qloo with useful data? | Prachit | Demo choice |
| Q-3 | Exact paths and parameters for Compare and Trending | Vedant | WU-01 |
| Q-4 | Where do we get ~300 known placements, and are we allowed to use that source? | Swara | WU-11 |
| Q-5 | What popularity cap counts as "emerging"? | Vedant | FR-8 |

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
