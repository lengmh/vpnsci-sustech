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
uv run pytest tests -q
```

说明：仓库根目录 `uv run pytest -q` 当前会额外收集
`tools/paper-search-pro/tests` 并触发既有 `tests.*` 导入布局错误；在该
collection 问题修复前，项目主测试套件以 `uv run pytest tests -q` 为准。

主题 alias pipeline 相关：

```powershell
uv run pytest `
  tests/test_theme_lexicon_concept_curation.py `
  tests/test_theme_lexicon_apply_concept_curation_to_build.py `
  tests/test_theme_lexicon_remap_review_decisions_for_curation.py `
  tests/test_theme_lexicon_fill_zh_alias_candidates.py `
  tests/test_theme_lexicon_pollution_guards.py `
  tests/test_theme_lexicon_block_accepted_alias_conflicts.py `
  tests/test_theme_lexicon_preserve_zh_review_decisions.py `
  tests/test_theme_lexicon_apply_zh_review_recommendations.py `
  tests/test_theme_lexicon_normalize_sources.py `
  tests/test_theme_lexicon_materialize_runtime_overlay.py `
  tests/test_theme_lexicon_query_alias_index.py `
  tests/test_theme_lexicon_parenthetical_acronym_normalization.py `
  tests/test_theme_lexicon_reviewed_source_alignment.py `
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

最新已知状态（2026-07-02 C6 suppressed/noise batch7 no-overlay post-review 后；
生产 compact runtime 仍保持 C5 duplicate acronym redirect 版本，未切 C6 工作视图）：

- compact runtime `build_status`: `review_complete`
- 中文候选覆盖：当前仍以 `lexicons/candidates` 生成清单为准，
  最新 fill `records_filled = 51844 / records_seen = 54682`；
  runtime 覆盖是最终可用覆盖，中文覆盖仍未完成
- runtime 中文覆盖：`48203 / 49554 = 97.27%`（curated denominator；
  raw 覆盖为 `48262 / 49849 = 96.82%`）
- runtime zh aliases: `48334`
- runtime en aliases: `189414`
- `en:accept`: `233199`
- `en:blocked`: `14798`
- `en:needs_review`: `0`
- `en:reject`: `101116`
- `zh:accept`: `48382`
- `zh:blocked`: `3695`
- `zh:needs_review`: `0`
- `zh:reject`: `13`
- accepted/runtime alias conflicts: `0`
- runtime en alias conflicts: `0`
- runtime zh alias conflicts: `0`
- runtime concept aliases: `49554`
- raw runtime concepts: `49849`
- curated runtime concepts: `49554`
- redirected concepts: `238`
- canonical display overrides: `127`
- suppressed concepts: `12`
- display-only concepts: `45`
- package/tool compact index byte-identical
- package/tool compact manifest byte-identical
- legacy full overlay package/tool 文件仍 byte-identical（batch-006 回滚保留，不默认读取；当前运行时以 compact index/manifest 为准）
- compact index SHA-256:
  `7202e4246a55a7ac595af8a061059dc946eeff97e65bd4c2dc05351f23feb0ee`
- compact manifest SHA-256:
  `80afdf958641f0123c3a36b26c8a551f4ede6c64f3d08e76ba400a8d30a57657`
- legacy full overlay SHA-256:
  `a6b8d726383f78e919a6273dab727d7647a9495801a0873a75cd4c0ffde9a85b`
- pollution audit：
  - ordinary English-heavy zh aliases: `0`
  - known bad-shape hits: `0`
- compact index 是当前运行时真源；legacy full overlay 未随 batch-007 之后的覆盖扩展更新，不再作为默认等价检查对象，也不再作为 runtime fallback 读取。
- 最近相关测试：C6 suppressed/noise batch7 后，targeted
  curation/build/remap/materialize/query suite `25 passed in 0.17s`；
  focused alias/runtime suite `927 passed in 27.65s`；project suite
  `1285 passed, 4 subtests passed in 95.05s`。
- concept curation C1-C4 已开始并完成首批临时验证：
  - C1 只读 audit 已完成，输出在 `F:\AI playground\TempFiles`；
    raw uncovered concepts `1587`，其中 `redirect_candidates = 436`、
    `needs_decision_candidates = 791`、`singleton_gaps = 279`、
    `topic_label_candidates = 70`、`suppressed_candidates = 11`；
  - C2 新增 versioned curation source
    `tools/theme-lexicon/concept_curation_decisions.json`，当前写入 C4 batch1-4
    共 `226` 条高置信 active `redirect` decision；
  - C2 新增 schema/overlay 校验脚本
    `tools/theme-lexicon/apply_concept_curation.py`；
  - C2 新增测试 `tests/test_theme_lexicon_concept_curation.py`；
  - C3 runtime overlay 接入已完成 fixture 验证：
    `materialize_runtime_overlay.py` 支持可选 `--curation-overlay`，
    redirect aliases 可归并到 canonical target，suppressed/display-only 不进入
    runtime concepts/aliases，manifest 可输出 raw/curated coverage；
    `query_alias_index.py` 可显示 redirect metadata；
  - C3 manifest `raw_concepts` 语义已修正为“curation 前、已接受 alias
    可物化的 runtime concepts”，不再使用 build source 总行数；
  - C4 batch1 post-review 修正 `3` 条 redirect target direction：
    `cellular_automata__2 -> cellular_automata`、`cad -> computer_aided_design`、
    `controller_area_network__2 -> controller_area_network`，避免 noisy/acronym
    target 成为 canonical display；
  - C3 redirect 物化顺序已修正：canonical target 自身 aliases 优先于
    redirected source aliases，避免 acronym source 抢占 target canonical；
  - C4 batch2 新增 `119` 条保守 base-id/source-variant redirect，只取已有
    base target 的明确 duplicate / 单复数 / 来源变体，跳过 topic-label、
    broad/noise 和 semantic-neighbor-only candidates；
  - C4 batch3 新增 `26` 条更严格 exact/base/source-variant redirect，先自动
    筛出 normalized English label 与 target alias 匹配的 `45` 条，再手工剔除
    Android/display/化学单体-类别等易歧义项；
  - C4 batch3 临时 materialize 结果：raw runtime concepts `49849`，
    curated concepts `49650`，redirected concepts `199`，raw zh coverage
    `48262 / 49849 = 96.82%`，curated zh coverage
    `48262 / 49650 = 97.20%`，accepted/runtime alias conflicts `0`，
    pollution audit `0 / 0`，temp compact index SHA-256
    `90ddf2a0ed14506a76c0320bb38f4c504916b0485b4e018dfd1d086bf13914ec`；
  - C4 batch4 初选 `29` 条 exact collision-target redirect，post-review 后保留
    `27` 条 active redirect；`rna_ribosomal_16s -> 16s_rrna` 因 16S rRNA
    与 16S rRNA gene 存在 RNA-vs-gene 歧义未写入 active decisions，
    `human_machine_interface -> human_computer_interface` 因 human-machine
    interface 比 human-computer interface 更宽泛而置为 inactive；
    `linguistic_and_cultural_study__2` 已改为 redirect 到
    `linguistic_and_cultural_study`，保留 arts/social-sciences base target
    作为 canonical；`online_social_networking__2` 直接压平到
    `on_line_social_network`，并在 `apply_concept_curation.py` 中新增
    “redirect target 不得继续 redirect”的校验；
  - C4 batch4 临时 materialize 结果：raw runtime concepts `49849`，
    curated concepts `49623`，redirected concepts `226`，raw zh coverage
    `48262 / 49849 = 96.82%`，curated zh coverage
    `48262 / 49623 = 97.26%`，accepted/runtime alias conflicts `0`，
    pollution audit `0 / 0`，temp compact index SHA-256
    `033a3b9b0e38a3b0458dbc2544fd2f04237b3d7ee97e1234c1e25d6ae2001360`；
  - C4 batch1-3 集中 redirect review 已完成：
    `199` 条 redirect 决策精炼审计 `issue_count = 0`；关系分布为
    `base_target = 96`、`src_label_matches_target = 80`、
    `zh_collision_target = 21`、`manual_direction_override = 2`；
    collision-driven 项已单独抽查，未发现需要回滚或改 target 的项；
    review artifact:
    `F:\AI playground\TempFiles\concept_curation_c4_redirect_review_audit_refined_20260630.json`；
  - C4 curation overlay 已接入生产 compact runtime；package/tool compact index
    与 manifest 均 byte-identical，生产 SHA 为
    `033a3b9b0e38a3b0458dbc2544fd2f04237b3d7ee97e1234c1e25d6ae2001360` /
    `daaee4573b4908f0b44cf2e99b288f4595cddd97624f4d9ec773929c0e99f753`。
  - C5 canonical batch1 已开始 source/build concept 清理的第一步：
    `apply_concept_curation.py` 默认改为校验
    `lexicons/builds/merged_en_concept_candidates.jsonl`，避免生产 compact
    runtime 隐藏 redirect source 后阻塞后续 curation；`materialize_runtime_overlay.py`
    支持 `canonical_overrides` 只修 display canonical，不改变 alias 匹配集合；
    首批写入 `14` 条 active `canonical` decision，用于清理
    `natural_language_processing__2`、`cellular_automata`、`automatic_speech_recognition__3`
    等 CS 概念的 acronym/source-suffix/plural display 源痕迹；生产 compact
    runtime 已重新物化，coverage 不变，package/tool compact index 与 manifest
    byte-identical，SHA 为
    `484969112b76214b12c91534ce9e268e556824830fd63f250bc02cafe52c49da` /
    `8ca75550e44a1bcff475c7488964c1d13744cb566484b502c64b597d373ba43c`。
  - C5 cleanup/topic-label batch1 已完成第 3、4 步首批：
    新增 `30` 条 canonical display override，继续清理 CS/工程概念的
    acronym parenthetical、`* systems`、plural/lowercase display 源痕迹；
    新增 `10` 条 topic-label `display_only` 与 `6` 条 broad/noise
    `suppressed` decision；`query_alias_index.py` 现在可对被排除 concept-id
    返回 `curation_status = display_only / suppressed`；生产 compact runtime
    已重新物化，curated coverage 为 `48254 / 49607 = 97.27%`，package/tool
    compact index 与 manifest byte-identical，SHA 为
    `047eafcb097bd4a1394c894520f5bb7005f0af0e6c15dc2619a157e7b86afcc3` /
    `8450742a760b667295d14c366e59a32e595c6478220d9c624b1f812d0d4bab57`。
  - C5 cleanup/topic-label batch2 已完成：
    新增 `30` 条 high-confidence canonical display override，集中清理
    CS/通信术语的 acronym parenthetical、lowercase display 与 source suffix
    源痕迹，例如 `Internet of Things`、`Signal-to-Noise Ratio`、
    `Software as a Service`、`Support Vector Machine`；新增 `15` 条
    coherent long-form topic-label `display_only` 与 `6` 条 broad/generated
    `suppressed` decision；继续不新增 alias、不改变 search alias 匹配、
    不自动 merge collision；生产 compact runtime 已重新物化，curated
    coverage 为 `48234 / 49586 = 97.27%`，package/tool compact index 与
    manifest byte-identical，SHA 为
    `56b93692156dc3a4b536aff7331d4aa6f9146f9e577d89e8729f360ecb956a1c` /
    `ead2fc90a8347dac8fad29ce55784377f210ad8e93096d9b16060d7c487a1dcf`。
  - C5 cleanup/topic-label batch3 已完成：
    初选 `65` 条 high-confidence canonical display override，post-review 移除
    `12` 条会与既有 base concept 形成重复 display label 的 acronym/full-form
    覆写，净增 `53` 条；继续清理 CS/通信概念的 acronym parenthetical 与明确
    lowercase display；代表项包括 `Digital Imaging and Communications in Medicine`、
    `Domain Name System`、`Hypertext Transfer Protocol`、`Wireless Sensor Network`；
    新增 `20` 条 long-form topic-label `display_only` decision；继续不新增
    alias、不改变 search alias 匹配、不自动 merge collision；生产 compact
    runtime 已重新物化，curated coverage 为 `48214 / 49566 = 97.27%`，
    package/tool compact index 与 manifest byte-identical，SHA 为
    `834a3ba4627fa62fc2c842f28df0c0d90fed07c003ddc152729f834abb383c0f` /
    `5f1f5553a2abd3ba929ddd9d2374d38fca5cc8cfd9b517c54627a62d1d06b0fe`。
  - C5 duplicate acronym redirect review 已完成：
    将 batch3 post-review 暂缓的 `12` 个 acronym/full-form duplicate source
    显式 redirect 到既有 full-form base target，包括
    `artificial_neural_network_ann -> artificial_neural_network__2`、
    `internet_protocol_ip -> internet_protocol`、
    `voice_over_internet_protocol_voip -> voice_over_internet_protocol`；
    不新增 alias、不自动 merge collision，只把 source aliases 归并到已审 target；
    生产 compact runtime 已重新物化，curated coverage 为
    `48203 / 49554 = 97.27%`，package/tool compact index 与 manifest
    byte-identical，SHA 为
    `7202e4246a55a7ac595af8a061059dc946eeff97e65bd4c2dc05351f23feb0ee` /
    `80afdf958641f0123c3a36b26c8a551f4ede6c64f3d08e76ba400a8d30a57657`。
  - C6 source/build 回灌首步已完成：
    新增 `tools/theme-lexicon/apply_concept_curation_to_build.py`，可把
    validated curation overlay 应用到
    `lexicons/builds/merged_en_concept_candidates.jsonl`，输出 curated build
    snapshot 与 manifest；redirect source evidence 会并入 target，
    canonical/display_only/suppressed 会在 build snapshot 层前移体现；当前
    只输出工作视图，不替换生产 runtime 输入，因为 L4 review decision rows
    仍引用 redirect source concept，直接 no-overlay materialize 会丢 source
    aliases。TempFiles 冒烟结果：input concepts `54682`，output concepts
    `54387`，retired concepts `295`。
  - C6 review decision remap 已完成：
    新增 `tools/theme-lexicon/remap_review_decisions_for_curation.py`，可把
    redirect source review rows 改写到 target，并丢弃 display_only/suppressed
    source rows；TempFiles remap 结果为 input rows `401203`，output rows
    `346267`，remapped rows `1230`，dropped excluded rows `171`，
    deduplicated rows `54765`。使用 curated build snapshot + remapped review
    decisions 做 no-overlay materialize 后，`missing_concepts = 0`，alias map
    与当前生产 compact index byte-equivalent in content，concept key set 相同，
    canonical diff `0`。后续 review 发现 source metadata 前移曾导致 `214`
    个 target 的 domain/parent/specificity metadata diff；已修正为 redirect
    source 只合并 aliases/source_refs，target domains/parents/specificity
    保持 target-owned。
  - C6 source-cleanup batch1 已完成：
    production switch 明确暂缓；本轮只新增 `30` 条 active `display_only`
    source-cleanup decision，处理 high-confidence long-form/topic-label 概念，
    不新增 alias、不改变生产 compact runtime、不自动 merge collision。
    C2 overlay counts 为 `canonical=127`、`display_only=75`、
    `redirect=238`、`suppressed=12`；curated build 工作视图输出 concepts
    `54357`，retired concepts `325`；remapped review decisions 输出 rows
    `346211`，dropped excluded rows `257`；TempFiles no-overlay materialize
    `missing_concepts = 0`、accepted conflict groups `0`、runtime concepts
    `49531`，临时 compact index SHA 为
    `6f24a1919ec38e649998bc5fd6774713e133471ca4635d479a8a60971a141402`。
  - C6 source-cleanup batch2 已完成：
    production switch 继续暂缓；本轮新增 `25` 条 active `display_only`
    source-cleanup decision，继续处理 high-confidence long-form research /
    topic-label 概念，避开已知标准、组织名、模型名和术语本体；不新增 alias、
    不改变生产 compact runtime、不自动 merge collision。C2 overlay counts 为
    `canonical=127`、`display_only=100`、`redirect=238`、`suppressed=12`；
    curated build 工作视图输出 concepts `54332`，retired concepts `350`；
    remapped review decisions 输出 rows `346162`，dropped excluded rows `331`；
    TempFiles no-overlay materialize `missing_concepts = 0`、accepted conflict
    groups `0`、runtime concepts `49510`，metadata policy fix 后 common
    concepts 的 canonical/metadata diff 均为 `0`，临时 compact index SHA 为
    `17851bd0bfdae82e592890aa849a78e19bc2dc36400ff8c9bd45eef24c4c5d50`。
  - C6 source-cleanup batch3 已完成：
    production switch 继续暂缓；本轮先选 `25` 条 topic-label，review 发现
    `agricultural_economic_and_policy` 会导致英文 alias target 漂移后剔除，
    最终新增 `24` 条 active `display_only` source-cleanup decision；不新增
    alias、不改变生产 compact runtime、不自动 merge collision。C2 overlay
    counts 为 `canonical=127`、`display_only=124`、`redirect=238`、
    `suppressed=12`；curated build 工作视图输出 concepts `54308`，
    retired concepts `374`；remapped review decisions 输出 rows `346117`，
    dropped excluded rows `400`；TempFiles no-overlay materialize
    `missing_concepts = 0`、accepted conflict groups `0`、runtime concepts
    `49486`，common concepts 的 canonical/metadata diff 均为 `0`，
    changed alias targets `0`，临时 compact index SHA 为
    `1023f1b1137db22083c0287ab332e176a6c5ddde348631dff6790ea7ee8de6e2`。
  - C6 source-cleanup batch4 已完成：
    production switch 继续暂缓；本轮新增 `23` 条 active `display_only`
    source-cleanup decision，继续处理剩余 high-confidence long-form
    topic-label，并排除上轮已知 alias target 漂移项与已有 reject 项；不新增
    alias、不改变生产 compact runtime、不自动 merge collision。C2 overlay
    counts 为 `canonical=127`、`display_only=147`、`redirect=238`、
    `suppressed=12`；curated build 工作视图输出 concepts `54285`，
    retired concepts `397`；remapped review decisions 输出 rows `346071`，
    dropped excluded rows `469`；TempFiles no-overlay materialize
    `missing_concepts = 0`、accepted conflict groups `0`、runtime concepts
    `49463`，common concepts 的 canonical/metadata diff 均为 `0`，
    changed alias targets `0`，临时 compact index SHA 为
    `9d5ca1fa5e1eca1df74072d2bd52ff04fd5c42ea88979401329db7af18b693a5`。
  - C6 source-cleanup batch5 已完成：
    production switch 继续暂缓；本轮新增 `11` 条 active `display_only`
    source-cleanup decision，收尾剩余安全 topic-label；继续跳过
    `agricultural_economic_and_policy`（已知 alias target 漂移）与
    `technology_and_education_system`（已有 reject）。C2 overlay counts 为
    `canonical=127`、`display_only=158`、`redirect=238`、`suppressed=12`；
    curated build 工作视图输出 concepts `54274`，retired concepts `408`；
    remapped review decisions 输出 rows `346049`，dropped excluded rows `502`；
    TempFiles no-overlay materialize `missing_concepts = 0`、accepted conflict
    groups `0`、runtime concepts `49452`，common concepts 的 canonical/metadata
    diff 均为 `0`，changed alias targets `0`，临时 compact index SHA 为
    `a99f73d78078dc5fb07707e465213384254ae4bd06e938d9f376e31994f8d033`。
  - C6 redirect/source-variant batch1 已完成：
    production switch 继续暂缓；本轮从 redirect/source-variant 候选中选取
    `12` 条低风险术语变体，review 发现
    `light_amplifier -> optical_amplifier` 会让 target canonical 从
    `Optical Amplifier` 漂到 `Light Amplifiers` 后剔除，最终新增 `11`
    条 active `redirect` decision。C2 overlay counts 为 `canonical=127`、
    `display_only=158`、`redirect=249`、`suppressed=12`；curated build
    工作视图输出 concepts `54263`，retired concepts `419`；remapped review
    decisions 输出 rows `346049`，remapped rows `1263`；TempFiles no-overlay
    materialize `missing_concepts = 0`、accepted conflict groups `0`、
    runtime concepts `49441`，common concepts 的 canonical/metadata diff 均为
    `0`；changed alias targets `11` 且全部为本批 expected redirect source
    改挂，unexpected changed alias targets `0`；临时 compact index SHA 为
    `833c73f8c501b1fd42ebe9fd9c85856b72bfb4abc041edf1d41836a41828a67e`。
  - C6 redirect/source-variant batch2 已完成：
    production switch 继续暂缓；本轮初选 `12` 条低风险术语 / acronym
    variant，C2 validation 发现 `hemt` 会形成
    `hemt__2 -> hemt -> high_electron_mobility_transistor` redirect chain，
    已剔除；最终新增 `11` 条 active `redirect` decision。C2 overlay
    counts 为 `canonical=127`、`display_only=158`、`redirect=260`、
    `suppressed=12`；curated build 工作视图输出 concepts `54252`，
    retired concepts `430`；remapped review decisions 输出 rows `346049`，
    remapped rows `1309`；TempFiles no-overlay materialize
    `missing_concepts = 0`、accepted conflict groups `0`、runtime concepts
    `49430`，common concepts 的 canonical/metadata diff 均为 `0`；changed
    alias targets `23` 且全部为 expected redirect source 改挂，unexpected
    changed alias targets `0`；临时 compact index SHA 为
    `99ce9ac43c288848a4e2c5914e2641814436aeb958838902302a69a6d08940d5`。
  - C6 redirect/source-variant batch3 已完成：
    production switch 继续暂缓；本轮初选一批 source/terminology variant，
    review 发现部分 zh-only target 会让 target canonical 从 `None` 漂到
    source English label，已剔除；最终保留 `14` 条 active `redirect`
    decision，覆盖 `clustering_analysi -> cluster_analysi`、
    `non_fungible_token -> nonfungible_token`、`pomdp ->
    partially_observable_markov_decision_process`、`rough_sets ->
    rough_set` 等 exact collision-target/source 变体。C2 overlay counts 为
    `canonical=127`、`display_only=158`、`redirect=274`、`suppressed=12`；
    curated build 工作视图输出 concepts `54238`，retired concepts `444`；
    remapped review decisions 输出 rows `346042`，remapped rows `1385`；
    TempFiles no-overlay materialize `missing_concepts = 0`、accepted conflict
    groups `0`、runtime concepts `49416`，common concepts 的
    canonical/metadata diff 均为 `0`；changed alias targets `48` 且全部为
    expected redirect source 改挂，unexpected changed alias targets `0`；
    临时 compact index SHA 为
    `b0d2d5409df8bd62810e5098f94fad61c81564e3560749b780e65b03c6202b9b`。
  - C6 redirect/source-variant batch4 已完成：
    production switch 继续暂缓；本轮保留 `14` 条 active `redirect`
    decision，继续只取 target canonical 已稳定的 exact collision-target/source
    变体，覆盖 `electric_industry -> power_industry`、
    `mathematical_physic -> mathematical_physic__2`、
    `nonlinear_optical_material_study -> nonlinear_optical_material_research`、
    `ocdma -> optical_cdma`、`program_understanding ->
    program_comprehension`、`web_searching -> web_search__2` 等。C2 overlay
    counts 为 `canonical=127`、`display_only=158`、`redirect=288`、
    `suppressed=12`；curated build 工作视图输出 concepts `54224`，
    retired concepts `458`；remapped review decisions 输出 rows `346040`，
    remapped rows `1432`；TempFiles no-overlay materialize
    `missing_concepts = 0`、accepted conflict groups `0`、runtime concepts
    `49402`，common concepts 的 canonical/metadata diff 均为 `0`；changed
    alias targets `63` 且全部为 expected redirect source 改挂，unexpected
    changed alias targets `0`；临时 compact index SHA 为
    `f895ebf3a2bdbe6cd720471f676b3d321d000eff01ca82b28a093e8c60263f8a`。
  - C6 redirect/source-variant batch5 已完成：
    production switch 继续暂缓；本轮初选 `9` 条 exact/source variant，review
    发现 `polyethylen -> polyethylene` 会让 target canonical 从 `Polythene`
    漂到 `Polyethylenes`，已剔除；最终保留 `8` 条 active `redirect`
    decision，覆盖 `formal_approach -> formal_method`、
    `information_theory__3 -> information_theory__2`、`library_digital ->
    digital_library`、`material_science__2 -> material_science`、
    `multimedia -> multimedia__2`、`opportunistic_networking ->
    opportunistic_network`、`portfolio_management ->
    portfolio_management__2`、`translocation_genetic__2 ->
    translocation_genetic`。C2 overlay counts 为 `canonical=127`、
    `display_only=158`、`redirect=296`、`suppressed=12`；curated build 工作视图
    输出 concepts `54216`，retired concepts `466`；remapped review decisions
    输出 rows `346032`，remapped rows `1475`；TempFiles no-overlay materialize
    `missing_concepts = 0`、accepted conflict groups `0`、runtime concepts
    `49394`，common concepts 的 canonical/metadata diff 均为 `0`；changed
    alias targets `72` 且全部为 expected redirect source 改挂，unexpected
    changed alias targets `0`；临时 compact index SHA 为
    `d94830bc50e0c3368471ae556bbdf360d8e3cc095e4843ca351fce9d94496d9e`。
  - C6 redirect/source-variant batch6 已完成：
    production switch 继续暂缓；batch5 后剩余 redirect candidates 已输出风险
    审计 `F:\AI playground\TempFiles\concept_curation_c6_redirect_remaining_audit_after_batch5_20260701.json`，
    其中 remaining `145`，已知 skip/risk 包括 canonical drift、semantic-neighbor、
    redirect-chain、RNA-vs-gene 等；本轮从剩余项中仅保留 `2` 条 active
    `redirect` decision：`database__3 -> database__2`、`mammographic ->
    mammography__3`。初选中的 `fiber_sensor -> optical_fiber_sensor` 会让
    target canonical 从 `Optical Fiber Sensor` 漂到 `Fiber Sensor`，已剔除。
    C2 overlay counts 为 `canonical=127`、`display_only=158`、`redirect=298`、
    `suppressed=12`；curated build 工作视图输出 concepts `54214`，
    retired concepts `468`；remapped review decisions 输出 rows `346031`，
    remapped rows `1482`；TempFiles no-overlay materialize
    `missing_concepts = 0`、accepted conflict groups `0`、runtime concepts
    `49392`，common concepts 的 canonical/metadata diff 均为 `0`；changed
    alias targets `74` 且全部为 expected redirect source 改挂，unexpected
    changed alias targets `0`；临时 compact index SHA 为
    `2a97c358cd823751bf1cd210087efae1148f3570d66fd143545cfa5ccbafae9c`。
  - C6 suppressed/noise batch7 已完成：
    production switch 继续暂缓；完成性 review 发现 `11` 条 broad/noise
    suppressed candidates 尚未处置，本轮新增 `12` 条 active `suppressed`
    decision，覆盖 `abas`、`abstract__2`、`acme`、`acmestudio`、`alma`、
    `alpsm`、`application`、`applied_co`、`assessment`、`beauty`、`review`
    以及为避免 `en:review` retarget 到 `review__2` 而同步 suppressed 的
    `review__2`。C2 overlay counts 为 `canonical=127`、
    `display_only=158`、`redirect=298`、`suppressed=24`；curated build
    工作视图输出 concepts `54202`，retired concepts `480`；remapped review
    decisions 输出 rows `346013`，dropped excluded rows `532`；TempFiles
    no-overlay materialize `missing_concepts = 0`、accepted conflict groups
    `0`、runtime concepts `49380`，中文覆盖 `48162 / 49380 = 97.53%`，
    common concepts 的 canonical/metadata diff 均为 `0`；changed alias
    targets `74` 且全部为 expected redirect source 改挂，unexpected changed
    alias targets `0`；broad/noise suppressed bucket 已清空，剩余
    topic-label candidates 仅为已知 blocked/reject 的 `2` 条；临时 compact
    index SHA 为
    `70dd2e966faff468316b9caaedd2946960680446df73517acb53f5d38e00bcf5`。
