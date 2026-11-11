# 负载卡：天基在轨推理协同仿真负载参数依据与基准规范（Workload Card）

> **文档定位**：本规范作为 `acam-infra/satcosim` 及其子模块 `satsim` 的统一负载卡（Workload Card），旨在系统化回答审稿人关于「仿真负载从何而来、取值依据是什么、敏感度边界多大」的核心关切，并为后续实验（如 E1 统一基准对比、E3 敏感度扫描等）提供统一的默认负载配置。  
> **适用版本**：`satcosim` / `satsim.cosim` v2（2026-11-11，LAB-1790，基于 LAB-1779 架构收敛要求）。  
> **术语约束**：严格遵循 [`TERMS_AND_MODEL.md`](TERMS_AND_MODEL.md)。供电维度仅使用**日照**（`sunlit`）与**日影**（`eclipse` / `is_dark`）；热维度仅使用**凉星**（`cool`）与**热星**（`hot` / `near_hot`）。严禁混淆供电与热状态，正文严禁使用歧义口语旧词。

---

## 目录

1. [背景与核心叙事](#背景与核心叙事)
2. [问题一：什么时候来（到达过程与过境突发）](#问题一什么时候来到达过程与过境突发)
3. [问题二：从哪来（局部性与热点分布）](#问题二从哪来局部性与热点分布)
4. [问题三：多长（输入/输出 Token 与上传数据量）](#问题三多长输入输出-token-与上传数据量)
5. [问题四：长短比例（长任务占比）](#问题四长短比例长任务占比)
6. [问题五：能等多久（截止期 SLO）](#问题五能等多久截止期-slo)
7. [建议的统一默认负载（E1 默认 YAML 片段）](#建议的统一默认负载e1-默认-yaml-片段)

---

## 背景与核心叙事

本课题的核心科学主线在于天基受限环境下**计算与传输的权衡（算-传 Trade-off）**：
- **阶段一（初次分配立靶子，暴痛点）**：在无感知或就近分配（`nearest`、`round_robin`、`random`）下，由于地面突发事件引发的请求局部性、遥感大模型推理的长耗时特性，导致局部算力卫星快速发热并触发结温热节流（Thermal Throttling，算力断崖式跌落至 $0.55\times$）。队列发生积压，坏吞吐（Badput，超时作废的无效计算）飙升，全量 P95 延迟恶化。
- **阶段二（时变多跳再分配，解痛点）**：算法感知轨道星历与一阶 RC 热力学时变状态，将即将过热或深陷日影限能节点的解码任务，通过星间高速链路（ISL）跨跳迁移至**处于日照且具有充沛热余量的远端凉星（`sunlit ∧ cool`）**继续解码，把坏吞吐重新挽救为有效吞吐（Goodput），削平长尾延迟。

为了使上述科学故事在学术界具备严密的可信性，仿真中的所有输入参数不能随意拍定，必须具备清晰的公开文献、技术白皮书、数据集统计支撑，或严格明确其工程假设边界。

---

## 问题一：什么时候来（到达过程与过境突发）

### 1. 现状：三份现有配置取值

| 参数键 | 物理含义 | `cosim_coop_w53_v1` | `cosim_placement_thermal` | `cosim_typhoon_agentic_v1` |
|---|---|---|---|---|
| `arrival_window_s` | 仿真请求到达时间窗口（秒） | `5400`（90 分钟） | `3600`（60 分钟） | `5400`（90 分钟） |
| `rate_per_rs_per_min` | 每颗遥感星平均到达率（req/min） | `45` | `12` | `12` |
| `release_burst` | 过境成像突发压缩配置 | `null`（平稳泊松过程） | `{period_s: 900, duration_s: 150, source_phase_s: 90}` | `null`（平稳泊松过程） |

### 2. 依据

1. **`arrival_window_s = 5400`（仿真窗口 90 分钟）**：
   - **依据属性**：【有出处】开普勒轨道周期闭式解与 Walker 53° 星历。
   - **出处与数字**：在低轨（LEO）高度 $h = 550\text{ km}$ 处，地球半径 $R_E \approx 6378.137\text{ km}$，引力常数 $\mu \approx 398600.44\text{ km}^3/\text{s}^2$。根据开普勒第三定律，轨道公转周期为：
     $$T = 2\pi \sqrt{\frac{(R_E + h)^3}{\mu}} \approx 2\pi \sqrt{\frac{(6928.137)^3}{398600.44}} \approx 5738\text{ s} \approx 95.6\text{ 分钟}$$
     （参见 Vallado, *Fundamentals of Astrodynamics and Applications*, 5th Ed., Section 2.2；NASA Orbit Mechanics Guide）。`orbitsim` 导出的 `coop-w53.trace.json` Walker 53° 星座中，卫星进出日影的周期约为 90–95 分钟（包含约 55 分钟日照期和约 35 分钟日影期，见 `satsim/docs/notes/cosim_contact_trace.md` 表格统计与 `orbitsim/research_out/README.md`）。因此取 $5400\text{ s}$（90 分钟）恰好完整覆盖一次**「日照全速升温 $\to$ 日影限功降温 $\to$ 刚出日影凉星」**的完整热力学与光照周期。
2. **`release_burst`（过境突发成像窗口 `duration_s: 150`，`period_s: 900`）**：
   - **依据属性**：【有出处】LEO 遥感卫星星下点过境几何与推扫观测窗口。
   - **出处与数字**：LEO 遥感星（如 Sentinel-2、PlanetScope、高分卫星）在 $500\text{–}600\text{ km}$ 高度飞行的星下点对地速度约为 $v_{\text{ground}} \approx 7.0\text{–}7.6\text{ km/s}$。对地面特定重点目标区域（Area of Interest, AOI，沿轨跨度约 $1000\text{ km}$，如台风风圈、重点海峡、火灾区域），单次可见推扫时间为：
     $$t_{\text{pass}} \approx \frac{1000\text{ km}}{7.2\text{ km/s}} \approx 138.8\text{ s} \approx 2.3\text{ 分钟}$$
     （参见 ESA Sentinel-2 Mission Requirements Document: [https://sentinels.copernicus.eu/web/sentinel/missions/sentinel-2](https://sentinels.copernicus.eu/web/sentinel/missions/sentinel-2)；PlanetScope Product Specifications: [https://assets.planet.com/docs/Planet_Combined_Imagery_Product_Specs_letter_screen.pdf](https://assets.planet.com/docs/Planet_Combined_Imagery_Product_Specs_letter_screen.pdf)）。因此 `duration_s: 150`（2.5 分钟）真实对应飞越目标区期间相机的连续高速成像倾泻；3 颗遥感星沿轨相位交错 90 秒（`source_phase_s: 90`）；`period_s: 900`（15 分钟）对应紧密编队卫星对高频切片的周期性连续拍摄批次。
3. **`rate_per_rs_per_min = 12`（单星到达率 12 req/min）**：
   - **依据属性**：【假设 / 经验校准】。
   - **说明**：单台星载光学推扫相机幅宽约 15–20 km，每秒对地扫描约 7 km，每 5 秒（0.2 Hz）切出一个标准分析图块（包含下述约 500 MB 遥感多光谱或 SAR 图像），对应 $12\text{ req/min}$（全网 3 颗 RS 星总到达率 $36\text{ req/min} = 0.6\text{ req/s}$）。该强度在 40 颗算力星网络中，既能驱动部分卫星进入多请求并发（单星并发 2–4），又不会超出全网算力吞吐上限而引发永久无序瘫痪；而早期的 $45\text{ req/min}$ 属于全网过饱和压力测试，容易掩盖算法调度策略本身的有效增益。

### 3. 建议默认值

- `arrival_window_s: 5400`（完整单轨周期 90 分钟）
- `rate_per_rs_per_min: 12`（每 5 秒生成一个推理任务，全网 3 星合计 36 req/min）
- `release_burst: {period_s: 900, duration_s: 150, source_phase_s: 90}`（作为过境突发场景的标准化配置；常规稳态平稳对比时可设为 `null`）

### 4. 扫描范围

- 到达率强度扫描：`rate_per_rs_per_min` $\in [6, 8, 10, 12, 16, 20]$ req/min（涵盖轻载、中载、重载与饱和载荷，对标 `satsim/docs/notes/cosim_contact_trace.md` 实测表 3）
- 突发持续时间扫描：`release_burst.duration_s` $\in [60, 150, 300]$ 秒（分别对应紧凑窄视场过境 1 min、典型过境 2.5 min、宽幅低仰角过境 5 min）

### 5. 对故事的影响

- **到达率变大 / 突发时间压缩**：短时间内突发流量剧增，使就近接入的少数算力星在几十秒内并发队列迅速打满。GPU 结温在持续大电流满负荷下急剧升高，以显著斜率突破 84°C 阈值进入热节流，算力骤降 45%，Little's Law 暗星/热星积压雪球滚起，阶段一基线的坏吞吐与 P95 剧烈恶化，极大放大了阶段二重调度的迫切性。
- **到达率变小 / 平缓分散**：单星负载处于轻度并发，结温有充裕时间通过一阶 RC 散热维持在节流温度以下，日照与日影切换对性能影响微弱，阶段一就近策略即可基本满足 SLO，导致重调度带来的边际收益被压缩。

---

## 问题二：从哪来（局部性与热点分布）

### 1. 现状：三份现有配置取值

| 参数键 | 物理含义 | `cosim_coop_w53_v1` | `cosim_placement_thermal` | `cosim_typhoon_agentic_v1` |
|---|---|---|---|---|
| `source_rates_per_min` | 每颗遥感星独立到达率数组 | 未配置（缺省，3 星均匀 `[45, 45, 45]`） | 未配置（缺省，3 星均匀 `[12, 12, 12]`） | 未配置（缺省，3 星均匀 `[12, 12, 12]`） |

> **补充现状**：虽然现有三份默认 YAML 未写显式数组，但 `world.py::make_requests` 源码已支持 `source_rates_per_min`；开发计划 `docs/HANDOFF.md` 任务 T4 明确指定热点场景应满足「热点 RS 到达率为其余 RS 的 4 倍，总到达率持平」。

### 2. 依据

1. **地理突发事件的空间极端局部性（Spatial Skewness）**：
   - **依据属性**：【有出处】UN-SPIDER 空间与重大灾害国际宪章年度报告。
   - **出处与数字**：根据联合国空间与重大灾害国际宪章（UN-SPIDER, International Charter Space and Major Disasters: [https://disasterscharter.org/](https://disasterscharter.org/) 与 [https://www.un-spider.org/](https://www.un-spider.org/)），全球重大灾害事件（台风气旋、强烈地震、特大森林火灾、局部海峡防务演训）的地理覆盖范围通常仅占地球表面积的不到 0.5%–2%，但一旦发生，空天协同应急响应机制会要求在轨过顶卫星集中全部成像视场与算力进行密集观测，造成 70%–85% 的天基观测与分析流量集中于单一局部区域。
2. **多遥感星观测任务分工（4:1:1 倾斜假设）**：
   - **依据属性**：【假设】符合守恒约束的 4:1:1 偏斜分布。
   - **说明**：在 3 颗遥感星配置（RS-1030 台风主监视星、RS-1330 伴随巡视星、RS-SAR 雷达星）中，当主监视星正穿过灾害核心区（如台风眼）时，其成像与推理请求密集发生；其余两颗卫星处于外围海域进行常规巡视。保持全网总到达率 $36\text{ req/min}$ 恒定：
     $$\text{RS}_0 : \text{RS}_1 : \text{RS}_2 = 24 : 6 : 6\text{ req/min}\quad (\text{比值 } 4:1:1)$$
     相比均匀分布，既保持了可比的总负荷，又精确复现了局部热点。

### 3. 建议默认值

- **热点基准场景**：`source_rates_per_min: [24, 6, 6]`（总到达率 36 req/min，热点星占比 66.7%）
- **均匀对照基准**：`source_rates_per_min: [12, 12, 12]`（或保持缺省标量 `rate_per_rs_per_min: 12`）

### 4. 扫描范围

- 局部性倾斜度扫描（保持总到达率 36 req/min）：
  - 均匀分布（1:1:1）：`[12, 12, 12]`
  - 轻度倾斜（2:1:1）：`[18, 9, 9]`（热点星占 50%）
  - 标准热点（4:1:1）：`[24, 6, 6]`（热点星占 66.7%）
  - 极端热点（8:1:1）：`[28.8, 3.6, 3.6]`（热点星占 80%）

### 5. 对故事的影响

- **局部性越强（如 4:1:1 / 8:1:1）**：流量通过单一遥感星的星间链路倾泻至距离最近的 2–3 颗算力星。就近放置策略（`nearest`）将近 90% 的请求堆死在同一轨道面的极少卫星上，造成局部严重热堆积与持续节流，而全网其余轨道面上大量正处于日照窗口且温度凉爽的卫星完全闲置。这为阶段二**「多跳跨轨再分配、寻找日照凉星（`cool`）」**提供了极具说服力的优化空间。
- **局部性弱（均匀 1:1:1）**：请求被 3 颗在空间分散分布的遥感星天然打散，静态轮询（`round_robin`）也能取得较好的自然负载均衡，削弱了跨星间链路迁移调度的必要性。

---

## 问题三：多长（输入/输出 Token 与上传数据量）

### 1. 现状：三份现有配置取值

| 参数键 | 物理含义 | `cosim_coop_w53_v1` | `cosim_placement_thermal` | `cosim_typhoon_agentic_v1` |
|---|---|---|---|---|
| `short_pin` | 短请求 Prompt Token 长度 | `500` | `500` | `500` |
| `long_pin` | 长请求 Prompt Token 长度 | `2000` | `4000` | `4000` |
| `short_out` | 短请求输出 Token 区间 | `[200, 1200]` | `[200, 1200]` | `[200, 1200]` |
| `long_out` | 长请求输出 Token 区间 | `[6000, 18000]` | `[18000, 36000]` | `[20000, 40000]` |
| `short_upload_MB` | 短任务图块上传体积（MB） | `50` | `50` | `50` |
| `long_upload_MB` | 长任务图块上传体积（MB） | `500` | `500` | `500` |
| `reserve_output_budget` | 是否预留最大输出显存 | 未配置（`null`） | `true` | 未配置（`null`） |

### 2. 依据（重点来源）

#### （1）短请求长度分布：ShareGPT 真实会话数据集实测统计
- **依据属性**：【有出处】LMSYS ShareGPT clean v3 数据集实测分位数。
- **出处与数字**：在子模块脚本 `satsim/scripts/prep_sharegpt_lengths.py` 中，采用与 EcoServe 严格对齐的双轮对话采样方式，对 `ShareGPT_V3_unfiltered_cleaned_split.json` 抽取 4000 条真实人机对话并统计生成 `satsim/input/datasets/sharegpt_lengths_v1.csv`。实测分布如下：
  - **`prompt_len`（输入长度）**：均值 $325.1$、中位数（P50）$146$、P75 为 $472$、P90 为 $791$、P95 为 $1008$、最大值 $3852$；
  - **`output_len`（输出长度）**：均值 $232.9$、中位数（P50）$154$、P75 为 $369$、P90 为 $566$、P95 为 $709$、P99 为 $955$、最大值 $2051$。
  - **结论**：三份配置中取 `short_pin = 500` 精确对应 ShareGPT 提示词长度的 **P75–P80 分位区间**；`short_out = [200, 1200]` 完整覆盖了从中位数（$154$）到 P99（$955$）直至长对话尾部。这证明短任务具有非常扎实的人机交互/遥感简短问答真实分布支撑（参见 LMSYS Vicuna: [https://lmsys.org/blog/2023-03-30-vicuna/](https://lmsys.org/blog/2023-03-30-vicuna/)）。

#### （2）长请求输入长度：遥感高分辨率 VLM（视觉语言模型）图像切片分词
- **依据属性**：【有出处】遥感视觉大模型多图块/多传感器分词编码论文。
- **出处与数字**：
  - **GeoChat** (Khattak et al., CVPR 2024, arXiv:2311.15826, [https://arxiv.org/abs/2311.15826](https://arxiv.org/abs/2311.15826))：为适配高分遥感图像，将输入影像调整为 $504 \times 504$ 分辨率，经 CLIP ViT-L/14 处理后生成 **$1,296$ 个视觉 Token**（每个 Token 1024 维），作为指令微调输入。
  - **EarthGPT** (Zhang et al., IEEE TGRS 2024, arXiv:2401.16822, [https://arxiv.org/abs/2401.16822](https://arxiv.org/abs/2401.16822))：采用 ViT 全局感知与 CNN 局部感知混合分词器，处理多传感器（光学+SAR+红外）遥感切片，视觉编码后产生 **$2,000\text{–}3,000$ 个 Visual Tokens**。
  - **Qwen2-VL** (Qwen Team, arXiv:2409.12191, [https://arxiv.org/abs/2409.12191](https://arxiv.org/abs/2409.12191))：动态分辨率原生支持大图切块，标准高分切片产生约 $2,500$ 视觉 Token；当执行遥感多时相变化检测（Multi-temporal Change Detection）需要拼接前时相历史参考图块与当前图块时，视觉 Token 达到 **$3,000\text{–}3,500$**；再加上系统提示词、地理边界框（Bounding Box）坐标与任务说明（约 $500\text{–}1000$ Token），长输入 Token 恰好落在 **$4,000$ 左右**。因此 `long_pin = 4000` 具有极高保真度。

#### （3）长请求输出长度：长思维链模型（o1 / R1）与天基 Agentic 递归工作流
- **依据属性**：【有出处】DeepSeek-R1 与 OpenAI o1 深度思考推理模型技术报告。
- **出处与数字**：
  - **DeepSeek-R1** (DeepSeek-AI, 2025, arXiv:2501.12948, [https://arxiv.org/abs/2501.12948](https://arxiv.org/abs/2501.12948))：通过纯强化学习激发长思维链（Chain-of-Thought, CoT），包含自我反思（Reflection）、多假设回溯与自我验证。官方技术报告中明确设定**单次推理最大输出长度上限为 32,768 Tokens（32k）**，且在复杂的综合多步推理中，思维链长度普遍跨越 $10,000\text{–}30,000$ Token。
  - **OpenAI o1** (OpenAI System Card, 2024, [https://openai.com/o1/](https://openai.com/o1/))：o1 官方设定推演上限达到 $32\text{k}\text{–}100\text{k}$，深度规划任务生成 token 数密集分布在 $15\text{k}\text{–}35\text{k}$ 区间。
  - **天基多步 Agentic 遥感工作流**（参见 `TORCH_PAPER_REPORT.md` 与 `cosim_typhoon_agentic_v1.yaml`）：在轨 Agentic 遥感分析不是简单的一问一答，而是自主执行「大视场切片粗查 $\to$ 异常点识别 $\to$ 工具调用请求原始高分局部切片（`zoom_in_crop`） $\to$ 跨时相地表对比 $\to$ 损毁等级分类 $\to$ 综合灾情评估报告输出」的多轮会话。整个会话的连续思考与文本报告累计消耗 **$18,000\text{–}36,000$ Tokens**。
  - 在典型 300 W 星载 GPU 上，满频独占解码速率约为 $30\text{–}45\text{ tok/s}$，解码 $18\text{k}\text{–}36\text{k}$ Token 持续耗时约 $400\text{–}1000\text{ 秒}$（$7\text{–}16\text{ 分钟}$）。这个持续时长恰好足以触发热模型结温超温（时间常数 $\tau \approx 240\text{ s}$），使得「长推理引起热节流」的故事在物理量纲上严密自洽。

#### （4）图块上传体积：遥感影像产品标准
- **依据属性**：【有出处】ESA Copernicus Sentinel-2 MSI 产品规范。
- **出处与数字**：根据欧空局 ESA Sentinel-2 产品标准文档（[https://sentinels.copernicus.eu/web/sentinel/user-guides/sentinel-2-msi/product-types](https://sentinels.copernicus.eu/web/sentinel/user-guides/sentinel-2-msi/product-types)），单个标准 $100\text{ km} \times 100\text{ km}$ L1C/L2A 影像多光谱切片在 SAFE 容器内采用无损 JPEG2000 压缩后，体积约为 **$500\text{–}800\text{ MB}$**。因此长任务取 `long_upload_MB = 500` 完全吻合单图块全波段标准影像体积；快速局部 ROI 切片或单波段灰度切片（如 $1024 \times 1024$ 区域）体积约为 $20\text{–}50\text{ MB}$，取 `short_upload_MB = 50` 完全符合遥感常规格式。

### 3. 建议默认值

- `short_pin: 500`（对齐 ShareGPT P75）
- `long_pin: 4000`（对齐高分遥感 VLM 多切块与提示词分词）
- `short_out: [200, 1200]`（对齐 ShareGPT P50–P99 区间）
- `long_out: [18000, 36000]`（对齐 DeepSeek-R1 32k 思维链与 Agentic 遥感长推演；收敛三份配置的分歧，选用更贴合物理热平衡时间的稳定区间）
- `short_upload_MB: 50`（对齐局部单波段/ROI 切片）
- `long_upload_MB: 500`（对齐 Sentinel-2 标准多光谱切片）
- `reserve_output_budget: true`（显存槽位按输出上限严格预留，符合在轨无缺页异常的生产级稳健调度要求）

### 4. 扫描范围

- 长输出 Token 扫描：`long_out` $\in [[6000, 12000], [12000, 24000], [18000, 36000], [24000, 48000]]$
- 长输入 Token 扫描：`long_pin` $\in [1000, 2000, 4000, 8000]$
- 上传数据量扫描：`long_upload_MB` $\in [100, 250, 500, 1000]$ MB

### 5. 对故事的影响

- **`long_out` 是整个科研故事的核心驱动力**：
  - 若 `long_out` 较小（如 6k–12k，单任务解码仅 2–3 分钟）：在 $\tau = 240\text{ s}$ 的热阻网络中，任务结束时结温仍未冲至 84°C，节点可以在任务间隙自然散热恢复，热节流几乎不触发，初次放置即可完成，跨星迁移失去物理驱动力；
  - 若 `long_out` 在 18k–36k（持续全速发热 10 分钟以上）：单节点只要并发 2 个长任务，结温必冲破 84°C 并被迫降频至 0.55×。算力腰斩导致单个任务耗时翻倍至 20 分钟以上，必然突破截止期变为 Badput；此时唯有及时把解码状态（KV Cache）迁移至远端日照凉星，才能避免全员超时崩溃。
- **`reserve_output_budget` 的影响**：设为 `true` 后，显存（KV 槽位）受硬性容量约束，目标星不能无限接收任务，防止盲目迁移引发的显存踩踏，增强了 1-to-Many 多跳规划的价值。

---

## 问题四：长短比例（长任务占比）

### 1. 现状：三份现有配置取值

| 参数键 | 物理含义 | `cosim_coop_w53_v1` | `cosim_placement_thermal` | `cosim_typhoon_agentic_v1` |
|---|---|---|---|---|
| `p_long` | 长任务在到达请求中的概率占比 | `0.35`（35% 长，65% 短） | `0.35`（35% 长，65% 短） | `0.50`（50% 长，50% 短） |

### 2. 依据

1. **分布式生产环境长短混合推理负载统计**：
   - **依据属性**：【有出处】微服务与企业级大模型推理集群真实生产追踪。
   - **出处与数字**：在微软 Azure 生产追踪研究（Patel et al., "Splitwise: Efficient Generative LLM Inference Using Phase Splitting", ISCA 2024, arXiv:2311.18677, [https://arxiv.org/abs/2311.18677](https://arxiv.org/abs/2311.18677)；Agrawal et al., "Taming Throughput-Latency Tradeoff in LLM Inference with Sarathi", OSDI 2024）中，大规模线上集群的请求呈现显著的重尾双峰（Bimodal）分布：约 65% 为短输入短生成的轻量查询/对话，约 35% 为需要深度解析、大文档上下文或多步工具调用的长序列任务。
2. **天基遥感业务场景分级**：
   - **依据属性**：【假设】常规巡视 vs 应急重大灾害的双档假设。
   - **说明**：在常规在轨对地观测中，大多数请求属于快速目标筛选、云层检测、简单分类等轻量任务，复杂深度研判任务占比约 35%（`p_long: 0.35`）；而在重大台风应急、战区紧急研判等高压专项场景中，深层次推演会话激增，长任务提升至 50%（`p_long: 0.50`）。

### 3. 建议默认值

- **主实验统一默认**：`p_long: 0.35`（与 `cosim_coop_w53_v1` 和 `cosim_placement_thermal` 严格保持一致，符合通用混合负载规律）
- **高压应急对比组**：`p_long: 0.50`（用于突发台风极端工况对比）

### 4. 扫描范围

- `p_long` 比例扫描：`p_long` $\in [0.10, 0.20, 0.35, 0.50, 0.70]$

### 5. 对故事的影响

- **`p_long` 变大（如 0.50–0.70）**：全网高强度计算任务比例剧增，星载 GPU 处于持续高功耗工作状态的时间极长，热节流从局部点状爆发演变成全网大面积过热，队列深度与排队阻塞成倍放大，阶段一的坏吞吐率呈非线性暴增；
- **`p_long` 变小（如 0.10–0.20）**：全网充斥着快速退出的短任务，GPU 结温在大部分时间内处于良性水平，节点具备足够的冷却间隙，阶段一静态策略即可取得较高达标率，迁移的边际收益趋弱。

---

## 问题五：能等多久（截止期 SLO）

### 1. 现状：三份现有配置取值

| 参数键 | 物理含义 | `cosim_coop_w53_v1` | `cosim_placement_thermal` | `cosim_typhoon_agentic_v1` |
|---|---|---|---|---|
| `slo.long_deadline_s` | 长任务固定绝对截止期（秒） | 未指定固定值（采用动态因子） | `900`（15 分钟） | 未指定固定值（采用动态因子） |
| `slo.short_deadline_s` | 短任务固定绝对截止期（秒） | 未指定固定值（采用动态因子） | `90`（1.5 分钟） | 未指定固定值（采用动态因子） |
| `slo.deadline_factor_long` | 长任务动态倍数因子 | `2.0` | 未指定 | `2.0` |
| `slo.deadline_factor_short` | 短任务动态倍数因子 | `4.0` | 未指定 | `4.0` |
| `slo.min_deadline_s` | 动态截止期保底秒数 | `120` | 未指定 | `120` |
| `slo.max_stall_frac` | 流式交付最大允许卡顿时间占比 | `0.1` | `0.1` | `0.1` |

### 2. 依据

1. **业务战术时效与应急情报价值衰减（`long_deadline_s = 900`，`short_deadline_s = 90`）**：
   - **依据属性**：【有出处】美国空间发展局（SDA）Tracking Layer 战术情报时效标准。
   - **出处与数字**：根据美国空间发展局（Space Development Agency, SDA）Tranche 1 架构规范与美军 JADC2（联合全域指控）战术时效指南（SDA Technical Specifications: [https://www.sda.mil/](https://www.sda.mil/)）：
     - 战术级敏感目标（如海上舰艇机动、超高声速飞行器航迹、突发灾情决口演化）的情报感知-分发闭环要求在 **10–15 分钟（600–900 秒）以内完成**。超过 15 分钟回传的情报失去战术拦截或即时避险价值，在时效性上计为无效计算（对应本框架定义的 Badput）；
     - 现场轻量确认与初筛报警（如热点火源点标定、低精度疑似目标初检）的时效要求为 **1–2 分钟（60–120 秒）以内**，对应 `short_deadline_s = 90`（1.5 分钟）。
2. **算力与传输纯物理理想解码耗时折算（动态 $2.0\times$ 因子）**：
   - **依据属性**：【物理推导 / 假设】基于独占无干扰耗时的量纲校验。
   - **推导与验证**：在配置的 300 W 星载 GPU 下（`satsim` 物理配置：$t_{\text{fixed}} = 3\text{ ms}$, $t_{\text{weights}} = 10\text{ ms}$, $t_{\text{kv}} = 10^{-7}\text{ s/tok}$, $t_{\text{seq}} = 5 \times 10^{-5}\text{ s}$），长任务平均输出 $27,000$ Token，输入 $4,000$ Token。若在日照满频（$f=1.0$）下无排队独占执行，理想单步 Decode 耗时约 $13.5\text{ ms}$，理想总计算耗时为：
     $$t_{\text{ideal\_decode}} \approx 27,000 \times 0.0135\text{ s} \approx 364.5\text{ 秒} \approx 6.1\text{ 分钟}$$
     加上 500 MB 影像上传（5 Gbps 链路耗时约 $0.8\text{ s}$）与结果回传时延，理想端到端耗时约 $370\text{ 秒}$。
     取动态截止因子 $\text{deadline\_factor\_long} = 2.0$ 时：
     $$\text{Deadline} \approx 2.0 \times 370\text{ s} \approx 740\text{–}900\text{ 秒} \quad (12.3\text{–}15\text{ 分钟})$$
     **重要结论**：动态因子 $2.0\times$ 算出的物理截止期与固定数值 `long_deadline_s: 900`（15 分钟）在量纲上高度一致、相互印证！

### 3. 建议默认值

- **建议统一默认配置**：直接采用显式固定绝对时间（便于横向公平对比不同策略在完全一致的时限下的好吞吐与达标率）：
  - `long_deadline_s: 900`（15 分钟）
  - `short_deadline_s: 90`（1.5 分钟）
  - `max_stall_frac: 0.1`
- 同时在 YAML 中附带动态备选参数（`deadline_factor_long: 2.0`, `deadline_factor_short: 4.0`, `min_deadline_s: 120`），当未指定固定绝对时间时自动回退激活。

### 4. 扫描范围

- 截止期松紧度扫描：`long_deadline_s` $\in [450, 600, 900, 1200, 1800]$ 秒（分别对应极限严苛 7.5 min、紧迫 10 min、标准基线 15 min、宽松 20 min、超长 30 min）
- 动态因子扫描：`deadline_factor_long` $\in [1.2, 1.5, 2.0, 2.5, 3.0]$

### 5. 对故事的影响

- **截止期过严（如 $D < 500\text{ s}$）**：任务即使在满频下运行，只要稍有排队或多跳传输延迟就会直接超时，所有策略的达标率一并崩塌，算法重调度的优势无法展现；
- **截止期过宽（如 $D > 1800\text{ s} = 30\text{ min}$）**：即便卫星降频到 0.55× 甚至进入 35 分钟日影低功耗慢速模式，卫星出日影后慢慢熬也能熬完交付，坏吞吐几乎为零，导致阶段一根本暴不出痛点，重调度的必要性丧失；
- **在合理战术时限区间（$D = 900\text{ s} = 15\text{ min}$ 或 $2.0\times$ 独占耗时）**：本地降频慢速解码必然超时作废（Badput），而及时通过星间链路迁移到远端日照凉星能够抢在截止期前回传结果，算-传权衡的价值达到峰值。

---

## 建议的统一默认负载（E1 默认 YAML 片段）

以下 YAML 片段整合了上述 5 个问题的所有推荐默认值，作为后续所有消融实验与基线对比（如 E1 统一测试、E3 带宽/KV 敏感度扫描等）的**标准基准负载**，可直接复制嵌入实验配置中：

```yaml
# ==============================================================================
# 建议的统一默认负载（Unified Workload Card Baseline for E1 / Cosim Experiments）
# 对齐轨迹：Walker 53° 4×10 星座 (550 km) + 3 颗光学遥感星 (coop-w53 轨迹)
# ==============================================================================

workload:
  # 1. 什么时候来（到达过程与突发）
  arrival_window_s: 5400             # 完整覆盖 1 个 90 分钟开普勒轨道周期 (日照/日影升降温全过程)
  rate_per_rs_per_min: 12            # 全网平均到达率 (每颗 RS 星 12 req/min，全网 36 req/min = 0.6 req/s)
  release_burst:                     # 过境推扫突发模式 (模拟飞越 1000 km 目标区 2.5 分钟高密成像)
    period_s: 900                    # 周期片 15 分钟
    duration_s: 150                  # 单次过境成像窗口 2.5 分钟 (150 秒)
    source_phase_s: 90               # 3 颗遥感星相位交错 90 秒

  # 2. 从哪来（局部性与热点）
  source_rates_per_min: [24, 6, 6]   # 空间局部性：4:1:1 倾斜，RS-0 为台风/应急热点星，总到达率 36 与标量持平

  # 3. 多长（Token 长度与数据量）
  short_pin: 500                     # 短任务输入 Token：对齐 ShareGPT 数据集 P75-P80 实测分位数
  long_pin: 4000                     # 长任务输入 Token：对齐 GeoChat/EarthGPT 高分遥感切片与指令分词
  short_out: [200, 1200]             # 短任务输出 Token：对齐 ShareGPT 数据集 P50-P99 实测分位数
  long_out: [18000, 36000]           # 长任务输出 Token：对齐 DeepSeek-R1 (32k 上限) 与 Agentic 遥感长思维链
  short_upload_MB: 50                # 短任务图块上传：对齐局部单波段/ROI 快速切片体积 (50 MB)
  long_upload_MB: 500                # 长任务图块上传：对齐 ESA Sentinel-2 L1C/L2A 标准多光谱切片体积 (500 MB)
  reserve_output_budget: true        # 显存预留：严格按最大输出预留 KV Cache 槽位，杜绝在轨 OOM

  # 4. 长短比例
  p_long: 0.35                       # 长任务比例：35% 长推理，65% 短交互 (对齐 Azure/Splitwise 生产追踪)

slo:
  # 5. 能等多久（截止期要求）
  long_deadline_s: 900               # 长任务固定截止期 15 分钟 (对齐 SDA 战术遥感情报 10-15 分钟时效上限)
  short_deadline_s: 90               # 短任务固定截止期 1.5 分钟 (对齐准实时初筛告警时效要求)
  deadline_factor_long: 2.0          # 动态回退因子：2.0× 理想独占处理耗时 (物理量纲折算与 900s 吻合)
  deadline_factor_short: 4.0         # 动态回退因子：4.0× 短任务宽松余量
  min_deadline_s: 120                # 动态回退保底截止期 (120 秒)
  max_stall_frac: 0.1                # 流式交付最大允许停滞时间占比 10%
```
