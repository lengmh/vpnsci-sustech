# AGENTS.md — vpnsci-sustech 项目协作手册

本文件适用于仓库根目录及其子目录。若子目录存在更近层级的
`AGENTS.md` / `CLAUDE.md`，以更近层级规则为准。

本项目继续继承全局 Codex/Claude 安全规则，尤其是：

- 临时文件、测试中间产物、一次性脚本输出放到
  `F:\AI playground\TempFiles`。
- Python / pytest / 脚本执行优先用当前项目环境：
  `uv run python ...`、`uv run pytest ...`。
- 不要裸跑 `python` / `pytest`，除非已确认指向当前 `.venv`。
- 不要删除仓库外文件；删除仓库内非临时文件前需要用户明确同意。
- 新增/修改源码、Markdown、JSON、配置统一 UTF-8 无 BOM。

## 1. 项目定位

`vpnsci-sustech` 是面向 AI Agent 的学术论文检索与全文获取工具。

核心能力：

- MCP 服务入口：`vpnsci_sustech.mcp_server`
- CLI 入口：`vpnsci_sustech.cli`
- 标准检索：OpenAlex-first，Semantic Scholar / publisher-native backend
  补充，保存可恢复 `SearchSession`
- 全文获取：优先开放来源；必要时通过学校代理 / WebVPN / EZproxy /
  浏览器流程尝试机构订阅
- 报告桥接：将标准检索会话显式升级到 `paper-search-pro` 报告流程
- 报告恢复：基于 download workflow sidecar / SearchSession 重建报告输入

术语优先参考 `CONTEXT.md`。尤其注意：

- “标准检索”不是“专业调研”。
- “升级建议”不能自动触发“专业调研”。
- `seed_preview` / `seed_classified` 不能冒充 `full`。
- CNKI 必须走受控路由，普通中文 query 不默认访问 CNKI。
- `hit_key` 是会话结果级 continuation 的稳定标识，不能用数组序号替代。

## 2. 主要目录与职责

```text
vpnsci_sustech/
  cli.py                         # CLI 命令
  mcp_server.py                  # MCP 工具入口
  fetcher.py                     # 通用全文获取内核
  sources/                       # OpenAlex / Semantic Scholar / publisher backends
  report_bridge.py               # 搜索会话到报告流程的桥接
  report_recovery.py             # 报告恢复
  download_workflows.py          # 下载工作流 sidecar
  theme_clustering.py            # 报告主题 fallback / clustering
  theme_postprocess.py           # Phase E display postprocess
  data/                          # 包内运行时 JSON 数据

tools/
  paper-search-pro/              # bundled 报告运行时与前端资产
  theme-lexicon/                 # 主题概念 alias 离线构建/验证脚本

docs/
  agent-workflows/               # Agent 工作流合同和报告流程文档

tests/
  test_*.py                      # 回归测试源码；测试产物仍忽略

lexicons/
  sources/ normalized/ builds/ candidates/ review/
                                # alias pipeline 本地源和中间产物；gitignored
```

`.idea/`、`CONTEXT.md`、`lexicons/` 当前被 `.gitignore` 忽略。
`tests/` 测试源码应进入源码仓；`__pycache__`、`.tmp`、`.pytest_cache`
等测试产物仍忽略。

## 3. 常用验证命令

通用：

```powershell
uv run pytest -q
```

主题 alias pipeline 相关：

```powershell
uv run pytest `
  tests/test_theme_lexicon_fill_zh_alias_candidates.py `
  tests/test_theme_lexicon_pollution_guards.py `
  tests/test_theme_lexicon_block_accepted_alias_conflicts.py `
  tests/test_theme_lexicon_preserve_zh_review_decisions.py `
  tests/test_theme_lexicon_apply_zh_review_recommendations.py `
  tests/test_theme_lexicon_normalize_sources.py `
  tests/test_theme_lexicon_materialize_runtime_overlay.py `
  tests/test_theme_lexicon_query_alias_index.py `
  tests/test_theme_clustering_compact_alias_index.py `
  -q
```

报告前端源码变更后：

```powershell
pwsh -File scripts/refresh_report_frontend.ps1
```

MCP 入口冒烟：

```powershell
uv run python -m vpnsci_sustech.mcp_server
```

## 4. Theme Concept Alias Pipeline 当前状态

计划文件：

```text
.idea/plans/2026-06-08-theme-concept-alias-pipeline-plan.md
```

该 track 独立于 Phase E。Phase E 只处理报告 display-layer
postprocess；alias pipeline 构建 deterministic alias layer，用于把中英 /
同义候选合并到同一 `concept_id`。

边界：

- L1-L4：离线源解析、英文概念构建、中文候选、冲突验证与 review。
- L5：物化 runtime overlay 文件，但不改变现有运行时行为。
- L6：才允许把 runtime alias overlay 接入主题 fallback 逻辑。

当前 runtime alias 工作面：

```text
vpnsci_sustech/data/theme_concept_alias_index.json
vpnsci_sustech/data/theme_concept_alias_manifest.json
tools/paper-search-pro/assets/theme_concept_alias_index.json
tools/paper-search-pro/assets/theme_concept_alias_manifest.json
```

legacy full overlay 文件仍保留作回滚/清理确认对象：

```text
vpnsci_sustech/data/theme_concept_aliases.json
tools/paper-search-pro/assets/theme_concept_aliases.json
```

host Agent 默认不要打开 legacy full JSON 或 compact index 大文件做状态确认；
优先用 manifest、`summarize_alias_runtime.py`、`query_alias_index.py`。

运行时不得读：

```text
lexicons/sources/
lexicons/normalized/
lexicons/builds/
lexicons/candidates/
lexicons/review/
```

最新已知状态（2026-06-18 zh-exact-expansion-batch-261-to-280 后）：

- compact runtime `build_status`: `review_complete`
- 中文候选覆盖：当前仍以 `lexicons/candidates` 生成清单为准，约 25%+；
  runtime 覆盖是最终可用覆盖，中文覆盖仍未完成
- runtime 中文覆盖：`8373 / 48863 = 17.14%`
- runtime zh aliases: `8387`
- runtime en aliases: `189471`
- `en:accept`: `233199`
- `en:blocked`: `14798`
- `en:needs_review`: `0`
- `en:reject`: `101116`
- `zh:accept`: `8387`
- `zh:blocked`: `11491`
- `zh:needs_review`: `0`
- `zh:reject`: `173`
- accepted/runtime alias conflicts: `0`
- runtime en alias conflicts: `0`
- runtime zh alias conflicts: `0`
- runtime concept aliases: `48863`
- package/tool compact index byte-identical
- package/tool compact manifest byte-identical
- legacy full overlay package/tool 文件仍 byte-identical（batch-006 回滚保留，不默认读取；batch-280 运行时以 compact index/manifest 为准）
- compact index SHA-256:
  `b740d86d5a3f1017990e45bb37654058d01f001e4e712be532fb9758caa9be29`
- compact manifest SHA-256:
  `e94dce66f9ff2ec7467e833f549e3cfa190e7d4ed28b3626e8d2ebac66219cdc`
- legacy full overlay SHA-256:
  `a6b8d726383f78e919a6273dab727d7647a9495801a0873a75cd4c0ffde9a85b`
- pollution audit：
  - ordinary English-heavy zh aliases: `0`
  - known bad-shape hits: `0`
- compact index 是 batch-280 当前运行时真源；legacy full overlay 未随 batch-007 至 batch-280 更新，不再作为默认等价检查对象。
- 最近相关测试：`343 passed in 2.73s`。

当前下一步：

