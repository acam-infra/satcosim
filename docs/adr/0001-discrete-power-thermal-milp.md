# 离散卫星功率档与线性热量约束联合调度（跨仓 ADR-0001）

对应子模块详细决策 `satsim/docs/adr/0007-discrete-power-thermal-milp.md` 与完整数学报告 `docs/DISCRETE_POWER_DESIGN.md`（`LAB-1867`）。

- **背景**：原连续指数批功耗 `device_power(batch, f)` 与 `84°C/76°C` 热回滞使 MILP 无法直接内嵌热约束。
- **决策**：在保留旧模式默认零回归（`diffs=0`）的前提下，新增 `power.mode: discrete_tiers`（零请求严格 `0 W` + 离散工作功率/容量档位 `(P_k, B^max_k, f_k)`），同时实现**多时隙时空联合 ILP（`discrete_time_ilp`，`time_limit_s = 120s`）**与**结构感知滚动热贪心（`discrete_rh_greedy`，融合源端 `0W` 整批排空激励 + 多步线性 RC 前瞻）**，并在 `jm` 机器上并行评测两者的求解耗时与最终优化目标收益。
- **协同研发执行**：按 `docs/BRANCHING.md §8` 由强模型（`carbon-4`）冻结 `power_tiers.py` 契约骨架，交 `hydrogen-4` 子 agent 并发池沿集成分支 `int/step3-discrete-power-milp` 四路正交实现。
