# satcosim

Co-simulation orchestrator combining `orbitsim` (orbital contact traces) and `satsim` (discrete-event LLM inference & thermal/ISL simulation).

## Navigation

- Entry script: `cosim.py`
- Submodules: `orbitsim/` and `satsim/` (each has its own `GLOSSARY.md`; `satsim/` also has `satsim/AGENTS.md` and `satsim/docs/adr/`)
- Branching, worktrees, PRs, and multi-agent Multica workflow: `docs/BRANCHING.md`
- Domain terms & modeling background: `docs/TERMS_AND_MODEL.md`, `docs/ARCHITECTURE_AND_TODO.md`, `docs/HANDOFF.md`
- Coding standards (interfaces, seams, research rigor; read during `/code-review`): `CODING_STANDARDS.md`
- Structural lint & hygiene checks (`ruff.toml` + banned terms + viz `tsc`): `python cosim.py lint`

## Agent skills

### Issue tracker

Multica (`--profile gjam`) under project `科研 · Satellite` (`75c795bb-8da2-43f6-b743-2caf76371132`), supporting main issues (`--parent`) and staged/DAG sub-issues (`--stage`, `Blocked by:`). See `docs/agents/issue-tracker.md`.

### Triage labels

Canonical triage roles mapped to `gjam` statuses and workspace labels (`实现`, `调研`, `待人工`, `已归档`, etc.). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout (`GLOSSARY.md` + `docs/adr/` at root, created lazily) with submodule links to `satsim/` and `orbitsim/`. See `docs/agents/domain.md`.
