# satcosim — orbitsim × satsim 协同仿真

两个仓库作为子模块放在一起，用一个脚本串起来：

| 子模块 | 负责 | 产出 |
|---|---|---|
| [`orbitsim`](https://github.com/chocolatedesue/orbitsim) | 轨道闭式解、地影、星间可见性；3-D 查看器与回放页 `viz/play.html` | 接触轨迹 `orbitsim.contact_trace/v1` |
| [`satsim`](https://github.com/chocolatedesue/satsim) | 在轨推理网络与调度仿真 (`satsim.cosim`) | 回放数据 `satsim.cosim_playback/v1` |

```
orbitsim/export_cosim.py ──▶ satsim/input/traces/*.json ──▶ satsim-cosim ──▶ orbitsim/viz/public/playback/*.json ──▶ play.html
        (轨道几何)              (接触 + 地影区间)          (网络 + 推理)              (链路负载 / 迁移 / 断链)
```

## 快速开始

```bash
git clone --recursive https://github.com/chocolatedesue/satcosim.git
cd satcosim
python cosim.py setup      # 拉子模块 + uv sync 两边 + npm install
python cosim.py view       # 打开 http://localhost:5288/play.html
```

子模块里已经带了三个实验的回放数据，`view` 不用先跑仿真。需要 git、[uv](https://docs.astral.sh/uv/)、Node.js。

## 常用操作

| 想做的事 | 命令 |
|---|---|
| 改了调度策略 / 负载，重跑一个实验 | `python cosim.py run typhoon_agentic_v1` |
| 改了星座 / 链路，重新导出轨迹 | `python cosim.py trace`（可加 `coop-w53` 只导一个） |
| 轨迹 + 全部实验从头跑 | `python cosim.py all` |
| 跑三套测试 | `python cosim.py test` |
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

## 文档

- 实验与结论：[`satsim/docs/notes/cosim_contact_trace.md`](satsim/docs/notes/cosim_contact_trace.md)
- 引擎设计：[`satsim/docs/adr/0005-cosim-contact-trace.md`](satsim/docs/adr/0005-cosim-contact-trace.md)
- 回放页说明：[`orbitsim/viz/README.md`](orbitsim/viz/README.md)
- 轨道几何结论：[`orbitsim/research_out/README.md`](orbitsim/research_out/README.md)
