# Auditron — Product Requirements & System Design Document

**Project:** Digital Heroes Internship Qualification — Role 03/16, Software Development (SDE)
**Author:** [Your Name]
**Doc version:** 1.1 (backend stack revised to Python)
**Covers:** Task A (Build Auditron) + Task B (Prove it and explain it)

---

## 1. Problem Statement

Digital Heroes wants applicants to build a small, real, deployable tool that audits any public URL and returns a structured JSON report on that page's health — HTTP status, timing, SEO basics, and accessibility gaps. The tool must be a genuine working product (frontend + backend, deployed live), not a demo script, and it must degrade gracefully instead of crashing on bad input.

This document defines the product requirements, the system architecture, the API contract, the error-handling model, the testing strategy, and the documentation/proof deliverables needed to score well against the published rubric.

---

## 2. Goals & Non-Goals

### Goals
- Accept any URL and return a single JSON report describing the page's technical and SEO health.
- Ship a minimal frontend that calls the API and renders the report legibly.
- Handle all realistic failure modes (bad URL, timeout, non-HTML response, redirects, huge pages) without ever 500-ing unhandled.
- Be deployed live on a free tier, with the credit line required by the task kit.
- Be provably correct: automated tests for the parsing/audit logic, not just manual spot-checks.
- Be explainable: a README with setup, API contract, and 3 justified design decisions, plus a short recorded walkthrough.

### Non-Goals
- No user accounts, auth, or persistence (single-shot audit, stateless).
- No JS-rendering / headless browser crawling of SPA content (v1 is static-HTML audit only — documented as a limitation).
- No multi-page crawling — single URL in, single report out.
- No design system / pixel-perfect UI — "clean" is the bar, not "polished."

---

## 3. Success Metrics (mapped to rubric)

| Rubric criterion (Task A) | Weight | How this design satisfies it |
|---|---|---|
| Correctness & error handling | 40 | Explicit input validation, timeout budget, content-type guard, typed error envelope, no unhandled exceptions path |
| Code quality & structure | 35 | Layered architecture (fetch → parse → aggregate → respond), single-responsibility modules, typed contracts |
| API design | 25 | One clear REST endpoint, documented request/response schema, sensible status codes |

| Rubric criterion (Task B) | Weight | How this design satisfies it |
|---|---|---|
| Test quality | 40 | Unit tests for parser (happy path + ≥2 failure cases), isolated from network via fixtures |
| README & reasoning | 30 | Setup steps, API contract, 3 design decisions with tradeoffs |
| Self-critique in walkthrough | 30 | Loom script outline included (Section 9) naming a real thing to improve |

---

## 4. Users & Use Case

**Primary user:** the evaluator at Digital Heroes, who will paste a URL into the deployed frontend (or hit the API directly) and expect a JSON report back within a few seconds, or a clear error if the page can't be analyzed.

**Core user story:**
> As an evaluator, I paste any URL into the tool and get back a report telling me the page's status, load time, title/meta description, heading structure, image accessibility gaps, and rough word count — or a clear, specific error if the URL is invalid, unreachable, times out, or isn't HTML.

---

## 5. System Architecture

### 5.1 High-level shape

Stateless, single-request request/response service. No database, no queue, no background jobs — this is intentional: the task doesn't need persistence, and adding it would be over-engineering that hurts the "code quality & structure" score more than it helps.

```
┌─────────────┐        HTTPS         ┌──────────────────────────┐
│   Frontend  │ ───────────────────► │        Backend API        │
│  (static)   │ ◄─────────────────── │   POST /api/audit         │
└─────────────┘   JSON report/error   └──────────┬────────────────┘
                                                  │
                                                  ▼
                                     ┌────────────────────────────┐
                                     │  Audit Pipeline (in-process)│
                                     │  1. Validate URL            │
                                     │  2. Fetch (timeout budget)  │
                                     │  3. Guard content-type      │
                                     │  4. Parse HTML → DOM        │
                                     │  5. Extract signals         │
                                     │  6. Assemble JSON report    │
                                     └────────────────────────────┘
                                                  │
                                                  ▼
                                        Target URL (any host)
```

### 5.2 Component breakdown

