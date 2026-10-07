# Two-minute demo script

Record at 1440×900 with system audio on so the narration is heard. Rehearse twice, then record in one take. Small mistakes are fine.

| Time | Show | Say (roughly) |
|---|---|---|
| 0:00 | Home page, mortgage pack | "Regulated firms send people documents they don't understand. This turns the customer's own document into a personalised, accessible explainer, with answers grounded in that document." |
| 0:15 | Click Priya and play the first two scenes | "Every number here was extracted from her offer PDF by a local model, then checked before anything was rendered." |
| 0:35 | Toggle captions, open the transcript, tab through controls by keyboard | "It's built to WCAG 2.2 AA: captions, transcript, keyboard control, reduced motion. Axe runs on every commit." |
| 0:50 | Ask: "What happens when my fixed rate ends?", then click the citation | "Answers come only from her document, cite the passage, and refuse if it isn't there." |
| 1:05 | Switch to healthcare, then Imran | "Same engine, different industry pack: schema, script template and brand theme are all configuration. No code changes." |
| 1:20 | Under the hood: fields + evidence, quality report, lineage | "Every field carries its evidence quote and page. Quality rules are declarative per pack, such as recomputing the mortgage payment or checking fasting comes before arrival. Ungrounded values are flagged as possible hallucinations." |
| 1:40 | Eval table | "I measure extraction accuracy against ground truth per model, so model choice is a data decision rather than a guess." |
| 1:50 | Show the config switch or README diagram | "The model layer runs on Ollama for private-cloud deployments or a hosted model, switched by one setting. Lineage, data minimisation and a purge with deletion receipt are built in." |

## Questions to be ready for
- Why BM25 in the hosted function rather than embeddings?
- What happens when the grounding check fails? Who sees it?
- How would this change on GCP or AWS? (Vertex AI or Bedrock behind the same provider interface; Cloud Run or Lambda; KMS-encrypted storage; VPC Service Controls or PrivateLink.)
- How do you stop prompt injection from a document?
- How would you scale templating to 50 products? (Packs as versioned config, schema versioning, eval gating in CI.)
- What would you do differently with real customer data? (DPIA, retention, access control, audit logging, no PII in prompts sent to third parties without a DPA.)
