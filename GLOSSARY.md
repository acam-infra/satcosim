# satcosim

Co-simulation context combining `orbitsim` (orbital contact traces), `satplan` (clean `r3` time-expanded runtime reallocation engine), and legacy `satsim` reference baselines.

## Language

### Orbital & Thermal States

**日照 (Sunlit)**:
Satellite state where solar panels provide unlimited energy budget (subject to compute thermal cap `T_max`), keeping orbit clock factor at `1.0`.
_Avoid_: 光照, 亮星

**日影 (Eclipse)**:
Satellite state in Earth's shadow powered by battery under a cumulative Depth-of-Discharge (`DoD`) energy budget across the eclipse window.
_Avoid_: 阴影, shadow, 本影, 暗星

**DoD 电量约束 (Eclipse DoD Budget)**:
Cumulative battery energy limit (`sum P_jt * Delta t <= E_DoD`) governing how much compute/idle energy a satellite may spend over an eclipse interval.
_Avoid_: 恒定暗态降频, 总能耗优化目标

**凉星 (Cool)**:
Compute satellite with thermal headroom sufficient to absorb new decode load without violating its thermal cap (`T_max`).
_Avoid_: 阴影, 冷星

**热星 (Hot)**:
Compute satellite at or near its thermal cap (`T_max`), making it a migration source or candidate for low-power/idle cooling.
_Avoid_: 过热降频星

### Runtime Reallocation (`r3`)

**离散功率档位 (Discrete Power Tier)**:
A discrete `(P_l, mu_l)` operating level on a compute satellite, spanning `0W` idle, low-power steady hold, and high-power sprint.
_Avoid_: 连续调频曲线

**首次分配 (Placer)**:
Outer admission rule that selects the initial compute satellite `j_0(r)` when a request arrives (`nearest`, `least_loaded`, `orbit_thermal`).
_Avoid_: 混合放置迁移

**运行时再分配 (Runtime Planner)**:
Inner periodic planner (every `Delta t`) that jointly decides power tiers, request pause/resume, and multi-hop migration flows over horizon `H`.
_Avoid_: 单步启发式补丁

**挂起 (Suspend / Store-and-Run)**:
No-drop execution policy (`h_rjt = 1`) where a request pauses decoding (zero compute power) while keeping its KV memory stored on the satellite until compute resumes or migration moves it.
_Avoid_: 丢包, 丢弃, 抢占驱逐

**累计传完解锁 (Cumulative Unlock)**:
Invariant (`u_rjt`) requiring migrated KV bytes received at the destination across slots to reach `S_r^kv` before the destination may execute or suspend the request.
_Avoid_: 边传边算

**Shadow 有效条件 (Shadow Validity)**:
Background deadline and continuity rule (`D_r^sh`) separating valid Goodput from wasted Badput, orthogonal to the reported throughput-vs-tail-latency tradeoff.
_Avoid_: 唯一硬性指标

**算完即完成 / 下行开关 (Compute-End Switch / `rs_downlink`)**:
Boolean config toggle (`rs_downlink`, default `false`) controlling end-to-end request completion: when `false`, requests finish immediately at CS decode completion (`t_delivered = t_decoded`), isolating in-constellation compute, thermal/DoD, and ISL reallocation from return-pass wait (`next_conn`); set `rs_downlink: true` to re-enable RS return downlink (`final` / `stream`).
_Avoid_: 硬编码回传阻塞
