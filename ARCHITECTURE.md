# Canvas2Code — Architecture

Sketch/wireframe image → Gemini vision model → frontend code string, displayed verbatim in the browser. Two services, one synchronous request.

## 1. Data flow

```
[User browser]                                [FastAPI backend]                    [Google]
    |                                                 |                              |
    |  1. select framework (React/Vue/HTML), pick img |                              |
    |  2. preview via URL.createObjectURL             |                              |
    |  3. POST /generate (multipart: file, framework) ----->                         |
    |                                                 | 4. read bytes                |
    |                                                 | 5. build f-string prompt     |
    |                                                 | 6. genai.generate_content -->|
    |                                                 |                  Gemini 2.5  |
    |                                                 |                       Flash  |
    |                                                 | <----- response.text         |
    |  <-- {status: "success", code: "..."} ----------|                              |
    |  7. setCode → render in <pre><code>             |                              |
```

No streaming, no caching, no queueing. One HTTP request blocks the UI until Gemini returns.

The output is **rendered as text**, not as a live preview — `<pre><code>{code}</code></pre>` with a copy button. The "preview" the user sees in [frontend/app/page.tsx](frontend/app/page.tsx) is just the uploaded image, not the generated UI.

## 2. File responsibilities

### Backend ([backend/](backend/))
- [backend/main.py](backend/main.py) — entire backend. FastAPI app, permissive CORS, two routes: `GET /` (health) and `POST /generate`. Loads `.env`, instantiates one `genai.Client()` at import time.
- [backend/requirements.txt](backend/requirements.txt) — pinned deps; the load-bearing ones are `fastapi`, `uvicorn`, `google-genai`, `python-multipart`, `python-dotenv`.
- [backend/.env](backend/.env) — holds `GEMINI_API_KEY` (gitignored).

### Frontend ([frontend/](frontend/))
- [frontend/app/page.tsx](frontend/app/page.tsx) — the entire app. Client component owning file/preview/framework/loading/code/error/copied state, calls backend, renders code as text.
- [frontend/app/layout.tsx](frontend/app/layout.tsx) — root layout, Geist fonts, stale default `"Create Next App"` metadata.
- [frontend/app/globals.css](frontend/app/globals.css) — Tailwind v4 import + light/dark CSS vars.
- [frontend/app/test/page.tsx](frontend/app/test/page.tsx) — **hardcoded sample component** (Venmo-style payment screen). Not a live-preview route; unrelated to the upload flow.
- [frontend/app/test/vue/page.tsx](frontend/app/test/vue/page.tsx) — **empty file** (0 bytes).
- [frontend/next.config.ts](frontend/next.config.ts), [frontend/tsconfig.json](frontend/tsconfig.json), [frontend/package.json](frontend/package.json) — defaults from `create-next-app`. No extra runtime deps beyond `next`, `react`, `react-dom`.

## 3. API contract

### `POST /generate`
**Request** — `multipart/form-data`
| Field | Type | Required | Notes |
|---|---|---|---|
| `file` | binary (image) | yes | mime type passed straight to Gemini |
| `framework` | string | yes | Interpolated into the prompt verbatim. Frontend sends one of `"React"`, `"Vue 3"`, `"HTML/CSS"`, but the field accepts any string. |

**Response** — `application/json`, always HTTP 200:
```jsonc
// success
{ "status": "success", "code": "<raw component source>" }
// failure
{ "status": "error",   "message": "<exception str>" }
```

The client at [frontend/app/page.tsx:42-48](frontend/app/page.tsx#L42-L48) discriminates on `data.status` rather than HTTP status — errors are 200s with an error body.

### `GET /`
Returns `{"status": "success", "message": "canvas2code AI backend is live!"}`. Health/liveness check.

## 4. Tech debt & refactor opportunities

**Security / correctness**
- **Prompt injection surface.** `framework` is f-string-interpolated into the prompt with no validation ([backend/main.py:32-37](backend/main.py#L32-L37)). A caller can rewrite the system instruction. Whitelist to a known enum.
- **CORS is `allow_origins=["*"]` with `allow_credentials=True`** ([backend/main.py:13-19](backend/main.py#L13-L19)). Browsers reject this combination, and intent is wrong regardless. Lock to the frontend origin.
- **Bare `except Exception`** ([backend/main.py:49-50](backend/main.py#L49-L50)) returns 200 + error body and exposes raw exception strings. Use `HTTPException` with proper status codes; log internally.
- **No input validation.** No size cap (UI copy says "10MB" but it's unenforced — [frontend/app/page.tsx:104](frontend/app/page.tsx#L104)), no mime check, no rate limit, no auth, no timeout on the Gemini call.

**API / DX**
- **Hardcoded backend URL** `http://127.0.0.1:8000` ([frontend/app/page.tsx:37](frontend/app/page.tsx#L37)) — move to `NEXT_PUBLIC_API_URL`.
- **Error envelope inside a 200** makes it impossible to distinguish network failure from app-level failure on the client. Switch to real HTTP status codes; the existing `catch` block already handles network errors separately.
- **Markdown fences.** Prompt says "do not include ```javascript", but the model sometimes does anyway. The frontend should strip them defensively.

**Product / structure**
- **No live preview.** Generated code is shown as text only. The "test routes" mentioned in [CLAUDE.md](CLAUDE.md) (`/test/vanilla`, `/test/vue` via vue3-sfc-loader) are aspirational: `/test` is a static sample, `/test/vue/page.tsx` is empty, `/test/vanilla` doesn't exist, and `vue3-sfc-loader` isn't in [frontend/package.json](frontend/package.json). Either build the iframe sandbox or remove the stale routes.
- **`app/page.tsx` is ~200 lines of mixed concerns** — upload, preview, fetch, render, copy. Splitting `UploadCard`, `FrameworkSelect`, `ResultBlock` would help, but only worth it once a real preview iframe lands.
- **Stale metadata** in [frontend/app/layout.tsx:15-18](frontend/app/layout.tsx#L15-L18) still says "Create Next App".
- **No tests, no CI, no logging, no error tracking.** Fine for a prototype; flag for productionisation.

**Where the planned refactor lands**
The LangGraph multi-model + SSE + Redis + budget-circuit-breaker plan in [CLAUDE.md](CLAUDE.md) implies pulling [backend/main.py](backend/main.py) apart into: provider adapters, an orchestration graph, a streaming endpoint, a cache layer, and a `usage_logs` writer. The single-function endpoint today is the right place to start that split.
