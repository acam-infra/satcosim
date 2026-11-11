# satcosim / satsim 统一声明式架构与科研主线收敛方案（RFC & TODO）

> **状态**：Draft for Team Review  
> **适用仓库**：`acam-infra/satcosim`（协同总控）及子模块 `acam-infra/satsim`、`acam-infra/orbitsim`  
> **核心目标**：解决当前“双引擎分裂、一次性实验脚本泛滥、主实验控制变量混杂、论文故事线多头并存”的问题，收敛为**唯一仿真内核 + 五维可插拔场景 + 声明式实验矩阵（Suite YAML）**的可持续科研迭代体系。

> **审阅补充（2026-11-11，LAB-1779）**
> - 术语：本文「暗星 / 本影」= **日影**（`eclipse`，降频，迁出源）；迁入目标是**日照凉星**（`cool`）。口径见 [`TERMS_AND_MODEL.md`](TERMS_AND_MODEL.md)。
> - 第一节第 4 点数字更正：`torch_lp` 66.92% 相对 `deadline_rc` 62.07% 是 **+4.85pp**（4.31pp 是相对 `torch_no_relay`）。按 seed 配对（5 seed）：`torch_lp − deadline_rc` = +4.85 ± 0.38pp，`torch_no_relay − deadline_rc` = +0.54 ± 0.33pp，`orbit_thermal − nearest` = −0.17 ± 2.0pp（来源 `satsim/docs/torch_paper_eval/runs.csv`，standard:aligned150）。即现有收益大部分来自准入闸门，Step 2「选对首星」暂无证据。
> - 建议在 Phase 0 与 Phase 1 之间先做 **Phase 0.5：同配额公平复跑**（`HANDOFF.md` 的 T3 + E4），结果出来再决定是否做 Phase 1-3 的目录级重构。
> - 本轮开发任务拆分见 [`HANDOFF.md`](HANDOFF.md)，任务目标见 [`TASK_BRIEF.md`](TASK_BRIEF.md)。

---

## 一、现状复盘：为什么之前选了“声明式”，做着做着又乱了？

项目早期在 `satsim` L1 层（`input/scenarios/base_*.yaml` + `exp_*.yaml` + `SPEC_PLUGIN_FRAMEWORK.md`）其实已经选对了**声明式配置 + 插件解耦**路线。之所以后续演变成“每次做新想法都像推倒重来”（目前 `satsim/scripts/` 下堆积了 17 个独立脚本、近 180 KB 代码，比核心引擎还重），根源不在声明式本身，而在于 **4 个没设对的工程断点**：

1. **`cosim` 演进时丢掉了组合式声明，退回硬编码校验**
   - `satsim/src/satsim/cosim/run.py` 另起了一套扁平 schema，既不支持 `base / defaults` 模板继承，又在 `REQUIRED` 中强行绑死了磁盘静态文件 `trace` 与 `scenario`。
   - 后果：像 `synth_multi_sso()` 这类内存参数化合成星座、或动态注入的 `PassBurst` / `AgenticTether` 根本写不进 `satsim-cosim` 的 YAML，逼着开发者绕开主入口去写 Python 脚本。
2. **声明式配置缺少“多维扫描（Matrix / Sweep）”与“并行指纹缓存”**
   - 科研日常需要跑 `策略 × 到达率 × 物理参数(R_th / S_tile / ISL带宽) × 随机种子` 的笛卡尔积，但原配置加载器只能单线程跑固定参数。
   - 结果每个新实验都在 `scripts/` 里各自手写 `ProcessPoolExecutor`、自定义 CSV 读写和打印表（如 `cosim_agentic_tether.py`、`exp_motivation_multi_sso.py`、`sweep_torch_knob_free.py`），甚至直接把新策略类 `KnobFreeTorch` 写死在脚本里，资产无法跨实验复用。
   - 同时脚本级 CSV 缓存仅按 `(mode, profile, seed, policy_name)` 判重，不校验策略源码哈希，导致底层算法重构后旧缓存未失效，出现代码与评估表脱节。
3. **双引擎两套世界（L1 `satsim.method` vs L2 `satsim.cosim`）割裂**
   - 两套 `World`、两套请求状态机、两套互不兼容的评价口径（L1 测切换后单步 `TPOT <= tpot_slo`；L2 测端到端 `t_delivered <= deadline`），并且引发了叙事冲突（L1 文档主张淡化显式 RC 热模型做参数化 `CCE-Net`，L2 报告主张强依赖一阶 RC 积分做无旋钮 `TORCH`）。
