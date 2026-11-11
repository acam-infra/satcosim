# 分支与进度同步约定

> 适用：`acam-infra/satcosim`、`acam-infra/satsim`、`acam-infra/orbitsim` 三个仓库。2026-11-11 起执行。
> 配套：任务编号来自 [`HANDOFF.md`](HANDOFF.md)（T1–T9、E1/E3/E4）和 [`ARCHITECTURE_AND_TODO.md`](ARCHITECTURE_AND_TODO.md)（P0-x）。

## 1. 只有一个长期分支

- `main` 是唯一的长期分支，也是唯一的集成点。
- 其余分支都是**短命分支**：一个任务一个分支，合并后立刻删除。
- 不建 `dev`、`develop`、`release`、个人名分支（如 `zhangsan`）。

## 1.5 阶段集成分支（一个阶段多个任务并发时用）

一个阶段拆成几个并发任务时，加一层**集成分支**，任务分支从它切出、先合回它，整个阶段验收后再合进 `main`：

```
main
 └─ int/step1-measure-rules        ← 阶段集成分支（sub branch），阶段验收后 PR 合进 main
     ├─ feat/t1-node-state-helpers  ← 任务分支（sub-sub branch），各自一个 git worktree
     ├─ feat/t2-badput-p95-metrics
     └─ feat/t3-rebalance-invariants
```

- 集成分支命名 `int/step<n>-<简述>`，`n` 对应 TASK_BRIEF / 五步走的步号。
- 任务分支仍按第 2 节命名（`feat/t1-...`），**不要**写成 `int/step1-measure-rules/t1`：git 里一个分支名不能同时是另一个分支名的前缀目录，会报 `cannot lock ref`。
- 每个任务分支用一个独立 worktree 开发：
  ```bash
  cd satsim
  git fetch origin
  git worktree add ../wt-t1 -b feat/t1-node-state-helpers origin/int/step1-measure-rules
  git worktree add ../wt-t2 -b feat/t2-badput-p95-metrics origin/int/step1-measure-rules
  git worktree add ../wt-t3 -b feat/t3-rebalance-invariants origin/int/step1-measure-rules
  ```
- 任务做完：rebase 到最新的集成分支 → `uv run pytest -q` 全绿 → 回归检查通过 → 用 `--no-ff` 合进集成分支（保留每个任务的合并点，方便回看），推送，删掉任务分支和 worktree。
- 集成分支上全部任务合完后，再跑一次全量测试和回归，然后开 PR `int/step<n>-... → main`，由研究负责人验收合并。

## 2. 命名格式

```
<类型>/<任务号>-<简述>
```

全部小写，单词之间用 `-` 连接，简述 2~4 个英文单词。

| 类型 | 用途 | 示例 |
|---|---|---|
| `feat` | 新功能 / 新插件（代码） | `feat/t3-rebalance-invariants`、`feat/t7-cool-aware-migrator` |
| `fix` | 修 bug、修建模口径 | `fix/p0-1-tether-hop-time`、`fix/p0-3-numpy-deps` |
| `exp` | 实验配置与跑数（YAML、结果表），不改引擎 | `exp/e4-fair-quota`、`exp/e3-bw-kv-sweep` |
| `docs` | 只改文档 | `docs/glossary-sunlit-eclipse-cool` |
| `refactor` | 不改行为的重构（目录搬家、拆文件） | `refactor/p3-1-archive-scripts` |
| `chore` | 依赖、CI、子模块指针 | `chore/bump-satsim-t3` |

**任务号**怎么取：

| 来源 | 写法 | 例 |
|---|---|---|
| HANDOFF 开发任务 | `t<n>` | `t1` … `t9` |
| HANDOFF 实验 | `e<n>` | `e1`、`e3`、`e4` |
| RFC Phase 条目 | `p<phase>-<n>` | `p0-1`、`p1-4` |
| 都不是（临时探索） | 不写任务号，但必须用 `exp/` 并在 PR 里说明挂哪个 issue | `exp/multi-sso-ltan-scan` |

同一任务需要再开一次（比如第一版 PR 被关掉），在末尾加 `-v2`：`feat/t7-cool-aware-migrator-v2`。

## 3. 跨仓同名

改动在 `satsim`（或 `orbitsim`）里做，合并后要回 `satcosim` 提交子模块指针。**satcosim 上的指针分支和子模块分支用同一个名字**，方便一眼对上：

```bash
# 1) 子模块里开发
cd satsim && git switch main && git pull
git switch -c feat/t3-rebalance-invariants
# ... 提交、推送、开 PR 到 acam-infra/satsim，合并 ...

# 2) 回 satcosim 记录新指针（同名分支）
cd .. && git switch main && git pull
git switch -c feat/t3-rebalance-invariants
cd satsim && git switch main && git pull && cd ..
git add satsim && git commit -m "bump satsim: T3 rebalance invariants"
# 推送、开 PR 到 acam-infra/satcosim
```

