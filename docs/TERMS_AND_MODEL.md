# satsim 术语统一与建模说明（v2，2026-11-11）

> 适用：`acam-infra/satcosim` 及子模块 `satsim`（L2 `satsim.cosim`）。
> 用途：本仓库的术语口径。后续合入 `satsim/GLOSSARY.md` 新增一节，并作为 `satsim/docs/adr/0006-terms-sunlit-eclipse-cool.md` 的正文（由子模块维护者做）。
> 原则：**口语词和代码标识符一一对应，代码、注释、文档里只用标识符和下表的规范中文名。**

---

## 1. 为什么要改

之前的任务说明里，「阴影」同时被理解成两种东西：
- 背阳、只能靠电池供电、要降频的状态（代码里的 `is_dark` / `f_dark`）；
- 温度低、散热余量大、适合接收迁移的状态。

这两种状态在模型里是**两个独立的维度**（供电维、热维），方向也正好相反：前者是**迁出源**，后者是**迁入目标**。混用一个词，写代码时必然接错。

## 2. 两个维度、四个规范名

| 维度 | 规范中文名 | 口语 / 旧叫法 | 代码标识符 | 定义 | 对算力的影响 | 调度角色 |
|---|---|---|---|---|---|---|
| 供电 | **日照** | 光照、亮星 | `sunlit`（`not tr.is_dark(j,t)`） | 太阳翼供电，功率上限 `P_max` | `f_orbit = 1.0` | 可作迁入目标 |
| 供电 | **日影** | 背阳、地影、暗星、本影 | `eclipse`（`tr.is_dark(j,t)`） | 背阳，只靠电池，功率封顶 `P_dark` | `f_orbit = f_dark`（默认 80 W → 0.35） | **迁出源**；不作迁入目标 |
| 热 | **凉星** | **阴影**（用户口语）、冷星、低温星 | `cool`（`thermal_headroom_C(j) >= cool_margin_C`） | 结温离降频阈值还有足够余量 | 不降频，且能承接新负载一段时间 | **首选迁入目标** |
| 热 | **热星** | 过热、热节流 | `hot`（`thermal_f[j] < 1`）或 `near_hot`（预测 `lookahead_s` 内越过 `T_throttle_C`） | 结温达到或即将达到 `T_throttle_C`（84°C），回滞到 `T_release_C`（76°C）才恢复 | `f_thermal = f_throttle`（0.55） | **迁出源** |

**有效频率**：`f = min(f_orbit, f_thermal)`（已实现，`CoWorld.f_of`）。

**禁用词**：代码、注释、新文档里**不要再写「阴影」「shadow」「dark=cool」**。读到用户口语里的「阴影」，一律翻译成「凉星 / `cool`」；读到「日影 / 地影 / 背阳」，一律翻译成「日影 / `eclipse`（`is_dark`）」。

## 3. 两个维度怎么耦合（把「阴影=凉快」的直觉落到模型里）

一颗星绕一圈的典型时序：

```
日照满载 ──升温──▶ 热星（降频 0.55）
    │
    ▼ 进入日影
日影（功率封顶 80W，频率 0.35）── 功耗低，结温下降 ──▶
    │
    ▼ 出日影
刚出日影：日照 + 凉星  ← 最好的迁入目标（满频、热余量最大）
```

所以：
- **迁出源** = 日影中（或 `lead_s` 内即将进入日影）的星，以及热星 / 即将变热的星；
- **迁入目标** = 日照且凉的星（`sunlit ∧ cool`），其中**刚出日影的星**热余量最大；
- 这就是阶段二要用的「时变」信号：日照/日影由星历决定、可提前预知；热余量由 RC 模型积分、可向前预测。

> 现状：`T_amb_C` 是常数，日影期间降温**只来自功耗变低**（80 W 对 300 W），这已经足以产生「刚出日影的星最凉」。
> 可选增强（默认关闭、不改变现有结果）：热沉温度分两档 `T_amb_sunlit_C` / `T_amb_eclipse_C`，用于做敏感度扫描。

## 4. 其余术语（统一口径）

| 规范名 | 代码标识符 | 定义 |
|---|---|---|
| 初次分配 | `placer`（`PLACERS`） | 请求到达时选一颗可达且 KV 放得下的算力星。阶段一基线：`round_robin_all` / `nearest` / `random` |
| 再分配 / 迁移 | `migrator`（`MIGRATORS`）或整体策略的 `rebalance()` | 解码中途把请求连同 KV 通过星间链路搬到另一颗星 |
| 请求局部性 | `workload.source_rates_per_min` | 各遥感星（RS）的到达率不同，热点 RS 附近的算力星先被打满。**已支持**，只需在配置里给不均匀的数组 |
| 长推理 | `workload.long_out` / `p_long` | 输出 1.8 万~4 万 token 的长请求 |
| 算-传权衡 | — | 远端算力收益 vs `KV 传输 + 多跳时延 + 结果回传等待` 的代价。**只有链路窄、KV 大、链路间歇时才出现**；默认 10 Gbps 下 KV 迁移只要数秒，权衡不明显 |
| KV 迁移量 | `r.kv * w.bpt` | 默认模型 32 层 × 8 KV 头 × 128 维 × fp16 → 每 token 128 KiB；4 万 token ≈ 5.2 GB |
| 尾流 KV（Delta-KV） | `migration.delta_kv` | KV 传输期间源星继续解码产生的新 token，切换前要补传。**目前未计**，见 handoff T6 |
| 有效吞吐 Goodput | `goodput_tok_s` | 按时送达请求的输出 token / 到达窗口 |
| 坏吞吐 Badput | `badput_tok_s` | 已经算出来、但请求最终超时或未送达而作废的 token / 到达窗口 |
| 浪费率 | `waste_ratio` | `badput / (goodput + badput)` |
| 全量 P95 | `e2e_p95_all_s` / `long_p95_all_s` | 在**全部到达请求**上算；未送达请求按 `horizon − r.t` 记（右删失），同时报 `undelivered_frac`。现有 `lat_long_p90_s` 只算已送达请求，有幸存者偏差 |
| 公平配额 | `rebalance_invariants` | 迁移检查间隔、全网同时在途迁移数上限、单请求迁移次数上限。所有对比策略必须共用同一组值 |
| 准入闸门 | `admission_gate` | TORCH 里的 `viable_slack_s` 与 `pre_admission_relay`。属于**准入**，不是迁移；做消融时单独开关，并且要能套到 baseline 上 |

## 5. 阶段一 / 阶段二与代码的对应

| 任务说明 | 代码现状 |
|---|---|
| 阶段一：RR / 就近分配 | `round_robin_all`、`nearest`、`random` 已有 |
| 请求局部性 | `source_rates_per_min` 已有，需写一份热点配置 |
| 长推理 | 已有 |
| 过热降频 | `thermal:` 块（一阶 RC，84/76°C 回滞，0.55）已有 |
| 坏吞吐、全量 P95 | **缺**（T2） |
| 阶段二：往日照凉星多跳迁移 | `ThermalRebalance` / `TorchRebalance` 已做了一部分，但目标筛选没有显式的 `cool` 概念；新增 `cool_aware` 迁移器作为清晰的第一版（T7） |
| 拓扑时变、传+算+回传 | `tr.path(a,b,t)`、`FluidNet`、`tr.next_conn` 已有 |
| Decode 带 KV 迁移 | 已有（`CoWorld._migrate`），缺尾流 KV（T6） |