4. **策略插件边界未锁死，导致控制变量失守**
   - 声明式对比实验的前提是：**环境与系统配额由底座统一锁死，策略插件只能决定“分给谁（Placer）”和“怎么迁（Migrator）”**。
   - 当前代码中，`TorchRebalance` 在内部越权拦截了 `place()`（引入 `viable_slack_s=485.0` 暂缓低松弛慢请求准入），且与基线 `ThermalRebalance` (`deadline_rc`) 存在系统配额不对等：
     - 轮询间隔：`deadline_rc` 为 `30s`，`torch_lp` 为 `5s`；
     - 全局并发迁移上限：`deadline_rc` 为 `8`，`torch_lp` 为 `24`；
     - 单请求迁移上限：`deadline_rc` 为 `1`，`torch_lp` 为 `4`。
   - 现有 `docs/torch_paper_eval/summary.json` 数据显示：在 `standard:aligned150` 下，`deadline_rc` 为 `62.07%`，关掉准入接力与松弛门限的 `torch_no_relay` 为 `62.61%`（仅 `+0.54%`），开启 `pre_admission_relay + viable_slack_s=485` 的 `torch_lp` 为 `66.92%`（`+4.31%`）。必须把准入策略与重平衡配额拉平，才能得到经得起审稿推敲的净收益。

---

## 二、收敛后的唯一科研主线（Research Storyline）

抛弃“L1 一套故事、L2 另一套故事”的拼接模式，围绕**同一个真实且参数可控的太空仿真环境**，按单向因果链组织整篇工作：

1. **Step 1 — 问题诊断（只做初次分配 `migrator: none`）**
   - 在可控异构星座（如成像伴随影轨 + 晨昏全亮算力轨，叠加一阶 RC 自发热）下，评测地面常规初次分配（`nearest` / `round_robin` / `least_loaded`）。
   - 核心暴露三大病灶：
     1. **星间负载失衡**：空间跳数偏置 + 本影/热节流降频引发的暗星/热星队列积压（Jain 指数跌落、暗/亮队列比失衡）；
     2. **“带毒”的坏吞吐（Badput）**：慢星耗费宝贵的星载电力与热容（`C_th`）生成了大量最终超截止期作废的 token，不仅产出为 0，还推高结温触发 84°C 热节流，把同星正常请求一并拖死；
     3. **尾部延迟 `E2E P95` 崩塌**：落入阴影或热饱和节点的长序列请求造成严重长尾。
2. **Step 2 — 初次分配优化及其物理天花板（升级 `Placer`，仍锁死 `migrator: none`）**
   - 引入星历接触、供电段与热容裕度感知的初次分配器（`ephemeris` / `orbit_thermal`），量化“选对首星”能消除多少静态失衡、砍掉多少 `Badput` 与 `P95`。
   - 同时揭示其固有边界：当过顶突发（Pass Burst）到来导致可见邻星全部升温饱和，或超长推理运行中途跨入本影/断链时，仅靠初次分配仍残留显著 `Badput`。
3. **Step 3 — 受限星间链路下的运行期多跳流重平衡（锁死 `Placer` 与公平配额，升级 `Migrator`）**
   - 在严格对齐 `admission: fifo`、相同 `interval_s` 与相同 `max_inflight` 前提下对比：
     - `none`（不迁移基线）
     - `ideal_free`（无消耗瞬移，给出真实星座下的理论重平衡上限 C1）
     - `reactive`（进影/过热盲迁，暴露带宽争用与乒乓震荡代价 C2）
     - `one_to_one_rc`（单跳 1-to-1 热轨迹外部性迁移，暴露局部邻星热饱和瓶颈）
     - `torch_flow`（自研无旋钮 1-to-Many 多跳槽位边际流规划，将滞留负载向远端低温日照星疏散，把 `Badput` 转化为 `Goodput` 并削平 `P95`）
4. **Step 4 — 插件化场景泛化（零改参切换环境与业务插件）**
   - 保持上述调度器零改参，插拔替换场景插件验证普适性：
     - 切换 `orbitsim` 真实 Walker-53 / SSO2 接触迹线（联动 3D 可视化回放）；
     - 插入 `AgenticTether` 多模态原图切片回访插件（验证按回访代价自动涌现同心圆跳数分层与回传流量削减）；
     - 扫描受限激光链路带宽（如 `3 Gbps`）与散热热阻 `R_th`。

---

## 三、统一声明式架构设计（Target Architecture v2）

### 3.1 目录与职责分层

铁律：**`scripts/` 下严禁再写仿真循环、策略逻辑、指标计算或配置字典；一切实验通过声明式 `configs/suites/*.yaml` 驱动。**

