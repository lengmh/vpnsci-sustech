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
  test_*.py                      # 回归测试；本仓库 .gitignore 忽略 tests/

lexicons/
  sources/ normalized/ builds/ candidates/ review/
                                # alias pipeline 本地源和中间产物；gitignored
```

`.idea/`、`tests/`、`CONTEXT.md`、`lexicons/` 当前被 `.gitignore` 忽略。
如果修改这些文件，`git status` 默认可能不显示，需要显式检查。

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

运行时只能读 repo-tracked runtime alias 文件：

```text
vpnsci_sustech/data/theme_concept_aliases.json
tools/paper-search-pro/assets/theme_concept_aliases.json
```

运行时不得读：

```text
lexicons/sources/
lexicons/normalized/
lexicons/builds/
lexicons/candidates/
lexicons/review/
```

最新已知状态（2026-06-15 L3-L5 video/parallel/automatic/human bounded pass）：

- runtime `build_status`: `partial_review_pending`
- 中文候选覆盖：`13835 / 54682 = 25.30%`
- `zh:accept`: `1966`
- `zh:blocked`: `3306`
- `zh:needs_review`: `8539`
- `zh:reject`: `208`
- accepted/runtime alias conflicts: `0`
- runtime concept aliases: `48832`
- package/tool runtime alias 文件 byte-identical
- pollution audit：
  - ordinary English residue: `0`
  - known bad-shape hits: `0`
- 最近相关测试：`49 passed`

当前下一步：

- review medium-confidence `agent_compositional_glossary / medium`，
  按 domain 分层处理；下一优先高频桶：`dynamic`，以及剩余
  biomedical inverted/source-specific items。
- 低置信 `agent_review_gated_mixed_fallback` 不能当覆盖率来源；只能作为
  需要 exact/domain-specific replacement 的 review 队列。
- `System-on-a-chip -> 片上系统` 当前与 `system_on_chip*` 概念冲突，
  保持 blocked，不自动 merge。

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
- package/tool 两份 `theme_concept_aliases.json` byte-identical
- pollution audit 未恢复 ordinary English residue / known bad shapes
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

### 6.7 SubAgent review 规则

- `needs_review` 可交给 SubAgent 分桶审查，但 SubAgent 只返回建议。
- 主 Agent 必须筛选并负责最终写入 review decisions。
- 不使用 blanket `accept_missing`。
- RPM/TPM 紧张时减少 subagent 和等待频率，优先本地脚本分桶。

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

- `.idea/`、`tests/`、`lexicons/` 是 gitignored；这些文件改动不会默认出现在
  `git status --short`。
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