- 最近 C4/C5 相关测试：
  - `uv run pytest tests/test_theme_lexicon_materialize_runtime_overlay.py::MaterializeRuntimeOverlayTests::test_curation_overlay_redirects_aliases_and_excludes_suppressed_concepts -q`:
    先复现 `raw_concepts` 计数错误 `5 != 4`，修复后 `1 passed in 0.05s`；
  - `uv run pytest tests/test_theme_lexicon_materialize_runtime_overlay.py::MaterializeRuntimeOverlayTests::test_curation_overlay_keeps_target_own_aliases_before_redirected_source_aliases -q`:
    先复现 target canonical 被 acronym source 抢占：`ABC != Full Form Term`，
    修复后 `1 passed in 0.05s`；
  - `uv run pytest tests/test_theme_lexicon_materialize_runtime_overlay.py tests/test_theme_lexicon_query_alias_index.py tests/test_theme_lexicon_concept_curation.py -q`:
    `16 passed in 0.13s`；
  - C5 cleanup/topic-label batch3 targeted curation/materialize/query suite:
    `21 passed in 0.12s`。
  - C6 source/build backfill + review remap targeted curation/build/remap/materialize/query suite:
    `25 passed in 0.19s`。
  - C6 source/build backfill + review remap 后 focused alias/runtime suite:
    `927 passed in 29.00s`。
  - C6 source-cleanup batch1 targeted curation/build/remap/materialize/query suite:
    `25 passed in 0.18s`。
  - C6 source-cleanup batch1 focused alias/runtime suite:
    `927 passed in 28.98s`。
  - C6 source-cleanup batch2 targeted curation/build/remap/materialize/query suite:
    `25 passed in 0.17s`。
  - C6 source-cleanup batch2 focused alias/runtime suite:
    `927 passed in 50.70s`。
  - C6 source-cleanup batch3 targeted curation/build/remap/materialize/query suite:
    `25 passed in 0.29s`。
  - C6 source-cleanup batch3 focused alias/runtime suite:
    `927 passed in 27.60s`。
  - C6 source-cleanup batch4 targeted curation/build/remap/materialize/query suite:
    `25 passed in 0.17s`。
  - C6 source-cleanup batch4 focused alias/runtime suite:
    `927 passed in 27.07s`。
  - C6 source-cleanup batch5 targeted curation/build/remap/materialize/query suite:
    `25 passed in 0.16s`。
  - C6 source-cleanup batch5 focused alias/runtime suite:
    `927 passed in 51.63s`。
  - C6 redirect/source-variant batch1 targeted curation/build/remap/materialize/query suite:
    `25 passed in 0.17s`。
  - C6 redirect/source-variant batch1 focused alias/runtime suite:
    `927 passed in 28.11s`。
  - C6 redirect/source-variant batch2 targeted curation/build/remap/materialize/query suite:
    `25 passed in 0.21s`。
  - C6 redirect/source-variant batch2 focused alias/runtime suite:
    `927 passed in 27.48s`。
  - C6 redirect/source-variant batch3 targeted curation/build/remap/materialize/query suite:
    `25 passed in 0.17s`。
  - C6 redirect/source-variant batch3 focused alias/runtime suite:
    `927 passed in 27.25s`。
  - C6 redirect/source-variant batch4 targeted curation/build/remap/materialize/query suite:
    `25 passed in 0.20s`。
  - C6 redirect/source-variant batch4 focused alias/runtime suite:
    `927 passed in 29.43s`。
  - C6 redirect/source-variant batch5 targeted curation/build/remap/materialize/query suite:
    `25 passed in 0.21s`。
  - C6 redirect/source-variant batch5 focused alias/runtime suite:
    `927 passed in 27.89s`。
  - C6 redirect/source-variant batch6 targeted curation/build/remap/materialize/query suite:
    `25 passed in 0.19s`。
  - C6 redirect/source-variant batch6 focused alias/runtime suite:
    `927 passed in 27.05s`。
  - C6 suppressed/noise batch7 targeted curation/build/remap/materialize/query suite:
    `25 passed in 0.17s`。
  - C6 suppressed/noise batch7 focused alias/runtime suite:
    `927 passed in 27.65s`。
  - project suite:
    `1285 passed, 4 subtests passed in 95.05s`。

当前下一步：

- L5.5 紧凑 runtime index / manifest / query 工作面迁移已完成；
- concept curation 主线已从 post-95 exact-only 覆盖扩展转入基础 concept 清理：
  C1 audit、C2 schema 校验、C3 runtime overlay 能力均已完成；C4 batch1-4
  已写入并生产接入 `226` 条高置信 active redirect decision，并通过
  materialize / query smoke、focused suite 与 project suite 验证；batch1-3
  集中 review 未发现问题；batch4 post-review 已收口 RNA-vs-gene 歧义、
  HMI 过宽 redirect、语言与文化研究 target direction 与 redirect-chain
  压平问题；C5 已接入 `127` 条 canonical display override，并开始 topic-label
  disposition（生产 runtime 当前为 `45` display-only、`12` suppressed；
  C6 工作视图当前为 `298` redirect、`158` display-only、`24` suppressed）；
  C6 已新增 build-level curated snapshot helper 与 review decision remap
  helper，并完成 no-overlay materialize 对照；metadata merge policy 已收紧，
  redirect source 只合并 aliases/source_refs，不再污染 target
  domains/parents/specificity；suppressed/noise bucket 已清空，剩余 redirect
  candidates 主要为 blocked/needs-policy 或高风险项；production switch 已暂缓，
  后续若未来要切 runtime 默认输入，应作为单独迁移任务评审；
- post-7000 exact/domain-aware pattern milestone 已完成，runtime 中文覆盖到 `40.49%`；post-40 review cleanup 收口到 `43.18%`；post-40 continuation 已清理并达到 clean `50.01%`；post-50-to-60 子代理审查 milestone 已达到 clean `60.10%`；post-60-to-70 子代理审查 milestone 已达到 clean `70.00%`（exact `70.002%`）；post-70-to-80 子代理审查 milestone 已达到 clean `80.92%`；post-80-to-90 子代理审查 milestone 已达到 clean `90.07%`；post-90-to-final 子代理审查 milestone 已达到 `99.07%`；post-99 safe patch 已达到 `99.08%`；post-99 round2 safe patch 已达到 `99.10%`；post-99 round3 safe patch 曾达到 `99.13%`；post-99 correctness cleanup 因清理伪 exact / stale source 回落到 clean `95.49%`；post-95 singleton exact review batch 推进到 clean `95.91%`；post-95 singleton exact review round2 推进到 clean `96.01%`；post-95 exact collision review round3 推进到 clean `96.14%`；post-95 exact collision review round4 推进到 clean `96.21%`；post-95 exact collision review round5 推进到 clean `96.33%`；post-95 exact collision review round6 推进到 clean `96.45%`；post-95 exact collision review round7 推进到 clean `96.51%`；post-95 singleton exact review round8 推进到 clean `96.51%`（`48115 / 49853`）；post-95 new exact proposal round9 推进到 clean `96.74%`；post-95 new exact proposal round10 推进到 clean `96.76%`；post-95 new exact proposal round11 推进到 clean `96.80%`；post-95 new exact proposal round12 推进到 clean `96.82%`；post-95 new exact proposal round13 未新增 runtime-safe alias，coverage 保持 clean `96.82%`；
- post-70 review cleanup 已完成最终修复：package 与 paper-search-pro
  runtime 均使用 compact index 一致的 CJK/Latin alias 归一化与中文 alias
  extraction，并修复 `pH控制` / `AH控制` / `p-H控制` / `p H控制`
  误命中 `H控制`、`服务质量Q路由` / `服务质量123路由` 被当标点折叠、
  `μ-阿片受体` / `μ 阿片受体` 漏命中 `μ阿片受体` 的边界；reviewed
  exact alias 生产 overlay 不再污染同进程临时 candidate dir；`Epidemic Routing`、
  `Error Floor`、`Run Time Reconfiguration`、`Session Initiation Protocol` 的坏译源项已修正；
- post-99 correctness cleanup 已完成最终修复：
  - 修复中文/混合 alias normalization 丢弃 `+` 的问题，`C++语言` 不再折叠为
    `C语言`，`H+/K+交换ATP酶` 不再折叠为 `H/K交换ATP酶`，
    `NADP+` 不再折叠为 `NADP`；
  - 清理 active runtime 中非 exact 的生成式 `*主题` alias 和膨胀型
    `*技术` alias；保留 `LoRa技术`、`NoSQL技术`、`塑化技术` 等标准 named
    technology/technique 用法；
  - `reviewed_zh_exact_aliases.json` 已与 compact runtime 对齐，新增
    `tests/test_theme_lexicon_reviewed_source_alignment.py` 防止 source-only
    stale rows 回灌；
  - `算法主题`、`优化方法主题`、`糖尿病研究主题`、`药学词典主题`、`薄膜主题`、
    `功耗技术`、`线圈技术`、`声音技术`、`设施管理技术` 均不再命中；
  - runtime 中文覆盖从 post-99 round3 的 `48628 / 49055 = 99.13%` 收口到
    clean `46837 / 49051 = 95.49%`；后续继续推进应从该 clean baseline 出发；
- post-99 runtime fallback review fix 已完成：
  - correctness review 未发现 alias 污染或冲突，但指出 `theme_clustering.py`
    仍会在 compact index 缺失时回退读取 stale legacy full overlay；
  - package 与 paper-search-pro runtime loader 已改为 compact index 缺失即抛出
    clear `FileNotFoundError`，不再静默使用 legacy `theme_concept_aliases.json`；
  - `tests/test_theme_clustering_compact_alias_index.py` 已改为覆盖 “compact
    缺失不得 fallback legacy” 的负向契约；
  - 该修复不改变 runtime 覆盖与 manifest SHA，只收紧运行时真源契约；
- post-95 singleton exact review batch 已完成：
  - 从 post-99 cleanup 后未覆盖概念中抽取 `240` 条 non-runtime-colliding
    singleton high/exact 候选交给 `3` 个子代理审查；
  - 子代理明确 reject `25` 条，主代理再过滤 runtime collision、内部 alias
    collision、坏形态和已覆盖 alias 后形成 `215` 条 explicit accept recommendation；
  - L3-L5 后实际接受 `211` 条；`4` 条子代理接受项因重新 fill/validate 后没有对应
    zh review row 未强行加入；
  - `3` 条剩余 zh needs_review 已显式 blocked；`713` 条 English short acronym
    queue 继续 blocked；
  - 删除 `reviewed_zh_exact_aliases.json` 中 `1` 条 stale source-only row
    `人类第6-12和X染色体`，保持 reviewed source 与 compact runtime 对齐；
  - runtime 中文覆盖从 `46837 / 49051 = 95.49%` 增至
    `47047 / 49051 = 95.91%`；
  - accepted conflict groups: `0`；runtime en/zh alias conflicts: `0`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `无线传感器网络`、`人工神经网络`、`自适应算法`、
    `优化链路状态路由` 可命中；`患者代理人移动IPV6`、`商业过程管理`、
    `脑器官信号` 保持不命中；
  - 后续继续从剩余 uncovered 中选取 subagent-reviewed exact/domain-aware 候选，
    不打开 low-quality mixed fallback、不 blanket accept medium compositional
    candidates、不自动 merge collision；
- post-95 singleton exact review round2 已完成：
  - 从 fresh singleton exact pool 中选取 `300` 条候选，分 `3` 个 chunk 交给
    子代理审查；子代理接受 `228` 条、拒绝 `72` 条；
  - 主代理追加拒绝 `分布式参数系统`，因为既有审查与控制领域标准术语偏向
    `分布参数系统`；最终 explicit recommendation 为 `227` 条；
  - 修复 `preserve_zh_review_decisions.py`：当 validator 重新生成
    collision-blocked 行时，保留此前显式审过的 zh `accept/reject/blocked`
    决策，避免已选定 runtime target 被重新挤出；hard reject 仍不会被旧
    accept 覆盖；
  - L3-L5：fill `records_filled = 51815`，validate `review_decisions = 401174`；
    final preserve 恢复 `4463` 条 prior collision/needs-review 决策；实际净增
    `225` 条 zh runtime alias，旧 zh runtime alias 移除数为 `0`；
  - `1` 条剩余 zh needs_review 已显式 blocked；`713` 条 English short acronym
    queue 继续 blocked；
  - runtime 中文覆盖从 `47047 / 49051 = 95.91%` 增至
    `47272 / 49236 = 96.01%`；runtime concept aliases 增加来自新接受 zh
    alias 激活此前没有 runtime alias 的概念；
  - accepted conflict groups: `0`；runtime en/zh alias conflicts: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest
    byte-identical；legacy full overlay 未更新；
  - compact index SHA-256: `7af4967916c3021d0d389b5177245a0034488bff57a2d088c2ae16c252cd8537`；
  - compact manifest SHA-256: `f20fe64eaf496c15bd6754f851cdb17106a0b0d75e801172210b9aa65826892e`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `事故预防`、`数据采集`、`机器学习`、`光学成像`、
    `量子密钥分发`、`人工神经网络`、`信道状态信息` 可命中；`声学发射`、
    `基金会模型`、`燃料细胞`、`随机访问存储`、`片剂计算机`、`分布式参数系统`
    保持不命中；
  - 相关测试：focused alias/runtime suite `909 passed in 27.51s`；
    project suite `1267 passed, 4 subtests passed in 98.97s`；
