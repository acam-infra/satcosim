# HANDOFF：satsim 阶段一/阶段二开发任务（给编码模型）

> 版本 2026-11-11 · 来源 LAB-1779（gjam）· 研究入口 LAB-1466
> 仓库：`https://github.com/acam-infra/satcosim`（含子模块 `satsim`、`orbitsim`），基线提交 `cb8d4278`
> 先读：同目录的 [`TASK_BRIEF.md`](TASK_BRIEF.md)（目标）和 [`TERMS_AND_MODEL.md`](TERMS_AND_MODEL.md)（术语）。**术语以它为准，读不懂先停下来问，不要自己猜。**

---

## 0. 你要做的事（一句话）

在现有 `satsim.cosim` 数值仿真上，补齐「阶段一劣化指标」和「阶段二往日照凉星迁移」所需的最小代码，让后续实验能用 YAML 配置跑出**同配额、按 seed 配对**的对比表。**不重写引擎，不做大重构。**

## 1. 铁律（每个任务都要遵守）

1. **默认行为不变**：所有新功能默认关闭。不加新配置项时，现有配置跑出来的已有指标必须**逐字段完全一致**（新增字段可以多出来）。验收方法见 §3。
2. **不动 L1**：除 T9 外，不改 `src/satsim/method/` 下任何文件。
3. **不新增仿真脚本**：`scripts/` 下不新增文件。实验一律用 YAML + `satsim-cosim` 或 T5 的 `satsim-suite` 跑。
4. **术语**：代码、注释、文档里不写「阴影」「shadow」。用 `eclipse`（= `is_dark`，日影，迁出源）和 `cool`（凉星，迁入目标）。
5. **数字不手抄**：文档和 PR 描述里的每个数字，都必须来自本次运行的原始输出（CSV/JSON），并写明文件路径。不允许估算、编造或「大约」。
6. **一个任务一个分支一个 PR**，PR 标题 `satsim: T<n> <简述>`。子模块默认是游离 HEAD，先 `cd satsim && git switch main && git pull && git switch -c t<n>-<slug>`。
7. **测试**：每个任务都要新增 pytest 用例，并保证 `uv run pytest -q` 全绿。
8. **卡住就停**：遇到下列情况停下来，在 PR 或 issue 里写清楚问题，不要绕过：需求有歧义、需要改 L1、默认行为对不上、测试原本就是红的。


## 1.5 插件化约定（本轮的边界）

任务说明要求「环境与策略解耦、像插件一样替换」。本轮**不做**目录级大重构（`core/` + `plugins/`，见 `ARCHITECTURE_AND_TODO.md` Phase 1-3），而是在现有结构上把插件边界钉死，后续重构时直接平移：

| 插件维 | 接口（已存在） | 注册 / 选择方式 | 本轮新增 |
|---|---|---|---|
| 初次分配 Placer | `place(w, r) -> node \| None`，在 `CoWorld._life` 里调用（`world.py` L206） | `policies.PLACERS`，YAML `{place: nearest}` | — |
| 再分配 Migrator | `rebalance(w) -> None`，每个 `control_period_s` 调用（L194），通过 `w.migrate(r, dst)` 发起迁移 | `policies.MIGRATORS`，YAML `{place: nearest, migrate: cool_aware}`，由 `CompositePolicy` 组合 | T7 `cool_aware` |
| 负载 Workload | `make_requests(cfg, trace, seed)` 读 `workload:` 块 | 配置键：`source_rates_per_min`（局部性）、`release_burst`（过境突发）、`agentic_classes` | T4 热点配置 |
| 环境 Trace | `Trace`（日影区间、链路、可达性） | `trace:` 指向 orbitsim 导出文件；`synth_multi_sso` 内存合成 | — |
| 物理 Physics | `thermal:` 块（RC 热模型，可省略）、`power.P_dark`（日影限频） | 配置键 | T9 分档热沉（可选） |
| 网络 Network | `FluidNet`（max-min 带宽分享） | `net.link_gbps` | T6 尾流 KV |
| 公平约束 | — | `rebalance_invariants`（T3），由 `run_one` 注入每个策略 | T3 |

规则：
1. **新策略 = 新类 + 注册表一行**。不准在 `world.py` 里按策略名写 `if/else`。
2. **策略只读状态、只通过 `w.migrate()` 动作**。读状态用 T1 的 `is_eclipse / is_hot / is_cool / thermal_headroom_C`、`w.iter_of`、`w.tr.*`、`w.net`；不准直接改 `w.nodes`、温度或 `w.acc`。
3. **环境新特性 = 新配置键，默认关闭**（T6、T9 同理）。
4. **配额和准入不属于策略**：迁移配额走 `rebalance_invariants`，准入闸门（`viable_slack_s`、`pre_admission_relay`）作为显式开关，做消融时要能套到所有对比组。
5. 目录级重构（`core/` + `plugins/`）、`trace.kind` 插件、`ideal_free` 网络，等 E4 结果出来、研究负责人给 go 之后再按 RFC 做。