只改 satcosim 自己的文件（比如 `docs/`、`cosim.py`）时不涉及子模块，正常开分支即可。

## 4. 提交与 PR

| 项 | 约定 | 例 |
|---|---|---|
| 提交信息 | `<任务号大写>: <做了什么>`，英文或中文都行 | `T3: lift max_inflight/max_mig_per_req into rebalance_invariants` |
| PR 标题 | `<仓库>: <任务号> <简述>` | `satsim: T3 rebalance invariants` |
| PR 描述 | 按 HANDOFF §5 的模板（做了什么 / 默认行为回归 / 测试 / 新数字 / 没做） | — |
| 合并方式 | **Squash merge**，合并后删除源分支 | — |

## 5. 进度怎么同步

不另建看板。用分支和 PR 的状态表达进度，任何人在 GitHub 的 PR 列表里就能看到：

| 状态 | 怎么表示 | 含义 |
|---|---|---|
| 未开始 | 没有对应分支 | — |
| 进行中 | 分支已推送，**开 Draft PR** | 第一次 push 就开 Draft，别等写完 |
| 待审阅 | Draft 转 Ready for review | 自测、回归、pytest 都过了 |
| 完成 | PR 已合并，分支已删 | — |
| 搁置 | PR 关闭，描述里写原因 | 负结果也记下来 |

查进度：

```bash
gh pr list -R acam-infra/satsim --state all --search "head:feat/t"   # 全部开发任务
gh pr list -R acam-infra/satsim --state open --draft                 # 正在做的
```

科研侧（gjam Multica）：
- 实验类 PR（`exp/e*`）合并后，把 PR 链接和 `summary.md` 路径写回 **LAB-1466**，进入 S4 claim 核对；
- 开发类 PR 不用逐个回写，T1–T7 全部合并后在 LAB-1466 回一条汇总。

## 6. 分支卫生

- 分支超过 **7 天**没有新提交：要么 rebase 到最新 `main` 继续，要么关掉 PR、删分支。
- 不在别人的分支上直接推提交，要改就在 PR 里提 review。
- 合并前必须 rebase 到最新 `main`，并重跑 HANDOFF §3 的回归检查。
- 不允许直接推 `main`。例外：只改文档的小修，以及仓库维护者的子模块指针同步。

## 7. 本轮计划的分支一览

| 分支名 | 仓库 | 依赖 |
|---|---|---|
| `fix/p0-1-tether-hop-time` | satsim | — |
| `fix/p0-2-milp-constraints` | satsim | — |
| `fix/p0-3-numpy-deps` | satsim | — |
| `feat/t1-node-state-helpers` | satsim | — |
| `feat/t2-badput-p95-metrics` | satsim | — |
| `feat/t3-rebalance-invariants` | satsim | — |
| `exp/t4-hotspot-config` | satsim | T2 |
| `feat/t5-suite-runner` | satsim | T2 |
| `feat/t6-delta-kv` | satsim | — |
| `feat/t7-cool-aware-migrator` | satsim | T1、T3 |
| `exp/e1-stage1-hotspot` | satsim | T4、T5 |
| `exp/e3-bw-kv-sweep` | satsim | T5、T6、T7 |
| `exp/e4-fair-quota` | satsim | T3、T5、T7 |
| `feat/t9-sink-temp-two-level`（可选，先问） | satsim | 动 L1，需确认 |

没有依赖关系的任务（P0-x、T1、T2、T3、T6）可以并行开。

## 8. 多 Agent 协同开发与审阅流程

在 Multica 平台上推进 `satcosim / satsim / orbitsim` 迭代时，固定采用**「强模型规划与集成 Review + 3.8 Flash 并发开发」**的分工流程，兼顾推进速度与科研可信度。

### 8.1 角色分工

