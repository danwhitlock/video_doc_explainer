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

### 2.1 — Provider interface (2026-10-07)
- **What:** `pipeline/providers/base.py` — the `LLMProvider` Protocol (`extract`, `answer`, `name`, `model`) and `pipeline/providers/__init__.py` (empty, package marker). Tests prove structural matching with a non-inheriting `DummyProvider`.
- **Why this way:** `Protocol` over `abc.ABC` + `@abstractmethod` - a `Protocol` lets `OllamaProvider`/`ClaudeProvider` satisfy the interface purely by shape, with no inheritance relationship to this module at all. Keeps each provider module fully independent of the others and of `base.py`.
- **How it fits:** `extract.py` (step 5) and the Phase 7 Q&A code will depend only on this shape, never on a concrete provider class - that's the mechanism behind `LLM_PROVIDER=ollama|claude` swapping models via config, not code.
- **Check question:** "Why `Protocol` over `abc.ABC` here?" — Dan: "because it lets other classes satisfy it without inheriting from it." Correct.

### 2.2 — Ollama provider (2026-10-07)
- **What:** `pipeline/providers/ollama.py` — `OllamaProvider.extract()` (structured output via `format=<schema>`) and `.answer()` (plain prompt over cited passages). Tests use a `FakeOllamaClient` injected in place of the real `ollama.Client`, so no live server is needed.
- **Why this way:** constructor accepts an optional `client` (dependency injection) specifically so provider logic (building the request, parsing the response) can be tested without a running Ollama server or a pulled model. A malformed model response is left to raise `json.JSONDecodeError` naturally rather than being caught here - retrying belongs to `extract.py` (step 5), not the provider.
- **How it fits:** second concrete `LLMProvider`; `get_provider()` (step 4) will return this when `LLM_PROVIDER=ollama`.
- **Check question:** "Why let `json.JSONDecodeError` propagate instead of catching it and returning `{}`?" — asked, moved on before an answer; worth revisiting (an empty dict would look like a valid-but-empty extraction to any caller, hiding the real failure).

---

## Glossary
Terms explained along the way, in plain English.

| Term | Meaning |
|---|---|
| Entry point | A mapping in `pyproject.toml` ([project.scripts]) that lets a shell command (`explainer`) resolve to a specific Python function, like a phone extension routing to a desk. |
| Typer callback | A function decorated with `@app.callback()` that runs before/instead of any subcommand; required for Typer to build a valid command tree even with zero subcommands. |
| Character offset | A position counted in characters from the start of a string (e.g. `start=120, end=180`). Lets later code point back at exactly which slice of source text a value came from, without copying that text around. |
| `extra="allow"` (pydantic) | A model setting that stores any fields you didn't explicitly declare instead of rejecting or dropping them, kept in `.model_extra`. Like an intake form with a few required fields plus a free-text box for anything else. |
| Protocol / structural typing | A way of saying "anything with this shape counts as this type," rather than nominal typing's "you must inherit from this base class." Duck typing, checkable by a type checker (and at runtime, with `@runtime_checkable`). |
| Dependency injection | Passing a class the thing it depends on (e.g. a client object) rather than having it construct that dependency itself - lets tests hand it a stand-in instead of the real thing. |
| Structured output | Telling a model API "your reply must match this JSON Schema" as a request parameter, rather than just asking in the prompt and hoping. |