- L5.5 紧凑 runtime index / manifest / query 工作面迁移已完成；
- batch-261 至 batch-280 中文 coverage 扩展已完成，runtime 中文覆盖已到 `17.14%`；用户要求继续 20-batch 分组处理并逐轮 commit，直到 runtime 中文覆盖超过 `20%`；
- host Agent 默认不要再打开完整 `theme_concept_aliases.json` 或 compact index 大文件做状态确认；
- 需要状态时优先看 manifest/stats/query 工具输出；
- 最新 batch-261 至 batch-280 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_261_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_280_ALIASES`，覆盖 knowledge/Kohonen/Kr/Kv、L 系酶和 L-band、lab/laboratory、lac/lactate/lactobacillus/lactose、lambda/lamin、land/lane/language、Laplace/large language、laryngeal/laser/latent/lead/learning/least 等 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试并扩展 side-effect replacement cases，先红灯后转绿；修正 `β-内酰胺类`、`食品标识`、`产品标识`、`概念格`、`人工喉`、`乳酸钠`、`层粘连蛋白受体` 等 exact 输出；
  - grouped L3-L5：fill `records_filled = 19844`，validate `review_decisions = 369164`；
  - 显式接受 `304` 条 exact/domain-aware recommendation；
  - 显式阻断 `8` 条由 exact 词条引发的 compositional/title side-effect；
  - duplicate/collision exact-backed 输出继续保持 blocked，不自动 merge（包括 `大语言模型`、`知识转移`、`激光通信` 等多 concept exact 输出）；
  - runtime 中文覆盖从 `8070 / 48862 = 16.52%` 增至 `8373 / 48863 = 17.14%`；
  - `zh:accept`: `8387`，`zh:blocked`: `11491`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `b740d86d5a3f1017990e45bb37654058d01f001e4e712be532fb9758caa9be29`；
  - compact manifest SHA-256: `e94dce66f9ff2ec7467e833f549e3cfa190e7d4ed28b3626e8d2ebac66219cdc`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - 相关测试：`343 passed in 2.73s`。
- batch-280 后 review：
  - 本轮新增 `303` 个 runtime zh-covered concepts，覆盖率到 `17.14%`，距 `>20%` 目标仍需继续；
  - `Cellular Automata And Lattice Gases`、`Device Lead Extraction`、`Landslides And Related Hazards`、`Language Acquisition And Education` 等组合/title side-effect 已显式 blocked；
  - `Beta-lactams -> β-内酰胺类`、`Larynx, Artificial -> 人工喉`、`Sodium Lactate -> 乳酸钠`、`Receptors, Laminin -> 层粘连蛋白受体` 用更具体 exact replacement 修正，避免组合候选污染；
  - query smoke 已确认 `Kv1.1钾通道`、`L-氨基酸氧化酶`、`β-内酰胺类`、`Kohonen自组织映射`、`人工喉`、`乳酸钠`、`层粘连蛋白受体` 可命中；`大语言模型`、`知识转移`、`激光通信` 因多 concept collision 保持 blocked；
  - 下一轮从 batch-281 至 batch-300 继续，优先 L 段后续 high-confidence exact 术语。
- 最新 batch-241 至 batch-260 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_241_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_260_ALIASES`，覆盖 isotope 后续、IT/iterative、Janus/Jagged/Java、jaw/jejunal/joint/Josephson/JPEG、KNN/K-means/Kalman/keratin/kernel/key/kidney/knowledge 等 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；修正 `17-酮类固醇`、`闭项集`、`血浆激肽释放酶`、`光谱核型分析`、`知识获取` 等 exact 输出；
  - grouped L3-L5：fill `records_filled = 19529`，validate `review_decisions = 368849`；
  - 显式接受 `228` 条 exact/domain-aware recommendation；
  - 显式阻断 `1` 条由 exact 词条引发的 compositional/title side-effect；
  - duplicate/collision exact-backed 输出继续保持 blocked，不自动 merge；
  - runtime 中文覆盖从 `7843 / 48861 = 16.05%` 增至 `8070 / 48862 = 16.52%`；
  - `zh:accept`: `8084`，`zh:blocked`: `11476`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `40b6e0f95af03ab48a80cd748248e2e42d49abbc4133792e2b16e2196fc72fca`；
  - compact manifest SHA-256: `2e09ac20cef7037f1a8338b3d3e39adb54734e76f4634b6ecf6d2ec9a2ed92f0`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - 相关测试：`323 passed in 2.41s`。
- batch-260 后 review：
  - 本轮新增 `227` 个 runtime zh-covered concepts，覆盖率到 `16.52%`，距 `>20%` 目标仍需继续；
  - `Job Satisfaction And Organizational Behavior` 作为 title/domain 组合 side-effect 已显式 blocked；
  - `17-ketosteroids -> 17-酮类固醇`、`Closed Itemsets -> 闭项集`、`Plasma Kallikrein -> 血浆激肽释放酶`、`Spectral Karyotyping -> 光谱核型分析` 用更具体 exact replacement 修正，避免组合候选污染；
  - 下一轮从 batch-261 至 batch-280 继续，优先 K/L 段高确定性 exact 术语。
- 最新 batch-221 至 batch-240 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_221_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_240_ALIASES`，覆盖 image/imaging、immune/immunity/immunoglobulin/immunotherapy、implant/infection/influenza/infrared/insulin/internet/intracranial/ionic/isotope 等 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；修正 `三维成像`、`牛免疫缺陷病毒`、`免疫酶技术`、`渗透浓度`、`脊髓肿瘤` 等 exact 输出；
  - grouped L3-L5：fill `records_filled = 19298`，validate `review_decisions = 368618`；
  - 显式接受 `129` 条 exact/domain-aware recommendation；
  - 显式阻断 `4` 条由 exact 词条引发的 compositional/title side-effect；
  - duplicate/collision exact-backed 输出继续保持 blocked，不自动 merge；
  - runtime 中文覆盖从 `7722 / 48861 = 15.80%` 增至 `7843 / 48861 = 16.05%`；
  - `zh:accept`: `7857`，`zh:blocked`: `11472`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `9614cff2957223f8a4e2fc6f20d261d247d2cc59fbbb0603ca86a7363ca373a4`；
  - compact manifest SHA-256: `c3722b426dca0154ec12ca9e35dd9244ef8c898cfb7bc21d42edf8e94542898b`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - 相关测试：`303 passed in 2.82s`。
- batch-240 后 review：
  - 本轮新增 `121` 个 runtime zh-covered concepts，覆盖率到 `16.05%`，距 `>20%` 目标仍需继续；
  - `Cancer, Stress, Anesthesia, And Immune Response`、`Immune Response And Inflammation`、`Immunotherapy And Immune Responses`、`Interferon And Immune Responses` 作为 title/domain 组合 side-effect 已显式 blocked；
  - `Osmolar Concentration -> 渗透浓度`、`Spinal Cord Neoplasms -> 脊髓肿瘤` 用更具体 exact replacement 修正，避免组合候选污染；
  - 下一轮从 batch-241 至 batch-260 继续，优先 I/J/K 段高确定性 exact 术语。
- 最新 batch-201 至 batch-220 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_201_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_220_ALIASES`，覆盖 human/humanoid/humidity/hyaluronic/hybrid、hydraulic/hydrocarbon/hydrogen/hydroxy、hyper/hyperspectral/hypertension/hypo/hypothalamus/hypoxia 等 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；修正 `人脸检测`、`肺动脉高压`、`高光谱图像分类`、`下丘脑-垂体-性腺轴` 等 exact 输出；
  - grouped L3-L5：fill `records_filled = 19174`，validate `review_decisions = 368494`；
  - 显式接受 `394` 条 exact/domain-aware recommendation；
  - 显式阻断 `21` 条由 exact 词条引发的 compositional/mixed side-effect；
  - `63` 条 exact-backed 输出因 duplicate/collision 保持 blocked，不自动 merge（包括 `人脸检测`、`人脸识别`、`人因`、`类人机器人`、`羟基磷灰石` 等重复/碰撞概念）；
  - runtime 中文覆盖从 `7368 / 48857 = 15.08%` 增至 `7722 / 48861 = 15.80%`；
  - `zh:accept`: `7737`，`zh:blocked`: `11468`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `e5bcd7fab44a941a0def2d1aea67661053acceb7df34b2ac21fd2a481749bddc`；
  - compact manifest SHA-256: `e2efa7f8b057bbe092c2b4c62e77fa1ef8f9c5aaa666ff3c14f096dab47e2e07`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - 相关测试：`283 passed in 3.13s`。