| Component | Responsibility | Notes |
|---|---|---|
| `validators/url.py` | Confirms input is a syntactically valid absolute URL with http/https scheme | Rejects `javascript:`, `file:`, missing scheme, malformed strings before any network call |
| `fetcher.py` | Performs the HTTP GET with a hard timeout and size cap, records timing | Uses `httpx.AsyncClient` with a timeout budget; measures wall-clock response time |
| `content_guard.py` | Inspects `Content-Type` header before parsing | Non-HTML → typed error, never fed to the HTML parser |
| `parser/*.py` | Pure functions operating on a parsed `BeautifulSoup` tree: title, meta description, H1 count, images missing `alt`, word count | Pure & synchronous — this is what gets unit-tested in Task B, no network involved |
| `report_builder.py` | Aggregates fetch metadata + parser outputs into the final JSON contract | Single source of truth for response shape |
| `errors.py` | Maps every failure category to a consistent `{ error: { code, message } }` shape and HTTP status via a custom `AppError` exception | Ensures "never crash" requirement |
| `routes/audit.py` | Thin HTTP layer: parse request → call pipeline → return response | No business logic lives here |
| Frontend `AuditForm` | Input field, submit button, loading state | Calls the API, renders report or error message |
| Frontend `ReportView` | Renders the JSON report as readable sections | Pure presentational component |

### 5.3 Suggested stack

Any stack is acceptable per the brief; the following is fast to build and deploy on a free tier:

- **Backend:** Python 3.11+ with **FastAPI** + **Uvicorn**, `httpx` for the outbound fetch (native async timeout support), `BeautifulSoup4` for HTML parsing (fast, no headless browser needed for static audit)
- **Frontend:** Single static page — plain HTML/CSS/vanilla JS — satisfies "simple page with an input field" with zero build tooling
- **Deployment:** Backend on Render free tier (Python web service, `uvicorn` start command); frontend on Vercel/Netlify/Cloudflare Pages free tier
- **Testing:** `pytest` for the parser unit tests

This choice directly serves the "code quality" and "correctness" weight: FastAPI's Pydantic models validate request/response shapes automatically, and `BeautifulSoup4` gives synchronous, easily-testable DOM parsing without spinning up a browser. `httpx.AsyncClient` provides first-class async timeout and streaming support, which maps cleanly onto the timeout-budget and size-cap requirements in Section 7.

---

## 6. API Contract

### `POST /api/audit`

**Request body**
```json
{
  "url": "https://example.com"
}
```

**Success response — `200 OK`**
```json
{
  "url": "https://example.com",
  "status": 200,
  "responseTimeMs": 342,
  "title": "Example Domain",
  "metaDescription": null,
  "h1Count": 1,
  "imagesMissingAlt": 2,
  "totalImages": 5,
  "approxWordCount": 187,
  "fetchedAt": "2026-07-24T10:15:00.000Z"
}
```

**Error response shape (all failure modes)** — `4xx`/`5xx` as appropriate
```json
{
  "error": {
    "code": "TIMEOUT",
    "message": "The target page did not respond within 8000ms."
  }
}
```

### 6.1 Error taxonomy

| Scenario | HTTP status | `error.code` | Notes |
|---|---|---|---|
| Missing/empty `url` field | 400 | `MISSING_URL` | Validated before any I/O |
| Malformed URL / unsupported scheme | 400 | `INVALID_URL` | e.g. no scheme, `ftp://`, `javascript:` |
| DNS failure / connection refused | 502 | `UNREACHABLE` | Target host cannot be reached |
| Request exceeds timeout budget (e.g. 8s) | 504 | `TIMEOUT` | `AbortController`-driven |
| Non-2xx response from target | 200* | n/a — `status` field reflects it | A 404 on the *target* page is still a valid report about that page, not a tool error |
| Response `Content-Type` isn't `text/html` | 415 | `UNSUPPORTED_CONTENT_TYPE` | e.g. PDF, image, JSON API response |
| Response body exceeds size cap | 413 | `RESPONSE_TOO_LARGE` | Protects against memory blowup on huge pages |
| Unexpected internal error | 500 | `INTERNAL_ERROR` | Caught by a top-level handler; never leaks stack traces to the client |

\* Design decision — see Section 8.2.

---

## 7. Audit Pipeline — Processing Steps

1. **Validate** the URL string (scheme, structure) — reject fast, no network call for garbage input.
2. **Fetch** with:
   - Hard timeout (e.g. 8s) via `httpx.AsyncClient(timeout=...)`
   - `follow_redirects=True` with `httpx`'s built-in redirect limit to avoid redirect loops
   - Streamed reads (`response.aiter_bytes()`) with a byte cap to avoid loading multi-GB responses into memory
   - Timing captured from request start to response fully read
