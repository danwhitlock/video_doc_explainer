# Explainer Engine — project brief for Claude Code

## What this is
A portfolio demonstrator that turns a customer's own complex document (a mortgage offer, a hospital procedure letter) into a **personalised, accessible, narrated explainer** with grounded Q&A.

One engine, configured per industry by an **industry pack** (schema + script template + brand theme). Two packs ship: `mortgage` (fictional lender *Fernmoor Building Society*) and `healthcare` (fictional provider *Brackenridge Health*).

It exists to evidence two roles:
- **Data & AI Engineer** — document → structured, validated, template-ready data; quality checks; lineage; evaluation; retention/deletion.
- **UX/UI Engineer** — customer-facing video + Q&A interface in React; brand theming through configuration; WCAG 2.2 AA.

Every design choice should be explainable in an interview. Prefer simple, well-tested, well-named code over clever code. When there is a trade-off, write a one-line note in `docs/DECISIONS.md`.

## Hard rules
- **Fictional brands and synthetic people only.** Never use real company names, logos, real patients or real customer data. Phone numbers use the Ofcom drama range `01632 960xxx`. Every screen footer says "Fictional demonstrator — not financial or medical advice".
- **No secrets in the repo.** API keys come from env vars only. `.env` is gitignored; `.env.example` lists the names.
- **The demo must work with no API key.** Pipeline outputs are committed as JSON; live Q&A falls back to precomputed answers.
- **Model-agnostic AI layer.** All LLM calls go through `pipeline/providers/` (Python) or `web/api/` (hosted Q&A). Provider chosen by `LLM_PROVIDER=ollama|claude`. Model names come from env (`OLLAMA_MODEL`, `ANTHROPIC_MODEL`), never hardcoded. Default to Ollama; Claude is used only for hosted Q&A and the optional eval comparison.
- **Industry-agnostic engine.** No `if pack == "mortgage"` in engine code. Anything industry-specific lives in `packs/<name>/` (schema, template, theme, checks config).

## Stack
- **Pipeline:** Python 3.11+, `uv`, `pydantic` v2, `pdfplumber`, `jinja2`, `pyyaml`, `ollama`, `anthropic`, `pytest` (readability via a simple syllable heuristic, or `textstat`, which needs NLTK cmudict), `typer` CLI.
- **Web:** Vite + React + TypeScript, plain CSS with custom properties (no UI kit — the theming is the point), `vitest`, Playwright + `@axe-core/playwright`.
- **Hosted Q&A:** one Vercel serverless function `web/api/ask.ts` calling the Claude API (current Haiku model, from `ANTHROPIC_MODEL`).
- **CI:** GitHub Actions. **Hosting:** Vercel free tier.

## Repo layout (target)
```
packs/<pack>/
  pack.yaml            # name, description, document type, scene visual types used
  schema.json          # JSON Schema for extraction; every field has a description
  checks.yaml          # declarative quality rules for this pack
  template.yaml        # scene-by-scene script, Jinja2 narration, conditions
  theme.json           # brand tokens
  customers.json       # synthetic customer profiles + which document is theirs
  samples/*.pdf        # the customer documents (input)
  samples/ground_truth/*.json  # correct answers, for evaluation ONLY — never read by the pipeline
pipeline/
  ingest.py            # PDF -> pages -> chunks (with page numbers + char offsets)
  providers/           # base.py (interface), ollama.py, claude.py
  extract.py           # schema-guided extraction with evidence per field
  checks.py            # quality engine: runs checks.yaml rules + built-in grounding check
  render.py            # template.yaml + extracted data + profile -> scenes.json + captions.vtt
  index.py             # chunk index (embeddings via Ollama nomic-embed-text) for Q&A
  lineage.py           # run manifest
  purge.py             # retention/deletion with receipt
  evaluate.py          # field-level accuracy vs ground truth, per model
  cli.py               # `explainer run|evaluate|purge|answers`
  tests/
web/
  src/ ...             # player, scenes, theming, Q&A, under-the-hood view
  public/data/<pack>/<customer>/  # pipeline outputs consumed by the web app
  api/ask.ts
docs/
  ARCHITECTURE.md  DECISIONS.md  DEMO_SCRIPT.md
```

## Pipeline behaviour
1. **Ingest** — extract text per page; split into chunks of ~500 chars on paragraph boundaries; keep `page`, `start`, `end`.
2. **Extract** — call the provider with the pack's JSON Schema (Ollama `format=<schema>`; Claude via tool use). For **every field** the model returns `{value, evidence_quote, page}`. Validate with Pydantic models generated from / mirroring the schema.
3. **Check** — run quality rules and produce `quality_report.json`:
   - *Built-in grounding check:* each `evidence_quote` must appear (normalised whitespace, case-insensitive) in the source page text. If not → field flagged `ungrounded`. This is the hallucination guard.
   - *Pack rules from `checks.yaml`:* required, type/range, regex, cross-field (e.g. recompute the monthly payment from loan/rate/term and compare within tolerance; fasting cut-off must be before arrival time).
   - *Readability:* rendered narration Flesch Reading Ease ≥ 60 (warn below).
   - Severity: `error` blocks rendering for that customer; `warn` renders but is shown in the UI.
