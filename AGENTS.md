# AGENTS.md — 维护约定

本文件适用于仓库及子目录；更近层级的 `AGENTS.md` / `CLAUDE.md` 优先。

## 项目与入口

`vpnsci-sustech` 提供标准学术检索、全文获取、SearchSession、报告桥接与恢复。先读 [README](README.md) 和 [文档入口](docs/README.md)。

- CLI：`vpnsci_sustech.cli`；MCP：`vpnsci_sustech.mcp_server`。
- 标准检索采用 OpenAlex-first，其他 backend 补充；标准检索不默认生成报告。
- 报告 runtime 位于 `tools/paper-search-pro`；包内 staged runtime 用于安装态，仓库 fallback 仅用于源码开发态。
- `hit_key` 是会话结果级 continuation 的稳定标识，不得用数组序号代替。
- CNKI URL 保持受控 continuation / download 路由，不并入通用 DOI/URL fetch 内核，普通中文 query 不默认访问 CNKI。

## 文件与执行

- 使用当前项目环境：`uv run python ...`、`uv run pytest ...`；直接运行解释器前确认其属于当前 `.venv`。
- 源码、Markdown、JSON 和配置使用 UTF-8 无 BOM。
- 临时文件与测试产物默认使用系统临时目录，或调用方显式指定的可写目录；实际创建、删除探针后再使用，不只检查目录是否存在。
- 保留既有测试环境变量覆盖（`VPNSCI_TEST_TMP`、`VPN_SCI_TEST_TMP`）；仅清理本次创建的临时文件，不删除调用方目录或其中已有内容。
- 不删除仓库外文件；删除仓库内非临时文件需要用户明确授权。不按进程名批量终止进程，不终止其他会话的 Python / uv / 浏览器进程。
- `.idea/`、`CONTEXT.md`、`lexicons/` 是本地工作面，已被忽略；缺失时不能把本地计划当作公开维护依赖。`tests/` 源码和 runtime JSON 应跟踪，测试产物继续忽略。

## 验证

```powershell
uv run pytest tests -q
```

根目录无范围的 pytest 会额外收集 `tools/paper-search-pro/tests`，存在 `tests.*` 导入布局问题；主套件显式指定 `tests`。疑似测试挂起时使用限时执行、`--collect-only` 和 `-o faulthandler_timeout=30`，先区分收集、临时目录权限和测试体问题。

主题数据维护先读 [Theme Lexicon Maintenance](docs/agent-workflows/theme-lexicon-maintenance.md)，报告变更遵循 [Full Report Handoff](docs/agent-workflows/paper-search-pro-full-workflow.md) 和 [Theme Postprocess Contract](docs/agent-workflows/theme-postprocess-contract.md)。

报告前端源码变更后使用：

```powershell
pwsh -File scripts/refresh_report_frontend.ps1
```

该命令会刷新构建产物及用户本地 runtime；随后仍需按变更验证代表性报告和可见页面，长期运行的 MCP 可能需要重载。

## 报告与主题数据

- `seed_preview` / `seed_classified` 不冒充 `full`；完整调研无法执行时明确说明 fallback，不静默降级。
- 报告模块缺数据时原位显示占位，不整块消失。`raw_theme_treemap` 与 `theme_treemap` 的差异必须来自可审计的 display quality gate，不隐藏 Agent 重聚类或重命名。
- compact alias index 是运行时真源，manifest 是状态检查入口；默认使用 `query_alias_index.py` / `summarize_alias_runtime.py`，不要打开完整大 JSON 确认状态。
- legacy full overlay 仅作回滚或显式审计，不作为 runtime fallback。运行时不读取 `lexicons/` 下的源、build、候选或 review 中间产物。
- 物化前备份 review decisions；保持已有 review，先执行 accepted collision guard。未决 collision 维持 blocked，不自动 concept merge，不 blanket accept。
- non-canonical English alias 只允许 exact glossary hit；compositional generation 仅用于 canonical label。翻译按 domain/source/path 核对，保持标识符、英文残留、重复拼接和领域漂移防护。
- recommendation 以 `(lang, concept_id, alias)` 匹配；英文 short acronym 不使用 blanket `--accept-missing`，使用显式 recommendation / allowlist。审查建议由主维护者筛选后写入。
- runtime singular / 中文去标点 normalization 的兼容性碰撞保持既有顺序映射，不混同 review-time accepted conflict。
- package/tool 的 compact index、manifest 及 ambiguous candidate 文件保持 byte-identical；校验 schema、normalization、`review_complete`、冲突与污染，执行相关测试。
- deterministic coverage 与 candidate-resolvable coverage 分开报告；effective coverage 不等于 accepted runtime coverage 或每份报告都能成功消歧。
- Host Agent 只能基于本报告证据选择请求内候选；无证据返回 unresolved。结果必须符合 `theme_candidate_resolution_result.v1`，只影响本报告，不反写 deterministic runtime。

## 外部访问与合法使用

- CNKI live browser access、真实账号、可见浏览器下载、批量下载及生产外部服务操作需要显式确认；`cnki_visible_smoke` 默认 dry-run。
- 不采集账号密码，不自动化登录，不绕过验证码、DRM、付费墙或下载限制。验证码由用户人工处理；保留节流、冷却、连续失败停止和 resume state。
- CAJ/CAJX 外部转换默认关闭，不自动安装或捆绑转换器；转换失败仍保留原文件。

## 公开内容与交付

- 仅保留必要维护规则、设计结论、通用验证方法和未验证边界。不要在 AGENTS.md 或发布说明追加私人任务计划、授权对话、检索/下载记录、逐次操作流水、本机路径或临时产物清单。
- 真实搜索会话、下载文件、报告和浏览器状态留在仓库外；不得改称合成数据后提交。公开示例使用明确占位；必要测试 fixtures 单独审查，不整体忽略 plan/report/JSON/CSV。
- 规则变化时更新对应规则；技术合同更新对应文档，不追加日期化流水。状态和覆盖指标从当前 manifest、源码和精确提交的验证结果核对，不沿用历史批次数字。
- 交付说明改动、关键文件、实际验证、未完成项及下一步；CI 与自动审查按精确 head 核对，排队/运行中不算通过。
