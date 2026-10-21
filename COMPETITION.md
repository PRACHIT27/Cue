# Competition

Summary of the Qloo Agentic Hackathon rules as read on 21 Oct 2026. **The live pages win** if they
disagree with this file:

- Overview: https://qloo.devpost.com/
- Rules: https://qloo.devpost.com/rules
- API key and developer guide: https://docs.qloo.com/reference/qloo-llm-hackathon-developer-guide

## 1. Dates (Eastern Time)

| What | When |
|---|---|
| Submissions open | 30 Sep 2026, 9:00 AM |
| **Submissions close** | **30 Oct 2026, 11:45 PM** |
| Judging | 2 Nov, 12:00 PM to 16 Nov, 11:45 PM |
| Winners announced | Around 23 Nov, 3:00 PM |

## 2. What to build

A working app that integrates the Qloo API and either works as an agentic tool, is built with an
agent framework, or wires Qloo into an existing agent. Qloo must be the difference: the overview
says a project that would work the same without Qloo is the wrong thing to build.

## 3. Submission requirements

- [ ] Link to a functional demo that judges can use end to end
- [ ] Hosted and fully published externally (a website, or a hosted APK or TestFlight build). Local-only doesn't qualify
- [ ] Public repo on GitHub, GitLab or Bitbucket with all source, assets and setup instructions
- [ ] Open-source license file, detected and visible in the repo's About section
- [ ] Text description of features and what makes it Qloo-powered
- [ ] In English
- [ ] Free to use, without restriction, until judging ends (16 Nov). If login is needed, give judges credentials in the testing instructions
- [ ] Works the way the description says
- [ ] New, or significantly updated during the submission period (explain how)
- [ ] Not submitted to another hackathon (last year an entry was disqualified for this)

A demo video is not required. Judges may still judge from the description and images alone, so the
write-up and screenshots matter.

## 4. Judging

**Stage one, pass or fail:** does it fit the theme and reasonably use the required API?

**Stage two, four criteria weighted equally:**

| Criterion | What judges ask |
|---|---|
| Technological Implementation | How thoroughly and skillfully does it use Qloo? Real, non-trivial code? |
| Design | A complete, coherent product, not a proof of concept? |
| Potential Impact | A credible, specific case for a real problem and audience, actually addressed in what's shown? |
| Quality of the Idea | Creative, non-obvious use of Qloo, with real understanding of the problem space? |

**Ties** go to the higher score on the first criterion, Technological Implementation.

Judging may use expert panels, peer review, automated AI analysis, or a mix. Write the description
so a reader, human or AI, can see exactly where and how Qloo is used.

## 5. Prizes

| Place | Prize |
|---|---|
| 1st | $15,000 |
| 2nd | $6,000 |
| 3rd | $4,000 |
| Bonus | Jason Calacanis invests $25,000 in his favourite entry |

Each project can win one prize.

## 6. Judges

Jason Calacanis (investor) · Mike Diolosa (CTO, Qloo) · Nicole Seligman (OpenAI board) · Todd Boehly
(Eldridge Industries) · Cedric the Entertainer · Michael Abrams (Live Nation).

## 7. API notes from the developer guide

- Keys take a few business days; check spam
- Keys work only on `https://hackathon.api.qloo.com`
- All documented endpoints are available; don't use `/recommendations` or `/recs`
- Private server-side caching is allowed with no time limit; never put Qloo data in a public repo
- Limits can be raised per user on request in Discord `#api-help`
- Keys are deactivated after the hackathon closes