- batch-220 后 review：
  - 本轮新增 `354` 个 runtime zh-covered concepts，覆盖率到 `15.80%`，距 `>20%` 目标仍需继续；
  - side-effect `21` 条已全部显式 blocked；其中 `先天性高胰岛素血症`、`自身免疫垂体炎`、`肥胖通气不足综合征` 等看似可用的组合候选仍应后续通过 exact/domain-specific replacement 重新打开，不在本轮 blanket accept；
  - duplicate/collision exact 输出 `63` 条继续不自动 merge；
  - 下一轮从 batch-221 至 batch-240 继续，优先 I 段 immune/immun*/image/infection/inflammation 等高确定性 exact 术语。
- 最新 batch-181 至 batch-200 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_181_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_200_ALIASES`，覆盖 high/higher/Hilbert/Hippo、histamine/histone/HIV/HLA、home/hospital/host/housing、human/HT/HTTP 等 exact/domain-aware 术语；
  - 新增 `21` 个代表性回归测试，先红灯后转绿；其中 `Hippo Pathway Signaling And Yap/taz -> Hippo-YAP/TAZ信号通路` 用于避免 English-heavy zh pollution audit 误命中；
  - grouped L3-L5：fill `records_filled = 18787`，validate `review_decisions = 368107`；
  - 显式接受 `441` 条 exact/domain-aware recommendation，另接受 `1` 条 exact-backed variant recommendation（`Hitting Time -> 击中时间`）；
  - 显式阻断 `13` 条由 exact 词条引发的 compositional/domain-title side-effect；
  - `高电子迁移率晶体管`、`医院信息系统`、`人体活动识别` 等 exact-backed 输出因 duplicate/collision 保持 blocked，不自动 merge；
  - runtime 中文覆盖从 `6959 / 48851 = 14.25%` 增至 `7368 / 48857 = 15.08%`；
  - `zh:accept`: `7383`，`zh:blocked`: `11426`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `c3213cd0fa6a4af638765dd29c11d5eb94081636192b2214180936cc67c579b1`；
  - compact manifest SHA-256: `9d8f995e195c850d622c61d81a6f7a338560923ea3e43b945675774a2ae09cbd`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - 相关测试：`263 passed in 2.22s`。
- batch-200 后 review：
  - 本轮新增 `409` 个 runtime zh-covered concepts，覆盖率已超过 `15%`；
  - side-effect `13` 条已全部显式 blocked；其中 `甲状旁腺激素`、`公共住房` 等看似可用的组合候选仍应后续通过 exact/domain-specific replacement 重新打开，不在本轮 blanket accept；
  - duplicate/collision exact 输出继续不自动 merge；
  - 若继续扩大覆盖，建议先确认新覆盖目标，再从 H/I 段 exact 术语继续。
- 最新 batch-161 至 batch-180 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_161_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_180_ALIASES`，覆盖 hazard/head、health/healthcare、hearing/heart/heat、helicobacter/helix/hematology/heme/hemodynamics、hepatitis/heparin、herpes/hernia/hidden/hierarchical/high 等 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；修正 `HCV NS3/4A蛋白酶抑制剂`、`医疗相关性肺炎`、`血红素结合蛋白` 等 exact 输出；
  - grouped L3-L5：fill `records_filled = 18419`，validate `review_decisions = 367740`；
  - 显式接受 `378` 条 exact/domain-aware recommendation，另接受 `6` 条 exact-backed plural/variant recommendation；
  - 显式阻断 `45` 条由 exact 词条引发的 compositional/domain-title side-effect；
  - `51` 条 exact-backed 输出因 duplicate/collision 保持 blocked，不自动 merge（包括 `高性能计算`、`高维数据`、`头戴式显示器`、`卫生支出` 等重复/碰撞概念）；
  - runtime 中文覆盖从 `6636 / 48848 = 13.58%` 增至 `6959 / 48851 = 14.25%`；
  - `zh:accept`: `6974`，`zh:blocked`: `11467`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `f8843ed145acadf13de20b8c3f7267973a0c6fdf128875cbf8ced339e7c8dc4d`；
  - compact manifest SHA-256: `3f0b1ff247b44850632ac2f61e1b1cb07575fdfdf56b9a148d9f3fd94de2f080`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - 相关测试：`243 passed in 1.69s`。
- batch-180 后 review：
  - 本轮新增 `323` 个 runtime zh-covered concepts，覆盖率已到 `14.25%`，但仍未超过 `15%`；
  - side-effect `45` 条已全部显式 blocked，主要为 helminth/health/heavy metal/hemagglutination/hernia/high 等组合派生词；
  - duplicate/collision exact 输出 `51` 条继续不自动 merge；
  - 下一轮应继续 batch-181 至 batch-200，优先从 high/histology/hiv/home/hormone/human 等高确定性 exact 术语推进。
- 最新 batch-141 至 batch-160 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_141_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_160_ALIASES`，覆盖 graphics/grasp/Graves、green/grey/grid、ground/group/growth、GTP/guanine/guanosine、H.264/Haar/Haemophilus/hair/hand/haptic/hardware/harmonic/hash 等 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；其中修正 `Grey Relational Analysis -> 灰色关联分析` 等组合输出；
  - grouped L3-L5：fill `records_filled = 18092`，validate `review_decisions = 367409`；
  - 显式接受 `369` 条 exact/domain-aware recommendation；
  - 显式阻断 `28` 条由 exact 词条引发的 compositional/domain-title side-effect；
  - `70` 条 exact-backed 输出因 duplicate/collision 保持 blocked，不自动 merge（包括 `石墨`、`探地雷达`、`陀螺仪`、`硬件` 等重复/碰撞概念）；
  - runtime 中文覆盖从 `6276 / 48846 = 12.85%` 增至 `6636 / 48848 = 13.58%`；
  - `zh:accept`: `6651`，`zh:blocked`: `11454`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `8b36fc8326d3ca9baa0d0f2598141b2b57582f09cc915cd78ff415df37dbb70d`；
  - compact manifest SHA-256: `bc87c4eae0e2385315aef8e18146267f232d1135398e121502c4d05512c2acda`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - 相关测试：`223 passed in 1.75s`。
- batch-160 后 review：
  - 本轮新增 `360` 个 runtime zh-covered concepts，是近期单组收益较高的一轮；
  - side-effect 升至 `28`，主要来自新增组件在 title/research/domain 组合和手/导星/哈希等派生词中复用，已全部显式 blocked；
  - duplicate/collision exact 输出 `70`，继续不自动 merge；
  - 覆盖率仍未达 `15%`，下一轮可从 hard/health/heart/helicobacter/hematology 等 H 段高确定性 exact 继续。
- 最新 batch-121 至 batch-140 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_121_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_140_ALIASES`，以 glucose transporter、glucoside/glucuronide、glutamate/glutathione、glycine/glycogen/glyco、GPS/GPU/graft、Gram/granuloma、graph/graphene 等 exact 术语为主；
  - 新增 `21` 个代表性回归测试，先红灯后转绿；额外修正 `α葡萄糖苷酶类 -> α-葡萄糖苷酶`、`形式化语法 -> 形式文法`、`等离子体细胞肉芽肿肺 -> 肺浆细胞肉芽肿`、`受体甘氨酸 -> 甘氨酸受体`、`受体粒细胞集落刺激因子 -> 粒细胞集落刺激因子受体`；
  - grouped L3-L5：fill `records_filled = 17723`，validate `review_decisions = 367037`；
  - 显式接受 `219` 条 exact/domain-aware recommendation；
  - 显式阻断 `3` 条由 exact 词条引发的 compositional/domain-title side-effect；
  - `6` 条 exact-backed 输出因 duplicate/collision 保持 blocked，不自动 merge（包括 `图卷积网络`、`图绘制`、`石墨烯` 等重复概念）；
  - runtime 中文覆盖从 `6057 / 48844 = 12.40%` 增至 `6276 / 48846 = 12.85%`；
  - `zh:accept`: `6291`，`zh:blocked`: `11442`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `ae39fc20ad7f3aa46fb5049ce96c766111d693f532f540c4e6c6cff0cd65243d`；
  - compact manifest SHA-256: `4f58c44992b8609211b30ac2bdfbe7be55c45217d0f888a4fc963507368e04b7`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - 相关测试：`203 passed in 1.73s`。