- post-95 exact collision review round3 已完成：
  - 生成 fresh high/exact pool 后，剩余可审 singleton 仅 `6` 条；转入
    collision alias group 的显式 target selection，不合并概念；
  - 选取 `306` 个 review item（`6` singleton + `300` collision group）交给
    `3` 个子代理审查；子代理合计接受 `213`、拒绝 `93`；
  - 主代理过滤后保留 `211` 条 explicit accept recommendation，另外阻断
    `生物技术`、`教育技术` 两条 suffix 形态，避免膨胀型 `*技术` 回灌；
  - 主要拒绝面：collision target 不可区分、译名生硬、过泛 alias、英文残留；
    继续不自动 merge duplicate/collision concept；
  - L3-L5：fill `records_filled = 51815`，validate `review_decisions = 401174`；
    preserve 恢复 `52037` 条 prior zh 决策；`211` 条 recommendation 全部命中
    对应 runtime target；
  - `needs_review = 0`；`713` 条 English short acronym queue 继续 blocked；
  - runtime 中文覆盖从 `47272 / 49236 = 96.01%` 增至
    `47483 / 49392 = 96.14%`；
  - accepted conflict groups: `0`；runtime en/zh alias conflicts: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest
    byte-identical；legacy full overlay 未更新；
  - compact index SHA-256: `e605003dcf9e92ba28580ed7b790c93d08856fd8e9c21a0dab31fac205bb8317`；
  - compact manifest SHA-256: `c3f93b7ec63725bccff59df9e76c3a31d75f51caaa67ae4feccf1356e8621a10`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认所有 `211` 条 accepted recommendation 可命中各自 target；
    `可穿戴计算机技术`、`词处理`、`工作环境`、`三维成像`、`访问控制`、
    `声学设备`、`主动学习`、`生物技术`、`教育技术`、`分布式参数系统`、`燃料细胞`
    保持不命中；
  - 相关测试：focused alias/runtime suite `909 passed in 25.67s`；
    project suite `1267 passed, 4 subtests passed in 100.84s`；
- post-95 exact collision review round4 已完成：
  - 重新生成剩余 high/exact pool，已无新的安全 singleton，选取 `300` 个
    collision group 继续 explicit target selection；
  - 子代理审查合计接受 `110`、拒绝 `190`；主过滤后 `110` 条全部保留为
    explicit accept recommendation；
  - 本轮拒绝面进一步集中在 duplicate target 不可区分、过泛 alias、跨域
    泛词与重复概念；继续不自动 merge duplicate/collision concept；
  - L3-L5：fill `records_filled = 51815`，validate `review_decisions = 401174`；
    preserve 恢复 `52037` 条 prior zh 决策；`110` 条 recommendation 全部命中
    对应 runtime target；
  - `needs_review = 0`；`713` 条 English short acronym queue 继续 blocked；
  - runtime 中文覆盖从 `47483 / 49392 = 96.14%` 增至
    `47593 / 49467 = 96.21%`；
  - accepted conflict groups: `0`；runtime en/zh alias conflicts: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest
    byte-identical；legacy full overlay 未更新；
  - compact index SHA-256: `405b4e487d0be1c432213712e93f2ab68b7ced69f9db8ca4d5a170ead788bc1a`；
  - compact manifest SHA-256: `3c3ce877b0a886c284133565f69e162dcda686ea63742ecac52c00bea607ca08`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认所有 `110` 条 accepted recommendation 可命中各自 target；
    `错误分析`、`评估模型`、`事件检测`、`人脸检测`、`故障检测`、`图像处理`、
    `信息安全`、`物联网`、`生物技术`、`教育技术` 保持不命中；
  - 相关测试：focused alias/runtime suite `909 passed in 25.75s`；
    project suite `1267 passed, 4 subtests passed in 93.32s`；
- post-95 exact collision review round5 已完成：
  - 继续从剩余 high/exact pool 中跳过 post95 已审/已拒绝项，选取 `300`
    个 collision group 做 explicit target selection；
  - 子代理审查合计接受 `227`、拒绝 `73`；主过滤后保留 `226` 条 explicit
    accept recommendation，跳过 `纳米技术` 以保持当前膨胀型 `*技术` policy；
  - L3-L5：fill `records_filled = 51815`，validate `review_decisions = 401174`；
    preserve 恢复 `52037` 条 prior zh 决策；`226` 条 recommendation 全部命中
    对应 runtime target；
  - `needs_review = 0`；`713` 条 English short acronym queue 继续 blocked；
  - runtime 中文覆盖从 `47593 / 49467 = 96.21%` 增至
    `47819 / 49641 = 96.33%`；
  - accepted conflict groups: `0`；runtime en/zh alias conflicts: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest
    byte-identical；legacy full overlay 未更新；
  - compact index SHA-256: `7b60291f69b17c29696649f8ce176e49aeca41f65d17e37f9fc60906367dde26`；
  - compact manifest SHA-256: `e5e5fd0701c159100d382bee5c654d2631bf1b054790ba60a2a3baca855eac83`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认所有 `226` 条 accepted recommendation 可命中各自 target；
    `互联网拓扑`、`反问题`、`同位素`、`抖动`、`卡尔曼滤波算法`、`知识管理`、
    `纳米技术`、`物联网`、`恶意软件`、`图像处理` 保持不命中；
  - 相关测试：focused alias/runtime suite `909 passed in 28.01s`；
    project suite `1267 passed, 4 subtests passed in 97.70s`；
- post-95 exact collision review round6 已完成：
  - 继续从剩余 high/exact pool 中跳过 post95 已审/已拒绝项，选取 `300`
    个 collision group 做 explicit target selection；
  - 子代理审查合计接受 `172`、拒绝 `128`；主过滤后保留 `170` 条 explicit
    accept recommendation，跳过 `制药技术`、`光声学技术` 以保持当前膨胀型
    `*技术` policy；
  - L3-L5：fill `records_filled = 51815`，validate `review_decisions = 401174`；
    preserve 恢复 `52037` 条 prior zh 决策；`170` 条 recommendation 全部命中
    对应 runtime target；
  - `needs_review = 0`；`713` 条 English short acronym queue 继续 blocked；
  - runtime 中文覆盖从 `47819 / 49641 = 96.33%` 增至
    `47989 / 49753 = 96.45%`；
  - accepted conflict groups: `0`；runtime en/zh alias conflicts: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest
    byte-identical；legacy full overlay 未更新；
  - compact index SHA-256: `e263971743f4593e1f7958731d26dd4d8e0b4a517d9a0b169a160f35110145b1`；
  - compact manifest SHA-256: `03978cdc40bc9632c79ddb1a78e1d65d27aa101a39f1e3e305e4513351a5b6bd`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认所有 `170` 条 accepted recommendation 可命中各自 target；
    `神经科学`、`目标检测`、`光学字符识别`、`开源软件`、`光调制器`、`并行计算`、
    `路径规划`、`光声学技术`、`制药技术` 保持不命中；
  - 相关测试：focused alias/runtime suite `909 passed in 27.49s`；
    project suite `1267 passed, 4 subtests passed in 97.21s`；
- post-95 exact collision review round7 已完成：
  - 当前 pool 继续跳过 post95 已审/已拒绝 alias，剩余可审 collision group 为
    `221` 个，分 `3` 个 chunk 交给子代理审查；
  - 子代理审查合计接受 `124`、拒绝 `97`；主过滤没有额外剔除，最终
    explicit recommendation 为 `124` 条；
  - L3-L5：fill `records_filled = 51815`，validate `review_decisions = 401174`；
    preserve 恢复 `52037` 条 prior zh 决策；`124` 条 recommendation 全部命中
    对应 runtime target；
  - `needs_review = 0`；`713` 条 English short acronym queue 继续 blocked；
  - runtime 中文覆盖从 `47989 / 49753 = 96.45%` 增至
    `48113 / 49853 = 96.51%`；
  - accepted conflict groups: `0`；runtime en/zh alias conflicts: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest
    byte-identical；legacy full overlay 未更新；
  - compact index SHA-256: `c6e229891731a53b6b315c4dd9cad6aac68d94e758d64dd44f32a04e726094ad`；
  - compact manifest SHA-256: `dc34c299778d4eda19e74f31e88a7b52b6efd2d1eb28285311e0c342fb4582e6`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认所有 `124` 条 accepted recommendation 可命中各自 target；
    `环境辅助生活`、`随机森林`、`推荐系统`、`远程控制`、`软件工程`、`语音识别`、
    `系统生物学`、`文本挖掘`、`车联网`、`白人噪声` 保持不命中；
  - 相关测试：focused alias/runtime suite `909 passed in 26.83s`；
    project suite `1267 passed, 4 subtests passed in 97.14s`；
- post-95 singleton exact review round8 已完成：
  - round7 后剩余 high/exact pool 已无可用 collision group；跳过 prior
    post95 rejected alias 后，剩余 `86` 条 singleton blocked 候选；
  - 子代理审查合计接受 `8`、拒绝 `78`；主过滤没有额外剔除，最终
    explicit recommendation 为 `8` 条；
  - 接受项为 `关联规则挖掘`、`体型`、`悲伤`、`干扰约束`、`虹膜识别`、
    `消息认证`、`回归分析`、`水下设备`；
  - L3-L5：fill `records_filled = 51815`，validate `review_decisions = 401174`；
    preserve 恢复 `52037` 条 prior zh 决策；`8` 条 recommendation 全部命中
    对应 runtime target；
  - `needs_review = 0`；`713` 条 English short acronym queue 继续 blocked；
  - runtime 中文覆盖从 `48113 / 49853 = 96.51%` 增至
    `48115 / 49853 = 96.51%`；本轮主要增加 alias，概念覆盖净增 `2`；
  - accepted conflict groups: `0`；runtime en/zh alias conflicts: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest
    byte-identical；legacy full overlay 未更新；
  - compact index SHA-256: `b514d3a48c68ecad93009f0aa77c33d509b34a3eac9d8915d4c992f069f81523`；
  - compact manifest SHA-256: `c41c53fd1fb07ab0d8b22044ea99771df29f1c8d7dda1aad2f3d7dbe08a38288`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认所有 `8` 条 accepted recommendation 可命中各自 target；
    `声学发射`、`块代码`、`商业过程管理`、`基金会模型`、`燃料细胞`、`片剂计算机`、
    `白人噪声`、`智能玻璃`、`空间时间代码`、`断层成像光学` 保持不命中；
  - 相关测试：focused alias/runtime suite `909 passed in 26.91s`；
    project suite `1267 passed, 4 subtests passed in 96.36s`；
- post-95 new exact proposal round9 已完成：
  - 旧 high/exact pool 基本耗尽后，改从 `1738` 个 uncovered concepts 中抽取
    `300` 个高分专业术语候选，交给 `3` 个子代理提出/审查新 exact 中文 alias；
  - 子代理审查合计接受 `211`、拒绝 `89`；主过滤后保留 `119` 条写入
    `tools/theme-lexicon/reviewed_zh_exact_aliases.json`；
  - 主过滤跳过 `91` 条 runtime alias collision，不自动改写既有 target；跳过
    `1` 条 generic `*技术` 形态；
  - L3-L5：fill `records_filled = 51823`，validate `review_decisions = 401182`；
    preserve 恢复 `51941` 条 prior zh 决策；显式接受 `119` 条 round9
    recommendation；`4` 条未审 generated zh needs_review 明确 blocked；
  - `needs_review = 0`；accepted conflict groups: `0`；runtime en/zh alias
    conflicts: `0`；
  - runtime 中文覆盖从 `48115 / 49853 = 96.51%` 增至
    `48227 / 49851 = 96.74%`；本轮净增 `112` 个 zh-covered concepts；
  - package/tool compact index byte-identical；package/tool compact manifest
    byte-identical；legacy full overlay 未更新；
  - compact index SHA-256: `c319094060a968781c5487ff2d1ab402c709d4b6aa1dba5ecb440faa48bd1108`；
  - compact manifest SHA-256: `85bf6f0a7ea6c3f6b585420ce98a4098efb59062ba157ba408ea041d1abdbb2e`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认所有 `119` 条 round9 accepted alias 可命中各自 target；
    被跳过的 collision alias 仍指向既有 runtime target，`声学发射`、`基金会模型`、
    `燃料细胞` 等坏译保持不命中；
  - 相关测试：focused alias/runtime suite `909 passed in 27.62s`；
    project suite `1267 passed, 4 subtests passed in 96.98s`；
- post-95 new exact proposal round10 已完成：
  - 从当前 `1624` 个 uncovered concepts 中筛选 `300` 个 fresh exact/domain-aware
    候选，分 `3` 个 chunk 交给子代理审查；
  - 子代理审查合计接受 `103`、拒绝 `197`；主过滤初筛保留 `64` 条，
    但 final validate 发现其中 `51` 条为 duplicate/collision blocked，
    另有 `1` 条未生成可接受 row；最终只保留 `12` 条 runtime-safe reviewed
    source row；
  - L3-L5 final：fill `records_filled = 51825`，validate
    `review_decisions = 401184`；preserve 恢复 `52038` 条 prior zh 决策；
    final actual recommendation 已被 preserve 保持，`1` 条 remaining zh
    needs_review 与 `713` 条 en acronym needs_review 均显式 blocked；
  - `needs_review = 0`；accepted conflict groups: `0`；runtime en/zh alias
    conflicts: `0`；
  - runtime 中文覆盖从 `48227 / 49851 = 96.74%` 增至
    `48237 / 49851 = 96.76%`；本轮净增 `10` 个 zh-covered concepts；
  - package/tool compact index byte-identical；package/tool compact manifest
    byte-identical；legacy full overlay 未更新；
  - compact index SHA-256: `112f9c72163599990525dbc974a98460232eac429a9aa0936c76b4812f663b1f`；
  - compact manifest SHA-256: `7eff78af45df2858ac122fded1f8619e0197ea418be7fd9f214193431f830793`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `12` 条 actual accepted alias 均命中各自 target；被清理的
    collision candidate 不会误命中被跳过 target；
  - 相关测试：focused alias/runtime suite `909 passed in 27.18s`；project suite
    `1267 passed, 4 subtests passed in 98.15s`；
- post-95 new exact proposal round11 已完成：
  - 跳过此前 post95 已选 `668` 个概念后，从当前 `1614` 个 uncovered
    concepts 中筛出 `300` 个 fresh exact/domain-aware 候选；
  - 子代理审查合计接受 `174`、拒绝 `126`；主过滤初筛保留 `113` 条，
    跳过 `51` 条 runtime collision、`2` 条 internal collision、`8` 条坏形态；
  - final validate 后清理 `95` 条 duplicate/collision blocked source-only row，
    最终保留 `18` 条 runtime-safe reviewed source row；
  - L3-L5 final：fill `records_filled = 51835`，validate
    `review_decisions = 401194`；preserve 恢复 `52029` 条 prior zh 决策；
    `2` 条 remaining zh needs_review 与 `713` 条 en acronym needs_review 均显式
    blocked；
  - `needs_review = 0`；accepted conflict groups: `0`；runtime en/zh alias
    conflicts: `0`；
  - runtime 中文覆盖从 `48237 / 49851 = 96.76%` 增至
    `48253 / 49849 = 96.80%`；本轮净增 `16` 个 zh-covered concepts；
  - package/tool compact index byte-identical；package/tool compact manifest
    byte-identical；legacy full overlay 未更新；
  - compact index SHA-256: `37d15c0416924cec95b8df30c361d065c0b93629af5cebbf7aaf57c4d04b8f14`；
  - compact manifest SHA-256: `b33c66a469203965635ad49e885ef3776dd757cea14454bef611299a4cf11fd9`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `18` 条 actual accepted alias 均命中各自 target；被清理的
    collision candidate 不会误命中被跳过 target；
  - 相关测试：focused alias/runtime suite `909 passed in 27.58s`；project suite
    `1267 passed, 4 subtests passed in 98.75s`；
- post-95 new exact proposal round12 已完成：
  - 跳过此前 post95 已选 `968` 个概念后，remaining fresh high-score pool 仅剩
    `133` 个候选；
  - 子代理审查合计接受 `88`、拒绝 `45`；主过滤初筛保留 `62` 条，跳过
    `19` 条 runtime collision、`3` 条 internal collision、`4` 条英文残留形态；
  - final validate 后清理 `52` 条 duplicate/collision blocked 或未生成可接受 row，
    最终保留 `10` 条 runtime-safe reviewed source row；
  - L3-L5 final：fill `records_filled = 51844`，validate
    `review_decisions = 401203`；preserve 恢复 `52063` 条 prior zh 决策；
    `2` 条 remaining zh needs_review 与 `713` 条 en acronym needs_review 均显式
    blocked；
  - `needs_review = 0`；accepted conflict groups: `0`；runtime en/zh alias
    conflicts: `0`；
  - runtime 中文覆盖从 `48253 / 49849 = 96.80%` 增至
    `48262 / 49849 = 96.82%`；本轮净增 `9` 个 zh-covered concepts；
  - package/tool compact index byte-identical；package/tool compact manifest
    byte-identical；legacy full overlay 未更新；
  - compact index SHA-256: `1daa3b44657a16b87093f0681c5cadd24b115fbc6b1d88f1ae76a4b4f437ba19`；
  - compact manifest SHA-256: `4799f06f657fed06b76c4981b718b25cc22a1e835603ca0d16cddf4ead56e57f`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `10` 条 actual accepted alias 均命中各自 target；被清理的
    collision candidate 不会误命中被跳过 target；
  - 相关测试：focused alias/runtime suite `909 passed in 27.98s`；project suite
    `1267 passed, 4 subtests passed in 98.16s`；
- post-95 new exact proposal round13 已审查完成：
  - 跳过此前 post95 已选 `1101` 个概念后，fresh exact/domain-aware
    pool 只剩 `1` 个候选：`concept:photoacoustic_effect__2`；
  - 子代理审查结论：`0` accept、`1` reject；候选 alias 已是 collision-blocked
    duplicate 形态，没有安全 target-specific alias；
  - 未追加 `tools/theme-lexicon/reviewed_zh_exact_aliases.json`，未运行
    materialize，runtime 状态保持 round12：`48262 / 49849 = 96.82%`；
  - 当前 exact-only、no-retarget、no-merge 路线已基本耗尽；继续接近 `100%`
    需要先制定并实施 canonical duplicate/retarget policy，否则后续大多数标准
    中文术语仍会被 collision guard 阻断；
- 后续连续扩展继续采用新的提交节奏：每 `5` 轮 `20-batch` 处理作为一个最终 milestone commit；中间 checkpoint、review 清单和 smoke 产物仅放在 `F:\AI playground\TempFiles`，不再每轮 20-batch 都提交；
- batch-2187-to-3400 milestone 临时审查产物：
  `F:\AI playground\TempFiles\review_decisions.before-35pct.20260625-012746.jsonl`，
  `F:\AI playground\TempFiles\exact_domain_35pct_aliases_v3b.json`，
  `F:\AI playground\TempFiles\zh_review_recommendations_35pct_exact_domain_v3b.json`，
  `F:\AI playground\TempFiles\zh_review_recommendations_35pct_needs_review_cleanup.json`，
  `F:\AI playground\TempFiles\theme_alias_runtime_full_audit_35pct_final.jsonl`；
- post-20% 质量复盘和窄 L6 treemap/text fallback 修复已完成；当前主线回到 exact/domain-aware 中文 alias 覆盖扩展；
- post-35% review cleanup 已完成；已修复 `remote` / `solution` / `software libraries` 多义坏译，`遥感控制器`、`遥感监测与控制`、`遥感监测系统`、`溶液设计` 不再进入 runtime；
- full zh runtime audit + solution cleanup 已完成；修复 CJK/Latin、`∞`、括号缩写归一化，`H控制` / `H∞控制` 与 `NADPH` / `NAD(P)H` 不再错误折叠；修复 `云数据安全溶液`、`硬件溶液`、`导航溶液`、`接触晶状体溶液`，当前 full-audit triage: accepted/runtime mismatch `0`，old bad alias hits `0`，unresolved major/critical flags `0`；
- full-audit cleanup 产物：`F:\AI playground\TempFiles\review_decisions.before-full-audit-solution-cleanup.20260626.jsonl`，`F:\AI playground\TempFiles\zh_review_recommendations.full-audit-solution-cleanup-20260626.json`，`F:\AI playground\TempFiles\theme_alias_runtime_full_audit_full_review_solution_cleanup_20260626.jsonl`，`F:\AI playground\TempFiles\theme_alias_full_zh_audit_post_solution_cleanup_20260626.json`，`F:\AI playground\TempFiles\theme_alias_full_zh_audit_post_solution_cleanup_flags_20260626.jsonl`；
- `优化链路状态路由` 与 `光码分多址` 当前因 acronym/full-form duplicate collision 阻断，不作为 runtime 可命中 alias；`SAW滤波器` 与 `声表面波滤波器` 仍是后续 canonical-target / duplicate review 项，不自动 merge；
- full-audit triage 已覆盖此前 bounded risk scan：当前 old bad alias hits `0`，unresolved major/critical flags `0`，剩余 `溶液` flags 均为 info-level biomedical solution forms；暂不建议 full manual sweep；
- host Agent 默认不要再打开完整 `theme_concept_aliases.json` 或 compact index 大文件做状态确认；
- 需要状态时优先看 manifest/stats/query 工具输出；
- 最新 post-99 round3 safe patch 已完成：
  - 从 remaining uncovered 中筛选不碰撞多词标准术语，继续保持不放开 mixed fallback、不 blanket accept medium compositional candidates、不自动 merge collision；
  - 子代理接受 `16` 条、拒绝 `4` 条；进入 runtime 的 `16` 条为：`二维材料与应用`、`算法设计与分析`、`异常检测技术与应用`、`天线设计与分析`、`天线设计与优化`、`大数据技术与应用`、`数据挖掘算法与应用`、`地震检测与分析`、`心电监测与分析`、`博弈论与应用`、`地球物理方法与应用`、`模糊系统与优化`、`无人机应用与优化`、`水质监测与分析`、`水资源管理与优化`、`化学合成与分析`；
  - `流量测量与分析`、`力显微镜技术与应用`、`岩土工程与分析`、`环境化学与分析` 因歧义或生成感保持不命中；
  - L3-L5：fill `records_filled = 53085`，validate `review_decisions = 402467`，reconstruct 后 `zh:accept = 48742`、`zh:blocked = 4595`、`zh:reject = 17`、`zh:needs_review = 0`；
  - runtime 中文覆盖从 `48612 / 49055 = 99.10%` 增至 `48628 / 49055 = 99.13%`；
  - accepted conflict groups: `0`；runtime en/zh alias conflicts: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay 未更新；
  - compact index SHA-256: `951143f89f435160acea7d2bcae172b4023465d995f24e77145fe4680a536dde`；
  - compact manifest SHA-256: `2cc00d7986e8145eae25e0e847b3b51903217e555d4ba1b9c75b3c0dba36b386`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - 相关测试：focused alias/runtime suite `903 passed in 22.21s`。
