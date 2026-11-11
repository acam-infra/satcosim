# satcosim — orbitsim × satsim 协同仿真

两个仓库作为子模块放在一起，用一个脚本串起来：

| 子模块 | 负责 | 产出 |
|---|---|---|
| [`orbitsim`](https://github.com/acam-infra/orbitsim) | 轨道闭式解、地影、星间可见性；3-D 查看器与回放页 `viz/play.html` | 接触轨迹 `orbitsim.contact_trace/v1` |
| [`satsim`](https://github.com/acam-infra/satsim) | 在轨推理网络与调度仿真 (`satsim.cosim`) | 回放数据 `satsim.cosim_playback/v1` |

```
orbitsim/export_cosim.py ──▶ satsim/input/traces/*.json ──▶ satsim-cosim ──▶ orbitsim/viz/public/playback/*.json ──▶ play.html
        (轨道几何)              (接触 + 地影区间)          (网络 + 推理)              (链路负载 / 迁移 / 断链)
```

## 快速开始

```bash
git clone --recursive https://github.com/acam-infra/satcosim.git
cd satcosim
python cosim.py setup      # 拉子模块 + uv sync 两边 + npm install
python cosim.py view       # 打开 http://localhost:5288/play.html
```

子模块里已经带了三个实验的回放数据，`view` 不用先跑仿真。需要 git、[uv](https://docs.astral.sh/uv/)、Node.js。

## 常用操作

| 想做的事 | 命令 |
|---|---|
| **前置问题确认（Motivation）**：即时合成多轨道面异构 SSO，对比 `nearest` / `rr` / `random` 等计算负载与达标率 | `PYTHONPATH=satsim/src:orbitsim/src python satsim/scripts/exp_motivation_multi_sso.py` |
| 改了调度策略 / 负载，重跑一个实验 | `python cosim.py run typhoon_agentic_v1` |
| 改了星座 / 链路，重新导出轨迹 | `python cosim.py trace`（可加 `coop-w53` 只导一个） |
| 轨迹 + 全部实验从头跑 | `python cosim.py all` |
| 跑三套测试 | `python cosim.py test` |
| 检查轨迹、回放、子模块是否一致（提交前跑） | `python cosim.py check` |
| 看两边当前提交和未提交改动 | `python cosim.py status` |
| 把子模块更新到各自分支最新 | `python cosim.py update` |

`run` 接受完整路径、`configs/` 下的文件名，或去掉 `cosim_` 前缀的短名：`coop_w53_v1`、`coop_sso2_v1`、`typhoon_agentic_v1`。
新实验：复制 `satsim/configs/cosim_typhoon_agentic_v1.yaml` 改 `name` 和参数，然后 `python cosim.py run <新名字>`。

## 提交规则（子模块）

子模块是独立仓库，改动要先在子模块里提交并 push，再在这里记录新的提交号：

```bash
cd satsim && git switch main        # 子模块默认是游离 HEAD, 先切到分支再改
git commit -am "..." && git push
cd .. && git add satsim && git commit -m "bump satsim" && git push
```

改了策略并重跑后，通常两个子模块都有改动：satsim（代码/配置）和 orbitsim（`viz/public/playback/` 里的新回放）。
两边各自 push 后，在这里 `git add orbitsim satsim` 一次提交。

## 哪些文件入库

| 文件 | 位置 | 入库 | 说明 |
|---|---|---|---|
| 接触轨迹 | `satsim/input/traces/*.json` | 是 | 实验输入，保证可复现；`cosim.py trace` 从 orbitsim 重新生成 |
| 轨迹导出缓存 | `orbitsim/cosim_out/` | 否 | `export_cosim.py` 默认输出 |
| 回放数据 | `orbitsim/viz/public/playback/*.json` | 是 | 克隆即可看；带 `provenance`，不显示 diff（`linguist-generated`）|
| 实验汇总 / 扫描 CSV | `satsim/runs/` | 否 | 本地结果，结论写进 `docs/notes/` |
| 截图 | `orbitsim/viz/shots/` | 否 | `shot_play.mjs` 默认输出；README 引用的才拷到 `viz/docs/` |
| 依赖锁 | `uv.lock`、`viz/package-lock.json` | 是 | 可复现安装 |
| venv / node_modules / 缓存 | 各子模块 | 否 | 各自 `.gitignore` |

三个仓库都用 `.gitattributes` 固定 LF 换行（不受 `core.autocrlf` 影响）。回放文件较大（现在合计约 12 MB），只提交要展示的实验；超过约 50 MB 时改用 Git LFS 或 GitHub Release 附件。

`cosim.py check` 做三件事：用 orbitsim 当前代码重新导出轨迹，和 `satsim/input/traces` 逐字节比较；用回放里的 `provenance` 哈希判断回放是不是由当前轨迹和配置生成的；确认两个子模块当前提交已 push、工作区干净。任一项不过就以退出码 1 结束，并提示该跑哪条命令。

## 文档

- **任务目标（阶段一 / 阶段二）**：[`docs/TASK_BRIEF.md`](docs/TASK_BRIEF.md)
- **术语与建模口径（日照 / 日影 / 凉星 / 热星）**：[`docs/TERMS_AND_MODEL.md`](docs/TERMS_AND_MODEL.md)
- **架构收敛与迭代路线图（待 Review）**：[`docs/ARCHITECTURE_AND_TODO.md`](docs/ARCHITECTURE_AND_TODO.md)
- **开发任务单（Handoff，T1–T9）**：[`docs/HANDOFF.md`](docs/HANDOFF.md)
- **分支命名与进度同步约定**：[`docs/BRANCHING.md`](docs/BRANCHING.md)
- 实验与结论：[`satsim/docs/notes/cosim_contact_trace.md`](satsim/docs/notes/cosim_contact_trace.md)
- 引擎设计：[`satsim/docs/adr/0005-cosim-contact-trace.md`](satsim/docs/adr/0005-cosim-contact-trace.md)
- 回放页说明：[`orbitsim/viz/README.md`](orbitsim/viz/README.md)
- 轨道几何结论：[`orbitsim/research_out/README.md`](orbitsim/research_out/README.md)
