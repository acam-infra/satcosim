# HANDOFF_SATPLAN：Multica 总控推进、Review 门禁与研发交接规范

> 适用：`acam-infra/satcosim` 主仓与 `satplan/`（`acam-infra/satplan`）`r3` 干净架构主线（主追踪票 **`LAB-2004`**，项目 `科研 · Satellite` `75c795bb-8da2-43f6-b743-2caf76371132`）。  
> 旧版 `satsim` T1–T9 交接仍见 [`HANDOFF.md`](HANDOFF.md)（只读基线，不动 `satsim/` / `orbitsim/`）。  
> 必读配套：[`AGENTS.md`](../AGENTS.md)、[`CODING_STANDARDS.md`](../CODING_STANDARDS.md)、[`GLOSSARY.md`](../GLOSSARY.md)、[`BRANCHING.md`](BRANCHING.md)、[ADR-0001](adr/0001-satplan-r3-clean-submodule.md)、[ADR-0002](adr/0002-rs-downlink-toggle.md)。

---

## 0. 职责边界：Multica 原生总控闭环

研发协调与质量门禁统一运行在 **Multica 平台**（主控入口 `LAB-2004`），脱离本机终端持续轮询：

| 角色 | 运行载体 | 核心职责 |
|---|---|---|
| **总控与审计者（Orchestrator & Reviewer）** | `LAB-2004` 绑定的 **`cc · hydrogen-4 · gu20x · agy`**（`a2bb5e27-0863-4876-80dc-c2e6ba041f96`） | 按 Stage Barrier 放行并派发子票；利用 `multica issue wakeup` 事件驱动等待子票进入 `in_review`；拉取 PR 执行 4 项硬性 Review 门禁；打回缺陷或 Squash Merge 合入 `satplan/main`；同步更新 `satcosim` 子模块指针并推进下一阶段。 |
| **子票实现者（Stage Workers）** | 各阶段子票（`LAB-2005`..`LAB-2009`），统一派 **`cc · hydrogen-4 · gu20x · agy`**（不使用易 EOF 断流的 `carbon`） | 在独立 `feat/lab<id>-*` 分支严格按单票边界编码、补充独立物理/Seam 单测、通过 `pytest` 与根目录 `cosim.py lint` 后提交 Ready PR 并切 `in_review`。 |

**身份与凭据约定（`cc` 环境）**：
- `git-credential-gh-multi` 自动将 `acam-infra/*` 路由至 `fumayulaa`（拥有 `satcosim` 与 `satplan` `push / admin` 权限）。
- 仓库配置 `git config user.name fumayulaa`、`git config user.email fumayula@gmail.com`；执行 `gh pr create / merge / view` 时传 `GH_TOKEN="$(gh auth token -u fumayulaa)"`。

---

## 1. 模型与工程铁律（Worker 与 Reviewer 共守）

1. **物理与目标不变量**：
   - **日照 (Sunlit)**：太阳翼无限供能上限，受离散/连续热模型 **`T_max`（一阶线性 RC）** 制约；
   - **日影 (Eclipse)**：累积 **DoD 电量约束 (`eclipse_dod_budget_j`)**，`sum P_jt * dt <= E_DoD`，出影回到日照后自动满额恢复；**不设总能耗最小化目标**；
   - **Store-and-Run 零丢弃**：支持 **挂起 (Suspend)**（`h_rjt`，`0W` 计算并保留完整 KV，严禁丢弃/驱逐请求）与 **累计传完解锁 (Cumulative Unlock)**（`u_rjt`，双端占压 KV 直至累计收到 `S_r^kv` 字节）；
   - **下行开关 `rs_downlink: false`（默认关闭，[ADR-0002](adr/0002-rs-downlink-toggle.md)）**：CS 解码完成即结束请求（`t_delivered = t_decoded`），剥离末端 `next_conn` 几何噪声；显式置 `rs_downlink: true` 才恢复回传/流式卡顿路径；
   - **观察 Seam 严密隔离**：`LocalStateView` 严禁暴露 `trace`、`power_segments`、`next_conn`、`eclipse` 等未来轨线属性，只有 `ForecastView` 才提供 $H$-slot 预知视图。