- batch-140 后 review：
  - 本轮新增 `219` 个 runtime zh-covered concepts，收益与 batch-101-to-120 接近；
  - side-effect 仅 `3` 条，均为 title/research/application 组合，已阻断；
  - exact duplicate/collision 降至 `6`，但 `图卷积网络`、`图绘制`、`石墨烯` 仍不自动 merge；
  - 覆盖率仍未达 `15%`，下一轮可从 graph/graphite/grass/growth/H 段高确定性 exact 继续。
- 最新 batch-101 至 batch-120 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_101_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_120_ALIASES`，以 Genetic profile/risk/service/techniques、Genome/Genomic、Genital/Geographic/Geotechnical、Geriatric/Giant/Gingival、Glaucoma/Global/Glomerular/Glucagon/Glucose 等 exact 术语为主；
  - 新增 `21` 个代表性回归测试，先红灯后转绿；额外修正 `β葡聚糖类 -> β-葡聚糖`、`钙葡萄糖酸盐 -> 葡萄糖酸钙`、`受体胃饥饿素 -> 胃饥饿素受体`、`受体糖皮质激素 -> 糖皮质激素受体`；
  - grouped L3-L5：fill `records_filled = 17516`，validate `review_decisions = 366830`；
  - 显式接受 `231` 条 exact/domain-aware recommendation；
  - 显式阻断 `4` 条由 exact 词条引发的 compositional/domain-title side-effect；
  - `32` 条 exact-backed 输出因 duplicate/collision 保持 blocked，不自动 merge（包括 `遗传编程`、`遗传变异`、`细菌基因组`、`线粒体基因组` 等重复概念）；
  - runtime 中文覆盖从 `5828 / 48844 = 11.93%` 增至 `6057 / 48844 = 12.40%`；
  - `zh:accept`: `6072`，`zh:blocked`: `11454`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `7bed40da38dfa7b91f0bb86f189704ab1825d31981080a01ea76ca0d91c19df5`；
  - compact manifest SHA-256: `8c449d8b3687799c85a83ce9f8a0be6dcb199e247de4c9348cc2a7e39229b60d`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - 相关测试：`182 passed in 1.56s`。
- batch-120 后 review：
  - 本轮新增 `229` 个 runtime zh-covered concepts，收益与 batch-081-to-100 接近；
  - side-effect 仅 `4` 条，均为 title/domain/geographical 派生，已阻断；
  - 新增 side-effect exact 修正后，`葡萄糖酸钙`、`胃饥饿素受体`、`糖皮质激素受体` 等可进入 runtime；
  - duplicate/collision exact 输出降至 `32`，accepted/runtime conflict 仍为 `0`；继续不自动 merge；
  - 若继续追求 >15%，下一轮可从 glutamate/glycine/glycogen/gold/gonadal 等 exact 密集区继续。
- 最新 batch-081 至 batch-100 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_081_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_100_ALIASES`，以 Gaussian、gelatin/gemcitabine、Genes、Gene expression/product/rearrangement/therapy、gender、generative AI、genetic algorithm/association/disease/marker 等 exact 术语为主；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；修正组合输出词序，如 `高斯波束 -> 高斯光束`、`基因DCC -> DCC基因`、`基因MHC类I -> MHC I类基因`，并保留 `Gene Targeting -> 基因打靶`；
  - grouped L3-L5：fill `records_filled = 17300`，validate `review_decisions = 366613`；
  - 显式接受 `238` 条 exact/domain-aware recommendation；
  - 显式阻断 `4` 条由 exact 词条引发的 compositional/domain-title side-effect；
  - `81` 条 exact-backed 输出因 duplicate/collision 保持 blocked，不自动 merge（包括 `高斯分布`、`高斯信道`、`高斯噪声`、`视线跟踪`、`齿轮`、`凝胶`、`线粒体基因`、`生成式AI`、`基因表达谱分析`、`遗传标记` 等重复概念）；
  - runtime 中文覆盖从 `5608 / 48845 = 11.48%` 增至 `5828 / 48844 = 11.93%`；
  - `zh:accept`: `5843`，`zh:blocked`: `11466`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `6e96ee776aaa78c12020cf3ec6a3dd2536b6c2e8136876650392336bb548bf4f`；
  - compact manifest SHA-256: `dedaaead98c7c63ef72de5e913dc72baa59e8e8d3b0ecf4790c20777256ca2db`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - 相关测试：`161 passed in 1.46s`。
- batch-100 后 review：
  - 本轮新增 `220` 个 runtime zh-covered concepts，收益继续低于前两轮，主要因为 Gaussian/gene/generative/genetic 段多源重复概念较多；
  - side-effect 仅 `4` 条，均为 title/component 派生，已阻断；
  - duplicate/collision exact 输出升至 `81`，但 accepted conflict 仍为 `0`；继续不自动 merge；
  - 若继续追求 >15%，下一轮可从 genetic 后续、genome/genomics、geographic/geriatric、glucose/glycan 等 exact 密集区继续。
