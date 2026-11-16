# Domain Docs

How engineering skills should read and update domain terminology and architectural decisions in `satcosim`.

## Before exploring, read these

- **`GLOSSARY.md`** at the repo root (created lazily when the first root-level domain term is crystallized by `/domain-modeling`).
- **`docs/adr/`** at the repo root (created lazily when the first root-level ADR is recorded).
- **Existing domain & spec references in this repo**:
  - [docs/TERMS_AND_MODEL.md](../TERMS_AND_MODEL.md) — physical/simulation terminology (e.g. `sunlit`/`eclipse`/`cool`).
  - [docs/ARCHITECTURE_AND_TODO.md](../ARCHITECTURE_AND_TODO.md) — overall architecture and consolidation roadmap.
- **Submodules** (`satsim/`, `orbitsim/`): when working inside a submodule, also consult its own domain docs:
  - `satsim/GLOSSARY.md`, `satsim/docs/adr/`, `satsim/docs/agents/domain.md`
  - `orbitsim/GLOSSARY.md`

If `GLOSSARY.md` or `docs/adr/` at the repo root does not exist yet, **proceed silently**. `/domain-modeling` (invoked by `/grill-with-docs` and `/improve-codebase-architecture`) creates them lazily when terms or decisions crystallize.

## File structure

Single-context at the `satcosim` root:

```text
/
├── GLOSSARY.md
├── docs/
│   ├── adr/
│   └── agents/
│       ├── domain.md
│       ├── issue-tracker.md
│       └── triage-labels.md
├── satsim/
└── orbitsim/
```

## Use the glossary's vocabulary

When naming a domain concept in an issue title, refactor proposal, hypothesis, or test name, use the canonical term from `GLOSSARY.md` (and `docs/TERMS_AND_MODEL.md` / submodule glossaries where applicable). Avoid synonyms the glossary explicitly bans (for example, use `eclipse` / `cool` rather than `shadow`).

## Flag ADR conflicts

If a proposed change contradicts an existing ADR (at root `docs/adr/` or in `satsim/docs/adr/`), surface it explicitly rather than silently overriding:

> _Contradicts ADR-XXXX (<title>), but worth reopening because…_