2. **目录与术语纪律**：
   - 禁止修改 `satsim/` 与 `orbitsim/` 源码；
   - `GLOSSARY.md` 规范：禁用词（`阴影`、`shadow`、`dark=cool`、`丢包/丢弃/抢占/驱逐`、`边传边算`、`恒定暗态降频`）必须 **0 命中**。
3. **数据真实与单一事实源**：
   - 所有指标数字必须来自当前分支或合并后的真实命令行输出，写清配置（如 `configs/w53_baseline.yaml`）、`rs_downlink` 状态与 `seeds`；不得手抄或沿用合并前旧数字。
   - 遵循 `.agents/skills/` 内项目级技能约定（`tdd`、`code-review`、`diagnosing-bugs`、`domain-modeling`、`pr`）。

---

## 2. 总控工作流（Orchestrator 推进 & Event Wakeup 循环）

总控 Agent 每次被唤醒（首次启动、子票状态事件触发、`wakeup` 超时兜底或人工指令）按以下 **Step A → D** 推进：

### Step A：检查全局看板与 Stage Frontier
1. 运行 `multica --profile gjam issue children LAB-2004 --output json` 查看所有子票（Stage 1–4）状态与 `Blocked by:` 依赖。
2. 对已阻塞解除、仍处于 `backlog` 的下一阶段子票（Stage `N` 需前一 Stage `< N` 全部为 `done` 或 `cancelled`）：
   - 先核对本地/远端 `satplan/main` 与 `satcosim/main` 已含前序合并提交，避免后阶段从旧基线切分支；
   - 更新子票基线说明（如最新 `main` commit）后置 `todo` 并指派 `--to-id a2bb5e27-0863-4876-80dc-c2e6ba041f96`（`cc · hydrogen-4 · gu20x · agy`）。
3. **巡检活跃子票**：对处于 `todo` / `in_progress` 的子票，检查 `multica --profile gjam issue runs <id>` 与末尾 `run-messages`：
   - 若连续多轮报 `API error ... EOF` 或停滞无进展（`msgs` 长时间未增）或越界改 `satsim/`，立即 `issue cancel-task` 终止异常 run 并重派；
   - 若正常工作，禁止发冗余评论打断。

### Step B：注册事件唤醒（零空转等待）
派发或等待子票进入 `in_review` 时，禁止在本机终端空转轮询——直接在总控票 **`LAB-2004`** 上挂载 **Multica 原生条件唤醒**：

```bash
# 示例：等 Stage 2 的 LAB-2007 进入 in_review（带 45m 超时兜底，防静默卡死）
multica --profile gjam issue wakeup create LAB-2004 \
  --until-issue LAB-2007 \
  --until-issue-state in_review \
  --expires-in 45m \
  --on-timeout wake \
  --instruction "LAB-2007 已进 in_review（或超时兜底）：拉取 PR #2 跑 4 项 Review 门禁并合并/打回。"
```

若使用阶段性 `--every` 巡检唤醒且本轮核查一切正常还在运行中，调用 `multica --profile gjam issue wakeup checkin` 静默结束本轮，不产生评论噪音。

### Step C：4 项硬性 Review 门禁（比照 `.agents/skills/code-review`）
任一子票到达 `in_review`、PR 就绪后，总控**不得凭自述直接合入**，必须拉取 PR 分支到干净目录依次复验：

1. **作用域与全仓库规范门禁**：
   - `git diff origin/main...HEAD --name-only` 确认无 `satsim/` / `orbitsim/` 改动；
   - **从 `satcosim` 根目录**执行 `python3 cosim.py lint satplan/src satplan/tests`（务必从根目录触发 `known-first-party`，确认 **0 ruff 错误 / 0 禁用词命中**，避免仅在 `satplan/` 目录运行漏掉 `I001` import 排序问题）。