- 最新 batch-061 至 batch-080 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_061_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_080_ALIASES`，以 G 段 GABA 受体、gadolinium、gait、galactose、galanin、gallbladder、gallium、game/gamete、gamma、ganglia/ganglioside、gas/gastric/gastrointestinal、GATA/gated 等 exact 术语为主；
  - 新增 `21` 个代表性回归测试，先红灯后转绿；其中补充修正 `α半乳糖苷酶 -> α-半乳糖苷酶`、`G M1神经节苷脂 -> GM1神经节苷脂`、`受体甘丙肽1型 -> 1型甘丙肽受体` 等 side-effect 词序/格式；
  - grouped L3-L5：fill `records_filled = 17109`，validate `review_decisions = 366415`；
  - 显式接受 `268` 条 exact/domain-aware recommendation；
  - 显式阻断 `14` 条由 exact 词条引发的 compositional/domain-title side-effect；
  - `35` 条 exact-backed 输出因 duplicate/collision 保持 blocked，不自动 merge（包括 `Gabor滤波器`、`步态识别`、`星系`、`镓化合物`、`博弈论`、`游戏化`、`伽马射线`、`石榴石`、`气相色谱法` 等重复概念）；
  - runtime 中文覆盖从 `5371 / 48844 = 11.00%` 增至 `5608 / 48845 = 11.48%`；
  - `zh:accept`: `5623`，`zh:blocked`: `11488`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `7071142ba481dcc68417f8ac1fd6acbd8965b5658bf60e4afdc8e580cb2c2732`；
  - compact manifest SHA-256: `2b3b0afc6ef26b047c3ebc3ccd1304df745f5a1a13273f169b59e7095a6c5d61`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - 相关测试：`141 passed in 1.26s`。
- batch-080 后 review：
  - 本轮新增 `237` 个 runtime zh-covered concepts，收益低于 batch-041-to-060 的 `295`，但仍可继续 20-batch 分组；
  - side-effect 降至 `14`，主要是 title/domain 组合（如 `胃肠动力与障碍`、`星系形成演化现象`）和未选中的组件派生（如 `量子气体`），已保持 blocked；
  - duplicate/collision exact 输出 `35`，主要来自 Gabor/gamma/game/gas 等多源重复概念，继续不自动 merge；
  - 后续继续扩大到 15% 时，应优先选择高置信 MeSH exact 和具体 CS/工程术语，同时继续把 OpenAlex `Research/Studies/And ...` title side-effect 阻断。
- 最新 batch-041 至 batch-060 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_041_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_060_ALIASES`，以 F/G 段 fibroma、fibrosis、filovirus、fish、flavivirus、fluorescence、fluoride、fluoro-drug、focal、folate、food、foot、fracture、fungal、fusobacterium、GABA 等 exact 术语为主；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；
  - grouped L3-L5：fill `records_filled = 16861`，validate `review_decisions = 366170`；
  - 显式接受 `296` 条 exact/domain-aware recommendation；
  - 显式阻断 `30` 条由 exact 词条引发的 compositional/domain-title side-effect；
  - `31` 条 exact-backed 输出因 duplicate/collision 保持 blocked，不自动 merge（包括 `流式细胞术`、`有限元分析`、`甲醛`、`傅里叶分析`、`四维计算机断层成像` 等重复概念）；
  - runtime 中文覆盖从 `5076 / 48843 = 10.39%` 增至 `5371 / 48844 = 11.00%`；
  - `zh:accept`: `5386`，`zh:blocked`: `11480`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `d3f79d856994605923dc3fe9567575cef1c486d76b2f089d417f7edb0791c594`；
  - compact manifest SHA-256: `4f89436379256928696d6a7592963b74ff09c09cb0ec388a01e32ea0d7a9dbb9`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - 相关测试：`120 passed in 1.20s`。
- batch-060 后 review：
  - 一次性处理 `20` 个 batch 仍能保持 `needs_review = 0` 和 accepted/runtime conflict `0`；
  - runtime 中文覆盖首次达到 `11%`，本轮新增 `295` 个 runtime zh-covered concepts；
  - side-effect 从上一轮 `3` 上升到 `30`，主要来自 exact component 在 title/study/domain 组合词中的复用，后续扩大批量时应继续用自动分桶审查 side-effect；
  - duplicate/collision exact 输出从上一轮 `13` 上升到 `31`，仍不自动 merge；需要单独做 canonical target/merge decision 后才能处理。
- 最新 batch-031 至 batch-040 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_031_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_040_ALIASES`，以 D/E/F 段 diagnosis、DNA、drug、enzyme、eye、factor、fibroblast 等生物医学 exact 术语为主；
  - 新增代表性回归测试，先红灯后转绿；额外修正 `药物载波 -> 药物载体`、`耐药性多重 -> 多重耐药性`、`受体成纤维细胞生长因子 -> 成纤维细胞生长因子受体`、`人为障碍 -> 做作性障碍`；
  - grouped L3-L5：fill `records_filled = 16525`，validate `review_decisions = 365835`；
  - 显式接受 `287` 条 exact/domain-aware recommendation；
  - 显式阻断 `3` 条由 exact 词条引发的 compositional/domain-title side-effect；
  - `13` 条 exact 输出因 duplicate/collision 保持 blocked，不自动 merge（包括 `计算机辅助诊断`、`DNA拷贝数变异`、`药物发现`、`肌张力障碍`、`日本脑炎病毒`、`脑炎病毒`、`内皮细胞`）；
  - runtime 中文覆盖从 `4791 / 48843 = 9.81%` 增至 `5076 / 48843 = 10.39%`；
  - `zh:accept`: `5091`，`zh:blocked`: `11439`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `cd7b9fd5f9ca6f7ece2cc99b9f299cfb22b9db383e7ed5378741dbb6ae7cc7d3`；
  - compact manifest SHA-256: `2efe66b0ca56700218d1c751f2ab1cfcc716a9003f78b82e6f5175378ec0a919`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - 相关测试：`100 passed in 1.33s`。
- batch-040 后 review：
  - runtime 中文覆盖首次超过 `10%`，本轮新增 `285` 个 runtime zh-covered concepts；
  - batch-031-to-040 覆盖收益高于 batch-021-to-030：`285` vs `201`，说明 D/E/F 段 exact 术语仍有高收益；
  - duplicate/collision 数上升到 `13`，但 accepted conflict 仍为 `0`，应继续保持不自动 merge；
  - 后续应继续用更具体 exact replacement 修正词序错误，title/study/in-disease side-effect 仍保持 blocked。
- 最新 batch-021 至 batch-030 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_021_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_030_ALIASES`，以 C/D 段生物医学 exact 术语为主；
  - 新增代表性回归测试，先红灯后转绿；额外修正冠状病毒相关词序，如 `人冠状病毒229E`、`牛冠状病毒`、`冠状病毒受体`；
  - grouped L3-L5：fill `records_filled = 16304`，validate `review_decisions = 365617`；
  - 显式接受 `201` 条 exact/domain-aware recommendation；
  - 显式阻断 `4` 条由 exact 词条引发的 compositional/domain-title side-effect；
  - `1` 条 exact 输出因 duplicate/collision 保持 blocked，不自动 merge（`DNA Viruses -> DNA病毒`）；
  - runtime 中文覆盖从 `4590 / 48843 = 9.40%` 增至 `4791 / 48843 = 9.81%`；
  - `zh:accept`: `4806`，`zh:blocked`: `11505`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `996622fb5985032d6099b3de949312378aa23136294d15df452a49b117529823`；
  - compact manifest SHA-256: `646515baa5fb6f619e4be0df3c92387164c9792043485ef10a2d3e35e03b3a7b`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - 相关测试：`90 passed in 1.06s`。
- batch-030 后 review：
  - batch-021-to-030 单轮覆盖收益高于 batch-016-to-020：`201` 个新增 runtime zh concepts vs `142` 个；
  - 10 个小 batch 合并一轮 L3-L5 的方式可继续使用，但单个 batch 仍应保持同域、小而可审；
  - 词序 side-effect 先用更具体 exact replacement 修正，剩余 `研究`、`并发症` 等 title/domain 组合候选保持 blocked；
  - 后续仍不应把 side-effect 或 medium compositional 候选批量 accept。
