# Decision log

One line per decision: what, why, and what would change it.

- **Ollama by default, Claude for hosted Q&A only.** Free to run, keeps documents local (the private-cloud story), and the provider interface keeps the hosted option open. Would change if extraction accuracy on Ollama falls below the eval threshold.
- **Synthetic documents with ground truth.** Enables measurable evaluation and avoids real brands or personal data.
- **Pipeline outputs committed as JSON.** The demo can never break on a missing key or a slow model.