## 2. 代码地图（只列你会碰的）

| 文件 | 关键位置 | 作用 |
|---|---|---|
| `satsim/src/satsim/cosim/world.py` | `CoWorld.__init__`、`f_of`、`_thermal_tick`、`_control`、`_migrate`（约 L324）、`good`、`make_requests` | 仿真世界：节点状态、热模型推进、迁移、请求生成 |
| `satsim/src/satsim/cosim/record.py` | `summarize`（L57） | 每次运行的指标汇总 |
| `satsim/src/satsim/cosim/run.py` | `REQUIRED`、`load_config`、`run_one`、`run` | 读配置、跑 policy × seed |
| `satsim/src/satsim/cosim/policies.py` | `MAX_INFLIGHT=8`、`MAX_MIG_PER_REQ=2`（L28-29）、`PLACERS`、`MIGRATORS`、`make_policy` | 分配器 / 迁移器注册 |
| `satsim/src/satsim/cosim/thermal_rebalance.py` | `ThermalRebalance`（L12，`interval_s=30`，在途上限用 `MAX_INFLIGHT=8`，单请求迁 1 次写死在 L78）、`ThermalForecast`（L119）、`TorchRebalance`（L216，`interval_s=5, max_inflight=24, max_mig_per_req=4, viable_slack_s=485, pre_admission_relay=True`） | 热感知迁移策略 |
| `satsim/src/satsim/cosim/trace.py` | `is_dark`、`power_segments`、`path`、`next_conn`、`horizon` | 星历：日影区间、链路、可达性 |
| `satsim/configs/cosim_placement_thermal.yaml` | `thermal:` 块 | 带热模型的参考配置，新配置从它复制 |
| `satsim/scripts/cosim_agentic_tether.py` | `std_policies` | 生成 `docs/torch_paper_eval/` 的脚本，用来对照 policy 写法（不要改它） |

## 3. 通用验收：默认行为回归检查

**每个任务开工前**先在 `main` 上跑一次，存基线：

```bash
cd satsim
uv sync
uv run pytest -q 2>&1 | tail -3                     # 记下结果
uv run satsim-cosim configs/cosim_placement_thermal.yaml --out /tmp/base_pt
uv run satsim-cosim configs/cosim_coop_w53_v1.yaml   --out /tmp/base_w53
```

改完后，用同样的命令输出到 `/tmp/new_pt`、`/tmp/new_w53`，然后对比两边的 `summary.json`（`run.py` 写在 `--out` 目录下）：除 `wall_s` 这类耗时字段外，已有字段逐个相等才算通过，新增字段可以忽略。对比脚本写在 `tests/` 的临时测试里，或者直接用一行 python 跑，**不要放进 `scripts/`**。

---

## 4. 任务清单（按顺序做，T1→T7 必做，T8 跑实验，T9 可选）

### T1 节点状态辅助函数（术语落地）

- 在 `CoWorld` 上新增：
  - `thermal_headroom_C(j) -> float`：`T_throttle_C − 当前温度`；没开热模型时返回 `math.inf`。
  - `is_eclipse(j, t=None) -> bool`：等价于 `self.tr.is_dark(j, t)`，只是换个名字。
  - `is_hot(j) -> bool`：`self.thermal_f[j] < 1.0`。
  - `is_cool(j, margin_C) -> bool`：`not is_hot(j) and thermal_headroom_C(j) >= margin_C`。
- 读温度用 `DynamicThermal` 已有的接口（看 `src/satsim/method/policies/thermal/dynamic.py` 的 `temperature(j)`），**只读不改**。
- 测试：构造一颗日影星和一颗热星，断言四个函数的返回值。
- 验收：§3 回归通过。

### T2 指标：坏吞吐、浪费率、全量 P95

在 `record.summarize` 里**新增**以下字段，已有字段一个都不动：

| 字段 | 定义 |
|---|---|
| `badput_tok_s` | `sum(r.gen for r in rs if not w.good(r)) / window` |
| `waste_ratio` | `badput / (goodput_gen + badput)`，其中 `goodput_gen = sum(r.gen for r in good)`（分子分母都用 `gen`，口径一致） |
| `undelivered_frac` | 未送达请求数 / 全部请求数 |
| `e2e_p95_all_s` | 全部请求的 P95；未送达的按 `horizon − r.t` 计 |
| `long_p95_all_s` | 同上，只算长请求 |
| `throttle_s` | 各算力星处于热降频状态的累计秒数（在 `_thermal_tick` 里按 `control_period_s` 累加；没开热模型时为 0） |

