# Page Pulse

A small web tool that audits any URL and returns a JSON report on the page's
technical and SEO health — HTTP status, response time, title, meta
description, H1 count, images missing alt text, and approximate word count.

Built for the Digital Heroes Internship Qualification Task Kit (Role 03/16,
Software Development).

**Backend stack:** Python 3.11+ — FastAPI + Uvicorn + httpx + BeautifulSoup4
**Frontend stack:** plain HTML/CSS/vanilla JS (no build step)

## Project structure

```
page-pulse/
├── backend/                    # Python + FastAPI API
│   ├── app/
│   │   ├── validators/
│   │   │   └── url.py              # URL validation (fail-fast, before any I/O)
│   │   ├── parser/
│   │   │   ├── title.py            # <title> extraction
│   │   │   ├── meta_description.py # <meta name="description"> (case-insensitive)
│   │   │   ├── headings.py         # H1 count
│   │   │   ├── images.py           # alt-text audit
│   │   │   ├── word_count.py       # approx. visible word count
│   │   │   └── parse.py            # parse_html() — combines all parser functions
│   │   ├── routes/
│   │   │   └── audit.py            # POST /api/audit route handler
│   │   ├── fetcher.py              # httpx GET with timeout, size cap, timing
│   │   ├── content_guard.py        # rejects non-HTML content-types before parsing
│   │   ├── errors.py               # AppError exception → {code, status, message}
│   │   ├── report_builder.py       # run_audit() — full pipeline orchestrator
│   │   └── main.py                 # FastAPI app factory + CORS + global error handlers
│   ├── tests/
│   │   ├── fixtures/
│   │   │   ├── happy_path.html           # well-formed page with all SEO signals
│   │   │   ├── missing_metadata.html     # no <title> or <meta description>
│   │   │   ├── malformed.html            # severely truncated / unclosed-tag HTML
│   │   │   └── multiple_h1_and_scripts.html  # complex case: 3×H1, mixed alt, scripts
│   │   ├── conftest.py                   # shared fixtures_dir + load_fixture
│   │   ├── test_fixtures.py              # PRD rubric: happy path + 2 failure cases
│   │   ├── test_parser.py                # per-extractor unit + integration tests
│   │   ├── test_validate_url.py          # URL validator coverage
│   │   ├── test_content_guard.py         # content-type guard coverage
│   │   ├── test_errors.py                # AppError + error envelope coverage
│   │   ├── test_report_builder.py        # run_audit() with mocked fetch/parse
│   │   ├── test_route_audit.py           # HTTP integration via TestClient
│   │   └── test_audit_request.py         # Pydantic AuditRequest schema
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── .env.example
│   └── .gitignore
├── frontend/                   # Static HTML/CSS/vanilla JS (no build step)
│   ├── index.html              # form + report/error rendering + credit footer
│   ├── script.js               # calls the API, renders report or error
│   ├── config.js               # set the deployed backend URL here before deploying
│   └── style.css
├── docs/
│   └── page-pulse-prd.md       # original PRD
├── .gitignore
├── PROGRESS.md                 # PRD progress tracker & agent context bridge
└── README.md                   # this file
```

## Setup — run locally

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
```

The API is now live at `http://localhost:8000`. Check `GET /health` for a
quick liveness check.

Run the tests:

```bash
pytest
```

### Frontend

The frontend is plain static files — no build step required.

```bash
cd frontend
npx serve .          # or open index.html directly, or use a Live Server extension
```

By default `config.js` points at `http://localhost:8000`. Before deploying,
update `window.PAGE_PULSE_API_BASE` in `frontend/config.js` to your deployed
backend URL.

## API contract

### `POST /api/audit`

**Request**
```json
{ "url": "https://example.com" }
```

**Success — `200 OK`**
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
  "fetchedAt": "2026-07-24T10:15:00Z"
}
```

**Error — shape is consistent across all failure modes**
```json
{ "error": { "code": "TIMEOUT", "message": "The target page did not respond within 8000ms." } }
```

| Scenario | Status | `error.code` |
|---|---|---|
| Missing/empty `url` | 400 | `MISSING_URL` |
| Malformed URL / unsupported scheme | 400 | `INVALID_URL` |
| DNS failure / connection refused | 502 | `UNREACHABLE` |
| Timed out (8s budget) | 504 | `TIMEOUT` |
| Non-HTML response | 415 | `UNSUPPORTED_CONTENT_TYPE` |
| Response too large | 413 | `RESPONSE_TOO_LARGE` |
| Unexpected internal error | 500 | `INTERNAL_ERROR` |

Note: a non-2xx status *on the target page itself* (e.g. auditing a URL that
404s) is **not** a tool error — it's a normal `200` report where the `status`
field reflects it. Only failures of the audit process itself become error
responses. See design decision #2 below.

## Design decisions

**Starting points from the PRD — finalize wording once you've built and
tested against real URLs:**

1. **`BeautifulSoup4` over a headless browser** — full correctness on
   server-rendered HTML signals at a fraction of the memory/deploy cost, and
   zero compiled/system dependencies on a free-tier build; known limitation
   on pure client-rendered SPAs.
2. **Target 404/500 is a `200` from our API** — the tool reports on a page's
   health; the target's own status *is* the finding, not a tool failure.
3. **Fail-fast validation before any network I/O** — malformed URLs are
   rejected in the same call, never consuming timeout budget or reaching the
   fetch/parse pipeline.

## Deployment

- **Backend:** deploy `backend/` to Render as a Python web service. Build
  command: `pip install -r requirements.txt`. Start command:
  `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Free tier requires no
  credit card, but cold-starts after ~15 min idle.
- **Frontend:** deploy `frontend/` as a static site to Vercel, Netlify, or
  Cloudflare Pages, with `config.js` updated to point at the live backend URL.
- Don't forget the required credit line in the footer — it's already wired up
  in `frontend/index.html`, linked to `digitalheroesco.com`.
# Auditron