- 最新 post-99 round2 safe patch 已完成：
  - 继续只处理不碰撞、子代理明确接受的 exact/domain-aware 中文 alias；
  - 子代理接受 `11` 条候选；实际进入 runtime `10` 条：`数字印刷`、`分布式内存架构`、`电气布线`、`工程与材料科学研究`、`极限学习机`、`入侵防御`、`信道状态信息`、`单片微波集成电路`、`皮肤癣菌病`、`马蹄蟹`；
  - `身体与器官系统` 未进入 runtime：当前 fill/validate 未生成可接受 zh review row；
  - L3-L5：fill `records_filled = 53085`，validate `review_decisions = 402467`，reconstruct 后 `zh:accept = 48726`、`zh:blocked = 4611`、`zh:reject = 17`、`zh:needs_review = 0`；
  - runtime 中文覆盖从 `48602 / 49055 = 99.08%` 增至 `48612 / 49055 = 99.10%`；
  - accepted conflict groups: `0`；runtime en/zh alias conflicts: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay 未更新；
  - compact index SHA-256: `55ebe1237561ae9b79da96c1e4b26a5769c8faa5d562157bac9b41936f84994b`；
  - compact manifest SHA-256: `2546c72ce762c94cc816f7628782b8a8e5edf929418257a33cb6a07be6cb5df8`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认上述 `10` 条新增 alias 可命中，`身体与器官系统` 保持不命中；
  - 相关测试：focused alias/runtime suite `903 passed in 22.79s`。
- 最新 post-99 safe patch 已完成：
  - 在不放宽低质 fallback、medium compositional blanket accept、collision/duplicate merge 的前提下，复核最终 uncovered 中少量 high-confidence 候选；
  - 子代理接受 `18` 条候选，主代理保留既有 reject/collision 决策，仅显式接受 `5` 条不碰撞且未被旧审查否决的 exact/domain-aware alias：`农业与农村发展研究`、`计算机编程语言`、`围手术期护理`、`钠通道激动剂`、`电压门控钠通道激动剂`；
  - `数字管理`、`心理学计算` 被子代理拒绝；`高等数学恒等式`、`数据检测`、`图书馆管理`、`护理管理研究`、`公共卫生管理` 等保留既有 reject 决策，不覆盖旧审查；
  - L3-L5：fill `records_filled = 53082`，validate `review_decisions = 402464`，preserve/reconstruct 后 `zh:accept = 48716`、`zh:blocked = 4615`、`zh:needs_review = 0`；
  - runtime 中文覆盖从 `48597 / 49055 = 99.07%` 增至 `48602 / 49055 = 99.08%`；
  - accepted conflict groups: `0`；runtime en/zh alias conflicts: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay 未更新；
  - compact index SHA-256: `4079162b9caba380850046539e81ae9e4741db4fa6afb79462fea571ea7c2c17`；
  - compact manifest SHA-256: `0e673b490dde3f4ce9e655ee759e79dde67b32304791f1d5f66c21d97755089f`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `农业与农村发展研究`、`计算机编程语言`、`围手术期护理`、`钠通道激动剂`、`电压门控钠通道激动剂` 可命中，`数字管理`、`心理学计算` 保持不命中；
  - 相关测试：focused alias/runtime suite `903 passed in 22.70s`；project suite `1261 passed, 4 subtests passed in 95.38s`。
- 最新 post-90-to-final subagent-reviewed milestone 已完成：
  - 继续使用 `tools/theme-lexicon/reviewed_zh_exact_aliases.json` 作为 versioned reviewed exact/domain-aware 中文别名真源；
  - 对 post-90 剩余 uncovered 进行多轮子代理审查：round1 全量 `10` chunks、round2 `8` chunks、completion `6` chunks、final-gap `1` chunk；
  - 主代理每轮均过滤普通英文残留、invalid zh alias、runtime/source/internal collision 和 known bad shape；不自动 merge duplicate/collision concept；
  - completion round 明确采用“中文检索/display alias”口径，但仍保留 collision/污染/坏形态边界；
  - final L3-L5：fill `records_filled = 53082`，validate `review_decisions = 402464`，preserve 恢复 `47460` 条 prior review 决策；最终显式应用 round1/round2/completion/final-gap recommendations；剩余 `165` 条 zh needs_review 与 `713` 条 en acronym needs_review 均显式 blocked；
  - runtime 中文覆盖从 `44379 / 49273 = 90.07%` 增至 `48597 / 49055 = 99.07%`；
  - `zh:accept`: `48711`，`zh:blocked`: `4620`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；runtime en/zh alias conflicts: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay 未更新；
  - compact index SHA-256: `e5e0a4b63dd6c72b6e2b9a5fa9b69df071e5ef41c325d6968148fb27d3620d09`；
  - compact manifest SHA-256: `8daa8d958cc759d8a75b5406f5e5ad905350e83a6f7aaeb39bc624b2a93bfbae`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - `100%` 数学覆盖未强行声称完成：最终剩余 `458` 个 uncovered concept 已归档在 `F:\AI playground\TempFiles\theme_alias_100pct_final_uncovered_audit_20260629`；继续硬冲需要放宽 collision/duplicate 或低质 alias 边界，不符合当前约束；
  - query smoke 已确认 `玛丽约瑟夫修女结节`、`三维IC与硅通孔技术`、`SPECT成像` 可命中，`Sister Mary Joseph结节`、`三维IC与TSV技术`、`SPECT图像重建`、`智能汽车溶液`、`逆运动学溶液`、`配置法`、`机器转换系统`、`噪声降维`、`小波领域` 保持不命中；
  - review 产物集中在 `F:\AI playground\TempFiles\theme_alias_100pct_review_uncovered_20260629`、`F:\AI playground\TempFiles\theme_alias_100pct_round2_uncovered_20260629`、`F:\AI playground\TempFiles\theme_alias_100pct_round3_completion_20260629`、`F:\AI playground\TempFiles\theme_alias_100pct_final_gap_20260629`；final full audit 输出为 `F:\AI playground\TempFiles\theme_alias_runtime_full_audit_100pct_final_gap_20260629.jsonl`；
  - 相关测试：focused alias/runtime suite `903 passed in 23.50s`；project suite `1261 passed, 4 subtests passed in 96.26s`。
- 最新 post-80-to-90 subagent-reviewed milestone 已完成：
  - 继续使用 `tools/theme-lexicon/reviewed_zh_exact_aliases.json` 作为 versioned reviewed exact/domain-aware 中文别名真源；
  - 子代理审查 `16` 个 90% uncovered chunks，修复中断遗留的 `reviewed-chunk-14.test.json` 误纳入风险，最终仅使用正式 `reviewed-chunk-14.json`；
  - 主代理过滤普通英文残留、已覆盖概念、内部 alias 碰撞、runtime/source alias 碰撞和坏形态后形成 `5284` 条 90% v2 recommendation；
  - 移除并阻断 `Sister Mary Joseph结节` ordinary-English-heavy 污染项，query smoke 确认不再命中；
  - 追加 `3` 个 supplement chunks 复核当前未覆盖 deterministic 候选；raw accept `1174`，最终过滤为 `552` 条 supplement recommendation，显式接受 `550` 条；
  - L3-L5 final：fill `records_filled = 49893`，validate `review_decisions = 399268`，preserve 恢复 `39116` 条 prior review 决策；显式接受 `5279` 条 90% v2 recommendation 与 `550` 条 supplement recommendation；剩余 `107` 条 zh needs_review 与 `713` 条 en acronym needs_review 均显式 blocked；
  - runtime 中文覆盖从 `39698 / 49058 = 80.92%` 增至 `44379 / 49273 = 90.07%`；
  - `zh:accept`: `44493`，`zh:blocked`: `5633`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；runtime en/zh alias conflicts: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay 未更新；
  - compact index SHA-256: `efde2051a33ad6c3379fddcf23b7812e719a678d55c7cffb733abf4c003883e1`；
  - compact manifest SHA-256: `088065a671cedc1d5bb04e653c06bb27352f47d4c2fab1fac9c4d524c04c2385`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `线性判别分析` 可命中，`Sister Mary Joseph结节`、`三维IC与TSV技术`、`SPECT图像重建` 保持不命中；
  - review 产物集中在 `F:\AI playground\TempFiles\theme_alias_90pct_review_all_uncovered_20260629_021207` 和 `F:\AI playground\TempFiles\theme_alias_90pct_supplement_20260629`，final full audit 输出为 `F:\AI playground\TempFiles\theme_alias_runtime_full_audit_90pct_final2_20260629.jsonl`；
  - 相关测试：focused alias/runtime suite `903 passed in 20.93s`；project suite `1261 passed, 4 subtests passed in 93.31s`。
- 最新 post-70-to-80 subagent-reviewed milestone 已完成：
  - 继续使用 `tools/theme-lexicon/reviewed_zh_exact_aliases.json` 作为 versioned reviewed exact/domain-aware 中文别名真源；
  - 子代理审查 `14` 个 80% uncovered chunks，主代理过滤普通英文残留、已覆盖概念、内部 alias 碰撞、坏形态和泛词后新增 `4635` 条 reviewed exact aliases；
  - post-review chunks 01-07 共发现并修复 `80` 个 replacement；其中 `Ising Model -> 伊辛模型`、`Persian Gulf -> 波斯湾`、`Psychology Transfer -> 心理迁移`、`Non-Polyadenylated RNA -> 非多聚腺苷酸化RNA`、`Natural Satellite -> 天然卫星` 等旧泛化/错配 alias 已阻断；
  - 新增 reviewed exact 优先级规则：`subagent_post_review_fix_*` 来源优先于早期 reviewed/raw exact，避免 raw canonical exact 挡住窄 replacement；
  - 更新 CJK/ASCII alias normalization，保留 `#`、`%`、`,` 等有语义符号，`C#语言` 不再折叠为 `c 语言`，`GM(1,1)灰色模型` 不再折叠为 `gm 1 1 灰色模型`；
  - L3-L5 final：fill `records_filled = 44741`，validate `review_decisions = 394113`，preserve 恢复 `35320` 条 prior review 决策；显式接受 `5333` 条 combined recommendation，并应用 `80` 条 post-review replacement；剩余 `118` 条 zh needs_review 与 `713` 条 en acronym needs_review 均显式 blocked；
  - runtime 中文覆盖从 `34343 / 49060 = 70.00%` 增至 `39698 / 49058 = 80.92%`；
  - `zh:accept`: `39812`，`zh:blocked`: `5159`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；runtime en/zh alias conflicts: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay 未更新；
  - compact index SHA-256: `c4d874823c8ff15ec29b71d517d15b0c4e128b34e1ca1d01a43311e352ddaee7`；
  - compact manifest SHA-256: `1017d3be78b9c96a03b537060773e8366729cf48655bbd1dd26fed5af943fc2e`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - targeted source-to-runtime smoke 已确认 `80` 个 post-review replacement 全部命中，`80` 个旧 alias 不再命中原 concept；
  - query smoke 已确认 `心理迁移`、`非多聚腺苷酸化RNA`、`天然卫星`、`C#语言`、`GM(1,1)灰色模型` 可命中，`机器学习`、`核糖核酸`、`太阳系`、`c 语言`、`gm 1 1 灰色模型` 保持不命中；
  - post-review 产物集中在 `F:\AI playground\TempFiles\theme_alias_80pct_post_review_20260629_010846`，final full audit 输出为 `F:\AI playground\TempFiles\theme_alias_runtime_full_audit_80pct_post_review_final_20260629.jsonl`；
  - 相关测试：focused alias/runtime suite `903 passed in 18.80s`；project suite `1261 passed, 4 subtests passed in 86.71s`。
- 最新 post-60-to-70 subagent-reviewed milestone 已完成：
  - 继续使用 `tools/theme-lexicon/reviewed_zh_exact_aliases.json` 作为 versioned reviewed exact/domain-aware 中文别名真源；
  - 子代理审查 `15` 个 70% chunk/segment 输出，主代理过滤普通英文残留、已覆盖概念、内部 alias 碰撞、坏形态和泛词后形成 `5897` 条 combined explicit recommendation；
  - 另补充少量主代理逐条 exact biomedical/domain term supplement，用于跨过 `70%` 四舍五入边界；
  - L3-L5 final：fill `records_filled = 41434`，validate `review_decisions = 390806`，preserve 恢复 `35594` 条 prior review 决策；最终显式接受 `22` 条最后补量 recommendation，剩余 `1` 条 zh needs_review 与 `713` 条 en acronym needs_review 均显式 blocked；
  - runtime 中文覆盖从 `29479 / 49049 = 60.10%` 增至 `34343 / 49060 = 70.00%`（exact `70.002%`）；
  - `zh:accept`: `34459`，`zh:blocked`: `7180`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；runtime en/zh alias conflicts: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay 未更新；
  - compact index SHA-256: `0e9d204aaa46f10b00c032c9f6dfb8ad7e075395ff7d63353687c664e6f10db0`；
  - compact manifest SHA-256: `69b49640d0a9e60a304f9ab59f7aa2f5f97618124a0d68acffb7b4ad546a6464`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - post-review 产物集中在 `F:\AI playground\TempFiles`，包括 `zh_review_recommendations_70pct_final_combined_20260628.json`、`theme_alias_runtime_full_audit_70pct_final4_20260628.jsonl`、`review_decisions.before-70pct-final4-clean.20260628.jsonl`；
  - 相关测试：`882 passed in 6.56s`。
- 最新 post-50-to-60 subagent-reviewed milestone 已完成：
  - 新增 `tools/theme-lexicon/reviewed_zh_exact_aliases.json`，收纳子代理审查后的 exact/domain-aware 中文别名，`fill_zh_alias_candidates.py` 仅在默认生产 candidate dir 下 lazy-load 该文件，避免单元测试临时目录被生产大表污染；
  - 新增 biomedical named-class suffix review-gated 候选生成，并保持 medium 候选仍需显式 review；
  - 子代理审查 chunks 01-09：输入 `9600` 条未覆盖概念，原始 accept `6991`，经主代理过滤普通英文残留、既有 alias 冲突、内部碰撞和坏形态后形成 `6363` 条 reviewed exact aliases；另显式接受 `123` 条 safe needs_review cleanup，其余 `384` 条 remaining zh needs_review 明确 blocked；
  - 修正 materialize pollution audit 对 `蛋白酪氨酸磷酸酶` 的误报：`酸磷酸酶` 仅作为完整 alias 坏形态命中，合法 `酪氨酸磷酸酶` 不再被污染审计误报；
  - L3-L5 final：fill `records_filled = 35699`，validate `review_decisions = 385064`，preserve 恢复 `23670` 条 prior review 决策；显式接受 `6193` 条 filtered recommendation，`713` 条 English short acronym queue 继续 blocked；
  - runtime 中文覆盖从 `25302 / 50592 = 50.01%` 增至 `29479 / 49049 = 60.10%`；
  - `zh:accept`: `29595`，`zh:blocked`: `6301`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；runtime en/zh alias conflicts: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay 未更新；
  - compact index SHA-256: `6a0afc8a2cda5094af44deaaff6a388d09543632eee77d0aa88f5d54779ec20e`；
  - compact manifest SHA-256: `4ee27eb2a7c896c32258dfc82e86da8933e988e249032c6255063b581a7504e3`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `2-氨基嘌呤`、`分形天线`、`蛋白酪氨酸磷酸酶` 可命中，`酸磷酸酶` 保持不命中；
  - 相关测试：`882 passed in 7.04s`。