- `horizon` 用 `w.tr.horizon`。
- 在 `run.load_config` 里加一条**警告**（不报错）：`trace.horizon − arrival_window_s < long_deadline_s` 时打印 warning，说明长请求可能没机会完成，P95 被删失主导。
- 测试：手造 3 个请求（按时送达 / 超时送达 / 未送达），断言 6 个字段的值。

### T3 公平配额与准入闸门的配置化

目标：所有对比策略能共用同一组迁移配额；TORCH 的准入部分能单独开关。

- 新增可选配置块（默认不出现 = 行为不变）：
  ```yaml
  rebalance_invariants:
    interval_s: 5.0
    max_inflight: 24
    max_mig_per_req: 4
  ```
- `ThermalRebalance.__init__` 新增参数 `max_inflight: int | None = None`、`max_mig_per_req: int | None = None`。为 `None` 时保持现状：全网在途迁移上限用 `policies.MAX_INFLIGHT`（=8），单请求只允许迁 1 次（现在是 L78 的 `or r.n_mig` 写死的，要改成 `r.n_mig >= self.max_mig_per_req`，默认值 1）。
- `policies.py` 里用到 `MAX_INFLIGHT` / `MAX_MIG_PER_REQ` 的迁移器（`Reactive`、`ContactAware`）同样改成可传参，默认值不变。
- 在 `run.run_one` 里：如果配置有 `rebalance_invariants`，把三个值注入每个 policy spec（`thermal_rebalance`、`torch_rebalance` 和 `place`+`migrate` 组合形式都要覆盖）。**如果某个 policy spec 自己显式写了同名参数且值不同，直接报错**，不要静默覆盖。
- TORCH 的 `viable_slack_s` 和 `pre_admission_relay` 保持现有参数名，在 docstring 里写明它们属于「准入闸门」。
- 测试：
  1. 不写 `rebalance_invariants` 时，三个策略对象的配额等于原默认值；
  2. 写了之后三者一致；
  3. 冲突时抛异常。

### T4 阶段一热点场景配置

- 新建 `configs/cosim_hotspot_v1.yaml`：从 `cosim_placement_thermal.yaml` 复制，`name` 改成 `cosim_hotspot_v1`。
- 用 `workload.source_rates_per_min` 设置不均匀到达率（数组长度 = trace 里 RS 的个数，先从 trace JSON 读出来）。默认让第一个 RS 的到达率是其余的 4 倍，总到达率和原配置持平。
- `policies:` 只放阶段一基线：`round_robin`（`round_robin_all`）、`nearest`、`random`。
- 跑 5 个 seed，把 T2 的新字段贴进 PR 描述（附原始输出路径）。**不要为了让数字难看去调参数**；参数改动都要在 YAML 注释里写理由。

### T5 最小 suite 执行器

新增 `src/satsim/cosim/suite.py`，在 `pyproject.toml` 的 `[project.scripts]` 注册 `satsim-suite = "satsim.cosim.suite:main"`。

输入 YAML 格式：

```yaml
name: e4_fair_quota
base: ../cosim_placement_thermal.yaml   # 相对 suite 文件
seeds: [11, 12, 13, 14, 15]
set:                                    # 对所有单元格生效，语法同 --set
  rebalance_invariants: {interval_s: 5.0, max_inflight: 24, max_mig_per_req: 4}
axes:                                   # 可选，笛卡尔积展开
  net.link_gbps.inter: [10.0, 1.0, 0.3]
policies:                               # 覆盖 base 的 policies
  orbit_thermal: {policy: orbit_load}
  deadline_rc: {policy: thermal_rebalance, placement: {policy: orbit_load}, thermal_aware: rc}
report:
  baseline: orbit_thermal
  metrics: [good_long_frac, goodput_tok_s, badput_tok_s, waste_ratio, long_p95_all_s, migrations, mig_abort, mig_GB]
jobs: 8
```

行为：
- 复用 `run.load_config`、`run.run_one`、`summarize`，**不复制仿真逻辑**。
- 用 `ProcessPoolExecutor(jobs)` 并行跑 `axes 组合 × policy × seed`。
- 输出到 `runs/<name>/`：
  - `runs.csv`：每行一个 (axes 取值, policy, seed) 及全部指标；
  - `summary.md`：对每组 axes 取值，列出各 policy 相对 baseline 的**按 seed 配对**差值，格式 `均值 ± sd (n)`。
- 不做缓存。
- 测试：用一个极小配置（1 个 seed、很短的 `arrival_window_s`）跑通，断言 CSV 行数 = 组合数 × policy 数 × seed 数。

### T6 尾流 KV（Delta-KV）

