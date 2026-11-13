# satcosim 联合仿真领域术语表（Glossary）

本词表统一 `acam-infra/satcosim` 及其双子模块（`orbitsim` × `satsim`）的核心领域语言。代码标识符、配置字段与实验报告只使用下列规范名称。

## 供电维与热维（正交四态）

**日照**（`sunlit`）:
算力星处于太阳翼受晒供电区间（`not tr.is_dark(j, t)`），供电上限为 `P_max`，轨道供电频率倍率为 `1.0`。
_Avoid_: 泛称亮星而不区分热态

**日影**（`eclipse` / `is_dark`）:
算力星进入地球背阳区（`tr.is_dark(j, t)`），仅靠电池供电（上限 `P_dark`，默认 `80 W`）；高功耗档位禁用或频率封顶 `f_dark`，属于迁出源。
_Avoid_: 阴影, shadow

**凉星**（`cool`）:
结温未触发热限且距温限阈值保有充足裕度（`thermal_headroom_C(j) >= margin_C`）的算力星；**日照 + 凉星**（尤其刚出日影的卫星）是首选迁入目标。
_Avoid_: 阴影低温区, dark=cool

**热星**（`hot`）:
结温达到或在前瞻热窗口内即将越过温限上限 `T_max_C`（或节流阈值 `T_throttle_C`）的算力星，属于迁出源。
_Avoid_: 暗星

## 离散功率与热量约束模型（LAB-1867）

**离散功率模式**（`discrete_tiers`）:
将卫星功耗配置简化为有限个离散档位（`power.mode: discrete_tiers`），消除连续批利用率功耗与热回滞跳变，使一阶 RC 热量约束线性化并直接纳入标准 MILP 求解器（HiGHS）。
_Avoid_: 与连续指数功耗公式混写

**离散功率档**（`power_tiers`）:
算力星可选状态表 `(power_w, max_batch, clock_f)`：第 `0` 档为零请求空闲档，第 `1..K` 档为固定功率、承载上限与频率倍率的工作档。
_Avoid_: 连续无级调频

**零请求零功率档**（`zero_power_idle`）:
驻留活跃请求数为 `0` 时强制选用的第 `0` 档，工作功率严格为 `0 W`，使整批排空后的卫星以最快 RC 速率向 `T_amb_C` 降温。
_Avoid_: 空星常驻 60W 热底噪

**温限裕度**（`thermal_margin_C`）:
最高允许结温 `T_max_C` 减去当前结温 `T_j(t)` 的差值（`°C`）。
_Avoid_: 无量纲热评分

**前瞻热窗口**（`thermal_horizon_s`）:
MILP 线性 RC 温限约束使用的前瞻时长 $\Delta_H$（默认 `30 s`），用于提前拦截持续高功运行导致的超温指派。
_Avoid_: 仅看单控制步瞬时温升

## 调度与评测标尺

**首次分配**（`place_once`）:
请求到达时选定算力星放置、运行中途不迁移的基准策略；所有实验对比表统一以它作为 100% 参照基线。
_Avoid_: 以无消耗迁移 `free` 当基线

**公平配额**（`rebalance_invariants`）:
所有对比迁移策略必须共用的控制周期 `interval_s`、全网在途迁移上限 `max_inflight` 与单请求迁移上限 `max_mig_per_req`。
_Avoid_: 单一策略私享高频控制或隐式配额

**有效吞吐与浪费率**（`goodput_tok_s` / `waste_ratio`）:
截止期内按时送达请求的输出速率，以及超时作废输出 token 占总生成 token 的比例 `badput / (goodput + badput)`。
_Avoid_: 只报已完成请求均值而忽略右删失请求