- 最新 post-40-to-50 continuation review 已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_7001_TO_9000_ALIASES` 后续 exact/domain-aware 术语，覆盖 acoustic/radar/optical/communications/security/programming/control/data/software/knowledge/routing 等 CS/通信/控制高置信术语，并补充少量 biomedical exact replacement；
  - 新增 `test_50pct_review_feedback_corrects_exact_standard_terms` 回归测试，固定 `Cluster Computing -> 集群计算`、`SQL Injection -> SQL注入`、`Phase Change Memory -> 相变存储器`、`Clinical Decision Support Systems -> 临床决策支持系统`、`Optical Tomography -> 光学断层成像`、`Collocation Method -> 配点法` 等标准译法，阻断 `聚类计算`、`SQL注射`、`相位变化存储`、`断层成像光学`、`视觉变压器`、`配置法` 等坏形态；
  - 显式 review 后接受 50% milestone 非碰撞 exact/domain-aware recommendation；`会话初始协议`、`运行时重构`、`错误平台`、`流行路由` 等 review 坏译保持 blocked；duplicate/collision 仍不自动 merge；
  - runtime 中文覆盖从 post-40 baseline `21133 / 48947 = 43.18%` 增至 `25302 / 50592 = 50.01%`；
  - `zh:accept`: `25423`，`zh:blocked`: `3166`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；runtime en/zh alias conflicts: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay 未更新；
  - compact index SHA-256: `11f5168a1210c7312680c14dae734d7f24ce0e39fc2aaac46c7e5cc55e7a7689`；
  - compact manifest SHA-256: `0b76105360d187610552f53c3496f6c08c3e15a4152ca4acaa5a891082c353ba`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `配点法`、`条件随机场`、`深度包检测`、`知识图谱补全`、`随机游走`、`安全多方计算`、`软件漏洞` 可命中；`配置法`、`会话初始协议`、`运行时重构`、`错误平台`、`流行路由`、`缓冲区溢出` 保持不命中；
  - 相关测试：`879 passed in 6.79s`。
- post-50% review：
  - 当前 clean runtime 已超过 `>40%` 目标；相比 post-40 baseline 净增 `4169` 个 zh-covered concepts；
  - 新增 alias 相比 HEAD 净增约 `4287` 条 zh runtime alias，`7` 条旧 runtime alias 被 replacement/collision 规则挤出，`18` 条 alias target 在重复概念间切换；
  - 不打开低质 mixed fallback、不 blanket accept medium-confidence compositional candidates、不自动 merge collision、不进入新的 L6；
  - 建议先由用户决定是否提交当前 `50.01%` 未提交变更；若继续扩大覆盖，下一目标应单独确认，仍从 exact/domain-aware explicit review 推进。
- 最新 post-7000 exact/domain-aware pattern milestone 已完成：
  - 新增受控 domain-aware exact 生成层：life/physical domain 组件表、短 canonical 全组件 exact helper、physical/function/treatment/signaling 语义覆盖、ASCII 残留 guard 与坏形态 guard；
  - 新增 `ZH_EXACT_EXPANSION_BATCH_7001_TO_9000_ALIASES` 小型 exact 覆盖，并修正 `energy efficient routing -> 能效路由`；
  - L3-L5 final：fill `records_filled = 27632`，validate `review_decisions = 376984`，preserve 恢复 `23225` 条 prior review 决策；显式接受 `402 + 177 + 1` 条 needs_review high/exact，并重开 `618 + 465` 条 non-collision high/exact blocked；`713` 条 validator-regenerated English short acronym queue 继续 blocked；
  - runtime 中文覆盖从 `18258 / 48932 = 37.31%` 增至 `19828 / 48973 = 40.49%`；
  - `zh:accept`: `19839`，`zh:blocked`: `7966`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；runtime en/zh alias conflicts: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay 未更新；
  - compact index SHA-256: `e0b641e848f3a4980c09a0fffc0d4d6d14b978502dca5b23435c22bc75ec7511`；
  - compact manifest SHA-256: `9cdbed668246ec2c4acee231cd59fd911c059dc49d9620a58ff8653eccb76a80`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；additional bad-shape scan hits `0`；
  - query smoke 已确认 `原子力显微镜`、`高级加密标准`、`高级氧化水处理`、`通信系统信令`、`节能以太网`、`能效路由`、`智能汽车解决方案`、`逆运动学解`、`帕累托解`、`求解方法`、`分数微分方程解`、`人因工程`、`应用数学`、`蓝牙设备`、`CNC机床` 可命中，`肾上腺素能光纤`、`乳腺馈电`、`通信系统信号转导`、`碱性情绪`、`调节柔顺`、`全率`、`能源高效路由`、`智能汽车溶液`、`逆运动学溶液`、`帕累托溶液`、`溶液方法`、`溶液概念`、`溶液精度`、`分数微分方程溶液` 保持不命中；
  - 相关测试：`871 passed in 6.32s`。
- post-40% review：
  - 本 milestone 新增 `1569` 个 runtime zh-covered concepts，主要来自 high/exact review、受控 full-component exact 规则和少量 replacement cleanup；
  - 不打开低质 mixed fallback、不 blanket accept medium-confidence compositional candidates、不自动 merge collision、不进入新的 L6；
  - post-40 canonical collision target review 曾显式选择 canonical high-exact collision target；后续 cleanup deferred 未完成的 50% pending 候选并修复 bad-shape 污染，保持“一 alias 只接受一个 runtime target”，未合并 duplicate/collision concept；
  - runtime 中文覆盖收口到 `21133 / 48947 = 43.18%`，`zh:accept = 21143`，`zh:blocked = 6649`；
  - accepted conflict groups: `0`；runtime en/zh alias conflicts: `0`；pollution audit bad-shape hits: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；compact index SHA-256: `af7d955caaaa9dd641807e9aee4350cdbc7697c2b4ec3bc3fd85621ff56a71cc`；
  - query smoke 已确认 `S期`、`S期细胞周期检查点`、`S期激酶相关蛋白`、`抗酒石酸酸性磷酸酶` 可命中，`S相位`、`S相位细胞周期检查点`、`S相位激酶相关蛋白`、`酸磷酸酶V`、`二进制流体`、`农业安全与调节` 保持不命中；
  - 后续建议先提交 40%-43.18% 变更，再决定是否继续冲 `45%` 或转入 treemap/text fallback 质量验证。
- 最新 batch-4001 至 batch-7000 exact/domain-aware 五组 milestone 已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_4001_TO_4600_ALIASES`、`ZH_EXACT_EXPANSION_BATCH_4601_TO_5200_ALIASES`、`ZH_EXACT_EXPANSION_BATCH_5201_TO_5800_ALIASES`、`ZH_EXACT_EXPANSION_BATCH_5801_TO_6400_ALIASES`、`ZH_EXACT_EXPANSION_BATCH_6401_TO_7000_ALIASES`；
  - 覆盖 data/software/web/signal、RNA/DNA/protein/viral/cell、dental/tooth、receptor/CXCR/dopamine/GABA/interleukin/KIR/opioid 等 exact/domain-aware 术语；
  - 新增 `10` 个回归测试，确认 `Data Abstraction -> 数据抽象`、`RNA, Long Noncoding -> 长链非编码RNA`、`Dental Calculus -> 牙结石`、`Receptors, CCR5 -> CCR5受体`、`Receptors, Interleukin-6 -> 白细胞介素6受体` 等候选生成，并阻断 `移动临时网络`、`DNA洗牌`、`牙科微积分`、`补体受体三维`、`缺口4受体` 等坏形态；
  - 五组 L3-L5 后：final fill `records_filled = 27186`，final validate `review_decisions = 376547`，preserve 恢复 `22698` 条 prior review 决策；
  - 显式接受 `579` 条 exact/domain-aware recommendation，cleanup 接受 `9` 条中文候选，阻断 `5` 条宽泛/坏形态中文候选；`713` 条 validator-regenerated English short acronym queue 继续 blocked；
  - `digital_forensic / 数字取证` 旧 runtime target 已显式恢复，`digital_investigation / 数字取证` 保持 blocked，不自动 merge duplicate concepts；
  - runtime 中文覆盖从 `17678 / 48932 = 36.13%` 增至 `18258 / 48932 = 37.31%`；
  - `zh:accept`: `18270`，`zh:blocked`: `9090`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；runtime en/zh alias conflicts: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay 未更新；
  - compact index SHA-256: `dc975bb3df0425f8e91070027d55c7ab3dec8d22acc41f1ad8d3036ef63581dd`；
  - compact manifest SHA-256: `5df995720bae6c3417c5907fc6f43e341d06a6a5153a7c5533304e9700ef8abd`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `数据抽象`、`分布式哈希表`、`长链非编码RNA`、`重组DNA`、`蛋白质折叠`、`病毒载量`、`牙结石`、`牙髓坏死`、`阻生牙`、`CCR5受体`、`多巴胺D2受体`、`白细胞介素6受体`、`KIR2DL1受体`、`μ阿片受体` 可命中，`移动临时网络`、`DNA洗牌`、`牙科微积分`、`补体受体三维`、`缺口4受体` 保持不命中；
  - 相关测试：`869 passed in 6.03s`。
- batch-7000 后 review：
  - 本 milestone 新增 `580` 个 runtime zh-covered concepts，覆盖率增至 `37.31%`；
  - 目标 `>40%` 仍需继续，下一段建议继续 high-confidence biomedical exact 族，但避免化学长名和低质 mixed fallback；
  - 不 blanket accept medium-confidence compositional candidates、不自动 merge collision、不进入新的 L6。
- 最新 batch-3401 至 batch-4000 exact/domain-aware 推进已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_3401_TO_3600_ALIASES`，覆盖 adaptive/audio/augmented reality/authentication/background subtraction/backpropagation/client-server/data visualization/device-to-device/electromagnetic/free-space optical 等 A-F 段高置信技术术语；
  - 新增 `ZH_EXACT_EXPANSION_BATCH_3601_TO_3800_ALIASES`，覆盖 fuzzy/grid/interaction/IP/iris/optical/QoS/radio/regularization/RFID/robot/semantic 等 G-R 段技术术语；
  - 新增 `ZH_EXACT_EXPANSION_BATCH_3801_TO_4000_ALIASES`，覆盖 machine translation/noise reduction/process-oriented/software/Web/XML/visual/wavelet 等 M-Z 段技术术语；
  - 新增 `6` 个回归测试，确认 `Audio-visual -> 视听`、`Device-to-device Communication -> 设备到设备通信`、`Human Computer Interface -> 人机接口`、`Real Number -> 实数`、`Machine Translation Systems -> 机器翻译系统`、`Noise Reduction -> 降噪`、`Wavelet Domain -> 小波域`、`Web Crawler -> Web爬虫` 等候选生成，并阻断 `总线基于`、`聚类基于`、`通信信道信息理论`、`机器转换系统`、`噪声降维`、`小波领域` 等坏形态；
  - batch-3801 final L3-L5：fill `records_filled = 26710`，validate `review_decisions = 376054`；preserve 恢复 `22270` 条 prior review 决策；
  - 三段合计显式接受 `260` 条本轮 exact/domain-aware recommendation，cleanup 接受 `16` 条新中文候选，阻断 `5` 条宽泛/生硬中文候选；`713` 条 validator-regenerated English short acronym queue 继续 blocked；
  - runtime 中文覆盖从 `17413 / 48932 = 35.59%` 增至 `17678 / 48932 = 36.13%`；
  - `zh:accept`: `17691`，`zh:blocked`: `9173`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay 未更新；
  - compact index SHA-256: `181207350c3668b34f04a3a596d242c7f08514d985be3ce8128d83b03b1f846d`；
  - compact manifest SHA-256: `62cbe54bf7e3b97c0c226bdfd0380fd22ea054555091f4279ba0338b7795ca9e`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `加性白噪声 -> concept:additive_white_noise`、`视听 -> concept:audio_visual`、`设备到设备通信 -> concept:device_to_device_communication`、`数据可视化与分析 -> concept:data_visualization_and_analytic`、`IP地址 -> concept:ip_address`、`QoS路由协议 -> concept:qos_routing_protocol`、`实数 -> concept:real_number`、`语义倾向 -> concept:semantic_orientation`、`机器翻译系统 -> concept:machine_translation__2`、`Web爬虫 -> concept:web_crawler` 可命中，`通信信道信息理论`、`音频视觉`、`器件到器件通信`、`嵌入式`、`人机器交互`、`逆方法`、`质量服务`、`机器转换系统`、`噪声降维` 保持不命中；
  - 相关测试：`859 passed in 6.59s`。
- batch-4000 后 review：
  - 本轮新增 `265` 个 runtime zh-covered concepts，覆盖率增至 `36.13%`；
  - 目标 `>40%` 仍需继续，下一段继续 exact/domain-aware curated glossary 与显式 review；
  - 不打开低质 mixed fallback、不 blanket accept medium-confidence compositional candidates、不自动 merge collision、不进入新的 L6。
- 最新 batch-2187 至 batch-3400 exact/domain-aware milestone 已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_2187_TO_3400_ALIASES`，覆盖 temporal/text/cryptographic/software-defined/spatio-temporal、access/cache/control/fault/formal/remote/security/software/speech/VLSI/WDM 等 exact/domain-aware 技术术语；
  - 新增 `2` 个分组/污染回归测试，先红灯后转绿；修正 `Temporal Database -> 时态数据库`、`Quality Of Service Routing -> 服务质量路由`、`Remote Authentication -> 远程认证`、`Electric Impedance Tomography -> 电阻抗断层成像`、`Remote Controllers -> 遥控器`、`Remote Monitoring System -> 远程监测系统`、`Solution Design -> 解决方案设计` 等坏词序/误译；
  - grouped L3-L5：fill `records_filled = 26529`，validate `review_decisions = 375856`；
  - preserve-except selection 恢复 `21646` 条 prior review 决策；显式接受 `1253` 条非碰撞 exact/domain-aware recommendation，并 cleanup 接受 `2` 条新 `needs_review`；
  - `839` 条 selected collision/duplicate 输出继续 blocked，不自动 merge；`软件定义无线电`、`二元决策图` 等 collision 输出未进入 runtime；
  - runtime 中文覆盖从 `16165 / 48914 = 33.05%` 增至 `17413 / 48932 = 35.59%`；
  - `zh:accept`: `17424`，`zh:blocked`: `9227`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `46485e2b61e0d35b00ed01a1b155d990b20f3c32e8da3c0f4137b9cdd3ee18ad`；
  - compact manifest SHA-256: `d3558009b7dd7063b4f5ea832f453c1ae33f9cdde6df8fa3fe54ee397e3850fa`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `时态数据库 -> concept:temporal_database`、`密码算法 -> concept:cryptographic_algorithm`、`时空数据库 -> concept:spatio_temporal_database`、`服务质量路由 -> concept:quality_of_service_routing`、`远程认证 -> concept:remote_authentication`、`电阻抗断层成像 -> concept:electric_impedance_tomography`、`H控制 -> concept:h_control`、`H∞控制 -> concept:h_infinity_control`、`硝酸还原酶(NADPH) -> concept:nitrate_reductase_nadph`、`硝酸还原酶(NAD(P)H) -> concept:nitrate_reductase_nad_p_h`、`遥控器 -> concept:remote_controller`、`远程监测与控制 -> concept:remote_monitoring_and_control`、`远程监测系统 -> concept:remote_monitoring_system`、`解决方案设计 -> concept:solution_design`、`云数据安全解决方案 -> concept:cloud_data_security_solution`、`硬件解决方案 -> concept:hardware_solution`、`导航方案 -> concept:navigation_solution`、`隐形眼镜护理液 -> concept:contact_lens_solution`、`声表面波滤波器 -> concept:acoustic_surface_wave_filter`、`文本分类 -> concept:text_categorization` 可命中，`服务路由的质量`、`遥感认证`、`遥感控制器`、`遥感监测与控制`、`遥感监测系统`、`溶液设计`、`云数据安全溶液`、`硬件溶液`、`导航溶液`、`接触晶状体溶液`、`软件图书馆`、`电动阻抗断层成像`、`I J条件`、`优化链路状态路由`、`光码分多址` 保持不命中；
  - 相关测试：`855 passed in 5.51s`。
- batch-3400 后 review：
  - 本 milestone 新增 `1248` 个 runtime zh-covered concepts，覆盖率超过 `35%` 目标；
  - accepted/runtime conflict 继续为 `0`，duplicate/collision 仍不自动 merge；
  - 不打开低质 mixed fallback、不 blanket accept medium-confidence compositional candidates、不进入新的 L6；
  - 若继续扩大覆盖，下一轮从 batch-3401 起，仍优先 exact/domain-aware glossary 与显式 review。
- 最新 batch-1481 至 batch-2186 exact/domain-aware milestone 已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_1481_TO_1700_ALIASES` 与 `ZH_EXACT_EXPANSION_BATCH_1701_TO_2186_ALIASES`，覆盖 adaptive/agent/agile、binary/blind/cache/channel、data/decision/digital/distributed/dynamic、finite/fuzzy/information/knowledge、routing/rule/SAR/satellite/security/semantic/semiconductor/service/signal/spectral/stochastic/system/switching/time/tracking 等 exact/domain-aware 术语；
  - 新增 `11` 个分组代表性回归测试；修复 `microphone signals -> 麦克风信号` UTF-8 破损，并移除 `agent-based framework` exact entry 以保留 mesh/biomedical pollution guard；
  - grouped L3-L5 完成：先接受 `915` 条非碰撞 exact/domain-aware reopen/prefix recommendation，清理 `59` 条 needs_review（接受 `35`、阻断 `24`），再接受 `478` 条 batch-1701-to-2186 exact glossary recommendation；`793 + 8` 条 collision 相关输出继续 blocked，不自动 merge；
  - runtime 中文覆盖从 `14750 / 48909 = 30.16%` 增至 `16165 / 48914 = 33.05%`；
  - `zh:accept`: `16176`，`zh:blocked`: `10406`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `f9190c2268fb710890a1796ef84ed9c7d28c869baec1f570994b6872947e45a0`；
  - compact manifest SHA-256: `aa5b58fe7e23b09e509008bdfaa2d9267a4d8e56ebaeb7630e490c1dc521b73e`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `规则库 -> concept:rule_base`、`安全需求工程 -> concept:security_requirement_engineering`、`半导体器件测量 -> concept:semiconductor_device_measurement`、`系统级仿真 -> concept:system_level_simulation`、`分时计算机系统 -> concept:time_sharing_computer_system`、`时频分析 -> concept:time_frequency_analysi`、`跟踪误差 -> concept:tracking_error`、`谱聚类 -> concept:spectral_clustering` 可命中，`规则碱基`、`自自适应`、`集合点跟踪`、`稀疏溶液`、`频谱图书馆` 保持不命中；
  - 相关测试：`851 passed in 6.03s`。
- batch-2186 后 review：
  - 本 milestone 新增 `1415` 个 runtime zh-covered concepts，覆盖率超过 `33%` 目标；
  - accepted/runtime conflict 继续为 `0`，duplicate/collision 仍不自动 merge；
  - 不打开低质 mixed fallback、不 blanket accept medium-confidence compositional candidates、不进入新的 L6；
  - 若继续扩大覆盖，下一轮从 batch-2187 起，仍优先 exact/domain-aware glossary 与显式 review。
- 最新 batch-1141 至 batch-1480 exact/domain-aware milestone 已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_1141_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_1340_ALIASES`，并新增 `ZH_EXACT_EXPANSION_BATCH_1341_TO_1440_ALIASES`、`ZH_EXACT_EXPANSION_BATCH_1441_TO_1480_ALIASES`，覆盖 physical/physiology/picture/plant/plasma、pneumatic/pneumonia/point/polio/poly、porphyria/portal/position/potassium/power、precision/pregnancy/prenatal/prescription/pressure/preventive 等 P 段 exact/domain-aware 术语；
  - 新增 `17` 个分组代表性回归测试；
  - grouped L3-L5 完成；最后一段 batch-1441-to-1480：fill `records_filled = 202`，validate `review_decisions = 375801`，preserve `22059` 条 prior review 决策；
  - batch-1441-to-1480 显式接受 `145` 条 exact/domain-aware recommendation，恢复 `6` 条 prior accepted valid alias，恢复 `713` 条 validator-regenerated English short acronym block；
  - batch-1441-to-1480 显式阻断 `10` 条 title/topic/compositional side-effect，包括 `掠夺性期刊主题`、`妊娠与子痫前期研究`、`产前筛查与诊断`、`压疮预防与管理`、`重量偏见`；
  - runtime 中文覆盖从 `13708 / 48904 = 28.03%` 增至 `14750 / 48909 = 30.16%`；
  - `zh:accept`: `14766`，`zh:blocked`: `11788`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `e4da85cac78a14442863bc9a8e08c7c33e12f5a9d713b35c59132586f5e64d52`；
  - compact manifest SHA-256: `20802d044cf623943ba664e5f95c53d25ea6969d62e0664cb459a43db2c5a96e`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `精密工程 -> concept:precision_engineering`、`孕前保健 -> concept:preconception_care`、`产前诊断 -> concept:prenatal_diagnosi`、`预防性维护 -> concept:preventive_maintenance`、`部分可观测马尔可夫决策过程 -> concept:partially_observable_markov_decision_process` 可命中，`掠夺性期刊主题`、`妊娠与子痫前期研究`、`产前筛查与诊断`、`压疮预防与管理`、`重量偏见`、`鲁棒模型预测控制` 保持不命中；
  - 相关测试：`840 passed in 8.56s`。
- batch-1480 后 review：
  - 本 milestone 新增 `1042` 个 runtime zh-covered concepts，覆盖率超过 `30%` 目标；
  - accepted/runtime conflict 继续为 `0`，duplicate/collision 仍不自动 merge；
  - 不打开低质 mixed fallback、不 blanket accept medium-confidence compositional candidates、不进入新的 L6。
- 最新 batch-1041 至 batch-1140 exact/domain-aware 五轮 milestone 已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_1041_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_1140_ALIASES`，覆盖 penile/pentose/peptide、perception/performance/peripheral/peritoneal/personal、Petri/phage/pharmaceutical/pharmacology、phase/phenyl/phosphate/photo/photovoltaic 等 P 段 exact/domain-aware 术语；
  - 新增 `5` 个分组代表性回归测试，先红灯后转绿；修正 `Phosphatidate Phosphatase -> 磷脂酸磷酸水解酶`，清除 `酸磷酸酶` 坏形态命中；
  - grouped L3-L5：fill `records_filled = 25360`，validate `review_decisions = 374673`；从 TempFiles checkpoint 恢复 prior review 决策，并恢复 `713` 条 validator-regenerated English short acronym queue；
  - 显式接受 `633` 条 exact/domain-aware recommendation，另重开 `11` 条 prior blocked exact 输出（包括 `性能评估`、`个人区域网络`、`光伏系统`）；
  - 显式阻断 `45` 条 compositional/domain-title side-effect；`药理学与纳米医学研究` 保持 blocked，`光子集成电路` 等 duplicate/collision 输出继续不自动 merge；
  - runtime 中文覆盖从 `13086 / 48902 = 26.76%` 增至 `13708 / 48904 = 28.03%`；
  - `zh:accept`: `13720`，`zh:blocked`: `11694`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `d821a62b7366ca1f33433c508ad216596b9aa861d1263b84542f51a095eb416d`；
  - compact manifest SHA-256: `5ab3c53060296a1d763c22b81c7d8d7910ff180884cb9eecff05de0203a49a36`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `磷酸戊糖途径 -> concept:pentose_phosphate_pathway`、`药物警戒 -> concept:pharmacovigilance`、`相变材料 -> concept:phase_change_material`、`光伏系统 -> concept:photovoltaic_system`、`磷脂酸磷酸水解酶 -> concept:phosphatidate_phosphatase` 可命中，`磷脂酸磷酸酶`、`药理学与纳米医学研究` 保持不命中；
  - 相关测试：`823 passed in 6.21s`。
- batch-1140 后 review：
  - 本 milestone 新增 `622` 个 runtime zh-covered concepts，覆盖率超过 `28%` 目标；
  - exact reopen audit 发现 `12` 条旧 pending-exact block，其中 `11` 条已按 exact/domain-aware 证据重开，`药理学与纳米医学研究` 因 title/domain 组合风险继续 blocked；
  - accepted/runtime conflict 继续为 `0`，duplicate/collision 仍不自动 merge；不打开低质 mixed fallback、不 blanket accept medium-confidence compositional candidates、不进入新的 L6。
- 最新 batch-941 至 batch-1040 exact/domain-aware 五轮 milestone 已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_941_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_1040_ALIASES`，覆盖 partial/particle、parvovirus/passive/password、patch/patella/pathology/patient、pattern/PAX/peak/Pearson、pediatric/peer/pelvic/penicillin 等 P 段 exact/domain-aware 术语；
  - 新增 `5` 个分组代表性回归测试，先红灯后转绿；修正 `Partial Differential Equations -> 偏微分方程`、`Patient Discharge -> 患者出院` 等 exact 输出；
  - grouped L3-L5：fill `records_filled = 24736`，validate `review_decisions = 374047`；从 TempFiles checkpoint 恢复 prior review 决策，补回 `246` 条 revalidation 后缺失的旧 zh 决策行，并恢复 `713` 条 validator-regenerated English short acronym queue；
  - 显式接受 `303` 条 exact/domain-aware recommendation，另通过 exact/domain-aware replacement 重开 `41` 条 prior blocked exact 输出；
  - 显式阻断 `3` 条 medium compositional side-effect（包括 `体图案化`、`动力学部分重构` 等），后续如需应通过更具体 exact/domain-specific replacement 重开；
  - runtime 中文覆盖从 `12755 / 48897 = 26.09%` 增至 `13086 / 48902 = 26.76%`；
  - `zh:accept`: `13158`，`zh:blocked`: `11870`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `7542a6473cbb50ee86d25df27f703a387fec3c8141f265b61cd114f9353e13fb`；
  - compact manifest SHA-256: `af3334e51ccac03a7177947e2d6a27828d1c8b512f42d311e53de0903cfa000a`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `偏微分方程 -> concept:partial_differential_equation`、`无源光网络 -> concept:passive_optical_network`、`患者出院 -> concept:patient_discharge`、`膜片钳技术 -> concept:patch_clamp_techniqu`、`青霉素G -> concept:penicillin_g` 可命中，`体图案化` 保持不命中；
  - 相关测试：`818 passed in 7.11s`。
