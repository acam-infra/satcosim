# Coding Standards (`satcosim` / `satsim` / `orbitsim`)

Read during `/code-review` and architectural refactors. Formatting, unused imports, and mechanical structural complexity thresholds are enforced by [ruff.toml](ruff.toml) and `python cosim.py lint`—this document governs **module abstractions, interface seams, and scientific rigor** that tooling cannot judge on its own.

---

## 1. Module Depth & Interface Seams

Use `/codebase-design` vocabulary (`module`, `interface`, `depth`, `seam`, `adapter`, `leverage`, `locality`):

1. **Deep modules over pass-through wrappers**
   - Hide numerical integration, graph/BFS caching, fluid bandwidth sharing, and thermal state evolution behind a small, stable interface.
   - Apply the **deletion test**: if removing a helper/class only moves code around without concentrating complexity, inline or collapse it.
2. **Respect simulation seams; do not poke into `World` internals**
   - Policy and workload plugins (`Placer`, `Migrator`, `Workload`, `Physics`, `Network`) interact with the simulation through explicit query/action methods (e.g. node-state queries `is_eclipse`, `is_hot`, `is_cool`, `thermal_headroom_C`, and `w.migrate(...)`).
   - Do not reach directly into internal mutable containers (`w.nodes`, `w.reserved`, `w.acc`, `w.net.flows`) or bypass invariants from external callers/policies.
3. **Extend by registry + seam, never `if/else` on policy names**
   - Adding a scheduler/plugin means adding one implementation class + one registry entry (`PLACERS`, `MIGRATORS`, etc.).
   - Never branch on strategy names (`if policy == "torch": ...`) inside `world.py` or `run.py`.
4. **One adapter = hypothetical seam; two = real seam**
   - Do not introduce abstract base classes, protocol hierarchies, or multi-file factories for a single implementation (`Speculative Generality`). Deepen the concrete module first; extract a seam only when a second real variant crosses it.
5. **Parse and validate configuration at the boundary**
   - Resolve nested YAML dicts, defaults, and unit conversions once in `schema` / `load_config` / `__init__` into typed attributes or small config dataclasses.
   - Avoid threading raw `cfg[...][...]` lookups into inner simulation loops or passing 8+ loose scalar arguments across helpers (`Data Clumps`).
6. **Bind derived caches to their owning instance**
   - Avoid module-level mutable caches keyed by `id(...)` (e.g. `_HOP_CACHE`) or implicit globals that survive across runs/seeds. Attach derived caches (adjacency, hop matrices) to the `Trace` or `World` instance whose lifetime owns them.

---

## 2. Research Control Variables & Scientific Integrity

1. **System budgets and admission gates belong to the environment, not individual policies**
   - Rebalance cadences and concurrency limits (`rebalance_invariants`: `interval_s`, `max_inflight`, `max_mig_per_req`) and admission gates must be injected uniformly by the runner/environment so every compared baseline runs under identical constraints.
   - A policy must never silently override shared budgets or embed hidden privilege flags.
2. **Preserve default behavior**
   - New modeling switches and YAML options must default to off; omitting new keys must leave existing baseline `summary.json` metrics unchanged.
3. **Verify boundary physics, not just green unit tests**
   - Review migration scoring and constraints for physical consistency: units (`W`, `°C`, `s`, `bytes` vs `bits`, `GiB` vs `GB`), `path_lifetime` vs `mig_timeout`, in-flight counters across control ticks, and partial decode progress during KV transfer.
   - Tail and waste metrics (`e2e_p95_all_s`, `badput_tok_s`, `waste_ratio`) must include all arrived requests (right-censored / undelivered included)—no survivor bias.
4. **No simulation sprawl in `scripts/`**
   - `satsim/scripts/` is for plotting and post-processing `runs/` artifacts only. New simulation loops, policies, and parameter sweeps belong in `satsim/src` driven by declarative YAML (`configs/` + `suite`).

---

## 3. Testing & Review Exemptions

### Test admission and cost control

- Prefer a small pure-data `R3Problem` or module test. Use a bounded full simulation when the defect crosses the `CoWorld / ProblemBuilder / R3Solver / PlanAction` seam; do not add another full simulation on every review round by default.
- Extend a parameter table for variants of one invariant. Around **800 lines per test file** triggers a split by invariant domain, with collected cases and assertions preserved. Do not remove distinct coverage merely to lower a count.
- Centralize shared builders in `tests/factories.py` and expose fixture entry points through `tests/conftest.py`; test modules must not import helpers from one another. Preserve intentionally different physical defaults explicitly.
- Register `unit`, `regression` and `e2e` markers. Daily feedback may use `pytest -m "not e2e"`; the PR gate runs full `pytest` and umbrella-root lint. Measure durations instead of promising a universal runtime.
- E2E `run_suite` tests validate composition and output contracts with one seed and a short horizon. Multi-seed matrices, performance comparisons and all-fine-grid MILP timeout references belong in declarative experiment packages on **cnb-compute/2**.
- After a core invariant is captured by pytest and passes the PR gate, retire the corresponding independent review script from routine reruns. Keep its original evidence; rerun only the relevant changed-point probe when it still adds an independent oracle, plus pytest and root lint. No cumulative replay of every historical review round.

See [satplan testing policy](satplan/docs/TESTING.md) for tier commands, invariant-domain modules and staged fixture consolidation. Test-only refactors must not change scientific workloads or invalidate a running experiment's frozen source/config/request hashes.

### Seam oracles and naming

1. **Test at module seams with independent oracles**
   - Assert observable behavior through public config/world/metric interfaces using worked hand calculations or conservation checks—do not mock internal fields or recompute production formulas inside assertions.
2. **Research naming exemptions**
   - Standard physical/domain symbols matching [docs/TERMS_AND_MODEL.md](docs/TERMS_AND_MODEL.md) and `GLOSSARY.md` (`R_th`, `C_th`, `P_max`, `P_dark`, `T_throttle_C`, `KV`) and short index variables (`i`, `j`, `t`, `r`, `w`) are valid and **exempt** from generic `Mysterious Name` complaints.
   - Banned legacy terms (`阴影`, `shadow`, `dark=cool`) must not appear in new code, tests, or docs—use `sunlit` / `eclipse` / `cool` / `hot`.
