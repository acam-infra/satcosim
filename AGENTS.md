# satcosim（orbitsim × satsim 联合仿真）

## 目录结构与跨仓架构（Layout）

- `orbitsim/`（Git 子模块 → `acam-infra/orbitsim`）：轨道几何闭式解、日照/日影周期与星间可见性计算，导出接触迹线 `orbitsim.contact_trace/v1`；另含三维回放前端 `orbitsim/viz/play.html`。
- `satsim/`（Git 子模块 → `acam-infra/satsim`）：在轨大模型在线推理、KV 状态跨星迁移、一阶 RC 动态热模型 / 离散功率模型与联合 MILP 调度引擎，导出回放数据 `satsim.cosim_playback/v1`。
- `cosim.py`：顶层统一入口（`setup` / `trace` / `run` / `all` / `view` / `test` / `check` / `status` / `update`）。
- `docs/`：跨仓研发与建模规范：
  - `docs/TERMS_AND_MODEL.md`：供电维（日照/日影）与热维（凉星/热星）术语统一说明；
  - `docs/DISCRETE_POWER_DESIGN.md`：离散卫星功率配置（零请求 0W + 工作档）与线性热量约束数学形式化报告；
  - `docs/HANDOFF.md` & `docs/TASK_BRIEF.md`：契约任务清单与默认行为零回归（`diffs=0`）验收规则；
  - `docs/BRANCHING.md`：集成分支（`int/step<n>-*`）、跨仓同名指针分支与「强模型规划审阅 + `hydrogen-4` 子 agent 并发开发」流程。

## 术语与架构决策（Language）

- 根目录统一术语表：`GLOSSARY.md`（与子模块 `satsim/GLOSSARY.md` 对齐）
- 跨仓建模决策记录：`docs/adr/`（推理调度引擎细则见 `satsim/docs/adr/`）
- 如何维护术语与 ADR：`docs/agents/domain.md`

## Agent skills

本仓库内置 `.agents/skills/`（来自 `mattpocock/skills` 的项目级工程与效率技能）。各技能读取以下仓库配置契约：

### Issue tracker

任务编排与分阶段（`--stage`）并发子票统一在 Multica 平台（`ccds-lab`）管理，不在 GitHub Issues 双开。详见 `docs/agents/issue-tracker.md`。

### Triage labels

五类标准分流角色与 Multica 状态/标签的映射约定。详见 `docs/agents/triage-labels.md`。

### Domain docs

联合仿真统一领域词表与结果表基线规范（以 `place_once` 首次分配为 100% 基准）。详见 `docs/agents/domain.md`。