- batch-1040 后 review：
  - 本 milestone 新增 `331` 个 runtime zh-covered concepts，覆盖率增至 `26.76%`；
  - 目标 `>28%` 仍需继续，下一轮从 batch-1041 起按同一 `5 x 20-batch` milestone 节奏推进；
  - accepted/runtime conflict 继续为 `0`，duplicate/collision 仍不自动 merge；不打开低质 mixed fallback、不 blanket accept medium-confidence compositional candidates、不进入新的 L6。
- 最新 batch-841 至 batch-940 exact/domain-aware 五轮 milestone 已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_841_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_940_ALIASES`，覆盖 oxygen/oxy/ozone、P2P/packet、pain/pairing/palatal/palliative/palm、pancreatic/papilloma/parallel/parameter/paraneoplastic/parasite/parathyroid/parental/parkinson 等 exact/domain-aware 术语；
  - 新增 `5` 个分组代表性回归测试，先红灯后转绿；修正 `Pancreas, Artificial -> 人工胰腺`、`Pain Threshold -> 痛阈` 等 exact 输出；
  - grouped L3-L5：fill `records_filled = 24450`，validate `review_decisions = 373762`；从 TempFiles checkpoint 恢复 prior review 决策并补回 `187` 条 revalidation 后缺失的旧决策行；
  - 显式接受 `295` 条 exact/domain-aware recommendation；
  - 显式阻断 `26` 条 medium compositional / low mixed fallback side-effect，包括 `自动并行化` 等，后续如需应通过更具体 exact/domain-specific replacement 重开；
  - runtime 中文覆盖从 `12468 / 48897 = 25.50%` 增至 `12755 / 48897 = 26.09%`；
  - `zh:accept`: `12814`，`zh:blocked`: `11871`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `3305e43ab3f1e5c88068a05952096de7b29408885e3c31291bfd8721fe01cef5`；
  - compact manifest SHA-256: `1d2d3240cf6ce24df7166322bddb65b93214b038d6e0cf8f5bd1a04a49d1b031`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `血氧饱和度 -> concept:oxygen_saturation`、`胰腺肿瘤 -> concept:pancreatic_neoplasm`、`副交感神经系统 -> concept:parasympathetic_nervou_system` 可命中，`自动并行化` 保持不命中；
  - 相关测试：`813 passed in 15.45s`。
- batch-940 后 review：
  - 本 milestone 新增 `287` 个 runtime zh-covered concepts，覆盖率增至 `26.09%`；
  - 目标 `>28%` 仍需继续，下一轮从 batch-941 起按同一 `5 x 20-batch` milestone 节奏推进；
  - accepted/runtime conflict 继续为 `0`，duplicate/collision 仍不自动 merge；不打开低质 mixed fallback、不 blanket accept medium-confidence compositional candidates、不进入新的 L6。
- 最新 batch-741 至 batch-840 exact/domain-aware 五轮 milestone 已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_741_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_840_ALIASES`，覆盖 open/open source/operating/ophthalmic、opioid/opportunistic/optic/optical、optimal/oral/orbital/organ、organic/orthopedic/osteoporosis/outage、ovarian/oxygen 等 exact/domain-aware 术语；
  - 新增 `5` 个分组代表性回归测试，先红灯后转绿；保留 `Optical Harmonic Generation -> 光学谐波产生` 既有标准译法；
  - grouped L3-L5：fill `records_filled = 24135`，validate `review_decisions = 373448`；从 TempFiles checkpoint 补回 `143` 条 prior zh review 决策，并恢复 `1` 条 prior runtime target（`concept:optical_tomography / 光学断层成像`），避免候选重排导致旧 runtime alias 回退；
  - 显式接受 `247` 条 exact/domain-aware recommendation；
  - 显式阻断 `29` 条 medium compositional / low mixed fallback side-effect，包括 `无源光网络`、`实时操作系统`、`骨科学设备`、`氧化磷酸化耦合因子` 等，后续如需应通过更具体 exact/domain-specific replacement 重开；
  - reblocked validator-regenerated English short acronym queue: `713`；
  - runtime 中文覆盖从 `12264 / 48897 = 25.08%` 增至 `12468 / 48897 = 25.50%`；
  - `zh:accept`: `12519`，`zh:blocked`: `11808`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `e7cc7ee89ded7eaa6fb1a5ce98ab05032608e750e6e0a2521891af7c50028f41`；
  - compact manifest SHA-256: `7627e9379a981e502ab41b2b0250eb18e13566a1c6327efe5a1f60c8c821b6c1`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `开放最短路径优先 -> concept:open_shortest_path_first` 可命中，`无源光网络`、`氧化磷酸化耦合因子` 保持不命中；
  - 相关测试：`808 passed in 8.27s`。
- batch-840 后 review：
  - 本 milestone 新增 `204` 个 runtime zh-covered concepts，覆盖率增至 `25.50%`；
  - side-effect `29` 条已显式 blocked，没有打开低质 mixed fallback，也没有 blanket accept medium-confidence compositional candidates；
  - accepted/runtime conflict 继续为 `0`，duplicate/collision 仍不自动 merge；
  - 若继续扩大覆盖，下一轮从 batch-841 起按同一 `5 x 20-batch` milestone 节奏推进，仍不进入新的 L6。
- 最新 batch-721 至 batch-740 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_721_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_740_ALIASES`，覆盖 oliguria/olive/olmesartan、OLSR/omni/on-chip、online/ontology、oncogene/oncology、oocyte/OOD、open/open loop/open RAN 等 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；修正 `Ontology Building -> 本体构建`、`Open Field Test -> 旷场实验` 等 exact 输出；
  - grouped L3-L5：fill `records_filled = 23883`，validate `review_decisions = 373197`；
  - 显式接受 `113` 条 exact/domain-aware recommendation；
  - 显式阻断 `5` 条由 open/onion/oncologist/oncostatin exact 组件引发的 compositional/title/word-order side-effect：`学术出版与开放获取`、`大蒜与洋葱研究`、`辐射肿瘤科医生`、`受体抑瘤素M`、`受体抑瘤素MII型`；
  - `本体构建` 等 duplicate/collision exact 输出继续保持 blocked，不自动 merge；
  - runtime 中文覆盖从 `12154 / 48897 = 24.86%` 增至 `12264 / 48897 = 25.08%`；
  - `zh:accept`: `12277`，`zh:blocked`: `11656`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `4dd94629e1dee0db345281e3a02e2df8c9157fa0a792ff2db8135e317c037a60`；
  - compact manifest SHA-256: `534bf36a0c4b77c8d70c7dfe9f4e3e6c5a15fe02cfcb228bf42c32f240ad9a33`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `开放式无线接入网 -> concept:open_ran` 可命中，`优化链路状态路由` 因 `concept:olsr` / `concept:optimized_link_state_routing` duplicate collision 保持不命中，`辐射肿瘤科医生` 保持不命中；
  - 相关测试：`803 passed in 5.20s`。
- batch-740 后 review：
  - 本轮新增 `110` 个 runtime zh-covered concepts，覆盖率增至 `25.08%`，已超过用户设定的 `>25%` 目标；
  - side-effect `5` 条已显式 blocked，后续如需 `放射肿瘤科医生`、`抑瘤素M受体` 等应通过更具体 exact/domain-specific replacement 重开；
  - post-25% review 初步结论：batch-701-to-740 近期 `247` accept / `10` blocked，compact index load 约 `158.51 ms`，text fallback smoke 约 `6.08 ms`；`开放式无线接入网` 可命中，`优化链路状态路由`、`光码分多址` 因 duplicate collision 保持不命中，`本体构建`、`辐射肿瘤科医生`、`受体抑瘤素M` 保持不命中；
  - treemap/text fallback 排序按“覆盖论文数 > concept specificity > frequency > 名称长度”，小样本中更宽泛的 `Access Network / 接入网` 可因跨论文支撑排在更具体单篇术语前；这是排序偏好，不是 alias 污染；
  - 建议先停止连续批处理并完成 post-25% 覆盖/质量复盘，再决定是否设置 `>30%` 等新目标；若继续扩展，仍按 exact/domain-aware 小批次推进，不打开低质 mixed fallback、不 blanket accept medium-confidence compositional candidates、不自动 merge collision、不进入新的 L6。
- 最新 batch-701 至 batch-720 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_701_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_720_ALIASES`，覆盖 occupational therapy practice、OCDMA、ocean/oceanographic、Ochrobactrum/Ocimum/OCR、octamer/octane/octanol、ocular/oculomotor、odonto/Odontogenic、OFDM/OFDMA、office/offshore/oil、OLAP/OLED、olfactory、oligodendrocyte/oligonucleotide 等 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；
  - grouped L3-L5：fill `records_filled = 23766`，validate `review_decisions = 373080`；
  - 显式接受 `135` 条 recommendation，其中 `MIMO-OFDMA -> 多输入多输出正交频分多址` 作为 exact-backed engineering variant 接受；
  - 显式阻断 `5` 条由 octanol/oils/odorant exact 组件引发的 compositional/word-order side-effect：`1辛醇类`、`燃料油类`、`工业油类`、`植物油类`、`受体气味物质`；
  - duplicate/collision exact 输出继续保持 blocked，不自动 merge；
  - runtime 中文覆盖从 `12021 / 48895 = 24.59%` 增至 `12154 / 48897 = 24.86%`；
  - `zh:accept`: `12167`，`zh:blocked`: `11649`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `b35ae86992dbc023fb07408a177d52b61544b765d1d8d64b887fcdcd74e147f5`；
  - compact manifest SHA-256: `e6317889a9461d8ce4dad580c5b32f4e4b044e677e5022ca276b9f3ec2766fa3`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke post-review 更正：`光码分多址` 因 `concept:ocdma` / `concept:optical_cdma` duplicate collision 保持不命中；
  - 相关测试：`783 passed in 4.95s`。
- batch-720 后 review：
  - 本轮新增 `133` 个 runtime zh-covered concepts，覆盖率增至 `24.86%`，仍未达到 `>25%`；
  - side-effect `5` 条已显式 blocked，后续如需 `燃料油`、`植物油`、`气味受体` 等应通过更具体 exact/domain-specific replacement 重开；
  - 下一轮应继续 batch-721 至 batch-740，优先从 oncology/online/open/operation/optical 等高确定性 exact 术语推进。
- 最新 batch-681 至 batch-700 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_681_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_700_ALIASES`，覆盖 NURBS、nurse/nursing、nutrition/nutritional、obesity/object/object-oriented、observation/obstacle/obstetric/occupational 等 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；修正 `护士新生儿 -> 新生儿护士`、`护理评估研究 -> 护理评价研究`、`面向目标* -> 面向对象*`、`产科学外科操作 -> 产科手术`、`职业损伤 -> 职业伤害` 等坏形态；
  - grouped L3-L5：fill `records_filled = 23606`，validate `review_decisions = 372920`；
  - 显式接受 `121` 条 exact/domain-aware recommendation；
  - 显式阻断 `21` 条由 observation/nutrition/nurse 等 exact 组件引发的 compositional/title side-effect；
  - `面向对象编程` 等 duplicate/collision exact 输出继续保持 blocked，不自动 merge；
  - runtime 中文覆盖从 `11914 / 48891 = 24.37%` 增至 `12021 / 48895 = 24.59%`；
  - `zh:accept`: `12034`，`zh:blocked`: `11622`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `222afd7a66965029dea3efc1dccadf58cd2de014d750a5983fc97212dae81b3e`；
  - compact manifest SHA-256: `f07f74335e5b6ec59787eea0c9895cbc04b2f60c8914dcbd56e4f6f7ce60e446`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `护理信息学`、`工作场所职业健康与安全` 可命中；`面向对象编程` 因 duplicate/collision 保持不命中；
  - 相关测试：`763 passed in 5.56s`。
- batch-700 后 review：
  - 本轮新增 `107` 个 runtime zh-covered concepts，覆盖率增至 `24.59%`，仍未达到 `>25%`；
  - side-effect `21` 条已显式 blocked，主要来自 observation/nutrition/nurse component 组合；
  - 下一轮应继续 batch-701 至 batch-720，优先从 occupational/ocean/ocular/OFDM/offline 等高确定性 exact 术语推进。
- 最新 batch-661 至 batch-680 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_661_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_680_ALIASES`，覆盖 normalized/Nor/North/Nose/NoSQL/Nuchal、nuclear/nucleic/nucleotide、number/numerical 等 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；其中修正 `Nuclear Family -> 核心家庭`、`Nuclear Structure And Function -> 核结构与功能`、`Number Of Hops -> 跳数`、`Numerical Control Systems -> 数控系统` 等坏形态或词序；
  - grouped L3-L5：fill `records_filled = 23496`，validate `review_decisions = 372811`；
  - 显式接受 `132` 条 exact/domain-aware recommendation；
  - 显式阻断 `5` 条由 exact 组件引发的 side-effect：`5核苷酸酶`、`核物理学与应用`、`核物理学研究`、`核苷Q`、`RNA核苷酸转移酶`；
  - duplicate/collision exact 输出继续不自动 merge；
  - runtime 中文覆盖从 `11783 / 48890 = 24.10%` 增至 `11914 / 48891 = 24.37%`；
  - `zh:accept`: `11927`，`zh:blocked`: `11620`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `fca124bef5c5d4d455e865ca9df8358bf79d9d61cd176e723ce70c28858b55ab`；
  - compact manifest SHA-256: `7875059787235bc7ee6f6723e4717cd51839a1dda41b5232125cb20a94596c80`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `核受体与信号传导` 可命中；
  - 相关测试：`743 passed in 5.32s`。
- batch-680 后 review：
  - 本轮新增 `131` 个 runtime zh-covered concepts，覆盖率增至 `24.37%`，仍未达到 `>25%`；
  - side-effect `5` 条已显式 blocked，其中 `核物理学与应用`、`核物理学研究`、`核苷Q` 后续可通过独立 exact/domain-specific review 重开；
  - 下一轮应继续 batch-681 至 batch-700，优先从 NURBS/Nursing/Nutrition/Obesity/Object 等高确定性 exact 术语推进。
- post-20% 复盘要点：
  - 质量审计 artifact:
    `F:\AI playground\TempFiles\theme_alias_post20_quality_review.json`；
  - theme smoke artifact:
    `F:\AI playground\TempFiles\theme_alias_post20_theme_smoke_refined.json`；
  - batch-361 至 batch-380 recommendation 复查：`348` accept，`23` blocked；heuristic suspect accepted `19` 条，多数为 `MATLAB`/`MEMS`/Meigs/Meige 等合法中英混排或 title-shaped exact concept，未发现需要立即回滚的 runtime pollution；
  - blocked exact-like 复查命中 `17` 条，包括 `循证医学`、`农业机械化`、`模糊隶属函数`、`传染病医学`、`等离子体材料加工`、`受体黑皮质素*`、`受体褪黑素*` 等；这些不应 blanket accept，后续应通过独立 exact/domain-specific review 或 canonical merge 决策打开；
  - alias conflict raw groups: `en = 3500`，`zh = 1731`，但 runtime accepted conflicts 仍为 `0`；
  - query smoke：预期 runtime alias `12 / 12` 命中；预期 blocked alias `0 / 7` 误命中；
  - treemap/text fallback smoke：`build_text_themes` 可产生 `Mean Absolute Error / 平均绝对误差`、`Medication Adherence / 用药依从性`、`Median Filter / 中值滤波器` 等 concept-level themes；
  - 窄 L6 修复已完成：中文 text candidate extractor 现在会先扫描 compact runtime 中已接受的中文 alias 短语，再走原 n-gram fallback，并过滤被已选 concept alias 覆盖的短片段；`主从系统` 已稳定归并到 `concept:master_slave_system`，不再显示 `主从系`。
- 最新 batch-641 至 batch-660 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_641_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_660_ALIASES`，覆盖 NoC/Nocardia/nociception/nocturnal/NOD/node/Nogo/noise、non-/nonlinear/noninvasive/nonvolatile、Norway/Norwalk/Nose/Notch 等 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；其中 `Non-functional Requirements -> 非功能性需求` 修正旧的坏输出 `非泛函需求`，`NoC Architectures -> NoC架构` 避免撞上既有 `片上网络架构`；
  - grouped L3-L5：fill `records_filled = 23370`，validate `review_decisions = 372685`；
  - 显式接受 `147` 条 exact/domain-aware recommendation；
  - 显式阻断 `1` 条 `nomenclature` 组件引发的 title/topic side-effect：`命名法主题`；
  - `去噪`、`命名法`、`噪声整形`、`非同质化代币`、`非参数统计`、`非政府组织`、`非易失性*`、`陷波滤波器` 等 exact-backed duplicate/collision 输出保持 blocked，不自动 merge；
  - runtime 中文覆盖从 `11637 / 48890 = 23.80%` 增至 `11783 / 48890 = 24.10%`；
  - `zh:accept`: `11796`，`zh:blocked`: `11625`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `9f4c87ec3c27b6f495f62e3104249383ed1ab04db27f7bff22cc241500a463e5`；
  - compact manifest SHA-256: `a4b52e555b401fff1e9abd403fa3c2a808bfc8918d8973aeea1529a21222cc10`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `NoC架构`、`非功能性需求` 可命中；`命名法主题` 保持不命中；
  - 相关测试：`723 passed in 3.85s`。
- batch-660 后 review：
  - 本轮新增 `146` 个 runtime zh-covered concepts，覆盖率增至 `24.10%`，仍未达到 `>25%`；
  - side-effect 控制在 `1` 条，主要收益来自 non-/nonlinear 与生医 exact 密集区；
  - duplicate/collision exact 输出继续不自动 merge；
  - 下一轮应继续 batch-661 至 batch-680，优先从 Nor/North/Nose/Notch/Nuclear/Nucleic/Nucleotide 等高确定性 exact 术语推进。
- 最新 batch-621 至 batch-640 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_621_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_640_ALIASES`，覆盖 nicotinamide/nicotine、Nidovirales/Niemann-Pick/Nigella/night、NIMA/Nimaviridae、niobium/Nipah/nipple/Nissl、nitrate/nitric/nitrite/nitro/nitrogen、NK/NLR/NMR/no-reflow 等 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；其中 `NIMA相关激酶1`、`NIH 3T3细胞` 通过 exact 证据重开旧 non-collision block；
  - grouped L3-L5：fill `records_filled = 23206`，validate `review_decisions = 372521`；
  - 显式接受 `142` 条 exact/domain-aware recommendation，并接受 `电子尼古丁递送系统` 这条 high-confidence exact-backed 派生；
  - 重开 `2` 条旧 non-collision exact block：`NIH 3T3细胞`、`NIMA相关激酶1`；
  - 显式阻断 `5` 条 bad-shape/title side-effect：`4硝基喹啉类1氧化物`、`碳氮元素连接酶类`、`碳氮元素裂解酶`、`钠亚硝酸盐`、`土壤碳与氮元素动力学`；
  - `夜视`、`铌元素`、`铌锡`、`氮元素`、`氮化合物` 等 exact-backed duplicate/collision 输出保持 blocked，不自动 merge；
  - runtime 中文覆盖从 `11494 / 48889 = 23.51%` 增至 `11637 / 48890 = 23.80%`；
  - `zh:accept`: `11650`，`zh:blocked`: `11607`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `fb8b9781d0358960ae777fae5ea0e50fb09b23e2b5bba8c82367248f692f4e7f`；
  - compact manifest SHA-256: `8b15a95945c9edcf467312e0a2a487737c44ef6d93783cb3e76cbadb031ff76b`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `尼古丁替代疗法`、`NIMA相关激酶1`、`电子尼古丁递送系统` 可命中；`钠亚硝酸盐`、`夜视`、`铌元素` 保持不命中；
  - 相关测试：`703 passed in 3.89s`。
