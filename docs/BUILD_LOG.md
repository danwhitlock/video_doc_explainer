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
- **Check question:** "Why two splitting strategies instead of always splitting on `\n`?" — pending Dan's answer.

---

## Glossary
Terms explained along the way, in plain English.

| Term | Meaning |
|---|---|
| Entry point | A mapping in `pyproject.toml` ([project.scripts]) that lets a shell command (`explainer`) resolve to a specific Python function, like a phone extension routing to a desk. |
| Typer callback | A function decorated with `@app.callback()` that runs before/instead of any subcommand; required for Typer to build a valid command tree even with zero subcommands. |
| Character offset | A position counted in characters from the start of a string (e.g. `start=120, end=180`). Lets later code point back at exactly which slice of source text a value came from, without copying that text around. |