4. **Render** — merge extracted data + customer profile into `template.yaml`; evaluate scene `when:` conditions; output `scenes.json` (ordered scenes: id, title, visual type, visual data, narration text, estimated duration) and `captions.vtt` (sentence-level cues; ~2.6 words/sec unless real audio durations exist).
5. **Lineage** — `manifest.json`: run id, timestamp, input file SHA-256, pack + schema version, provider + model, prompt SHA-256, per-stage durations, check summary, output file hashes.
6. **Data minimisation** — `scenes.json` contains only fields the template uses. Logs never contain customer names or document text (log field names and IDs only).
7. **Purge** — `explainer purge <customer>` deletes that customer's derived artefacts and writes `deletion_receipt.json` (what, when, hashes of deleted files). Retention period per pack in `pack.yaml`; `explainer purge --expired` applies it.
8. **Evaluate** — compare extraction to `ground_truth/` per field (exact / numeric tolerance / normalised string). Output a table per model: field accuracy, grounding rate, latency. Run for at least two Ollama models; optionally Claude.

## Web behaviour
- **Home:** choose industry → choose customer card. One click re-skins everything.
- **Player:** renders scenes as animated, data-driven visuals (types: `title`, `stat`, `comparison`, `timeline`, `checklist`, `table`, `alert`, `contact`). Narration via Web Speech API (pre-generated Piper audio if present in `public/data/.../audio/`). Controls: play/pause, previous/next scene, scene list (chapters), speed, captions on/off, transcript panel. Captions are synced to the active cue.
- **Ask:** question box beside the player, suggested questions as chips, answers cite the passage (page + quote) and can highlight it. Refuses politely when the document doesn't contain the answer.
- **Under the hood:** per customer — extracted fields with evidence and page, check results (pass/warn/error), lineage manifest, eval table. This is where the Data work is visible.
- **Theming:** `theme.json` → CSS custom properties at runtime. Fonts loaded from Google Fonts by name. A script (`npm run check:themes`) fails if any text/background pair is below 4.5:1 (3:1 for large text / UI components).

## Accessibility (WCAG 2.2 AA) — non-negotiable
Keyboard operable everywhere with visible focus; captions + full transcript; `prefers-reduced-motion` disables scene animation; no autoplay with sound; Q&A answers announced via `aria-live="polite"`; target sizes ≥ 24×24px; semantic landmarks and headings; colour never the only signal; zoom to 200% without loss. Axe runs in CI and must report zero serious/critical violations.

## Hosted Q&A (`web/api/ask.ts`)
- Input: `{pack, customer, question}`; reject questions > 300 chars.
- Retrieval: top 4 chunks by BM25 (MiniSearch) over that customer's committed `chunks.json` (embeddings are used locally; BM25 keeps the hosted function free of an embedding service — note this in DECISIONS.md).
- Prompt: system prompt says answer only from the provided passages, cite chunk ids, plain English, no personal financial/medical advice, otherwise say it can't answer and give the contact number. Passages wrapped in tags and treated as data, not instructions.
- `max_tokens` 300. If `ANTHROPIC_API_KEY` missing or the call fails → return the closest precomputed answer from `answers.json` with `mode: "demo"`.
- Client limits 10 live questions per session. A hard monthly spend limit is set in the Claude Console (documented in README).

## Commands (keep these working)
- `uv run explainer run --pack mortgage --all` / `--customer <id>`
- `uv run explainer evaluate --pack mortgage --models qwen2.5:7b,llama3.1:8b`
- `uv run explainer answers --pack mortgage` (precompute suggested-question answers)
- `uv run explainer purge --customer <id>`
- `uv run pytest`
- `cd web && npm run dev | test | test:a11y | check:themes | build`

## Working style: build WITH Dan, one step at a time
Dan is moving from project management into engineering. He must understand every part of this project well enough to explain and defend it in an interview. **Understanding matters more than speed.** Follow this loop for every step, without exception.

### 1. Before each phase: break it into steps
Split the phase from `PROMPTS.md` into small steps. One step = one concept, ideally ≤ 3 files and ≤ ~150 changed lines. Show the numbered list with a one-line purpose each, then **stop and wait** for Dan to agree or change it.

### 2. Before each step: announce, then wait
Use exactly this shape, then **stop and wait for "go"** (or questions):

> **Next: <what you'll build>**
> **What it does:** one or two plain-English sentences.
> **Where it fits:** which box in `docs/PROJECT_MAP.md` this is, what feeds into it and what uses its output.
> **How:** the library/technique, and *why* this one (name one alternative you rejected and why).
> **Files:** each file you'll create or change, one line each.
> **How we'll know it works:** the test or command we'll run.

### 3. Build it
Only what you announced. If you find you need something else, stop and say so before doing it. Keep code simple and well named; add a short comment where the *why* isn't obvious.

### 4. After each step: walk Dan through it
> **Built:** what now exists.
> **Key parts:** point to the 2–4 most important lines or functions and explain what each does.
> **Try it:** the exact command for Dan to run himself, and what he should see.
> **New concepts:** any term or pattern Dan may not know, explained in one or two sentences with an analogy to project delivery where it helps. Add it to the glossary in `docs/BUILD_LOG.md`.
> **Check your understanding:** one short question Dan should be able to answer (don't give the answer unless asked).

Then update `docs/PROJECT_MAP.md` (status of each component) and append an entry to `docs/BUILD_LOG.md`. Suggest a commit message. **Stop and wait.**

### Rules
- Never chain steps together or "quickly also" do something unannounced.
- If Dan asks a question, answer it fully before moving on, even if it slows things down.
- Prefer boring, readable code over clever code. Avoid introducing a new library without announcing it.
- Plain English. Define jargon the first time you use it.
- If Dan says "where are we?", show the project map with the current step highlighted.
- Write tests for checks, rendering conditions and the grounding check before wiring the UI.
- Don't add features outside this brief without asking.