- 新增配置项 `migration.delta_kv: false`（默认关）。
- 打开时，在 `CoWorld._migrate` 里：主 KV 流 `f.done` 之后，计算传输期间源星新增的 token 数 `Δ = r.gen(当前) − r.gen(开始时)`，再发一条 `Δ × bpt` 字节的尾流（同一条路径、同样受 `mig_timeout` 约束）。最多补两轮，第二轮之后剩下的增量直接计入切换。
- 尾流字节计入 `acc["mig_bytes"]`；新增计数 `acc["delta_kv_bytes"]`，并在 `summarize` 里输出 `delta_kv_GB`。
- 测试：低带宽配置下打开开关，断言 `delta_kv_GB > 0`，且 `mig_GB` 比关闭时大。

### T7 `cool_aware` 迁移器（阶段二第一版）

在 `policies.py` 新增类 `CoolAware`，注册进 `MIGRATORS["cool_aware"]`，可以和任意 placer 组合（`{place: nearest, migrate: cool_aware}`）。

每个控制周期：
1. **选源**：解码中的请求，所在星满足 `is_eclipse(j)`，或 `power_segments` 显示 `lead_s`（参数，默认 60）内会进入日影，或 `is_hot(j)`。按截止期余量从小到大排序。
2. **选目标**：候选 = `not is_eclipse(k) and is_cool(k, cool_margin_C) and fits(k, r)`，`cool_margin_C` 默认 10。
3. **打分**（这就是算-传权衡）：
   `est_finish(k) = t_transfer(r,k) + t_decode_remaining(r,k) + t_return(k)`，其中
   - `t_transfer = r.kv*bpt / 路径瓶颈带宽 + hop_lat*跳数`，瓶颈带宽用 `FluidNet` 当前分到的速率估计（参考 `thermal_rebalance.py` 的 `edge_users` 写法）；
   - `t_decode_remaining`：用 `w.iter_of(k, extra=r)` 乘剩余 token，再结合 `power_segments(k, ...)` 处理途中进日影的部分（参考 `policies.py` L70-74 的写法）；
   - `t_return = tr.next_conn(r.origin, k, 解码结束时刻) − 解码结束时刻`。
   和「留在原地」的 `est_finish(src)` 比，**只有在省下的时间 ≥ `min_gain_s`（默认 30）时才迁**。
4. 遵守 T3 的配额：`max_inflight`、`max_mig_per_req`、`interval_s`；另外每颗目标星每周期最多接收 1 个迁入（防止扎堆）。

不要做：多跳分流优化、MILP、学习型打分。这些是研究者的工作，不在本任务范围。

测试：构造一颗日影源星和两个目标（一个日照凉星、一个日照热星），断言请求迁往凉星；把链路带宽调到极低时，断言不迁。

### T8 实验配置（用 T5 跑，结果原样贴回）

在 `configs/suites/` 下新建以下文件，跑完把 `summary.md` 和 `runs.csv` 路径贴到 PR：

| 文件 | 目的 | 要点 |
|---|---|---|
| `e1_stage1_hotspot.yaml` | 阶段一劣化 | base = T4；`round_robin` / `nearest` / `random` / `orbit_thermal`；看坏吞吐、全量 P95、`throttle_s` |
| `e3_bw_kv_sweep.yaml` | 算-传权衡出现在哪 | `axes: net.link_gbps.inter: [10, 3, 1, 0.3]`、`net.link_gbps.intra` 同步；`migration.delta_kv: true`；policy：`nearest+none`、`nearest+reactive`、`nearest+cool_aware` |
| `e4_fair_quota.yaml` | 同配额公平对比 | `set.rebalance_invariants` 统一为 5/24/4；policy：`orbit_thermal`、`deadline_rc`、`torch_no_relay`（`pre_admission_relay: false, viable_slack_s: 0`）、`torch_lp`、`orbit_thermal+cool_aware`；seed 用 11-15，和 `docs/torch_paper_eval` 对齐 |

**只报数字，不写结论**。结论由研究者写。

### T9（可选，需先问）分档热沉温度

- `thermal.T_amb_sunlit_C` / `thermal.T_amb_eclipse_C`，缺省都等于 `T_amb_C`。
- 这需要改 L1 的 `DynamicThermal`（让 `T_amb` 能按节点按时刻取值），**动手前先在 issue 里确认**，并保证 L1 的 `tests/test_golden.py` 不变。

---

## 5. 交付格式（每个 PR 描述照这个写）

```
## 做了什么
- …

## 默认行为回归
- 命令：…
- 结果：已有字段全部一致 / 不一致的字段：…

## 测试
- uv run pytest -q：<原样贴最后 3 行>

## 新数字（如有）
- 来源文件：runs/<name>/runs.csv
- <表格>

## 没做 / 有疑问
- …
```
