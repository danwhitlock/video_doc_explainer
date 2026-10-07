# Build prompts for Claude Code

Paste one phase at a time into Claude Code from the repo root. Claude will first break the phase into small steps (see "Working style" in CLAUDE.md) and wait for your go-ahead before each one.

**Helpful commands:** `/next` proposes the next step · `/where` shows the project map · `/explain <thing>` explains anything · `/recap` catches you up after a break · `/quiz` gives interview practice.

**Settings:** keep the default permission mode so you see and approve every file edit; don't turn on auto-accept. For a new phase you can press Shift+Tab to switch to plan mode, which stops Claude editing anything until you approve the plan.

Each phase ends with tests passing and a commit. Read the diff before you accept it, and write down why each choice was made. That's what you'll be asked about in interview.

**Before you start**
```bash
ollama pull qwen2.5:7b && ollama pull llama3.1:8b && ollama pull nomic-embed-text
git init && git add . && git commit -m "Brief, industry packs and sample documents"
```
The six sample PDFs and their ground truth are already generated. To regenerate them: `uv run --with reportlab python tools/make_samples.py`.

**Time guide:** Day 1 covers phases 1–4. Day 2 covers phases 5–9.

---

## Phase 1 — Project skeleton and ingestion (~45 min)
> Read CLAUDE.md and the two folders in packs/. Set up the Python project with uv (`pyproject.toml`, a `pipeline` package, a typer CLI called `explainer`, pytest, ruff). Add `.gitignore` and `.env.example`. Implement `pipeline/ingest.py`: extract text per page with pdfplumber, then split into ~500-character chunks on paragraph boundaries, keeping page number and character offsets. Add a pack loader that reads pack.yaml, schema.json, checks.yaml, template.yaml, theme.json and customers.json into typed objects. Write tests for chunking and pack loading. Don't build anything else yet.

## Phase 2 — Provider layer and extraction (~1.5 hrs)
> Implement `pipeline/providers/` with a small `LLMProvider` interface (`extract(text, schema) -> dict`, `answer(question, passages) -> dict`, plus a `name` and `model`). Build `OllamaProvider` (structured output via `format=<json schema>`) and `ClaudeProvider` (tool use with the schema as the tool input schema). Choose the provider with `LLM_PROVIDER`, and the model from env.
> Implement `pipeline/extract.py`: wrap each schema field as `{value, evidence_quote, page}`, send the full document text with page markers, and validate the response. Retry once with the validation errors if it fails. Record the provider, model, prompt SHA-256 and duration. Write tests using a fake provider. Then run it for real on `mortgage/m-001` with Ollama and show me the output.

## Phase 3 — Quality checks, lineage and purge (~1.5 hrs)
> Implement `pipeline/checks.py`. Every rule type used in either pack's checks.yaml must be implemented generically: required, range (incl. min_items), regex (single field or list), compare, date_order (incl. `{date, time}` targets and skip_if_null), conditional (ops ==, >, <, in, not_null), and formula (named functions: `ltv`, `amortised_payment`, `erc_years_cover`). Add the built-in grounding check: the evidence quote must appear in the source page text after normalising whitespace and case. Add a readability check on rendered narration (Flesch Reading Ease; implement a simple syllable heuristic or use textstat, which needs NLTK's cmudict downloaded once).
> Output `quality_report.json` with each result's rule id, severity, status, message and fields. Implement `lineage.py` (manifest.json as described in CLAUDE.md) and `purge.py` (deletes a customer's derived files and writes deletion_receipt.json; `--expired` uses retention_days). Tests: one passing and one failing case per rule type, plus a grounding test where the quote is invented.

## Phase 4 — Rendering and the full run (~1 hr)
> Implement `pipeline/render.py`. Load template.yaml with Jinja2 (StrictUndefined) and implement every filter listed in the headers of both templates. Evaluate `when:` expressions and render narration and visual fields. Where a visual field is a whole list expression (e.g. `"{{ d.items_to_bring }}"`), pass the real list through, not its string form. Map the ERC schedule to table rows. Collapse whitespace in narration. Apply the template's `speech:` rules to produce a separate `speech` text for TTS (phone numbers as digits) while keeping `narration` for captions. Write `scenes.json` with estimated durations (2.6 words/sec) and `captions.vtt`. Include only the fields the template uses.
> Wire up `explainer run --pack X --all`: ingest, extract, check, render, chunks.json, then manifest. Write outputs to `web/public/data/<pack>/<customer>/`. Errors block rendering for that customer. Run both packs with Ollama and commit the outputs.