```text
satsim/
├── src/satsim/
│   ├── core/                      # [稳定底座层：统一状态机、权威标尺与执行器]
│   │   ├── world.py               # 唯一仿真引擎（基于现 CoWorld，补齐 ideal_free 网络模式与静态拓扑支持）
│   │   ├── metrics.py             # 唯一指标与探针面板（Goodput / Badput / 无偏 E2E P95 / LoadProbe）
│   │   ├── registry.py            # 五维插件统一注册器与配置 Schema 校验
│   │   └── suite_runner.py        # 声明式矩阵执行器（多进程池 + 源码指纹缓存 + 标准 Markdown/JSON 报表）
│   └── plugins/                   # [五维可插拔扩展层：每次迭代只新增独立插件文件]
│       ├── traces/                # file (orbitsim导出) | multi_sso (内存合成) | walker | static_graph (原L1拓扑)
│       ├── physics/               # umbra_only | explicit_step | rc_thermal
│       ├── networks/              # ideal_free | fluid_maxmin (支持背景流与断链中断)
│       ├── workloads/             # poisson | pass_burst (过顶突发修饰器) | agentic_tether (原图回访修饰器)
│       └── schedulers/
│           ├── placers/           # nearest | rr | least_loaded | greedy | ephemeris | orbit_thermal
│           └── migrators/         # none | reactive | contact_aware | one_to_one_rc | torch_flow
├── configs/                       # [声明式配置层：模块化组合 + 实验矩阵单]
│   ├── envs/                      # 环境预设（硬件 + 拓扑源 + 物理温控 + 网络）
│   ├── workloads/                 # 负载预设（平稳流 / 过顶突发 / Agentic 多类别）
│   └── suites/                    # 论文图表一一对应的实验矩阵单（suite_01 ~ suite_04）
└── scripts/                       # 仅保留纯绘图与外部数据预处理脚本（只读 runs/ 产物，不 import simpy）
```

### 3.2 统一权威指标定义（`core/metrics.py`）

每次仿真运行默认挂载轻量探针并输出统一指标集，彻底消除不同脚本口径不一与幸存者偏差：

| 维度 | 字段名 | 方向 | 物理定义 |
|---|---|---|---|
| **负载分布** | `load_jains_index` | ↑ | 算力节点平均并发队列长度的 Jain 公平指数 |
| | `q_dark_over_lit` | ↓ | 本影期节点瞬时队列均值 / 日照期节点瞬时队列均值 |
| | `throttle_time_s` | ↓ | 全网算力星处于热节流降频状态的累计秒数 |
| **吞吐质量** | `goodput_tok_s` | ↑ | 按时完成且满足交付约束（`w.good(r) == True`）请求的有效生成速率（`tok/s`） |
| | `badput_tok_s` | ↓ | **坏吞吐**：已实际消耗算力生成、但因超截止期/未送达/中断而作废的 token 速率（$\sum_{r \notin \mathcal{G}} \text{gen}_r / T_{\text{win}}$） |
| | `waste_ratio` | ↓ | **算力浪费率**：`badput_tok_s / (goodput_tok_s + badput_tok_s)` |
| | `good_long_frac` | ↑ | 长序列推理请求的 SLO 达标率 |
| **尾部体验** | `e2e_p95_s` / `long_p95_s` | ↓ | **全量到达请求**的 P95 端到端延迟（未按时送达请求计入窗口封顶惩罚，杜绝只算已送达请求的幸存者偏差） |
| **网络开销** | `mig_GB` / `tether_GB` | ↓ | 跨星 KV 迁移总流量 / Agentic 原图锚点拉取总流量 |
| | `mig_abort` | ↓ | 因激光断链或传输超时中断的失败迁移次数 |

### 3.3 控制变量硬约束（Engine-Enforced Invariants）

为从机制上保证实验公平性，底座引擎强制执行以下边界：
1. **准入控制归属底座**：请求等待与准入顺序（默认 `admission: fifo`）由 `World` 统一执行。`Placer.place(world, req)` 仅允许在当前可达且显存足够的候选星中返回节点 ID；若需研究准入丢单策略，必须作为独立的 `AdmissionPlugin` 对所有对比组同等开启。
2. **重平衡系统配额归属环境**：`rebalance_interval_s`（如统一 `5.0s`）、`max_inflight_migrations`（如统一 `24`）、`max_migrations_per_req`（如统一 `4`）上提至环境级公共配置，所有 `Migrator` 共享同一预算。
3. **源码级缓存指纹**：`SuiteRunner` 的结果缓存键定义为 `sha256(resolved_run_config_json + git_blob_hashes_of_plugins_and_core + seed)`。任何相关源码或参数改动自动触发对应单元格重算，未改动基线秒级复用。