- batch-640 后 review：
  - 本轮新增 `143` 个 runtime zh-covered concepts，覆盖率增至 `23.80%`，仍未达到 `>25%`；
  - side-effect 控制在 `5` 条，主要是 nitro/nitrogen 组件引发的坏词序和 title/domain 组合；
  - duplicate/collision exact 输出继续不自动 merge；
  - 下一轮应继续 batch-641 至 batch-660，优先从 no/NOX/Nocardia/noise/non-/normal/norovirus 等高确定性 exact 术语推进。
- 最新 batch-601 至 batch-620 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_601_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_620_ALIASES`，覆盖 neuronal/neuron、neuropathology/neuropeptide/neurophysiology、neuroprostheses/neuroprotection/neuropsychology、neuroscience/neurospora/neurosurgery/neurotransmitter，以及 neutral/neutrino/neutron/neutrophil、Nevus/New 地名、Newtonian/next-generation/NF/niacin/nickel 等 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；其中 `Receptors, Neurotensin -> 神经降压素受体` 修正 exact component 引发的 MeSH 词序问题；
  - grouped L3-L5：fill `records_filled = 23052`，validate `review_decisions = 372370`；
  - 显式接受 `130` 条 exact/domain-aware recommendation，包括 `广播新闻`、`快速中子`、`非牛顿流体`、`非牛顿液体`、`神经降压素受体` 等 high-confidence exact-backed 派生；
  - validator 重现的 `713` 条英文 acronym needs_review 按既有策略 blocked；
  - `镍元素` exact-backed 输出因 duplicate/collision 保持 blocked，不自动 merge；单字 `痣`、`镍` 和纯符号 `NF-κB` 不作为 runtime zh alias；
  - runtime 中文覆盖从 `11369 / 48888 = 23.26%` 增至 `11494 / 48889 = 23.51%`；
  - `zh:accept`: `11507`，`zh:blocked`: `11599`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `a4d6593d01cdfcfbc9fc001c3bae62a50acf26168d53fdfb3d6e39132b331820`；
  - compact manifest SHA-256: `79d7e922179d5bf346cdd12696071dff32923dc02e6c3cce898640953e77115a`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `神经降压素受体`、`非牛顿流体`、`广播新闻`、`神经元突起生长`、`NF-κB信号通路` 可命中；`受体神经降压素`、`痣`、`镍`、`NF-κB`、`SDMH` 保持不命中；
  - 相关测试：`683 passed in 4.46s`。
- batch-620 后 review：
  - 本轮新增 `125` 个 runtime zh-covered concepts，覆盖率增至 `23.51%`，仍未达到 `>25%`；
  - 新增 `nickel` 双来源翻译被 collision guard 阻断，继续不自动 merge；
  - 下一轮应继续 batch-621 至 batch-640，优先从 nicotinamide/nicotine/Nidovirales/Niemann-Pick/Nigella/night/niobium/nitrate/nitric/nitrogen 等高确定性 exact 术语推进。
- 最新 batch-581 至 batch-600 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_581_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_600_ALIASES`，覆盖 network pharmacology/protocol/routing/security/topology/traffic/networked，以及 neural/neuroblastoma/neurodevelopment/neuroendocrine/neurofibromatosis/neurology 等 N 段 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；其中 `Network Phase Transitions -> 网络相变`、`Neural Cell Adhesion Molecule L1 -> L1神经细胞黏附分子` 等 exact 词条覆盖较泛的 compositional 输出；
  - grouped L3-L5：fill `records_filled = 22917`，validate `review_decisions = 372241`；
  - 显式接受 `94` 条 exact/domain-aware recommendation，并重开 `13` 条旧 non-collision exact block（如 `神经机器翻译`、`神经网络硬件`、`神经通路`、`神经康复`）；
  - 显式阻断 `4` 条 compositional/title side-effect；`网络系统`、`神经与行为心理学研究` 两条旧宽泛/title-shaped block 继续保留；
  - `网络服务器`、`神经网络压缩`、`神经网络` 等 exact-backed duplicate/collision 输出继续保持 blocked，不自动 merge；
  - validator 重现的 `713` 条英文 acronym needs_review 按既有策略 blocked；
  - runtime 中文覆盖从 `11266 / 48888 = 23.04%` 增至 `11369 / 48888 = 23.26%`；
  - `zh:accept`: `11382`，`zh:blocked`: `11595`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `1369adcc990e611df1f98537fa1c747751df3b6140cd188a0289135ed1a40730`；
  - compact manifest SHA-256: `532113ca8d591b5c0d09d34c771c868bdefa86526da897eb2109a06c8b9c1ed2`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `网络药理学`、`神经机器翻译`、`神经风格迁移`、`神经母细胞瘤`、`神经系统检查` 可命中；`网络系统`、`神经与行为心理学研究`、`电动网络综合`、`遗传神经退行性疾病` 保持不命中；
  - 相关测试：`663 passed in 3.41s`。
- batch-600 后 review：
  - 本轮新增 `103` 个 runtime zh-covered concepts，覆盖率增至 `23.26%`，仍未达到 `>25%`；
  - neural/network 段 duplicate/collision 与旧 block 较多，后续仍需坚持 exact evidence reopen、collision stays blocked；
  - 下一轮应继续 batch-601 至 batch-620，优先从 neuromodulation/neuromorphic/neuromuscular/neuron/neuropeptide 等高确定性 exact 术语推进。
- 最新 batch-561 至 batch-580 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_561_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_580_ALIASES`，覆盖 neoplasm 后续分类、neoplastic/neovascularization、nephritis/nephrology/nephrotic、nerve/nervous system、netrin/network 等 N 段 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；其中 `Network Codes -> 网络码`、`Network Formation & Growth -> 网络形成与增长` 用 exact 词条覆盖较泛的 compositional 输出；
  - grouped L3-L5：fill `records_filled = 22814`，validate `review_decisions = 372138`；
  - 显式接受 `106` 条 exact/domain-aware recommendation；
  - 显式阻断 `2` 条由 `network analyzer` 组件引发的 compositional side-effect（`电动网络分析仪`、`向量网络分析仪`）；
  - validator 重现的 `713` 条英文 acronym needs_review 按既有策略 blocked；
  - runtime 中文覆盖从 `11163 / 48887 = 22.83%` 增至 `11266 / 48888 = 23.04%`；
  - `zh:accept`: `11279`，`zh:blocked`: `11593`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `8f4cbd5e2831a257df9c20be8caebe5453648b48c2a42fe9de970d082a21ad03`；
  - compact manifest SHA-256: `29e6ac81c303f93a1b4d8ccdc28e4c827c51d8172efde7abbf8c213daaeeb5de`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `肿瘤分期`、`肾病综合征`、`神经传导检查`、`网络入侵检测` 可命中；`电动网络分析仪`、`向量网络分析仪` 保持不命中；
  - 相关测试：`643 passed in 3.56s`。
- batch-580 后 review：
  - 本轮新增 `103` 个 runtime zh-covered concepts，覆盖率增至 `23.04%`，仍未达到 `>25%`；
  - network 段开始出现更多 duplicate/collision 风险，本轮只接受 exact/domain-aware 且无 accepted conflict 的候选；
  - 下一轮应继续 batch-581 至 batch-600，优先从 network 后续、networked、neural 等高确定性 exact 术语推进。
- 最新 batch-481 至 batch-500 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_481_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_500_ALIASES`，覆盖 multimorbidity/multiomics/multipath、multiple access/endocrine/sclerosis/system、multiplexing/multiprocessor/multiresolution/multitask/multiuser、muscarinic/muscle/muscular dystrophy/musculoskeletal/music 等 M 段 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；其中 `Multiple Kernels` 沿用既有 domain-sensitive 约定输出 `多核`，`Multiple Input Multiple Output (mimo) Radars` 沿用 `多输入多输出雷达`，`Muscular Dystrophy/Dystrophies` 因 label-only exact 归一化保持同一中文 alias `肌营养不良`；
  - grouped L3-L5：fill `records_filled = 22198`，validate `review_decisions = 371524`；
  - 显式接受 `129` 条 exact/domain-aware recommendation；
  - 显式阻断 `13` 条由 `multiplier`/`multiplication`/`muscular atrophy` 等 exact 词条引发的 compositional side-effect；
  - validator 重现的 `713` 条英文 acronym needs_review 按既有策略 blocked；
  - `多输入多输出雷达`、`多核` 等 exact-backed 输出因 duplicate/collision 保持 blocked，不自动 merge；
  - runtime 中文覆盖从 `10616 / 48878 = 21.72%` 增至 `10736 / 48879 = 21.96%`；
  - `zh:accept`: `10750`，`zh:blocked`: `11508`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `659197f4b22350ea0b72eea74d7f3f21fb88af938092311517b7445145a20e40`；
  - compact manifest SHA-256: `072818daffe999a80cb7f4c04c192d60198059d8f755370bacaf932a74805799`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `多病共存`、`多目标组合优化`、`多重聚合酶链反应` 可命中；`模拟乘法器`、`脊髓肌萎缩3型` 保持不命中；
  - 相关测试：`563 passed in 3.22s`。
- batch-500 后 review：
  - 本轮新增 `120` 个 runtime zh-covered concepts，覆盖率增至 `21.96%`，仍未达到 `>25%`；
  - `Multiple Kernels`、`MIMO Radar` 等新 exact 词条触发旧 domain-sensitive 约定，已改为服从既有术语，不用英文缩写或更具体 alias 覆盖旧行为；
  - 下一轮应继续 batch-501 至 batch-520，优先从 music/mutation/mycobacterium/myocardial/nanoparticle/neural 等 high-confidence exact 术语推进。
- 最新 batch-541 至 batch-560 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_541_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_560_ALIASES`，覆盖 nasal/nasopharyngeal、natural language/natural science、Nav voltage-gated sodium channels、near-field/near-infrared、neck/necroptosis、Neisseria、neodymium/neonatal/neoplasm 等 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；其中将 `Nd: Yag` 输出为 `掺钕钇铝石榴石`，避免纯英文 zh alias；`Neodymium/Neon/Needles` 使用 `钕元素`、`氖元素`、`针具` 避免单字 alias 被形态过滤；
  - grouped L3-L5：fill `records_filled = 22717`，validate `review_decisions = 372042`；
  - 显式接受 `155` 条 exact/domain-aware recommendation；
  - `颈损伤`、`颈肌肉`、`颈疼痛` 三条旧坏形态 accepted 被 exact replacement 替换为 `颈部损伤`、`颈肌`、`颈痛`；
  - validator 重现的 `713` 条英文 acronym needs_review 按既有策略 blocked；
  - runtime 中文覆盖从 `11011 / 48882 = 22.53%` 增至 `11163 / 48887 = 22.83%`；
  - `zh:accept`: `11177`，`zh:blocked`: `11599`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `b864cb7c3723397a8f3eed216481ef7b1ef0402ef326ee82ea91270a0ebeab44`；
  - compact manifest SHA-256: `67cd166bf67f3e393ae242cef4547357d89cdda38a6182082d3634cb56587e62`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `鼻咽癌`、`颈部损伤` 可命中；`颈损伤`、`SDMH` 保持不命中；
  - 相关测试：`623 passed in 3.54s`。
- batch-560 后 review：
  - 本轮新增 `152` 个 runtime zh-covered concepts，覆盖率增至 `22.83%`，仍未达到 `>25%`；
  - 本轮净增低于 accepted 数，是因为 3 条旧坏形态 accepted 被更准确 exact replacement 替换；
  - 下一轮应继续 batch-561 至 batch-580，优先从 neoplasm 后续、nerve/nephrology/network/neural 等高确定性 exact 术语推进。
- 最新 batch-521 至 batch-540 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_521_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_540_ALIASES`，覆盖 myosin/myositis/myotonia/myxoma、N-acetyl/N-terminal/NAD/NADPH、Naegleria/nail/Naive Bayes/Nakagami/Naloxone、named entity/NAND/nano、naphthalene/narcissism/narcolepsy/nasal 等 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；其中 `Nanometers -> 纳米` 仅生成候选但因 standalone generic unit 过宽保持 blocked，`肌球蛋白重链`、`朴素贝叶斯` 由旧 non-collision blocked 决策显式重开；
  - grouped L3-L5：fill `records_filled = 22562`，validate `review_decisions = 371888`；
  - 显式接受 `126` 条 exact/domain-aware recommendation，另重开 `2` 条旧 non-collision exact block；
  - 显式阻断 `19` 条中文候选，包括 `17` 条 medium compositional side-effect、`1` 条 low mixed fallback 和 `纳米` standalone generic unit；
  - validator 重现的 `713` 条英文 acronym needs_review 按既有策略 blocked；
  - `NAND闪存`、`纳米技术`、`纳米颗粒`、`纳米线`、`纳米生物技术` 等 exact-backed 输出因 duplicate/collision 保持 blocked，不自动 merge；
  - runtime 中文覆盖从 `10883 / 48879 = 22.27%` 增至 `11011 / 48882 = 22.53%`；
  - `zh:accept`: `11025`，`zh:blocked`: `11597`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `50becfae2c275d1cf8e4447000655e44926ef56add2e8308e52cad89b37505f9`；
  - compact manifest SHA-256: `712d8714da94ae690bbe95a3c7cacd42d069c0d121461ceb356d4b76bda44e17`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `肌球蛋白重链`、`朴素贝叶斯` 可命中；`纳米`、`纳米技术`、`SDMH` 保持不命中；
  - 相关测试：`603 passed in 3.85s`。
- batch-540 后 review：
  - 本轮新增 `128` 个 runtime zh-covered concepts，覆盖率增至 `22.53%`，仍未达到 `>25%`；
  - nano 段 exact 词条碰撞密集，继续不自动 merge；泛词 `纳米` 已阻断，避免 runtime 中文匹配污染；
  - 下一轮应继续 batch-541 至 batch-560，优先从 nasal/nasopharyngeal/natural language/neural/network 等高确定性 exact 术语推进。
- 最新 batch-501 至 batch-520 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_501_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_520_ALIASES`，覆盖 music/mutagenesis/mutation、mutual information/authentication、mycobacterium/mycoplasma、myelin/myeloid/myocardial/myofascial/myoglobin 等 M 段 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；其中 `Mutation Operator` 从旧组合输出 `突变算子` 修正为领域内更常用的 `变异算子`；
  - grouped L3-L5：fill `records_filled = 22356`，validate `review_decisions = 371682`；
  - 显式接受 `147` 条 exact/domain-aware recommendation；
  - 显式阻断 `6` 条由 myalgia/myoclonus/mycology/music therapy/mycotoxin/myoma 等 exact 词条引发的 compositional/title side-effect；
  - validator 重现的 `713` 条英文 acronym needs_review 按既有策略 blocked；
  - runtime 中文覆盖从 `10736 / 48879 = 21.96%` 增至 `10883 / 48879 = 22.27%`；
  - `zh:accept`: `10897`，`zh:blocked`: `11519`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `9f7e70a2b27184a8ce8e100314c68db07362d5639cc19c9061b597313546afb9`；
  - compact manifest SHA-256: `4e2b1cfda3587f5509390127be5c3c9a4c1498accc96aafb271c8c7dcd4183bb`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `音乐播放器`、`分枝杆菌属`、`肌红蛋白` 可命中；`音乐疗法与健康`、`农业中的霉菌毒素与食品` 保持不命中；
  - 相关测试：`583 passed in 3.11s`。
- batch-520 后 review：
  - 本轮新增 `147` 个 runtime zh-covered concepts，覆盖率增至 `22.27%`，仍未达到 `>25%`；
  - Mycobacterium/Mycoplasma 密集区收益较好，side-effect 仅 `6` 条；后续可继续在 myosin/myotonia/myxoma/N 段 exact 术语推进；
  - 下一轮应继续 batch-521 至 batch-540，优先从 myosin/myositis/myotonia/myxoma/N-acetyl/NAD/nanoparticle 等 high-confidence exact 术语推进。
- 最新 batch-461 至 batch-480 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_461_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_480_ALIASES`，覆盖 multi-label/multimodal/multi-objective/multipath/multirobot/multisensor/multicast/multimedia/multimodal 等 M 段 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；修正 `Multi-objective Differential Evolutions -> 多目标差分进化`、`Multi-objective Programming -> 多目标规划`、`Multi-signature -> 多重签名`、`Multi-spectral Imaging -> 多光谱成像` 等旧 compositional 词序/术语；
  - grouped L3-L5：fill `records_filled = 22050`，validate `review_decisions = 371374`；
  - 显式接受 `81` 条新 exact/domain-aware recommendation；
  - 显式重开 `58` 条已有 exact glossary 证据的旧 bounded-review blocked 决策；collision blocked 决策未重开；
  - validator 重现的 `713` 条英文 acronym needs_review 按既有策略 blocked；
  - `多目标跟踪`、`多媒体通信`、`多媒体`、`多层感知机`、`多模光纤` 等 exact-backed 输出因 duplicate/collision 保持 blocked，不自动 merge；
  - runtime 中文覆盖从 `10478 / 48878 = 21.44%` 增至 `10616 / 48878 = 21.72%`；
  - `zh:accept`: `10630`，`zh:blocked`: `11478`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `cae070839941f39e32669c3d3985f30f23119fbd4e34c474a2e1239a9c1ade12`；
  - compact manifest SHA-256: `9541db7aa8204c4d09a7cca40d1e00d25d3ff38e2059aeb9bf97db2074589f5b`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `多标签分类`、`多目标优化`、`多方计算`、`多传感器数据融合`、`组播路由`、`多用户MIMO系统`、`多媒体信号处理`、`多媒体技术`、`多目标算法`、`多路径路由`、`组播VPN`、`多模态图像配准` 可命中；`多目标跟踪`、`多媒体通信`、`多媒体`、`多层感知机`、`多模光纤` 保持不命中；
  - 相关测试：`543 passed in 3.69s`。
- batch-480 后 review：
  - 本轮新增 `138` 个 runtime zh-covered concepts，覆盖率增至 `21.72%`，仍未达到 `>25%`；
  - 旧 bounded-review block 会压住新 exact glossary，本轮已只对非 collision exact 项显式重开；后续批次如遇同类旧 block，应继续按“exact evidence reopen, collision stays blocked”处理；
  - 下一轮应继续 batch-481 至 batch-500，优先从 multimorbidity/multipath/multiple/multiplexing/multispectral/multitask/multiuser 等 high-confidence exact 术语推进。
