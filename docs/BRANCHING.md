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