- 最新 batch-016 至 batch-020 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_016_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_020_ALIASES`，以 B/C 段生物医学 exact 术语为主；
  - 新增代表性回归测试，先红灯后转绿；
  - grouped L3-L5：fill `records_filled = 16125`，validate `review_decisions = 365440`；
  - 显式接受 `142` 条 exact/domain-aware recommendation；
  - 显式阻断 `15` 条由 exact 词条引发的 compositional/domain-title side-effect；
  - 未发现本组 exact 输出因 duplicate/collision 被 validator blocking；
  - runtime 中文覆盖从 `4448 / 48843 = 9.11%` 增至 `4590 / 48843 = 9.40%`；
  - `zh:accept`: `4605`，`zh:blocked`: `11529`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `f84f8a55a2c0d993cd43f72c04f49d98f4065ed69000f195e29a6769fd127920`；
  - compact manifest SHA-256: `dc841402f031f25080d61e6c8e9018433eb29c6e56e23d8b4d5a5e7c26b220d7`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - 相关测试：`80 passed in 0.99s`。
- batch-020 后 review：
  - batch-016-to-020 比 batch-011-to-015 覆盖收益更高：`142` 个新增 runtime zh concepts vs `110` 个；
  - 未引入 accepted/runtime alias conflict，说明 exact/domain-aware 策略仍可继续；
  - side-effect 数从 `11` 增至 `15`，主要来自派生标题和组合候选，其中 `G1/G2/M/S相位...`、`脑干出血创伤性` 这类坏形态确认应保持 blocked；
  - 后续应优先继续 exact 术语和更具体 replacement，不应把 side-effect 或 medium compositional 候选批量 accept。
- 最新 batch-011 至 batch-015 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_011_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_015_ALIASES`，以 B/C 段生物医学 exact 术语为主；
  - 新增代表性回归测试，先红灯后转绿；
  - grouped L3-L5：fill `records_filled = 15983`，validate `review_decisions = 365298`；
  - 显式接受 `111` 条 exact/domain-aware recommendation；
  - 显式阻断 `11` 条由 exact 词条引发的 compositional/domain-title side-effect；
  - `7` 条 exact 输出因 duplicate/collision 保持 blocked，不自动 merge（`Bacterial Typing Techniques`、`Carpal Tunnel Syndrome`、`Cell Biology` 对应重复概念）；
  - runtime 中文覆盖从 `4338 / 48843 = 8.88%` 增至 `4448 / 48843 = 9.11%`；
  - `zh:accept`: `4463`，`zh:blocked`: `11529`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `4321268e5eaf32ea7a46f5e60a0db186bbfac170571262a9fe430d559febd4fd`；
  - compact manifest SHA-256: `4cbb344aec9572257559de787695e288d682213db0c2d6c0c85562d6497b5f5f`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - 相关测试：`75 passed in 1.52s`。
- 最新 batch-008 至 batch-010 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_008_ALIASES`、`ZH_EXACT_EXPANSION_BATCH_009_ALIASES`、`ZH_EXACT_EXPANSION_BATCH_010_ALIASES`；
  - batch-008 以 A 段生物医学 exact 术语为主：显式接受 `130` 条，阻断 `3` 条 compositional side-effect；
  - batch-009 以 CS/通信/信号处理 exact 术语为主：显式接受 `110` 条，阻断 `7` 条 compositional side-effect；`17` 条 exact 输出因 duplicate/collision 保持 blocked，不自动 merge；
  - batch-010 以 A/B 段生物医学 exact 术语为主：显式接受 `218` 条，阻断 `2` 条 compositional side-effect；`4` 条 exact 输出因 duplicate/collision 保持 blocked，不自动 merge；
  - runtime 中文覆盖从 `3884 / 48841 = 7.95%` 增至 `4338 / 48843 = 8.88%`；
  - `zh:accept`: `4353`，`zh:blocked`: `11530`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `40fe9e3d8ec091f889b497658fa9f6074fafd6587554faaf7141a69c23ea533d`；
  - compact manifest SHA-256: `9bb64799036b8a8fd47420d67a5043037d66886a10d46bb2a5c12283f9f27c52`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - 相关测试：`70 passed in 1.02s`。
- 最新 batch-007 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_007_ALIASES`，以心血管、线粒体、趋化因子、肿瘤/神经系统等高确定性生物医学术语为主；
  - `zh:needs_review`: `56 + 9 side-effects -> 0`；
  - 显式接受 `56` 条 exact/domain-aware recommendation；
  - 显式阻断 `9` 条由 exact 词条引发的 compositional/domain-title side-effect；
  - `Coronary Artery Disease -> 冠状动脉疾病` 因与 `coronary_disease` 翻译碰撞仍由 validator 保持 blocked，不自动 merge；
  - runtime 中文覆盖从 `3828 / 48841 = 7.84%` 增至 `3884 / 48841 = 7.95%`；
  - `zh:accept`: `3896`，`zh:blocked`: `11543`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；
  - compact index SHA-256: `2f97a5aaf8d1c257317088df2b69f1ba141269e5cf99e068bb3533ff02916add`；
  - compact manifest SHA-256: `527482326c857f206582186a98846b2cd8700ae38bd38adfc5fbbb2eb19ea87e`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - 相关测试：`67 passed in 0.89s`。
- 最新 batch-006 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_006_ALIASES`，以 S/Z 段高确定性
    生物医学、CS/通信/工程术语为主；
  - `zh:needs_review`: `159 -> 0`；
  - 显式接受 `159` 条 exact/domain-aware recommendation；
  - runtime 中文覆盖从 `3669 / 48841 = 7.51%` 增至
    `3828 / 48841 = 7.84%`；
  - `zh:accept`: `3840`，`zh:blocked`: `11552`；
  - `block_accepted_alias_conflicts.py` 结果：`accepted_conflict_groups = 0`；
  - 两份 runtime alias JSON byte-identical；
  - runtime SHA-256:
    `a6b8d726383f78e919a6273dab727d7647a9495801a0873a75cd4c0ffde9a85b`；
  - 相关测试：`58 passed in 0.44s`。
- batch-006 期间修正并纳入 exact/domain-aware 的副作用包括：
  `High-energy Shock Waves -> 高能冲击波`、
  `Mass Vaccination -> 大规模疫苗接种`、
  `Receptors, Serotonin -> 5-羟色胺受体`、
  `Shock Waves -> 冲击波`、
  `Sodium Salicylate -> 水杨酸钠`、
  `Subarachnoid Hemorrhage, Traumatic -> 创伤性蛛网膜下腔出血`、
  `Tachycardia, Sinus -> 窦性心动过速`、
  `Tachycardia, Ventricular -> 室性心动过速`；对应旧坏形态
  `高能源休克波`、`质量疫苗接种`、`受体5-羟色胺`、`休克波`、
  `钠水杨酸盐`、`蛛网膜下腔出血创伤性`、`心动过速窦`、
  `心动过速心室` 不应进入 runtime。
- en/zh review 均已清零，runtime `build_status` 已是 `review_complete`。
- 最新 batch-005 / 864 review sweep 已完成：
  - `zh:needs_review`: `864 -> 0`；
  - 规则化接受 `684` 条标准中文术语；
  - 阻断 `180` 条低置信组合候选（connector 短语、泛化后缀、过长/反序/重复）；
  - runtime 中文覆盖从 `2502 / 48834 = 5.12%` 增至
    `3669 / 48841 = 7.51%`；
  - `block_accepted_alias_conflicts.py` 结果：`accepted_conflict_groups = 0`；
  - 两份 runtime alias JSON byte-identical。
- 计划文件 `.idea/plans/2026-06-08-theme-concept-alias-pipeline-plan.md`
  已同步 batch-010 最新状态；若后续继续扩展，保持两处状态同步。
- 后续扩大中文 runtime coverage 只能通过 exact glossary、domain-aware replacement
  或中文来源扩充；不要直接把 medium-confidence compositional 候选批量转 accept。
- `zh-exact-expansion-batch-003` 已完成：runtime 中文覆盖到
  `2780 / 48834 = 5.69%`，相关测试当时为 `59 passed`。
- `zh-exact-expansion-batch-002` 已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_002_ALIASES`；
  - 显式接受 `165` 条 exact/domain-aware zh recommendation；
  - `16` 条 exact 输出保持非 reviewable，多数是 collision-blocked duplicate
    concepts；
  - `8` 条由 exact 词条引发的 compositional side-effect 已显式 blocked；
  - runtime 中文覆盖从 `2502 / 48834 = 5.12%` 增至
    `2666 / 48834 = 5.46%`。