2. **Seam 与架构规范核查（[`CODING_STANDARDS.md`](../CODING_STANDARDS.md)）**：
   - `PowerThermalModel` 须经不可变 `PhysicsParams`（`.from_config`）构造，内部不保留裸 `cfg` 字典，无重复选档/重置代码；
   - `LocalStateView` 与 `ForecastView` 严格隔离；空节点 / DoD 耗尽节点 `clock_f == 0.0` 时，`LocalStateView.iter_of` 不能触发 `ZeroDivisionError`；
   - `CompositePolicy` 与 `PlanAction / CoWorld.apply_plan` 为单一迁移/调档执行通道；在途迁移计数与防重入标志必须在发起 `env.process(...)` **之前同步置位**；
   - `rs_downlink` 默认 `False`、`orbit_thermal` 在无回传时直接以 `t_dec` 评分，无热循环读配置。
3. **物理边界与并发状态机审计（已踩坑必查项）**：
   - **DoD / `T_max` 边界零滞后**：区间结算须先按旧日照/日影状态把 `[last_t, now]` 结算至 `now` 再调 `on_eclipse_change`（防日照耗电漏扣进新日影 DoD），并以 **post-step `current_op()`** 决定是否 `wake_node(j)`（防 1 个控制周期 2s 超支）；
   - **迁移状态机安全**：`trace.path is None` 先判后占 KV（防断链锁死）；迁移完成解锁前检查 `r.state == "decode"`（防源端提前完成引发 `_detach_node` `ValueError` 并释放 `reserved[dst]`）；`hop_lat` 等待全程保持 `mig_in_flight` 占位防重复派流；多时隙传输防 `FluidNet` `1.0B` 截断死锁；
   - **节点级 `_node_decode_loop` 与 R3 MILP 边界**：无回退至逐请求 `poke()` 中断风暴；MILP 单元测试必须含独立物理/解析例子验证（不得拿简化公式互证）。
4. **本地全量实测复跑**：
   - `cd satplan && uv run pytest -v` 全部通过（含前序阶段回归单测 + 本票新增 Seam/边界测试）；
   - 涉及调度对比或性能变更时，本地复跑 `configs/w53_baseline.yaml`（`seeds=[1]`）或对应 `3 × 2` / `3 × 3` 套件，确认数值与 PR 描述一致。

### Step D：打回修复或 Squash Merge + 推进下一阶段
- **任一门禁不通过（含 CRITICAL / Lint 错误 / 回归缺失）**：
  1. 在对应子票评论给出带 `file:line`、复现机制与必补单测清单的审阅意见，明确要求**在原 PR 分支追加修改推送（不新开 PR、不自行合并 `main`）**；
  2. 将子票状态切回 `todo` 触发原 worker 修复，并在 `LAB-2004` 重新注册 `wakeup` 等该子票再次 `in_review`。
- **全部门禁通过**：
  1. Squash Merge PR：`GH_TOKEN="$(gh auth token -u fumayulaa)" gh pr merge <num> --repo acam-infra/satplan --squash --delete-branch`；
  2. 在子票评论记录合并 commit SHA 与实测摘要，置 `multica --profile gjam issue status <id> done --no-start`；
  3. 同步 `satcosim` 的 `satplan` 子模块指针（`git add satplan && git commit`）并推至 `origin/main`；
  4. 按 **Step A** 放行下一 Stage：
     - Stage 2（`LAB-2006` + `LAB-2007`）全部 `done` → 放行 Stage 3（`LAB-2008`: 纯数据 `R3Problem -> R3Solver -> PlanAction`）；
     - Stage 3（`LAB-2008`）`done` → 放行 Stage 4（`LAB-2009`: `ProblemBuilder` + `r3_milp` + `SuiteRunner` `3 × 3 × multi-seed`）；
     - Stage 4（`LAB-2009`）合并完成且全仓 `python cosim.py lint`、`python cosim.py test` 通过、区分度与敏感度表齐全 → 在总控票 `LAB-2004` 输出最终 `3 × 3` 对比结果与敏感度结论，将 `LAB-2004` 置 **`in_review`** 呈报人工终审。