- 最新 batch-441 至 batch-460 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_441_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_460_ALIASES`，覆盖 mobile 后续、mobility、model/model-checking/model-driven、modular/modulation、molecular、monitoring/morphine/morphology、moving target、multi-agent/multi-core/multi-criteria 等 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；修正 `Mobile Telecommunication Systems -> 移动通信系统`、`Model Checking -> 模型检测`、`Model View Controller -> 模型-视图-控制器`、`Multi Core -> 多核` 等旧 compositional 词序/格式；
  - grouped L3-L5：fill `records_filled = 21966`，validate `review_decisions = 371289`；
  - 显式接受 `98` 条 exact/domain-aware 或逐条确认的 exact-backed recommendation；
  - 显式阻断 `1` 条 non-exact side-effect（`Detection Of Moving Object -> 运动物体的检测`），另将 validator 重现的 `713` 条英文 acronym needs_review 按既有策略 blocked；
  - `移动通信系统`、`出行即服务`、`模型检测` 等 exact-backed 输出因 duplicate/collision 保持 blocked，不自动 merge；
  - runtime 中文覆盖从 `10384 / 48878 = 21.24%` 增至 `10478 / 48878 = 21.44%`；
  - `zh:accept`: `10492`，`zh:blocked`: `11531`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `1515fa862d771762beb2938051ab28a474cf635f015ee73d6b26b5b2dc08b84d`；
  - compact manifest SHA-256: `4185d28ebd84fca68099f3b3ab9d17ff0fd8e0c5e9673ee1f7d24b0ead29e1b0`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `移动WiMAX`、`移动Web`、`活动受限`、`移动模式`、`动物模型`、`模型检测算法`、`模型-视图-控制器`、`分子伴侣`、`分子靶向治疗`、`动态监测`、`吗啡`、`移动目标检测`、`多接入边缘计算`、`多核处理器`、`多准则决策分析` 可命中；`运动物体的检测`、`移动通信系统`、`出行即服务`、`模型检测` 保持不命中；
  - 相关测试：`523 passed in 4.57s`。
- batch-460 后 review：
  - 本轮新增 `94` 个 runtime zh-covered concepts，覆盖率增至 `21.44%`，仍未达到 `>25%`；
  - collision/duplicate 输出继续不自动 merge，尤其是 `移动通信系统`、`出行即服务`、`模型检测`；
  - 下一轮应继续 batch-461 至 batch-480，优先从 multi-objective/multipath/multiple/multiplexing/multispectral/multitask 等 high-confidence exact 术语推进。
- 最新 batch-421 至 batch-440 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_421_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_440_ALIASES`，覆盖 milk/millimeter/mindfulness/mineral/mining/minor/mirror/MIS/mitochondrial/MAPK/mixed/mobile 等 M 段 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；修正 `Mobile Application Development -> 移动应用开发`、`Mobile Interaction -> 移动交互` 等旧 compositional 词序；
  - grouped L3-L5：fill `records_filled = 21890`，validate `review_decisions = 371213`；
  - 显式接受 `111` 条 exact/domain-aware recommendation；
  - 显式阻断 `13` 条 non-exact side-effect，其中包括 `2` 条 low mixed fallback；未打开 mixed fallback；
  - `混合现实` 等 exact-backed 输出因 duplicate/collision 或既有阻断策略保持 blocked，不自动 merge；
  - runtime 中文覆盖从 `10275 / 48877 = 21.02%` 增至 `10384 / 48878 = 21.24%`；
  - `zh:accept`: `10398`，`zh:blocked`: `11549`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `e2ce594ce2889b2863d09bab157da944f2d1d3b6bc00b4a42ea41b5725b9b276`；
  - compact manifest SHA-256: `6483f32d9c201b60b4c25baea08d8506021d19679fbc8e041e94ef710454263d`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `人乳`、`正念`、`矿物油`、`微创外科手术`、`最小生成树`、`软件仓库挖掘`、`镜像神经元`、`米索前列醇`、`线粒体动力学`、`混合信号`、`移动应用开发`、`手机用户` 可命中；`混合现实`、`贝叶斯方法与混合模型`、`基于未成年人的知情同意`、`P38丝裂原活化蛋白激酶`、`受体盐皮质激素`、`唾液腺未成年人` 保持不命中；
  - review audit artifact: `F:\AI playground\TempFiles\theme_alias_batch_421_to_440_review_audit.json`；
  - 相关测试：`503 passed in 3.55s`。
- batch-440 后 review：
  - 本轮新增 `109` 个 runtime zh-covered concepts，覆盖率增至 `21.24%`，仍明显低于达到 `>25%` 所需增量；
  - non-exact side-effect `13` 条已全部显式 blocked；其中 low mixed fallback `基于未成年人的知情同意`、`P38丝裂原活化蛋白激酶` 未被打开；
  - 下一轮应继续 batch-441 至 batch-460，优先从 mobility/model/modulation/molecular/monitoring/morbidity/mouse 等 high-confidence exact 术语推进。
- 最新 batch-401 至 batch-420 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_401_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_420_ALIASES`，覆盖 mic/micro/microwave/middle/military/milk/millimeter/MIMO 等 M 段 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；将 Microsoft 条目改为 `微软SQL服务器`、`微软视窗`，避免 English-heavy zh alias；
  - grouped L3-L5：fill `records_filled = 21756`，validate `review_decisions = 371079`；
  - 显式接受 `106` 条 exact/domain-aware recommendation；
  - 显式阻断 `23` 条由 exact 词条引发的 compositional/domain-title side-effect；
  - `微机电系统`、`微流控`、`军事医学` 等 exact-backed 输出因 duplicate/collision 或既有阻断策略保持 blocked，不自动 merge；
  - runtime 中文覆盖从 `10169 / 48877 = 20.81%` 增至 `10275 / 48877 = 21.02%`；
  - `zh:accept`: `10289`，`zh:blocked`: `11523`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `2b63a5d094a5ee7ee416f4fe5d5c8e1d04ed4dba4bef20867f660f325a5eaab6`；
  - compact manifest SHA-256: `fcd7654f8b774d7cc3650aae875922c999147d2c77f0a1d64b1654d54828e1c0`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `米卡芬净`、`微纳机器人`、`微小RNA`、`微波消融`、`中东呼吸综合征冠状病毒`、`中间件`、`MIMO系统` 可命中；`微机电系统`、`微流控`、`军事医学`、`微流控设备`、`乳汁人类`、`先进MIMO系统优化` 保持不命中；
  - review audit artifact: `F:\AI playground\TempFiles\theme_alias_batch_401_to_420_review_audit.json`；
  - 相关测试：`483 passed in 3.37s`。
- batch-420 后 review：
  - 本轮新增 `106` 个 runtime zh-covered concepts，覆盖率增量较 batch-381-to-400 明显下降，主要因为 micro/military 等段落 duplicate/collision 和 side-effect 较多；
  - medium compositional side-effect `23` 条已全部显式 blocked；其中若后续需要 `微流控设备`、`无线麦克风`、`多用户MIMO系统` 等，应通过独立 exact/domain-specific replacement 打开；
  - runtime 覆盖仍未达 `>25%`，下一轮应继续 batch-421 至 batch-440，优先从 migration/mild/mineral/miRNA/mirror/missing/mixed/mobile 等高确定性 exact 术语推进。
- 最新 batch-381 至 batch-400 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_381_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_400_ALIASES`，覆盖 Men/Meningeal/Menstrual/Mental、Mercury/Mesenchymal/Mesh/Message、Meta/Metabolic/Metal、Methane/Methicillin/Methionine/Methyl、Mice 等 M 段 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；将 `Mercury -> 汞` 修正为 `汞元素` 以避免单字 alias，并把 `Mercury Poisoning, Nervous System`、`Wireless Mesh Networks`、`Network Meta-analysis`、`Integrated Circuit Metallization`、`Methylprednisolone Acetate`、`RNA Methylation` 等 medium compositional 候选改为显式 exact replacement；
  - grouped L3-L5：fill `records_filled = 21624`，validate `review_decisions = 370946`；
  - 本轮 exact 相关候选 `359` 条，其中显式接受 `326` 条 exact/domain-aware recommendation，`33` 条因 prior block、duplicate/collision 或旧 side-effect policy 保持 blocked；
  - 无 medium-confidence compositional 候选被 blanket accepted；validation 后恢复既有 English ambiguous blocked 决策，保持 `en:needs_review = 0`；
  - runtime 中文覆盖从 `9846 / 48877 = 20.14%` 增至 `10169 / 48877 = 20.81%`；
  - `zh:accept`: `10183`，`zh:blocked`: `11496`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `d62948acd497465932d9a8b25804209829ae3d2b45fcd22bc4a66aedfd5b72f1`；
  - compact manifest SHA-256: `c54ef0f4d4e92c4f87099dcda802f1a92605e09f6f5e7683d5755d722c1c7d3e`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - query smoke 已确认 `男性健康`、`脑膜炎球菌性脑膜炎`、`汞元素`、`间充质干细胞`、`消息认证码`、`荟萃分析`、`网络荟萃分析`、`代谢组学`、`金属有机框架`、`耐甲氧西林金黄色葡萄球菌`、`RNA甲基化`、`小鼠` 可命中；`心理健康服务`、`网状网络`、`超材料` 因 prior block 或 duplicate/collision 保持不命中；
  - review audit artifact: `F:\AI playground\TempFiles\theme_alias_batch_381_to_400_review_audit.json`；
  - 相关测试：`463 passed in 3.42s`。
- batch-400 后 review：
  - 本轮新增 `323` 个 runtime zh-covered concepts，覆盖率已到 `20.81%`，距离 `>25%` 目标仍需继续多轮；
  - `心理健康服务` 等 prior-blocked exact 输出没有在本轮强行打开；`网状网络`、`超材料` 等重复概念继续不自动 merge；
  - 下一轮应继续 batch-401 至 batch-420，优先从 mice/micellar/micro/migration 等 M 段 high-confidence exact 术语推进。
- 最新 batch-361 至 batch-380 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_361_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_380_ALIASES`，覆盖 mast/match/material/maternal/mathematical/matrix/max/mean/mechanical/media/medical/medicine/melanin/membrane/memory 等 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；将 `MATLAB`、`Matlab-simulink` 改为含中文成分的 `MATLAB软件`、`MATLAB/Simulink软件`，避免 English-only zh alias；
  - grouped L3-L5：fill `records_filled = 21303`，validate `review_decisions = 370624`；
  - 显式接受 `348` 条 exact/domain-aware recommendation，显式阻断 `23` 条由 exact 组件触发的 compositional side-effect；validation 后恢复 `713` 条既有 English ambiguous blocked 决策，保持 `en:needs_review = 0`；
  - 本轮 exact 相关行中 `145` 条因 duplicate/collision、单组件泛化或既有 medium-confidence blocking 保持 blocked；不自动 merge；
  - runtime 中文覆盖从 `9500 / 48868 = 19.44%` 增至 `9846 / 48877 = 20.14%`；
  - `zh:accept`: `9860`，`zh:blocked`: `11497`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `8c807854cc4f2a996ed0b18910aaa874f54b88f17980096c932961660c22c15f`；
  - compact manifest SHA-256: `893c7166ac10c2958a5cb8803ad96dea7062e7e1c733d44fc9050c3ae51b60f8`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - 相关测试：`443 passed in 3.74s`。
- batch-380 后 review：
  - 本轮新增 `346` 个 runtime zh-covered concepts，覆盖率已超过 `20%`；
  - `数学分析`、`MATLAB软件`、`基质金属蛋白酶9`、`最大似然估计`、`机械工程`、`医学图像配准`、`内存管理` 等 exact-backed 输出因 duplicate/collision 或既有 blocked 策略仍未进入 runtime；
  - `先进母亲年龄`、`循证医学`、`农业机械化`、`患者安全与用药错误`、`受体黑皮质素` 等 compositional side-effect 已显式 blocked，后续需要独立 exact/domain-specific 词条再打开；
  - query smoke 已确认 `改良根治性乳房切除术`、`主从系统`、`配对分析`、`材料性能`、`母胎交换`、`上颌窦炎`、`平均绝对误差`、`中值滤波器`、`用药依从性`、`中医` 可命中；blocked duplicate/collision/side-effect 示例不命中；
  - 下一步建议先提交本轮变更，再复盘是否设置新的覆盖目标。
- 最新 batch-341 至 batch-360 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_341_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_360_ALIASES`，覆盖 magneto/magnolia/maintenance/major/malaria/male/malicious/mammary/management/mandibular/mannose/MAP kinase/marine/Markov/mass/mast cell 等 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；将 `MapReduce` 改为中文 alias `映射归约`，并补充 `α-甘露糖苷酶`、`男性乳腺肿瘤`、`大型计算机`、`数字营销与社交媒体`、`质谱技术与应用` 等 exact replacement；
  - grouped L3-L5：fill `records_filled = 20992`，validate `review_decisions = 370313`；
  - 显式接受 `284` 条 exact/domain-aware recommendation；validation 后恢复 `713` 条既有 English ambiguous blocked 决策，保持 `en:needs_review = 0`；
  - 本轮 exact 相关行中 `66` 条因 duplicate/collision 保持 blocked，`1` 条由 validator reject；不自动 merge；
  - runtime 中文覆盖从 `9216 / 48866 = 18.86%` 增至 `9500 / 48868 = 19.44%`；
  - `zh:accept`: `9514`，`zh:blocked`: `11521`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `f052293e98d5ce1a3cdaa03fd7c25ff051609aecf2bf6a91abe1a9d1d5857e6c`；
  - compact manifest SHA-256: `cf8ffafb46833e2f99f4797730f6e871273aa57657fecc9aa537ca4c846c1abe`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - 相关测试：`423 passed in 3.20s`。
- batch-360 后 review：
  - 本轮新增 `284` 个 runtime zh-covered concepts，覆盖率到 `19.44%`，距 `>20%` 目标仍需继续；
  - `磁流体动力学`、`脑磁图`、`乳腺X线摄影`、`人机系统`、`流形学习`、`海洋生物学`、`马尔可夫链` 等 exact-backed 输出因 duplicate/collision 保持 blocked；
  - side-effect 复查后剩余 `0` 条；通过 exact replacement 修正了 male/mainframe/marketing/mannosidase/mass spectrometry 等组合副作用；
  - query smoke 已确认 `心磁图`、`磁光效应`、`重性抑郁障碍`、`恶意软件分析`、`乳腺样分泌性癌`、`中间人攻击`、`甘露糖受体`、`MAP激酶激酶1`、`地图匹配`、`质谱技术与应用` 可命中；blocked duplicate/collision 示例不命中；
  - 下一轮从 batch-361 至 batch-380 继续，优先 mast/match/material/maternal/mathematical/matrix 后续 high-confidence exact 术语，预计可超过 `20%`。
- 最新 batch-321 至 batch-340 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_321_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_340_ALIASES`，覆盖 lymphoma/lymphotoxin/lysine/lysosomal、M-phase/MAC/Macaca/Mach、machine learning/machining、macrophage/macular、magnesium/magnetic 等 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；补充 `农业机械`、`α-巨球蛋白`、磁共振波谱和巨噬细胞/溶血磷脂受体词序 exact replacement；
  - grouped L3-L5：fill `records_filled = 20704`，validate `review_decisions = 370026`；
  - 显式接受 `188` 条 exact/domain-aware recommendation；
  - 本轮无额外 side-effect block recommendation；validation 后恢复 `713` 条既有 English ambiguous blocked 决策，保持 `en:needs_review = 0`；
  - runtime 中文覆盖从 `9030 / 48866 = 18.48%` 增至 `9216 / 48866 = 18.86%`；
  - `zh:accept`: `9230`，`zh:blocked`: `11517`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `a81f6254f86b0a75e04eccad870e70753ddbbd277a1887607ecd03ceecd6d43f`；
  - compact manifest SHA-256: `48051710da1d5dccd3258c19252df1b4b15b6e33a9c2de7f55dedbbcd21890d0`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - 相关测试：`403 passed in 2.86s`。
- batch-340 后 review：
  - 本轮新增 `186` 个 runtime zh-covered concepts，覆盖率到 `18.86%`，距 `>20%` 目标仍需继续；
  - 本轮 exact replacement 主要修正机器/磁共振/受体类候选的标准译名和词序，未引入 accepted/runtime conflict；
  - duplicate/collision exact 输出继续不自动 merge；
  - query smoke 已确认 `农业机械`、`α-巨球蛋白`、`碳-13磁共振波谱`、`质子磁共振波谱`、`粒细胞巨噬细胞集落刺激因子受体`、`溶血磷脂受体`、`巨噬细胞集落刺激因子受体` 可命中；
  - 下一轮从 batch-341 至 batch-360 继续，优先 magnetic/magnetization/magnitude/malaria/manifold 等后续 high-confidence exact 术语。
- 最新 batch-301 至 batch-320 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_301_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_320_ALIASES`，覆盖 liquid/listeria/lithium/liver/load/local/location/logic/logistic、long-term/LSTM、lossless/low-power、LTE/LU/lubricants、luciferase/luminescence/lung/lupus、lutein/Lyapunov/Lyme/lymphatic/lymphocyte/lymphoma 等 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；保持单字中文 alias 门禁，不放宽全局形态约束，将 `Liver`/`Lung` exact 输出改为 `肝脏`/`肺脏`；
  - grouped L3-L5：fill `records_filled = 20519`，validate `review_decisions = 369840`；
  - 显式接受 `362` 条 exact/domain-aware recommendation；
  - 显式阻断 `4` 条 medium compositional/domain-title side-effect；另有 `51` 条 exact-backed 输出由 validator 因 duplicate/collision 保持 blocked，`2` 条 medium compositional collision 也保持 blocked；
  - validation 后恢复 `713` 条既有 English ambiguous blocked 决策，保持 `en:needs_review = 0`；
  - runtime 中文覆盖从 `8671 / 48864 = 17.75%` 增至 `9030 / 48866 = 18.48%`；
  - `zh:accept`: `9044`，`zh:blocked`: `11516`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `cad492abc92dade8e94d6cd7468b0a081c471f725094c7015bf27706050e7c00`；
  - compact manifest SHA-256: `d3e6a7f288fb2c5f11a3ccdd20d1dc2340ca849c62aa9b4ddf00c041b34e1415`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - 相关测试：`383 passed in 2.90s`。
- batch-320 后 review：
  - 本轮新增 `359` 个 runtime zh-covered concepts，覆盖率到 `18.48%`，距 `>20%` 目标仍需继续；
  - `遗传老化与模型生物体中的长寿`、`食品安全中的单核细胞增生李斯特菌`、`读写能力与教育实践`、`读写能力媒体与教育` 等 medium side-effect 已显式 blocked；
  - `长短期记忆`、`低通滤波器`、`局域网`、`逻辑门`、`环形天线` 等 exact-backed 输出因多 concept duplicate/collision 保持 blocked，不自动 merge；
  - query smoke 已确认 `液-液萃取`、`锂硫电池`、`肝特异性有机阴离子转运蛋白1`、`负荷频率控制`、`局部保持投影`、`基于位置的社交网络`、`Logistic回归`、`LTE上行链路`、`荧光素酶`、`间质性肺疾病`、`Lyapunov稳定性`、`莱姆病`、`淋巴管生成`、`非霍奇金淋巴瘤` 可命中；blocked side-effect 不命中；
  - 下一轮从 batch-321 至 batch-340 继续，优先 lymphomatoid/lysine/lysosomal/M-phase/MAC/Mach 后续 high-confidence exact 术语。
- 最新 batch-281 至 batch-300 exact/domain-aware 小批次已完成：
  - 新增 `ZH_EXACT_EXPANSION_BATCH_281_ALIASES` 至 `ZH_EXACT_EXPANSION_BATCH_300_ALIASES`，覆盖 least/lectin/leg/legacy、Leishmania/leprosy/leptospira、leucine/leukemia/leukocyte/leukotriene、Lewis/library/LiDAR/life/light、linear/link/lipid/lipoprotein/liquid 等 exact/domain-aware 术语；
  - 新增 `20` 个代表性回归测试，先红灯后转绿；
  - grouped L3-L5：fill `records_filled = 20172`，validate `review_decisions = 369494`；
  - 显式接受 `300` 条 exact/domain-aware recommendation；
  - 显式阻断 `34` 条由 exact 词条引发的 compositional/mixed side-effect；另有 `31` 条 exact-backed 输出由 validator 因 duplicate/collision 保持 blocked；
  - validation 后恢复 `713` 条既有 English ambiguous blocked 决策，保持 `en:needs_review = 0`；
  - runtime 中文覆盖从 `8373 / 48863 = 17.14%` 增至 `8671 / 48864 = 17.75%`；
  - `zh:accept`: `8685`，`zh:blocked`: `11524`，`zh:needs_review`: `0`；
  - accepted conflict groups: `0`；
  - package/tool compact index byte-identical；package/tool compact manifest byte-identical；legacy full overlay package/tool 仍 byte-identical；
  - compact index SHA-256: `f1288e19183fc0676f9de559f7e11a82271352597c77e1e7325ff4c91aabdbbc`；
  - compact manifest SHA-256: `b9acc4b9c495ed6abf2966a6d6128473400bb11fba3e54967d7e5c13b9339600`；
  - pollution audit: ordinary English-heavy zh aliases `0`，known bad-shape hits `0`；
  - 相关测试：`363 passed in 2.91s`。
- batch-300 后 review：
  - 本轮新增 `298` 个 runtime zh-covered concepts，覆盖率到 `17.75%`，距 `>20%` 目标仍需继续；
  - `受体瘦素`、`利什曼病研究上的研究`、`脂肪营养不良家族性部分`、`4 1BB配体` 等 medium/low side-effect 已显式 blocked；
  - `线性规划`、`线性预测编码`、`生命周期评价`、`数字图书馆` 等 exact-backed 输出因多 concept duplicate/collision 保持 blocked，不自动 merge；
  - query smoke 已确认 `最低有效位`、`利什曼病`、`左心耳封堵术`、`瘦素`、`急性髓系白血病`、`激光雷达系统`、`线性时不变系统`、`视距传播`、`液体活检` 可命中；
  - 下一轮从 batch-301 至 batch-320 继续，优先 liquid/listeria/lithium/liver/load/local/location/logic/long-term 后续 high-confidence exact 术语。
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
