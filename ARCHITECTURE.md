# Canvas2Code — Architecture

Sketch → multi-model fan-out → headless render → vision-judge → self-correction loop → user-driven refinement chat.

Three vision providers race to produce frontend code from a UI sketch. Each output is rendered via Playwright and scored by a Gemini-Flash judge against the original sketch. Underperforming outputs auto-refine (up to 3 iterations) until they're either good enough or stop improving. The user then picks a winner and continues refining in a conversational chat.

## 1. Pipeline (initial generation)

```
                        ┌→ gemini_generate     ┐
POST /generate          │                       │
  │                     ├→ groq_generate        ├→ merge_node → render_all → judge_outputs
  ▼                     │                       │                              │
generate_code (fan-out) ─┼─                     │                              │ (conditional)
                        └→ openrouter_generate ─┘                              ▼
                                                                          [needs refinement?]
                                                                          /             \
                                                                       yes               no
                                                                        │                 │
                                                                        ▼                 ▼
                                                             refine_loop  ─→ (loop)      END
                                                       (refine + render + judge,
                                                        only for pending providers)
```

## 2. Pipeline (user-driven refinement, post-selection)

```
POST /select-winner → graph.aupdate_state({ selected_provider, current_code })
                       (no LLM call; pure checkpoint mutation)

POST /refine        → _route sees current_code + selected_provider → refine_code
                       → provider.generate(text-only, prompt = current_code + critique-style chat message)
                       → emits SSE `code` event
```

## 3. State (LangGraph `GraphState` TypedDict)

| Field | Type | Reducer | Set by |
|---|---|---|---|
| `image_bytes` | bytes? | replace | `/generate` initial state |
| `framework` | str | replace | `/generate` initial state |
| `messages` | List[Message] | `operator.add` (append) | `/generate` (initial user msg) + `refine_code` (assistant msg) + `/refine` body (user msg) |
| `outputs` | Dict[provider, code] | `operator.or_` (merge) | provider nodes + `refine_loop` |
| `errors` | Dict[provider, msg] | `operator.or_` | provider nodes (gen errors), `render_all` (render errors), `refine_loop` (refinement errors) |
| `rendered_screenshots` | Dict[provider, bytes] | `operator.or_` | `render_all`, `refine_loop` |
| `judgments` | Dict[provider, Judgment] | `operator.or_` | `judge_outputs`, `refine_loop` |
| `iteration_count` | Dict[provider, int] | `operator.or_` | `judge_outputs` (cap on judge fail), `refine_loop` (increment per cycle, cap on failure/worse-score) |
| `llm_call_count` | int | `operator.add` (sum) | every node that calls an LLM |
| `current_code` | str? | replace | `refine_code`, `/select-winner` |
| `selected_provider` | str? | replace | `/select-winner` |
| `error` | str? | replace | `refine_code` failure |

`Judgment` shape: `{ score: float (0–1), critique: str, needs_refinement: bool, iteration: int }`.

## 4. Backend module map

```
backend/
├── main.py                  # FastAPI app, lifespan (Playwright + Postgres saver), SSE event emitter
├── graph/
│   ├── __init__.py
│   └── builder.py           # StateGraph topology, all node implementations, conditional routing
├── providers/
│   ├── __init__.py          # PROVIDERS registry (gemini, groq, openrouter — code generators)
│   ├── _mime.py             # magic-byte MIME detection (PNG/JPEG/WebP/GIF)
│   ├── gemini.py            # google-genai client, lazy-init
│   ├── groq.py              # OpenAI-compatible client → api.groq.com (Llama 3.2 Vision)
│   ├── openrouter.py        # OpenAI-compatible client → openrouter.ai (Qwen-VL)
│   └── judge.py             # JudgeProvider — Gemini Flash w/ structured JSON output
├── rendering/
│   ├── __init__.py
│   └── renderer.py          # render_code_to_screenshot — 3 framework harnesses (HTML/React/Vue)
├── requirements.txt
└── .env.example             # required + optional env vars
```

## 5. API contract

### `POST /generate` (initial generation)
Body: `multipart/form-data` with `file`, `framework`, `thread_id`.
Response: `text/event-stream` (SSE). Events below.

### `POST /select-winner`
Body: `application/json` — `{ thread_id: str, provider: "gemini" | "groq" | "openrouter" }`.
Response: JSON `{ status: "ok", selected_provider }` or 400 if that provider has no output for the thread.
No LLM call; updates checkpoint state only.

### `POST /refine`
Body: `application/json` — `{ thread_id: str, message: str }`.
Response: SSE with `status` / `code` / `error` events. Uses the previously selected provider.

### `GET /`
Liveness check.

### SSE event types