## Phase 5 — Web player and theming (~2.5 hrs)
> Create the web app in `web/` with Vite, React and TypeScript. Build:
> - **Home:** an industry switcher and customer cards, using the persona from customers.json.
> - **Theming:** a ThemeProvider that maps theme.json to CSS custom properties, loads the Google Fonts by name and draws a simple SVG brand mark from `brand.mark`.
> - **Player:** reads scenes.json. One React component per visual type (title, stat, comparison, timeline, table, checklist, alert, contact). Narration uses the Web Speech API with the theme's voice settings; time each scene from the utterance's end event, falling back to the estimated duration. Controls: play/pause, previous/next, a chapter list, speed, captions toggle and a transcript panel with the current sentence highlighted. Captions follow the active sentence.
> - Respect `prefers-reduced-motion`. No autoplay. Footer reads "Fictional demonstrator — not financial or medical advice".
> Use plain CSS with tokens only, and make it look like a polished product. Add `npm run check:themes`, which fails if any theme.json contrast pair is under its minimum.

## Phase 6 — Under the hood (~1 hr)
> Add an "Under the hood" view for each customer. Show the extracted fields table (value, evidence quote, page, and a grounded ✓/✗ badge), the quality report grouped by severity, the lineage manifest (hashes shortened, copy button) and the evaluation table if `eval.json` exists. The audience is a technical interviewer, so keep it dense but readable.

## Phase 7 — Ask (~1.5 hrs)
> Locally: `pipeline/index.py` embeds chunks with Ollama `nomic-embed-text`, and `explainer answers --pack X` precomputes answers to the pack's suggested_questions into `answers.json` (with cited chunk ids). Hosted: `web/api/ask.ts` is a Vercel function that does BM25 retrieval with MiniSearch over that customer's chunks.json, then calls the Claude API following CLAUDE.md's rules (passages wrapped in tags and treated as data, cite chunk ids, refuse and give the phone number when the answer isn't there, max_tokens 300, 300-char question limit). It falls back to answers.json with `mode: "demo"` if there's no key or the call fails.
> UI: an Ask panel next to the player with suggested-question chips and a text box. Show the answer with citations (page + quote); clicking a citation opens the passage. Use an `aria-live` region, cap live questions at 10 per session, and show a "demo mode" badge when the answer is precomputed. Record the BM25-vs-embeddings decision in docs/DECISIONS.md.

## Phase 8 — Evaluation (~45 min)
> Implement `pipeline/evaluate.py` and `explainer evaluate --pack X --models a,b[,claude]`. Compare each extracted field to `samples/ground_truth/` (numbers within 0.5% or 0.01; dates exact; strings normalised; lists compared item by item). Output `eval.json` per pack (accuracy by model and field, grounding rate, mean latency) and print a table. Run it for qwen2.5:7b and llama3.1:8b on both packs. Run Claude on one pack only if I confirm the budget. Note the deliberate traps in DECISIONS.md: the mortgage PDFs include an illustrative "if rates rise by 1%" payment and an ERC table that runs across a page break.

## Phase 9 — Accessibility, CI, deploy and docs (~2 hrs)
> 1. Add Playwright tests that load each pack and customer, play a scene, use the Ask panel by keyboard only, and run axe (fail on serious/critical). Fix everything found. Check 200% zoom and a 360px-wide viewport.
> 2. Add a GitHub Actions workflow: ruff + pytest, then npm ci, check:themes, vitest, build and Playwright+axe. Add `pip-audit`, `npm audit --audit-level=high` and gitleaks secret scanning. Show a status badge in the README.
> 3. Prepare for Vercel: root `web/`, `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` as env vars. Document setting a monthly spend limit in the Claude Console.
> 4. Write README.md (what it is, a GIF, the architecture diagram in Mermaid, how to run, design decisions, and how it maps to a regulated deployment) and docs/ARCHITECTURE.md. Keep both honest about what's real and what's simplified.

---

## After the build
- Record the 2-minute walkthrough using `docs/DEMO_SCRIPT.md` (macOS: Cmd+Shift+5).
- Put the repo link, live link and video at the top of your CV under a "Selected project" heading.
