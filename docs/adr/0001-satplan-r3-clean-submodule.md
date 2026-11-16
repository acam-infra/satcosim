# 0001: Introduce `satplan` Submodule for Clean `r3` Runtime Reallocation

- **Status**: accepted

## Context

`satsim` accumulated two separate simulation engines (`satsim.method` vs `satsim.cosim`), 16 overlapping heuristic variants (`discrete_rh_tier_v1`–`v16`) inside `DiscreteThermalMigrator`, reactive baselines reading future orbital `power_segments`, and 17+ ad-hoc experiment scripts. Meanwhile, `orbitsim` and its `orbitsim.contact_trace/v1` contract remain clean and decoupled.

## Considered Options

1. **In-place refactor inside `satsim`**: Keep `CoWorld` and `PowerThermalModel`, freeze `v1`–`v16`, and build clean seams alongside legacy code. Rejected because `satsim` retains L1/L2 dual-engine baggage, legacy tests tied to internal fields, and confusing history.
2. **New `satplan` submodule built around `v2_stateful_planning_model_r3`**: Create a fresh minimal repository (`acam-infra/satplan`) wired into `satcosim` alongside `orbitsim` and `satsim`, using minimal SimPy continuous events + `Delta t` periodic planning strictly scoped to the `3 × 3` cross-matrix.

## Decision

We adopt **Option 2**: introduce `satplan` as a clean third submodule in `satcosim` built natively around `v2_stateful_planning_model_r3` (`Placer × RuntimePlanner`, `LocalStateView` vs `ForecastView`, `PowerThermalModel` RC linearity, `z_jlt` / `h_rjt` / `u_rjt` actions, and two-stage Goodput-CVaR MILP).

## Consequences

- `orbitsim` remains unchanged and supplies `orbitsim.contact_trace/v1` traces (and `viz/play.html` consumes `satsim.cosim_playback/v1` when emitted).
- `satsim` remains untouched as a read-only reference baseline for cross-checks.
- `satplan` enforces [CODING_STANDARDS.md](../../CODING_STANDARDS.md) and [ruff.toml](../../ruff.toml) from commit 0, keeping the entire core minimal and test-covered at clean seams.