### 3.4 声明式 Suite YAML 样例

```yaml
# configs/suites/suite_02_rebalance_ablation.yaml
name: suite_02_rebalance_ablation
title: "可控异构 SSO 热-轨环境下分配与迁移正交消融"

compose:
  env: ../envs/multi_sso_rc.yaml          # 内含 trace: {kind: multi_sso, compute_ltans: [10.5, 13.5, 6.0], ...}
  workload: ../workloads/pass_burst.yaml  # 过顶集中释放负载

# 统一锁死的控制变量（所有对比策略强制共享）
invariants:
  admission: fifo
  rebalance:
    interval_s: 5.0
    max_inflight: 24
    max_per_req: 4

seeds: [1, 2, 3, 4, 5]

# 声明式对比矩阵（支持 list 展开与轴正交组合）
variants:
  place_nearest:      {placer: nearest,       migrator: none,          network: fluid_maxmin}
  place_rr:           {placer: rr,            migrator: none,          network: fluid_maxmin}
  place_orbit_therm:  {placer: orbit_thermal, migrator: none,          network: fluid_maxmin}
  rebal_ideal_free:   {placer: orbit_thermal, migrator: torch_flow,    network: ideal_free}
  rebal_reactive:     {placer: orbit_thermal, migrator: reactive,      network: fluid_maxmin}
  rebal_1to1_rc:      {placer: orbit_thermal, migrator: one_to_one_rc, network: fluid_maxmin}
  rebal_torch_ours:   {placer: orbit_thermal, migrator: torch_flow,    network: fluid_maxmin}

report:
  baseline: place_orbit_therm
  columns: [good_long_frac, goodput_tok_s, badput_tok_s, waste_ratio, long_p95_s, load_jains_index, mig_GB, mig_abort]
```

运行方式统一简化为：
```bash
# 运行单个论文实验矩阵（自动多进程 + 增量指纹缓存 + 生成 runs/<name>/summary.{json,csv,md}）
uv run satsim suite configs/suites/suite_02_rebalance_ablation.yaml

# 若需导出某个代表性种子的 3D 星历回放至 orbitsim/viz
python cosim.py run suite_02_rebalance_ablation --seed 1
```

---

## 四、分阶段实施 TODO 清单

### Phase 0：现状核对与基准问题清理（前置修正）
- [ ] **P0-1 修正流体网络 vs 存储转发回访时间公式**：在 `satsim/src/satsim/cosim/thermal_rebalance.py` 的 `_tether_extra_s` 中对齐 `FluidNet` 直通式带宽模型（传输耗时 `tile_bytes / bw` 不应重复乘以跳数 `hops`，仅传播时延 `hop_lat * hops` 乘跳数）。
- [ ] **P0-2 对齐 MILP 对拍脚本约束**：同步 `scripts/verify_torch_milp.py` 与去旋钮后的求解器物理约束（移除旧版硬编码 `max_b=2/3` 与残余未使用的 `max_src_out`），重新验证与 HiGHS 的精确吻合率。
- [ ] **P0-3 补齐 `satsim/pyproject.toml` 依赖声明**：将 `numpy`、`scipy` 纳入正式依赖（或 `optional-dependencies`），修复全新环境下脚本缺包问题。
- [ ] **P0-4 决定在途增量 KV（Delta-KV）建模口径**：明确迁移传输期间源星继续解码新生成的 token KV 是否在切换瞬间追加尾流传输，或在文档中明确其近似假设边界。

### Phase 1：统一标尺、正交策略收编与声明式 `SuiteRunner`（核心骨架）
- [ ] **P1-1 实现统一 `core/metrics.py`**：整合 `record.summarize` 与 `probe.LoadProbe`，新增 `badput_tok_s`、`waste_ratio`、无幸存者偏差的全量 `e2e_p95_s` / `long_p95_s`。
- [ ] **P1-2 支持 `network: ideal_free` 无消耗迁移模式**：在 `CoWorld` 中支持 0 耗时瞬移网络插件，使真实星座实验可直接测算理论重平衡上限（C1）与真实带宽回吐（C2）。
- [ ] **P1-3 完成全量 `Placer × Migrator` 正交收编**：
  - 将 `OrbitLoad` (`orbit_thermal`)、`ThermalRebalance` (`one_to_one_rc`)、纯物理无旋钮版 `TorchRebalance` (`torch_flow`) 全部接入统一正交注册表；
  - 从 `TorchRebalance.place()` 剥离 `viable_slack_s` 准入筛单；将 `pre_admission_relay` 拆分为显式可独立开关的消融项；
  - 将 `interval_s`、`max_inflight`、`max_mig_per_req` 上提为统一 `invariants` 参数。