3. **Guard content type** — read `Content-Type` response header; if not `text/html*`, short-circuit with `UNSUPPORTED_CONTENT_TYPE` before attempting to parse.
4. **Parse** the HTML body with `BeautifulSoup4` (`html.parser` backend, no extra system deps):
   - `title` → `<title>` text, trimmed, or `null`
   - `metaDescription` → `<meta name="description">` content, or `null`
   - `h1Count` → count of `<h1>` elements
   - `imagesMissingAlt` → count of `<img>` with missing/empty `alt`
   - `totalImages` → total `<img>` count
   - `approxWordCount` → strip `<script>`/`<style>`, take visible text, split on whitespace, count tokens
5. **Assemble** the final JSON report and return `200` with the full payload.
6. **Catch-all**: any unhandled exception in steps 2–5 is caught by a top-level error boundary and converted into the standard error envelope with `500 INTERNAL_ERROR` — this is what prevents "never crash" from being a reviewer's finding.

---

## 8. Key Design Decisions (for the README)

### 8.1 Parsing library: `BeautifulSoup4` over a headless browser
A headless browser (Playwright) would allow auditing JS-rendered SPAs, but it's heavier to deploy on a free tier (larger memory footprint, slower cold starts, more failure surface, and an extra system-level browser binary to install). Since the task's signals (title, meta, headings, alt text, word count) are all present in server-rendered HTML for the vast majority of real-world pages, `BeautifulSoup4` with the built-in `html.parser` backend gets full correctness at a fraction of the operational risk, with zero compiled dependencies to worry about on a free-tier build. **Tradeoff documented:** pure client-side-rendered pages will show near-empty results — this is a known limitation, not a silent bug.

### 8.2 A `404`/`500` on the *target* page is a `200` from *our* API
The tool's job is to report on a page's health, not to mirror the target's status as our own. If `example.com/missing` returns 404, that 404 *is* the finding — the tool should say "status: 404" in a normal `200` JSON report, not fail the whole request. Only failures of the *audit process itself* (can't connect, timed out, wrong content type) become tool-level error responses. **Tradeoff:** this asymmetry has to be documented clearly in the README so it isn't mistaken for a bug.

### 8.3 Fail-fast validation before any network I/O
URL syntax is validated synchronously before the fetch is attempted. This means malformed input never consumes a network timeout budget or touches the fetch/parse pipeline at all — it's rejected in the same tick. **Tradeoff:** strict scheme allow-listing (`http`/`https` only) means some technically-valid-but-irrelevant URL schemes are rejected outright, which is the correct behavior for a web page auditor.

---

## 9. Testing Plan (Task B)

Tests target the **pure parsing/audit functions**, not live network calls — this keeps tests fast, deterministic, and CI-friendly.

| Test | Type | Fixture |
|---|---|---|
| Happy path: well-formed HTML with title, meta, H1s, some images missing alt | Unit | Static HTML string fixture |
| Failure case 1: HTML with no `<title>`/no meta description | Unit | Confirms fields resolve to `null`, not throw |
| Failure case 2: malformed/truncated HTML | Unit | Confirms parser degrades gracefully, doesn't throw |
| Failure case 3 (bonus): non-HTML content-type short-circuit | Unit | Confirms guard runs before parser is invoked |
| Integration (optional): full `/api/audit` route with a mocked fetch layer | Integration | Validates status codes + error envelope shape end to end |

Minimum bar per the brief: happy path + 2 failure cases — the table above covers that plus one bonus case.

---

## 10. Loom Walkthrough Script (outline)

1. Show the deployed frontend, paste a real URL, show the JSON report render.
2. Paste a deliberately broken URL — show the clean error message (not a crash).
3. Open the repo, walk through `reportBuilder.ts` and one parser function.
4. **Self-critique (required by rubric):** name one concrete thing to improve given another day — e.g. *"I'd add a small in-memory LRU cache keyed by URL with a short TTL, since right now every request re-fetches the target page even if it was just audited seconds ago — that's wasted latency and unnecessary load on the target site."*

---

## 11. Deliverables Checklist

- [ ] Public GitHub repo
- [ ] Live deployed link (backend + frontend)
- [ ] Footer credit line: "Built for Digital Heroes Training Task" linked to digitalheroesco.com
- [ ] Test files in repo (parser unit tests, happy path + 2 failure cases minimum)
- [ ] README: setup instructions, API contract, 3 design decisions with reasoning (Section 8 above)
- [ ] Loom demo video (working tool + code walkthrough + self-critique)

---

## 12. Estimated Effort

- Task A (build): 3–4 hours
- Task B (tests, README, Loom): 2–3 hours
- **Total:** ~5–7 hours across both tasks
