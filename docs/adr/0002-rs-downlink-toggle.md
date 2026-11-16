# 0002: Decouple RS Return Downlink Behind `rs_downlink` Switch (Default Off)

- **Status**: accepted

## Context

In `satplan`, requests upload KV/context payloads from source `RS` nodes to compute satellites (`CS`), compete for KV capacity (`M_j`), **日照 (Sunlit)** thermal headroom (`T_max`), **日影 (Eclipse)** cumulative battery budget (`E_DoD`), and multi-hop ISL migration bandwidth (`Cumulative Unlock` + `Suspend`). Under earlier `final` / `stream` settings, every request's E2E completion also blocked after CS decode finished on `next_conn(RS, j, t_decoded)` and return `hop_lat`.

Because output tokens are small compared to multi-GB KV uploads/migrations and return pass timing is governed by last-mile RS orbital geometry rather than in-constellation resource scheduling, mandatory return downlink wait conflates ground/RS pass noise with CS compute, power/thermal, and ISL reallocation gains (and pushes `orbit_thermal` / MILP toward RS-pass proximity rather than thermal/DoD/ISL balance).

## Considered Options

1. **Always simulate RS return downlink (`next_conn` + `hop_lat`)**: Mixes last-mile downlink wait into `t_delivered` and `R3Problem` deadlines `D_r^sh`.
2. **Delete RS return downlink entirely**: Breaks future joint store-and-download or streaming stall (`stream` / `max_stall_frac`) ablations.
3. **Add boolean toggle `rs_downlink` defaulting to `false`**: End requests immediately on CS decode completion (`t_delivered = t_decoded`) by default while preserving `rs_downlink: true` for future downlink/stream studies.

## Decision

We adopt **Option 3**: add boolean config switch `rs_downlink` (default `false` in `CoWorld`, `LocalStateView`, and `configs/w53_baseline.yaml`):

- **`rs_downlink: false` (default)**: `CoWorld._deliver` sets `t_delivered = t_decoded` immediately on decode finish with zero return `next_conn` wait or return `hop_lat`; `orbit_thermal` optimizes predicted `t_dec` (upload + queue + thermal/`T_max`/DoD) directly; `R3Problem` deadlines `D_r^sh` constrain CS compute completion cleanly.
- **`rs_downlink: true` (opt-in)**: Restores exact `next_conn(origin, j, now)` wait, return `hop_lat`, `stream` disconnection stall accounting (`max_stall_frac`), and `orbit_thermal` downlink-aware `t_del` scoring.

## Consequences

- Primary `3 × 3` benchmarks (`{nearest, least_loaded, orbit_thermal} × {none, reactive, r3_milp}`) cleanly measure on-orbit compute, thermal/`T_max`, Eclipse `DoD`, and ISL reallocation without RS return-pass confounding.
- Enabling joint CS + RS-downlink ablations later requires only setting `rs_downlink: true` in experiment YAML.