- [ ] **P1-4 实现 `core/suite_runner.py` 与 `satsim suite` CLI**：支持 `compose` 多文件合并、`variants / matrix` 笛卡尔积展开、`ProcessPoolExecutor` 并行、源码哈希缓存及符合 `AGENTS.md` 规范的 Markdown 结果表自动生成。

### Phase 2：五维场景插件化与 4 张核心论文实验单落地
- [ ] **P2-1 Trace 插件化**：支持在 YAML 中直接声明 `trace: {kind: file | multi_sso | walker | static_graph, ...}`，将 `synth_multi_sso` 与原 L1 静态拓扑（四星环、跨轨瓶颈边 `E★`）统一封装为 `Trace` 生成插件。
- [ ] **P2-2 Workload 修饰器插件化**：将 `release_burst`（过顶突发）与 `agentic_classes`（多模态锚点回访）规范化为可叠加的声明式负载配置块。
- [ ] **P2-3 编写并跑通 4 份主线 `configs/suites/suite_01..04.yaml`**：
  - `suite_01_place_only_diagnosis.yaml`（初次分配失衡、`Badput` 与 `P95` 诊断）
  - `suite_02_placer_optimization.yaml`（天基感知初次分配收益与突发饱和边界）
  - `suite_03_rebalance_fair_ablation.yaml`（同配额下 `none / free / reactive / 1-to-1 / torch_flow` 严格单变量消融）
  - `suite_04_scenario_generalization.yaml`（`orbitsim` 真实轨迹、`AgenticTether` 切片扫描、窄带 ISL 与热阻 `R_th` 敏感度）
- [ ] **P2-4 联动外层 `satcosim/cosim.py`**：支持从 `suite_*.yaml` 指定代表性策略组一键导出 `orbitsim/viz/public/playback/*.json` 并通过 `cosim.py check` 溯源校验。

### Phase 3：收尾清理、文档对齐与防退化门禁
- [ ] **P3-1 归档与瘦身 `satsim/scripts/`**：删除已被 `suites/*.yaml` 替代的十余个散装仿真脚本，仅保留纯绘图脚本。
- [ ] **P3-2 退役或桥接旧 `satsim/src/satsim/method/`**：确认 `static_graph` 插件覆盖原 L1 黄金测试后，合并双引擎代码，消除重复维护。
- [ ] **P3-3 同步主文档与 `AGENTS.md` 开发铁律**：重写 `satsim/README.md` 与 `TORCH_PAPER_REPORT.md` 使其 100% 源自 `suite_01..04` 自动生成的汇总表；在 `AGENTS.md` 写入“禁止新增独立仿真脚本、新增实验必须走 `plugins + suites`”的门禁规范，并在 `pytest` 中加入架构合规测试（检查 `scripts/` 未定义 `Policy` 子类或直接实例化 `World`）。

---

## 五、请 Reviewer 重点拍板的 5 个问题（Open Questions）

1. **默认主实验场选择**：论文前两节的主默认星座，优先用参数可控性最强的 **`Multi-SSO`（成像影轨 + 晨昏亮轨）**，还是 `orbitsim` 导出的 **`coop-w53`（Walker 53° 4×10 + 3 RS）**？（另一方作为第 4 节泛化插件对照）。
2. **未完成请求的 `E2E P95` 计分规则**：对仿真窗口结束仍未送达或超时的请求，计算全量 `P95` 时是统一按 `horizon - r.t` 计入，还是按固定惩罚值（如 `2 × deadline`）封顶？
3. **`CCE-Net` 的去留定位**：合并单引擎后，原 L1 的 6 维参数化打分器 `CCE-Net` 是彻底归档退役（统一聚焦无旋钮物理流规划 `TORCH`），还是保留在 `migrators/` 中作为一个轻量启发式对比基线？
4. **准入控制（Admission）策略**：主实验是否严格统一锁死为无丢单 `FIFO`（以纯粹测算分配+迁移把 `Badput` 变 `Goodput` 的能力），而将“超时前主动拒单（Admission Shedding）”留作讨论或独立插件？
5. **`Delta-KV` 传算重叠精度**：是否在 Phase 0 顺手补齐“迁移传输期间新生成 token 的增量 KV 尾流计费”，以彻底堵住传算重叠建模的审稿漏洞？
