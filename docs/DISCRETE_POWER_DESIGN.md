# 离散卫星功率配置与热量约束简化模型：背景、输入、优化目标、约束条件与设计考量

> **承接基线**：`LAB-1779`（`acam-infra/satcosim` / `satsim`）及前置理论文档 `迁移核心数学建模与算法设计_v1.md`  
> **文档定位**：聚焦**数学形式化与代码架构对齐**，作为下一步修改 `satsim` 仿真器与 MILP 求解器的设计依据。

---

## 一、背景与问题缘起

### 1.1 现有方案的结构性痛点

在 `LAB-1779` 的 `acam-infra/satsim` 代码库与数学模型（问题 $\mathcal{P}_{\text{CM}}$）中，在轨推理调度与热力学演化之间存在两层强非线性耦合：

1. **功耗与并发批大小连续耦合**：在 `satsim/src/satsim/cosim/world.py` 的 `CoWorld.device_power(batch, f)` 中，空星仍有基础静态功耗 `P_idle = 60W`；一旦有请求驻留（`batch >= 1`），设备功率按饱和指数曲线 `P_idle + (P_max - P_idle) * (1 - 0.6 * exp(-batch / 4)) * f^2.4` 随 `batch` 连续变化（`P_max = 300W`）。
2. **热滞回跳变导致目标函数非可加**：温度按一阶 RC 微分方程演化，在 `T_throttle_C = 84°C` 触发 `f_throttle = 0.55` 降频，直到降至 `T_release_C = 76°C` 才恢复。在 `迁移核心数学建模与算法设计_v1.md` 中，这导致完成时间算子 $\Phi_j(r \mid \mathcal{B}'_j(\mathbf{x}), t)$ 成为**非可加的非线性集合函数**——多个任务同时迁入同一颗凉星会把它推过 `84°C` 热悬崖。
3. **求解器与热模型割裂**：`scripts/verify_torch_milp.py` 虽然用 `scipy.optimize.milp`（HiGHS）解了路径、显存与带宽约束 `(C1)-(C4)`，但**无法把热约束写进 MILP**，只能依赖外层 `ThermalRebalance` / `TorchRebalance` 贪心逐个重跑分段 RC 积分器 `ThermalForecast.finish`。

### 1.2 简化重构思路

实际上，`satsim` 早期 L1 层的 `DynamicThermal._power()`（`src/satsim/method/policies/thermal/dynamic.py`）原本就是三态离散功率原型。本次简化思路顺着这一结构，将卫星功耗模型收敛为：

- **离散功率档位**：每颗卫星配置几档离散的 `(工作功率, 请求承载)` 工作态；
- **零请求 0 功率**：当卫星上没有活跃请求时，工作功率严格归零（`0 W`），消除 `P_idle = 60W` 的无意义热底噪；
- **显式热量约束**：由于功耗仅由离散档位决定、不再依赖连续 `batch`，一阶 RC 温升与温度上限可**直接写成纯线性约束**，从而把「请求迁移」与「功率档位选择」统一进同一个标准 MILP 中全局求解。

---

## 二、系统输入（Inputs）

在每个滚动控制周期 $t = n\Delta t$（默认 $\Delta t = 2\text{ s}$ 或重平衡周期 $\Delta_p$），规划器接收以下四类输入：

### 2.1 时变星座拓扑与星历输入

- **星座有向图** $\mathcal{G}(t) = (\mathcal{V}_s \cup \mathcal{V}_c, \mathcal{E}(t))$：$\mathcal{V}_s$ 为遥感采集星，$\mathcal{V}_c$ 为算力星，$\mathcal{E}(t)$ 为当前建链星间链路（ISL）。
- **链路属性**：每条边 $e \in \mathcal{E}(t)$ 的可用带宽 $B_e(t)$（`w.net.cap`）、单跳传播时延 $d_e$（`hop_latency_s`）、星历决定的剩余连续可见寿命 $\tau_{\text{life}}(e, t)$（`path_lifetime`）。
- **日照 / 日影状态**：每颗算力星 $j \in \mathcal{V}_c$ 在当前及前瞻窗口内的供电状态 $\text{is\_eclipse}(j, t) \in \{0, 1\}$（对应 `tr.is_dark(j, t)`）及日影供电包络上限 $P_{\text{dark}}$（默认 `80 W`）。

### 2.2 算力星节点状态输入

对每颗算力星 $j \in \mathcal{V}_c$：
- **当前结温** $T_j(t)$（来自 `w.thermal.temperature(j)`）；
- **当前驻留请求集合** $\mathcal{B}_j(t)$ 及请求数 $n_j^{\text{cur}}(t) = |\mathcal{B}_j(t)|$；
- **物理显存上限** $M_j$（`kv_gib`，如 `40 GiB`）及在途预留字节 `w.reserved[j]`。

### 2.3 离散功率档位与热物理参数（本次核心新增）

对每颗算力星 $j \in \mathcal{V}_c$，定义离散档位集合 $\mathcal{K} = \{0, 1, \dots, K\}$：
- **零请求空闲档（$k = 0$）**：$P_{j,0} = 0\text{ W}$，$B^{\max}_{j,0} = 0$，$f_{j,0} = 0$；
- **工作档位（$k \in \{1, \dots, K\}$，最简两档即 $K = 2$）**：每档绑定三元组 $(P_{j,k},\; B^{\max}_{j,k},\; f_{j,k})$，分别表示该档位的固定工作功率（W）、最大并发请求承载数、以及有效算力频率倍率。
- **热力学常数**：热时间常数 $\tau_{\text{rc}}$（`tau_s = 240.0 s`）、等效热阻 $R_{\text{th}}$（`0.30 °C/W`）、环境热沉温度 $T_{\text{amb}}$（`20.0 °C`）、允许最高结温上限 $T_{\max}$（如 `84.0 °C`）。

### 2.4 活跃请求与系统不变量

- **活跃请求 $r \in \mathcal{R}_{\text{act}}(t)$**：到达时刻 $t_r$、源遥感星 $o_r$、截止期 $D_r$（`r.deadline`）、当前已生成上下文长度 $L_r(t)$、KV 显存占用 $\text{mem}_{\text{KV}}(r)$、迁移传输字节量 $V(r)$、已迁移次数 $n_r^{\text{mig}}$。
- **系统配额常数**：全网同时在途迁移上限 $B_{\text{mig}}$（`max_inflight`）、单请求最大迁移次数 $N_{\max}^{\text{mig}}$、规划窗口 $\Delta_w$、接触窗安全裕度 $\epsilon_{\text{guard}}$。

---

## 三、决策变量与优化目标（Decision Variables & Objective）

### 3.1 决策变量

1. **请求迁移变量** $x_{r,s,d,p} \in \{0, 1\}$：表示是否将源星 $s$ 上的活跃请求 $r$ 沿简单路径 $p \in \mathcal{P}_K(s, d, t)$ 迁移至目的星 $d$（所有候选均取 0 表示请求 $r$ 留在源星 $s$ 继续解码）。
2. **离散功率档位选择变量** $z_{j,k}(t) \in \{0, 1\}$：表示算力星 $j$ 在本控制窗口选择第 $k \in \{0, 1, \dots, K\}$ 档功率配置。
3. **辅助连续变量（工程兜底）** $s_j \ge 0$：节点 $j$ 的温限软松弛量，仅在极端全网过载无可行解时吸收超温，平时被大惩罚压为 0。

由迁移决策唯一确定的迁移后节点请求数 $n_j(t)$ 为线性表达式：

$$n_j(t) = |\mathcal{B}_j(t)| - \sum_{r \in \mathcal{B}_j(t)} \sum_{d, p} x_{r,j,d,p} + \sum_{s \neq j} \sum_{r \in \mathcal{B}_s(t)} \sum_{p} x_{r,s,j,p}$$

### 3.2 优化目标

**设计思路**：仿真最终验收的是硬达标率（`good_long_frac`）与有效吞吐（`goodput_tok_s`），但硬阶跃函数在截止期 $D_r$ 边界不可微且对长度预测误差敏感。因此，规划层目标函数采用**平滑期望有效吞吐净增益最大化**，同时扣除跨星通信代价与高功耗/超温松弛惩罚：

$$\max_{\mathbf{x}, \mathbf{z}, \mathbf{s}} \quad \sum_{r \in \mathcal{R}_{\text{act}}(t)} \sum_{d, p} \Delta U_{r,s,d,p} \cdot x_{r,s,d,p} - \lambda_{\text{comm}} \sum_{r,s,d,p} \frac{V(r)}{B_p(t)(D_r - t_r)} x_{r,s,d,p} - \lambda_{\text{pwr}} \sum_{j, k \ge 1} P_{j,k} z_{j,k}(t) - M_{\text{pen}} \sum_{j} s_j$$

其中：
- $\Delta U_{r,s,d,p} = U_r(\hat{t}^{\text{move}}_{r,d,p}) - U_r(\hat{t}^{\text{stay}}_{r,s})$ 为迁移前后单请求平滑效用差，$U_r(\hat{t}) = \bar{L}_r^{\text{out}} \cdot \sigma\left(\frac{D_r - \hat{t}}{\gamma_r}\right)$；
- 第三项 $-\lambda_{\text{pwr}} \sum P_{j,k} z_{j,k}$ 取极小权重，用于在吞吐相同时**自动偏好更低功耗档（以及零请求时优先选 $0\text{ W}$ 档）**；
- 第四项 $-M_{\text{pen}} \sum s_j$ 保证仅在无可行解时才允许突破温限。

---

## 四、约束条件（Constraints）

所有约束均为**纯线性整数/混合整数约束**，可直接送入 `scipy.optimize.milp`（HiGHS）求解：

### 4.1 原有网络、显存与迁移配额约束

1. **请求动作唯一性**：每个请求至多选择一个目的星与一条路径。

$$\sum_{d, p} x_{r,s,d,p} \le 1$$

2. **目的星 KV 显存硬上限**：迁入后总 KV 显存不超过物理显存 $M_d$。

$$\sum_{r \in \mathcal{B}'_d(\mathbf{x})} \text{mem}_{\text{KV}}(r) \le M_d$$

3. **ISL 接触窗与截止期硬约束**：迁移传输耗时留足安全裕度后，必须小于路径剩余寿命及请求剩余截止期。

$$x_{r,s,d,p} \cdot (1 + \epsilon_{\text{guard}})\,\delta(r, p) \le \min\left(\tau_{\text{life}}(p, t),\; D_r - t\right)$$

4. **多跳共享 ISL 边字节预算**：经过同一条物理边 $e$ 的迁移总字节量不超过窗口可用带宽容量。

$$\sum_{r,s,d,p : e \in p} x_{r,s,d,p} \cdot V(r) \le B_e(t) \cdot \Delta_w$$

5. **全网并发迁移配额与防乒乓**：

$$\sum_{r,s,d,p} x_{r,s,d,p} \le B_{\text{mig}} - N_{\text{inflight}}(t)$$

### 4.2 新增离散功率与线性热量约束

6. **离散功率档位互斥**：每颗算力星在每一时刻有且仅有一个工作档位被激活。

$$\sum_{k=0}^{K} z_{j,k}(t) = 1$$

7. **零请求 0 功率与请求-功率耦合**：有请求时必须开启能容纳 $n_j(t)$ 的工作档；无请求（$n_j(t) = 0$）时左式强制所有工作档为 0，由互斥约束自动落入 $k=0$（$P_{j,0} = 0\text{ W}$）。

$$\sum_{k=1}^{K} z_{j,k}(t) \le n_j(t) \le \sum_{k=1}^{K} B^{\max}_{j,k}\, z_{j,k}(t)$$

8. **日影供电包络约束**：处于日影段且功率超出电池上限 $P_{\text{dark}}$ 的高功耗档位强制禁用。

$$z_{j,k}(t) = 0 \quad (\text{is\_eclipse}(j,t) = 1 \text{ and } P_{j,k} > P_{\text{dark}})$$

9. **一阶 RC 线性热量演化与温限约束**（令衰减系数 $\alpha = e^{-\Delta t / \tau_{\text{rc}}}$）：

$$T_j(t+1) = \alpha\, T_j(t) + (1 - \alpha)\left(T_{\text{amb}} + R_{\text{th}} \sum_{k=0}^{K} P_{j,k}\, z_{j,k}(t)\right)$$

$$T_j(t+1) \le T_{\max} + s_j$$

---

## 五、核心设计考量与权衡（Design Considerations）

1. **为什么「零请求 0 功率」是关键激励机制？**  
   在原模型中，`P_idle = 60 W` 导致空星的稳态平衡温仍高达 $20 + 0.3 \times 60 = 38^\circ\text{C}$；改为零请求 `0 W` 后，空星平衡温直接跌回环境温度 $T_{\text{amb}} = 20^\circ\text{C}$，降温斜率显著加大。同时在约束 (7) 下，只有**整批排空**（$n_j = 0$）才能切换到 $P_{j,0} = 0$，保留了原论文里「整批排空降温」的核心物理直觉，但去掉了复杂的非线性判断。

2. **两档工作态（$K=2$）的粒度够用吗？**  
   在轨加速卡通常不需要连续调频，`(0W 空闲, 低功耗档, 高功耗档)` 三态已完整覆盖三种典型工况：
   - **空闲态 `0W`**：无任务驻留，全力散热；
   - **低功档 $(P_1, B^{\max}_1, f_1)$**：如匹配日影电池上限或热保守运行（例如 `80W~150W` 档）；
   - **高功档 $(P_2, B^{\max}_2, f_2)$**：日照凉星满频冲吞吐（例如 `300W` 档）。  
   每颗星仅增加 3 个二元变量，40 星星座也仅多出 120 个二元变量，HiGHS 仍可在毫秒级求得全局最优。

3. **规划步长 $\Delta t$ 与前瞻热窗口的匹配**  
   因为热时间常数 $\tau_{\text{rc}} = 240\text{ s}$ 较大，若控制步长 $\Delta t = 2\text{ s}$，单步温升 $(1 - e^{-2/240}) \approx 0.83\%$ 很小。建议在 MILP 的热量约束中，使用**前瞻规划步长 $\Delta_H$**（如 $\Delta_H = 30\text{ s}$ 或 $60\text{ s}$），即校验「如果维持当前档位运行一个前瞻窗口 $\Delta_H$ 后是否越过 $T_{\max}$」，这样能提前数十秒拦截即将过热的指派。

4. **档位频率与算步耗时 `iter_time` 的解耦程度**  
   功率和温度已经只由离散档位 $z_{j,k}$ 决定，但单步推理耗时 `iter_time(nd, ctx, f_k)` 仍受批大小与上下文影响。在 MILP 目标系数 $\Delta U_{r,s,d,p}$ 的预计算阶段，可按目的星当前负荷或各档位典型批大小估算 $\hat{t}^{\text{move}}$，保证 MILP 系数矩阵完全线性。

5. **最终评估指标的同步简化**  
   在沿用 `record.py::summarize` 原有核心吞吐与时延指标（`good_long_frac`、`goodput_tok_s`、`waste_ratio`、`long_p95_all_s`、`migrations`、`mig_abort`、`link_GB_hops`）的基础上，将原 `throttle_s` 扩展为离散功率体系下的可观测指标：**零功率空闲时间占比（`zero_power_frac`）、各工作档时间占比、累计总能耗（`energy_kj_total`）以及全网最小温限裕度（`min_thermal_margin_C`）**。


---

## 六、多时隙时空联合 ILP（`120s` 上限）的可扩展性边界与专用滚动贪心算法设计

1. **为什么带时间维度的完整规划（Time-Indexed Spatio-Temporal ILP）在 `120 s` 内算不出来或劣化？**
   - 单步短视指派（$H=1$）看不到未来 $H$ 个时隙内的进出日影切换、跨步一阶 RC 热量累积以及多跳 ISL 链路拥塞。
   - 若直接写出多时隙精确整数规划（`discrete_time_ilp`）：联合决策时隙 $\tau \in \{0, \dots, H-1\}$ 上的请求驻留 $y_{r,j,\tau} \in \{0,1\}$、跨星迁移 $m_{r,e,\tau} \in \{0,1\}$ 与离散功率档 $z_{j,k,\tau} \in \{0,1\}$，则二元变量规模按 $O(|\mathcal{R}|(|\mathcal{V}_c| + |\mathcal{E}|)H)$ 爆炸（`Walker 40 ~ 100` 星、$H=12\dots 20$ 时达数十万至数百万二元变量），且由于「零请求 `0W` 跳变开关」破坏 LP 松弛紧性，即便给足 **`time_limit = 120 s`** 求解预算，通用分支定界求解器（HiGHS）在中大规模下仍会超时无解或仅停留在高 Gap 次优解。

2. **专用结构感知算法：`discrete_rh_greedy`（源端 `0W` 排空联盟 + 多步线性 RC 前瞻贪心）**
   - **源星降档 / `0W` 排空联盟排序**：识别即将进入日影或热裕度紧迫的源星，对能使源星跨越离散档位阈值（尤其是从低功档彻底排空至 `0 W` 空闲档以触发最快指数散热）的请求集合赋予排空协同优先级；
   - **目的星 $H$ 步线性 RC 轨迹校验**：调用 `rollout_rc_temperatures` 在 $O(H)$ 时间内精确递推候选目的星未来 $H$ 个时隙的光照功率包络与结温轨迹，硬拦截任何会在未来触发 $T_j(\tau) > T_{\max}$ 的指派；
   - **边际效用/通信字节跳数比增量提交**：在满足 KV 显存、共享 ISL 边预算与 `rebalance_invariants` 公平配额下毫秒级出解。

3. **实验评测准则（`jm` 并行跑数，`120 s` 求解上限）**
   - 统一设定通用时空 ILP 求解器单次时间上限 `time_limit_s = 120.0`；
   - 在 `jm` 节点（注意容器 CPU 配额为 **8 核**，`nproc` 显示宿主 256 核不可直接采信；并发进程数控制在 `4~6` 且固定 `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1`，先 `nvidia-smi` 确认不影响在跑推理服务）并行跑规模扫描与 5-seed 端到端闭环评测；
   - 同时汇报 **单步/整轮求解时间（ms/s）** 与 **最终优化目标及有效吞吐（Objective / `good_long_frac` / `goodput_tok_s`，以 `place_once` 为 100% 参照基线）**，验证 `discrete_rh_greedy` 在求解速度数量级领先的同时，在 `120 s` 预算下取得比超时受限的普通时空 ILP 及短视基线更优的最终目标值。
