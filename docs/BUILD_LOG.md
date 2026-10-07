# Build log

Claude appends one entry per step. Read this before an interview.

## Entry format
### <Phase>.<step> — <title> (<date>)
- **What:** what was built
- **Why this way:** the choice made and the alternative rejected
- **How it fits:** what feeds it, what uses it
- **Check question:** the question asked, and Dan's answer

---

### 1.1 — Project skeleton (2026-10-07)
- **What:** `pyproject.toml` (uv-managed deps, `explainer` CLI entry point, ruff config), the `pipeline` package, and `pipeline/cli.py` with a working but command-less Typer app.
- **Why this way:** Typer over argparse — subcommands and `--help` text come free from type hints instead of being hand-rolled. Hit and fixed a real gotcha: a bare `typer.Typer()` with zero commands and no `@app.callback()` raises `RuntimeError: Could not get a command for this Typer instance` — Typer needs at least a callback to build a runnable command tree, even an empty one.
- **How it fits:** this is the entry point every later pipeline module plugs into — `ingest.py`, `extract.py`, etc. will each get a `@app.command()` wired in here in later phases.
- **Check question:** "Why did `uv run explainer --help` fail before adding `@app.callback()`, even though `app = typer.Typer()` looked complete?" — Dan correctly identified Typer needs a registered command (or callback) to build the Click command tree; zero of either leaves nothing to run.

### 1.2 — Ingest (2026-10-07)
- **What:** `pipeline/ingest.py` — `extract_pages()` (pdfplumber, text per page) and `chunk_pages()` (~500-char `Chunk` objects on paragraph boundaries, each carrying page number + character offsets).
- **Why this way:** inspected the real sample PDFs before writing the chunker and found pdfplumber's extracted text has no blank lines at all — every visual line is hard-wrapped with a single `\n`, even mid-sentence. So `_paragraph_spans()` prefers blank-line paragraphs where they exist and falls back to one unit per line where they don't, in both cases never splitting a unit internally. Rejected always-split-on-`\n`: that would be indistinguishable from the line fallback for our samples, but would silently break real paragraph-structured PDFs that do use blank lines.
- **How it fits:** feeds `extract.py` (Phase 2, sends page text to the LLM) and `index.py` (Phase 7, chunk + offsets back Q&A citations to an exact passage).
- **Check question:** "Why two splitting strategies instead of always splitting on `\n`?" — Dan: "because there aren't any blank lines in the extracted text" (correct for our samples; the fuller reason is that always splitting on `\n` would be fine for our hard-wrapped samples but would shred real blank-line-paragraph PDFs into one-line fragments).

### 1.3 — Pack loader (2026-10-07)
- **What:** `pipeline/packs.py` — pydantic models for `pack.yaml`, `checks.yaml`, `template.yaml`, `theme.json`, `customers.json` (`schema.json` kept as a plain dict), and `load_pack()` assembling all six into one typed `Pack`.
- **Why this way:** read both packs' `checks.yaml` and `template.yaml` side by side before modelling and found real structural differences between them (healthcare's `phone-format` rule uses a list of fields where mortgage uses a single string; healthcare's `template.yaml` has an extra top-level `anaesthetic_explained` lookup mortgage doesn't have). Used pydantic's `extra="allow"` on `Rule` and `TemplateConfig` so both packs load through the same model without the loader itself branching on which pack it is. `schema.json` was deliberately left unmodelled - it's already a JSON Schema document, re-describing it in our own model would just duplicate JSON Schema's own keywords.
- **How it fits:** every later stage (`extract.py`, `checks.py`, `render.py`, web theming) reads pack config through this loader instead of parsing files itself - it's the mechanism that keeps the engine industry-agnostic.
- **Check question:** "Why does `Rule` only declare `id`, `type`, `severity` when rules clearly have other fields?" — Dan: "because of differences in the format" (correct instinct; the fuller reason is each rule *type* has a different set of meaningful extra fields - `min`/`max` for `range`, `if`/`then` for `conditional`, etc. - so one fixed model would carry fields that don't apply to most rule types. `checks.py`, not the loader, is what will look at `type` and know which extras to expect).

---

## Glossary
Terms explained along the way, in plain English.

| Term | Meaning |
|---|---|
| Entry point | A mapping in `pyproject.toml` ([project.scripts]) that lets a shell command (`explainer`) resolve to a specific Python function, like a phone extension routing to a desk. |
| Typer callback | A function decorated with `@app.callback()` that runs before/instead of any subcommand; required for Typer to build a valid command tree even with zero subcommands. |
| Character offset | A position counted in characters from the start of a string (e.g. `start=120, end=180`). Lets later code point back at exactly which slice of source text a value came from, without copying that text around. |
| `extra="allow"` (pydantic) | A model setting that stores any fields you didn't explicitly declare instead of rejecting or dropping them, kept in `.model_extra`. Like an intake form with a few required fields plus a free-text box for anything else. |