| 角色 | 推荐模型池 | 职责边界 | 禁止事项 |
|---|---|---|---|
| **统筹规划与审阅（Planner & Reviewer）** | 强推理模型（如 `cc · carbon-4 · gu20x · agy` / `gemini-4-carbon`） | 1. 制定 S1 问题卡、负载物理量纲核算与 [`HANDOFF.md`](HANDOFF.md) 接口契约；<br>2. 将阶段目标切分为文件正交的子任务（`--stage 1/2/...`）；<br>3. 审计 `3.8 Flash` 提交的分支 diff、跨分支祖先关系与边界数学逻辑；<br>4. 在集成分支运行多 seed 配对实验，核对原始 `runs.csv` 数字后将集成分支 PR 转为 Ready。 | 不把未经手算校验的模糊需求直接派给并发层；不跳过原始 CSV 核对直接采信子票口头结论。 |
| **并发开发与跑数（Concurrent Workers）** | 多账号高并发池（`gemini-3.8-flash` / `qwen3.8-flash` 各节点） | 1. 一票一分支（`feat/t<n>-*`、`fix/p0-*`、`exp/e*`）独立 worktree 编码；<br>2. 编写针对性 `pytest` 用例并跑通 [`HANDOFF.md` §3](HANDOFF.md#3-通用验收默认行为回归检查) 默认行为零回归校验；<br>3. 执行 `satsim-suite` 参数扫描，原样回传 `runs.csv` / `summary.md` 路径与 Draft PR。 | 不跨票修改他人负责的模块；不改默认配置文件已有参数；不手抄或估算实验数字；不直接合入 `main`。 |

### 8.2 四步标准闭环

```
[Step 1 强模型立契约] ──▶ [Step 2 3.8 Flash 分 Stage 并发实操] ──▶ [Step 3 强模型集成审计与实测校准] ──▶ [Step 4 人工终审合入 main]
```

1. **Step 1 — 前置规划与契约冻结（强模型）**
   - 开工前在契约文档中明确钉死：**注册表键名**（如 `PLACERS` / `MIGRATORS` 字典键）、**公平不变量**（`rebalance_invariants` 周期与配额）、**禁用旧词检查**（只用 `日照/sunlit`、`日影/eclipse`、`凉星/cool`、`热星/hot`）以及**物理瓶颈手算预期**（确认目标负载能真实触发热节流或日影限频，避免在无瓶颈温水区空跑大规模网格）。
   - 切分任务时保证**同一 Stage 内的子票修改不同文件或正交注册项**；存在先后依赖的任务（如先合入 T1/T3 接口、再写 T7 迁移器与 T8 实验套件）严格拆入 `--stage 1` 与 `--stage 2`（后续阶段先置 `backlog`，前序验收后再放行）。

2. **Step 2 — 独立分支并发开发（3.8 Flash 工作池）**
   - 由强模型通过 Multica 子票并发派发至多个 `3.8 Flash` runtime（`multica issue create --parent <主票> --stage <N> --assignee <3.8-flash-agent>`），每张子票绑定唯一分支名与集成分支基线（如 `int/step2-scenario-plugins`）。
   - Worker 首次推送即开 **Draft PR**，交付评论必须贴齐三项硬证据：
     1. `uv run pytest -q` 尾部输出；
     2. 默认配置 `summary.json` 零回归比对结果（`diffs=0`）；
     3. 若含跑数，贴原始 `runs/<suite>/runs.csv` 与 `summary.md` 路径。

3. **Step 3 — 集成合流与深度审计（强模型 Review 必查 5 项）**
   - 并发提速最容易引入跨任务接口错位与玩具单测盲区，强模型在合入 `int/step<n>-*` 时必须逐项核查：
     1. **分支祖先完整性**：执行 `git merge-base --is-ancestor origin/int/step<n-1> HEAD`，防止后序集成分支从旧 commit 切出而漏掉前序审阅修复；
     2. **跨模块注册表闭环**：核对实验 YAML 引用的所有策略名（如 `orbit_thermal`、`round_robin_all`、`cool_aware`）在 `PLACERS` / `MIGRATORS` 中均已注册且 `.id` 属性齐全；
     3. **公平对比不变量**：确认同组对比策略共用同一套 `rebalance_invariants` 与准入开关，不存在单一策略私享高频控制周期或隐式预留配额；
     4. **领域物理与边界数学**：逐行审阅迁移打分与约束（如已超时请求的负余量排序、链路剩余可见寿命 `path_lifetime` 与 `mig_timeout` 守卫、跨控制周期在途迁入计数、传输期间源星已解码进度扣减），不能只看单测绿灯；
     5. **科学叙事区分度**：跑完 5 seeds 配对套件后检查阶段一基线是否真实暴露痛点、阶段一最强静态策略是否存在明确天花板、阶段二动态迁移是否在同配额下取得显著配对增益；若落入无区分度温水区，先完成场景参数敏感度扫描与校准，再冻结实验套件。

4. **Step 4 — 提交人工验收（Ready PR → `main`）**
   - 强模型确认全量测试、默认回归、术语扫描与 5-seed 配对表全部齐备后，将集成分支 PR 转为 **Ready for review**，在主票汇总 `【已测】` 表格与 PR 链接并置 `in_review`，由研究负责人最终点击合并至 `main`。