- `zh-exact-expansion-batch-001` 已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_001_ALIASES`；
  - 显式接受 `156` 条 exact/domain-aware zh recommendation；
  - `5` 条 exact 输出因 collision 保持 blocked；
  - `7` 条由 exact 词条引发的 compositional side-effect 已显式 blocked；
  - runtime 中文覆盖从 `2350 / 48834 = 4.81%` 增至
    `2502 / 48834 = 5.12%`。
- 后续 exact batch 的 L3-L5 顺序应为：
  `fill -> validate -> apply en recommendations -> apply zh exact batch recommendations
  -> preserve zh prior decisions -> block accepted collisions -> materialize`。
- 后续若继续扩大中文 runtime coverage，只能通过 exact glossary 或
  domain-aware replacement 重新打开已 blocked 的组合候选；不要直接把
  medium-confidence compositional 候选批量转 accept。
- 新增 exact 词条可能被 compositional 规则复用并产生宽泛派生候选；
  这类 side-effect 不应自动 accept，需显式 block 或加入更具体 exact。
- 短英文 acronym 默认保持 blocked；只有显式 acronym allowlist 或
  source-specific review 后才能进入 runtime。
- 低置信 `agent_review_gated_mixed_fallback` 不能当覆盖率来源；只能作为
  需要 exact/domain-specific replacement 的 review 队列。
- `System-on-a-chip -> 片上系统` 当前与 `system_on_chip*` 概念冲突，
  保持 blocked，不自动 merge。
- 本轮已纠正并接受的 biomedical exact 项包括
  `Acid Phosphatase -> 酸性磷酸酶`、
  `Activated Protein C Resistance -> 活化蛋白C抵抗`、
  `Acute-phase Reaction -> 急性期反应`、
  `B7-1 Antigen -> B7-1抗原`；旧坏形态
  `酸磷酸酶`、`活性蛋白C抗性`、`急性相位反应`、`B7 1抗原`
  不应进入 runtime。
- 最新 1000 条 bounded review 批次已处理：
  - `218 accept`：只接受无碰撞、无空格、无已知坏形态的
    biomedical/exact 标准命名；
  - `782 blocked`：低置信 `agent_review_gated_mixed_fallback / low`
    一律不作为覆盖来源，blocked pending exact/domain-specific replacement。
  - 新发现 biomedical mixed-class suffix 风险：
  `B7 2抗原`、`HCV NS3 4A蛋白酶抑制剂` 这类空格编号格式不自动
  accept；`S phase` 不得译为 `S相位`，应后续 exact 修正为 `S期`
  相关表述。
- 最新 goal2000 bounded review 后半批次已处理：
  - batch `006-010` 共 `1000` 条全部 `blocked`；
  - 未新增 accepted alias，runtime coverage 不增加；
  - 目的只是清理低质量 / 高风险 pending review 项，保留
    exact/domain-specific replacement 的后续空间；
  - 仍不自动 merge collision，不打开低质 mixed fallback，不进入 L6。
- 最新 goal-next2000 bounded review 批次已处理：
  - batch `001-010` 共 `2000` 条全部 `blocked`；
  - 处理对象优先级：OpenAlex topic compositional、MeSH compositional
    word-order、ASCII/spacing residual、多义/词序风险、敏感域组合词、
    已知技术误译风险、生医样式但非 exact 证据项、少量保守尾部；
  - 未新增 accepted alias，runtime coverage 不增加；
  - 仍不自动 merge collision，不打开低质 mixed fallback，不进入 L6。
- 最新 final zh needs review sweep 已处理：
  - batch `001-017` 共 `3369` 条全部 `blocked`；
  - 这些是高风险桶清理后剩余的 medium-confidence compositional 候选；
  - 未新增 accepted alias，runtime coverage 不增加；
  - 中文 review 完成：`zh:needs_review = 0`；
  - 仍不自动 merge collision，不打开低质 mixed fallback，不进入 L6。
- 最新 final en acronym review 已处理：
  - batch `001-004` 共 `713` 条全部 `blocked`；
  - 这些都是 validator 标记的 short acronym，主要来自 MeSH/biomedical；
  - 未新增 accepted alias，runtime coverage 不增加；
  - 英文 review 完成：`en:needs_review = 0`；
  - `tools/theme-lexicon/apply_zh_review_recommendations.py` 已向后兼容地
    增加 `--lang en|zh`，默认仍为 `zh`。

## 5. Alias pipeline 操作规范

重建链路前先备份 review decisions：

```powershell
$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$backupDir = Join-Path 'F:\AI playground\TempFiles' "vpnsci_alias_review_prior_$ts"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
Copy-Item -LiteralPath 'lexicons/review/review_decisions.jsonl' `
  -Destination (Join-Path $backupDir 'review_decisions.prior.jsonl') -Force
```

标准 L3-L5 deterministic chain：

```powershell
uv run python tools/theme-lexicon/fill_zh_alias_candidates.py `
  --candidate-dir lexicons/candidates --replace-generated

uv run python tools/theme-lexicon/validate_alias_overlay.py `
  --candidate-dir lexicons/candidates --output-dir lexicons/review --repo-root .

uv run python tools/theme-lexicon/preserve_zh_review_decisions.py `
  --prior '<TempFiles>\review_decisions.prior.jsonl' `
  --current lexicons/review/review_decisions.jsonl

uv run python tools/theme-lexicon/block_accepted_alias_conflicts.py `
  --review-decisions lexicons/review/review_decisions.jsonl

uv run python tools/theme-lexicon/materialize_runtime_overlay.py `
  --concepts lexicons/builds/merged_en_concept_candidates.jsonl `
  --review-decisions lexicons/review/review_decisions.jsonl
