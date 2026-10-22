# Cue

**Cue matches emerging musicians with the TV shows, films, games and ads whose audiences already
love their sound.**

Built for the [Qloo Agentic Hackathon](https://qloo.devpost.com/).

## The problem, in plain words

Getting a song placed in a TV show, film, game or ad ("sync licensing") is one of the few big
income sources an independent musician can reach without a record label. But artists don't know
which productions suit them, so they mass-email music supervisors and get ignored. Supervisors,
short on time, keep picking from the same few labels, so new artists rarely get heard.

Sync marketplaces let you search by genre and mood. None of them answer the question that matters:
*does this show's audience already love music like this?*

## Who uses it

- **Artists:** enter your name, get a ranked list of productions to pitch, with a reason for each
  and a pitch email you can edit and send yourself.
- **Music supervisors:** enter your show, film, game or brand, get a shortlist of emerging artists
  whose fans match your audience.

## How it works

1. **Find** the artist (or show) in Qloo.
2. **Profile** the fans: their tastes, age and gender lean, and audience groups.
3. **Match** across TV, films, games, podcasts and brands at once, with Qloo's explanation for
   each match.
4. **Check** each top match with Qloo's compare and trending data.
5. **Score** every match in plain code, drop anything that isn't a real Qloo entity, then **write**
   the pitch kit or shortlist.

You can watch every step, and every Qloo call, in the trace panel.

## How Cue uses Qloo

| Qloo endpoint | What Cue does with it |
|---|---|
| Search | Finds artists and productions; checks every name we show is real |
| Entities by ID | Pulls details for each result |
| Tags, Tag types | Turns genres and styles into taste signals |
| Audiences, Audience types | Describes who the fans are |
| Insights | Builds taste profiles and finds matches across TV, film, games, podcasts and brands |
| Compare | Scores how well an artist and a production fit |
| Trending | Favours productions and artists that were rising (Qloo's data runs to July 2026) |

## What we do not claim

- Cue doesn't listen to songs. It matches on audience taste, not sound.
- Cue doesn't predict income or guarantee a placement.
- Cue never sends anything. Every pitch is a draft you send yourself.
- Results only include artists and productions Qloo knows about.

## Results

The eval page compares Cue with an AI model alone and an AI model with web search, on a test set
of real past placements. Results will be published here before submission.

## Documentation

| Doc | What's in it |
|---|---|
| [PRD.md](PRD.md) | Problem, users, requirements |
| [DESIGN.md](DESIGN.md) | Architecture, Qloo usage, guardrails, caching, scoring, eval |
| [COMPETITION.md](COMPETITION.md) | Hackathon rules and submission checklist |
| [CLAUDE.md](CLAUDE.md) | Rules for everyone (and every AI session) working on the code |

## Setup

Coming with the first code. You'll need a Qloo hackathon API key
([request one here](https://docs.qloo.com/reference/qloo-llm-hackathon-developer-guide)) and an LLM
API key. Copy `.env.example` to `.env` and fill it in.

## Team

Prachit · Vedant · Swara

## License

[MIT](LICENSE)