| Type | Payload | Source |
|---|---|---|
| `status` | `{message}` | top-level status (start, complete, refining errors) |
| `provider_status` | `{provider, status}` | per-provider lifecycle: `generating` → `rendering` → `judging` → `refining`/`done`/`error` |
| `provider_code` | `{provider, content}` | a provider returned code (initial or after refinement) |
| `provider_screenshot` | `{provider, image_base64}` | rendered PNG (initial or after refinement) |
| `provider_error` | `{provider, message, stage}` | stage ∈ {`generation`, `rendering`} |
| `judgment` | `{provider, score, critique, iteration}` | one per judge call (initial + each refinement) |
| `refining` | `{provider, iteration}` | a refinement iteration started |
| `code` | `{content}` | `/refine` result (single-stream, post-selection) |
| `error` | `{message}` | top-level failure |

## 6. Phase 4 specifics

### 6.1 Rendering layer ([backend/rendering/renderer.py](backend/rendering/renderer.py))

`render_code_to_screenshot(code, framework, browser, viewport=1280x800, stability_delay=0.8, navigation_timeout_ms=15000) -> bytes`

- One shared `playwright.chromium` instance launched in FastAPI `lifespan`. Each render gets an isolated `BrowserContext` to prevent state leakage across providers.
- Three framework harnesses, applied based on `framework`:
  - **HTML/CSS** — wraps the code in a Tailwind-CDN HTML doc, unless the code already declares `<!DOCTYPE>` or `<html>`.
  - **React** — strips ES `import` statements and `export default` lines (these don't work in `<script type="text/babel">`), regex-detects the first PascalCase component name, injects `ReactDOM.createRoot().render(React.createElement(Name))`. Babel standalone compiles JSX in-browser. React production UMD + Tailwind CDN.
  - **Vue 3** — vue3-sfc-loader harness via CDN. SFC source embedded in `<script id="sfc-source" type="text/plain">` to avoid string-escaping headaches; `</script>` occurrences inside code are escaped to `<\/script>`.
- Stability: `wait_until="networkidle"` + 0.8s sleep before screenshot (allows Babel compile + Tailwind JIT to settle).
- Cleanup: `tempfile.mkstemp` for the harness file, `os.unlink` in a `finally`.

### 6.2 Vision-judge ([backend/providers/judge.py](backend/providers/judge.py))

`JudgeProvider.judge(original_sketch, rendered_screenshot, framework) -> { score, critique, needs_refinement }`

- Uses `gemini-2.5-flash` with `response_mime_type="application/json"` and `response_schema=_JudgmentSchema` (Pydantic) for structured output.
- Prompt explicitly tells the judge: sketches are imprecise on colors/fonts (don't penalize), but DO penalize for missing elements, wrong layout, wrong proportions, alignment issues.
- Threshold: `needs_refinement = score < 0.75` (judge model fills this; not derived client-side).
- Defensive parse: if structured output ever returns malformed text, falls back to `json.loads` then to a synthetic `{score: 0.0, critique: "could not parse"}` (which won't trigger refinement).

### 6.3 Self-correction loop ([backend/graph/builder.py](backend/graph/builder.py))

After `judge_outputs`, a conditional edge `_should_continue` decides:

```python
def _should_continue(state):
    for p in state["outputs"]:
        j = state["judgments"].get(p)
        if j and j["needs_refinement"] and state["iteration_count"].get(p, 0) < MAX_ITERATIONS:
            return "refine_loop"
    return END
```

`refine_loop` runs concurrently across pending providers (asyncio.gather). For each provider it does:
1. Build prompt = `REFINE_WITH_CRITIQUE_PROMPT` (previous code + judge's critique + sketch image).
2. Call `provider.generate` → new code.
3. `render_code_to_screenshot` → new screenshot.
4. `JUDGE.judge` → new judgment.
5. Compare scores (see termination rules below).
6. Update state.

The same `_should_continue` edge fires after `refine_loop`, so the cycle loops until termination.

### 6.4 Iteration cap logic

- `MAX_ITERATIONS = 3` ([backend/graph/builder.py](backend/graph/builder.py)).
- Counted per provider. Counter starts at 0; incremented once per `refine_loop` cycle.
- The conditional edge rejects any provider with `iteration_count >= 3`. Once a provider hits the cap, it's frozen for the remainder of the generation.
- Cap-hit cases:
  1. Three refinements completed and score still `< 0.75` → counter naturally reaches 3.
  2. Judge fails on initial outputs (in `judge_outputs`) → counter immediately set to 3 for that provider (no refinement attempts made).
  3. Refinement raises (provider error, render error, judge error during refinement) → counter set to 3 in `refine_loop`'s exception path.
  4. Refinement makes score worse → counter set to 3 (see no-improvement rule).

### 6.5 No-improvement termination rule

Inside `refine_loop`'s `refine_one` ([backend/graph/builder.py](backend/graph/builder.py)):

```python
if new_judgment["score"] < old_score:
    new_judgment["needs_refinement"] = False
    return { "provider": p, "kept_old": True, "judgment": new_judgment, "iteration": MAX_ITERATIONS, ... }
```

When the new score is strictly lower than the previous score:
- The new code and new screenshot are **discarded** — `outputs[p]` and `rendered_screenshots[p]` keep their previous values.
- The new judgment IS recorded (so the UI's iteration history shows "Iter N: 0.65 (worse, kept previous)").
- `iteration_count[p]` is forced to `MAX_ITERATIONS=3` to stop further attempts.
- The LLM calls still happened (one provider gen, one judge), so `llm_call_count` increments by 2.

Rationale: per spec, "if a refinement makes the score worse, stop refining that provider" — preserving the better artifact is safer than letting the model drift further.

### 6.6 LLM call accounting

Every node that calls an LLM returns `{"llm_call_count": n}` and the `operator.add` reducer sums:

| Node | Calls per run |
|---|---|
| `gemini_generate`, `groq_generate`, `openrouter_generate` | 1 each (3 total) |
| `judge_outputs` | 1 per screenshot (typically 3) |
| `refine_loop` | 2 per pending provider (gen + judge), upper bound |
| `refine_code` (post-selection chat) | 1 |

Logged at the end of `/generate` via `canvas2code` Python logger and surfaced in the final SSE `status` event (`"Comparison complete (N LLM calls)"`). State carries the running total for the upcoming budget-circuit-breaker phase.

## 7. Frontend ([frontend/app/page.tsx](frontend/app/page.tsx))

Two-mode UI gated on `selectedProvider`:

- **Comparison view** (no winner picked yet) — 3-column grid. Per column: provider name, score chip (color-coded ≥0.85 green / ≥0.5 yellow / red), status pill, Code/Preview toggle, code block or screenshot, iteration history (one row per judgment: `Iter N: 78% — critique`), Copy, Use this. Highest-scoring column gets a purple ring + ★ on its Use-this button.
- **Refinement view** (winner picked) — single panel with the chosen code, chat history, input box. "Switch model" button returns to comparison.

State pieces relevant to Phase 4:
- `providerStates[p].judgments: Judgment[]` — append-only history.
- `providerStates[p].status: "generating" | "rendering" | "judging" | "refining" | "done" | "error"`.
- `providerStates[p].screenshot?: string` — base64 PNG.
- `providerStates[p].renderError?: string` — render-stage error badge while code stays visible.
- Winner derivation: `Math.max(...PROVIDERS.map(p => providerStates[p].judgments.at(-1)?.score ?? -1))`.

## 8. Environment

Required (see [backend/.env.example](backend/.env.example)):
- `GEMINI_API_KEY` — google-genai SDK auto-reads this; used by the Gemini code provider AND the judge.
- `GROQ_API_KEY` — Llama 3.2 Vision via Groq's OpenAI-compatible endpoint.
- `OPENROUTER_API_KEY` — Qwen-VL via OpenRouter's OpenAI-compatible endpoint.
- `DATABASE_URL` — Neon-compatible Postgres connection string; `AsyncPostgresSaver` creates LangGraph checkpoint tables on first start.

Optional model overrides (defaults shift over time):
- `GROQ_MODEL` (default `llama-3.2-90b-vision-preview`)
- `OPENROUTER_MODEL` (default `qwen/qwen-2-vl-72b-instruct`)

Post-install:
```
python -m playwright install chromium
```

## 9. Tech debt / known limitations

**Carried over from Phase 1:**
- `framework` is still f-string-interpolated into prompts with no allowlist → prompt-injection surface.
- CORS still `allow_origins=["*"]` with `allow_credentials=True` (invalid combination; browsers reject anyway).
- No HTTPException on errors — most paths still return 200 with an error-shaped SSE event. `/select-winner` is the one exception (proper 400).
- Hardcoded backend URL `http://127.0.0.1:8000` in [frontend/app/page.tsx](frontend/app/page.tsx) — should be `NEXT_PUBLIC_API_URL`.
- No input validation on uploaded image (size/type cap).

**Phase 4-specific:**
- React harness component-name detection is regex-based — named exports, props-required components, or generated TypeScript-with-interfaces code may render blank.
- Vue harness assumes the model emits a valid SFC; partial SFCs fail silently to a render-error overlay.
- `wait_until="networkidle"` + 0.8s delay is empirical; complex Tailwind documents may need more.
- `refine_code` (chat refinement post-selection) doesn't re-render or re-judge. The conversational chat shows updated code but no updated screenshot. Could be added in a Phase 5.
- The judge sees a 1280x800 viewport screenshot regardless of sketch aspect ratio — tall mobile mockups get cropped.
- No retry/backoff on transient provider failures; one error per provider = one failed column.
- Refinement-stage errors are logged but not surfaced to the UI (silent per spec); user only sees the iteration_count cap.

**Open architectural questions:**
- Per-provider `refine_loop` packages refine + render + judge into one node, rather than three loop-edges. Cleaner topology, but each iteration emits a single SSE batch instead of streaming refine→render→judge separately.
- `errors` dict mixes generation and rendering errors; only the SSE `stage` field disambiguates. State alone doesn't distinguish — fine for now, less fine when the planned `usage_logs` table starts persisting failure modes.