```

每次物化后必须确认：

- accepted conflict groups 为 `0`
- package/tool 两份 `theme_concept_alias_index.json` byte-identical
- package/tool 两份 `theme_concept_alias_manifest.json` byte-identical
- legacy full overlay 若显式重生成，也必须 package/tool byte-identical；默认不要生成/读取
- manifest/stats 对齐，普通状态确认不读取完整 alias 大文件
- pollution audit 未恢复 ordinary English residue / known bad shapes
- compact loader 与 legacy loader 的 alias_key -> concept_id 等价性不回退
- 相关 tests fresh pass

## 6. 已遇到的问题与解决方案

### 6.1 外部标识符污染

症状：

- `merged_en_concept_candidates.jsonl` 曾出现无语义字段，例如
  `m.02y 3vt`、`101833716`。

处理：

- `build_en_concepts` / validator 增加 external identifier / literal
  pollution guards。
- `tests/test_theme_lexicon_pollution_guards.py` 覆盖该类输入。

### 6.2 低质 mixed fallback 污染

症状：

- 出现 `Knapsack问题`、普通英文残留、`English Label主题` 这类低质候选。

处理：

- 禁用低质量 source-label topic fallback。
- validator block ordinary untranslated English residue。
- exact glossary 中允许标准 acronym / proper-name mixed form，但仍需 review。

### 6.3 重复拼接污染

症状：

- 曾出现 `识别识别`、`物联网物联网`、`智能智能体`、`BANGBANG` 等。

处理：

- 增加 redundant adjacent translation guard。
- pollution audit 固定检查 known bad shapes。
- 不把讨论样例硬编码为唯一规则；优先抽象为重复/冗余形态检查。

### 6.4 多义词误译

典型问题：

- `agent`: CS/AI 为 `智能体`，医学/化学常为 `药剂` / `制剂` / `作用物`
- `charge`: circuits/power 为 `电荷`，access/social 语境可能为 `费用`
- `power amplifier`: 应为 `功率放大器`，不是 `电力放大器`
- `architectural`: CS 语境优先 `架构`，不是建筑领域的 `建筑`
- `identity`: 数学语境可能为 `恒等式`，不是 `身份`
- `dynamic`: CS/通信/软件多为 `动态*`，物理/力学/生物系统中的
  `dynamics` 多为 `动力学`；社科场景常为 `动态`。
  不接受机械生成的 `动力学带宽分配`、`动力学程序分析` 等。

处理：

- 使用 domain/source/path-aware overrides。
- 新增 exact/domain-aware glossary 时必须确认领域语义。
- 不确定英文是否专有名词时，后续可用 DuckDuckGo 快速搜索确认，但搜索结论
  只作为 source evidence，不直接自动 accept。

### 6.5 non-canonical alias scope drift

症状：

- canonical 是 `Ai Planning`，source alias `planning algorithms` 可能生成
  `规划算法`，导致 broader/narrower drift。
- canonical 是 `3-d Virtual Environment`，source alias
  `virtual reality technology` 可能生成 `虚拟现实技术`。

处理：

- non-canonical English aliases 只允许 exact glossary hit。
- compositional alias generation 只对 canonical label 开启。

### 6.6 alias collision / concept merge 风险

原则：

- unresolved collisions 默认 `blocked`。
- 不自动 concept merge。
- 需要显式 canonical target / merge decision 后才处理。
- accepted collision guard 必须在 materialize 前运行。

典型保留项：

- `Sigma-delta` / `Delta Sigma Modulator` 近重复，暂 blocked。
- `Admission Control` 与 `Access Control` 有翻译碰撞风险，暂 needs_review。

### 6.6.1 L5.5 runtime-normalization collision 规则

- review collision guard 继续使用 review-time normalization 判定 accepted conflict。
- compact runtime index 使用 runtime normalization（英文 singular、中文去标点）生成 lookup key。
- 若多个 accepted 英文别名只在 runtime singular normalization 后碰到同一 key，
  compact index 必须保持 legacy loader 行为：按 materialized entry 顺序保留第一个
  alias_key -> concept target，不把该类兼容性碰撞计入 accepted conflict groups。
- 已验证 compact loader 与 legacy full loader 的 alias_key -> concept_id 完全一致。

### 6.7 SubAgent review 规则

- `needs_review` 可交给 SubAgent 分桶审查，但 SubAgent 只返回建议。
- 主 Agent 必须筛选并负责最终写入 review decisions。
- 不使用 blanket `accept_missing`。
- RPM/TPM 紧张时减少 subagent 和等待频率，优先本地脚本分桶。
- `tools/theme-lexicon/apply_zh_review_recommendations.py` 支持
  `--lang en|zh`；recommendation 匹配必须使用
  `(lang, concept_id, alias)`，旧 recommendation 文件没有 `lang` 时按当前
  `--lang` 解释；manifest 使用 `{lang}_review_apply_manifest.json`。
- `--accept-missing` 只允许用于 `--lang zh` 的旧流程；英文 short acronym
  review 不允许 blanket accept，必须显式 recommendation / allowlist。

### 6.8 pytest / tempfile 长时间无输出

症状：

- 单个 pytest case 长时间无输出、CPU 很低，需要手动终止。
- 典型命令：
  `.\.venv\Scripts\python.exe -B -m pytest tests/test_theme_lexicon_fill_zh_alias_candidates.py::... -q`

已确认原因：

- 卡点不是 alias 生成规则，而是测试 `setUp()` 里的
  `tempfile.TemporaryDirectory(dir=F:\AI playground\TempFiles)`。
- 在 sandbox 内，`F:\AI playground\TempFiles` 可能存在但不可写；只检查
  `exists()` 不够。
- Python 3.14 / Windows 下 `tempfile.mkdtemp()` 遇到部分
  `PermissionError` 会反复尝试随机目录名，表现为长时间卡住。

处理规则：

- Python / pytest / tempfile 诊断命令一律用 timeout wrapper，不再裸跑可疑命令。
- 若怀疑卡住，先用 `--collect-only` 区分 collection 与 test body。
- 用 `-o faulthandler_timeout=30` 抓栈，确认是否卡在 `tempfile.py`。
- `tests/temp_helpers.py` 提供 temp parent 可用性探测；theme lexicon tests
  必须实际 `mkdir + rmdir` 成功后才把目录交给 `TemporaryDirectory`。
- 若有残留进程，只终止路径精确等于当前仓库
  `.venv\Scripts\python.exe` 的进程；不要按进程名批量杀。

## 7. 报告 / 搜索主链注意事项

- 标准检索默认只返回结果和 SearchSession，不默认生成报告。
- `generate_search_report(mode="full")` 才进入完整专业调研。
- `seed_preview` 是快速预览，不是 full。
- 如果 full 因 SubAgent / 环境不足不能执行，必须显式说明 fallback，不得静默降级。
- HTML 报告模块要遵守“模块原位显示”：缺数据展示占位，不整块消失。
- `raw_theme_treemap` 与 `theme_treemap` 允许不同，但只能因 deterministic
  display quality gate 置空/过滤，不能隐藏 Agent 侧重聚类或重命名。

## 8. CNKI / 浏览器 / 外部服务安全边界

- CNKI live browser access 是 gated 操作。
- 未经用户明确确认，不要启动真实账号、真实浏览器下载、批量下载或生产外部服务操作。
- `cnki_visible_smoke` 默认 dry-run；live 需要显式确认。
- 下载 artifact / batch download 需要尊重 throttling、cooldown、resume state。
- 不要杀不属于当前会话的 `python` / `uv` / 浏览器进程，除非用户明确要求并确认。

## 9. 文件状态与交付说明

交付时至少说明：

- 改了什么。
- 涉及哪些关键文件。
- 跑了哪些验证，给出命令和结果。
- 当前风险 / 未完成项 / 下一步。
- 若产生临时文件，说明它们在 `F:\AI playground\TempFiles`，可按需清理。

注意：

- `.idea/`、`lexicons/` 是 gitignored；这些文件改动不会默认出现在
  `git status --short`。
- `tests/` 测试源码不再整体 gitignored；测试产物如 `tests/*.tmp`、
  `tests/**/__pycache__/` 仍忽略。
- runtime alias 文件是 tracked，变更会出现在 git status。
- 不要把 source dumps、review working files 或大中间产物提升进 runtime JSON。

## 8. AGENTS.md 自我更新规则

### 8.1 何时更新

出现以下任一情况时，主 Agent 应顺手更新本文件，不另等用户提醒：

- 工具 / MCP / 依赖 / 验证命令发生变化；
- 用户对确认边界、交付方式、部署方式、安全目录提出新要求；
- 新增关键目录、关键文件或 pipeline stage；
- 解决了一个值得复现的污染、中断、冲突或故障；
- 任务出现多次中断，需要记录“当前状态 + 下一步”才能安全接力；
- 发现新的常见坏形态、误译模式或反模式。

### 8.2 更新哪些内容

只追加当前有价值的状态和约定，不删改已有安全红线：

- **当前状态块**：活跃 tracks、关键指标、最近一次验证结果；
- **已知风险与反模式**：典型误译、未决 collision、多义词 domain 规则；
- **标准命令**：新增 pipeline 后给出可直接复制的命令；
- **中断恢复点**：最近一次备份位置与下一步主行动；
- **与人的明确约定**：用户说过“不自动 accept collision”、“不杀外部进程”等直接约束。

### 8.3 更新格式

- 新增条目用 `##` / `###` 节；关键状态尽量给出命令或路径。
- 覆盖旧状态时用显式日期时间子节，保留历史。
- 不要修改第 0 节安全红线。
- 不要把一次性中间产物路径写进核心规则正文，只作为“当前状态”或“中断恢复点”出现。

### 8.4 责任与边界

- Codex 每次完成一个 L1+ 任务后，检查 AGENTS.md 是否需要更新。
- 用户可以直接编辑 AGENTS.md；Codex 读到更新后按最新规则执行。
- 若 AGENTS.md 与 `.idea/plans/*.md` 冲突，以 AGENTS.md 为项目基线，以 `.idea/plans/*.md` 为当前任务细节。
