# 领域术语与文档规范（Domain docs）

阅读或修改 `satcosim` 及子模块 `orbitsim` / `satsim` 前，请遵守以下统一规范。

## 必读入口

- 根目录 `GLOSSARY.md` 与 `docs/TERMS_AND_MODEL.md`：联合仿真统一术语表（正交区分供电维 `日照/日影` 与热维 `凉星/热星`，以及离散功率档 `power_tiers`）。
- `docs/DISCRETE_POWER_DESIGN.md` 与 `docs/adr/`（及 `satsim/docs/adr/`）：核心架构与数学建模决策记录。

## 目录布局

```text
/
├── GLOSSARY.md
├── docs/
│   ├── TERMS_AND_MODEL.md
│   ├── DISCRETE_POWER_DESIGN.md
│   ├── adr/
│   └── agents/
├── orbitsim/
└── satsim/
```

## 用词与结果表红线

1. 严禁在新增代码、注释或文档中使用「阴影 / shadow / dark=cool」指代低温凉星；一律使用 `日照 (sunlit)`、`日影 (eclipse)`、`凉星 (cool)`、`热星 (hot)`。
2. 新改动若推翻既有 ADR 结论，必须先新增或修订对应 ADR。
3. 实验对比表统一以 `首次分配 (place_once)` 为 100% 参照基线，数值旁写出相对百分比（如 `19.2 (+50%)`），粗体标出该列最优值。
