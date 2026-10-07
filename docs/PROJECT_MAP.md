# Project map

Claude updates this after every step. Status: ⬜ not started · 🟨 in progress · ✅ done

```mermaid
flowchart LR
  subgraph Offline pipeline - Python, runs on your Mac
    A[Customer PDF] --> B[Ingest<br/>pages + chunks]
    B --> C[Extract<br/>LLM + schema + evidence]
    C --> D[Quality checks<br/>rules + grounding]
    D --> E[Render<br/>template -> scenes + captions]
    B --> F[Index<br/>chunks for Q&A]
    C -.-> G[Evaluate<br/>vs ground truth]
    D --> H[Lineage manifest]
  end
  subgraph Web app - React, hosted on Vercel
    E --> I[Player]
    F --> J[Ask panel]
    D --> K[Under the hood]
    H --> K
    G --> K
    T[Theme config] --> I
  end
  J --> L[ask.ts<br/>Claude API or demo answers]
```

| Component | Phase | Status | What it does | Key files |
|---|---|---|---|---|
| Project skeleton | 1 | ✅ | Python project, CLI, tests | `pyproject.toml`, `pipeline/cli.py` |
| Pack loader | 1 | ✅ | Reads an industry pack's config | `pipeline/packs.py` |
| Ingest | 1 | ✅ | PDF → page text → chunks | `pipeline/ingest.py` |
| Provider layer | 2 | ⬜ | One interface for Ollama or Claude | `pipeline/providers/` |
| Extract | 2 | ⬜ | Fields + evidence from the document | `pipeline/extract.py` |
| Quality checks | 3 | ⬜ | Rules + grounding (hallucination guard) | `pipeline/checks.py` |
| Lineage + purge | 3 | ⬜ | Audit trail, deletion receipts | `pipeline/lineage.py`, `purge.py` |
| Render | 4 | ⬜ | Template → scenes.json + captions | `pipeline/render.py` |
| Web player + theming | 5 | ⬜ | The explainer video experience | `web/src/` |
| Under the hood | 6 | ⬜ | Shows the data work | `web/src/` |
| Ask (Q&A) | 7 | ⬜ | Grounded answers with citations | `pipeline/index.py`, `web/api/ask.ts` |
| Evaluate | 8 | ⬜ | Accuracy per model | `pipeline/evaluate.py` |
| Accessibility, CI, deploy | 9 | ⬜ | Tests, scans, live site, docs | `.github/workflows/` |

**Current step:** Phase 1 complete (skeleton, ingest, pack loader) — next is Phase 2 (provider layer + extract)
