# 2026-06-01 — 文献命名与 CNKI 探针阶段交付

## 已交付

- 新增统一文献 artifact 命名器：`identifier`、`title_author`、`title_year_author`、`custom`。
- `fetch_paper` / CLI `fetch` / `batch` / `search --fetch` 支持命名参数。
- CLI `batch` 保存的 JSON / Markdown / TXT sidecar 结果也复用同一套命名规则；默认 `identifier` 保持兼容。
- CLI `config-cmd` 支持配置 `paper_filename_max_length` 与 `paper_filename_collision`，并校验：policy 仅允许 `identifier/title_author/title_year_author/custom`，max length 必须为正整数，collision 仅允许 `hash/increment`。
- 友好命名策略在标题/作者等元数据不足、模板结果为空白、纯符号或纯下划线时，会回退到稳定 `identifier` stem，避免 `-.pdf` / `_.pdf` 这类文件名。
- MCP `fetch_paper` 支持 `ask_rename`，客户端支持 elicitation 时可询问一次命名策略；失败或取消时回退配置。
- 当 `paper_filename_ask=true` 且 MCP 客户端传入 `ctx` 并支持 elicitation 时，`fetch_paper` 即使未显式传 `ask_rename` 也会按配置主动询问一次；可用 `paper_filename_ask=false` 关闭。
- 新增 CNKI 显式路由边界：普通中文 query 不自动路由 CNKI。
- 新增 CNKI metadata-only 探针骨架：页面状态分类与 URL identifier 提取。
- 新增正式 `Artifact` 模型：PDF/CAJ/CAJX/NH/KDH 等多文件结果可统一输出 `path/format/kind/text_extracted/note`。
- 新增 `download_cnki_artifact(local_file=...)` MCP 工具与 `vpnsci-sustech cnki-download --local-file ...` CLI 命令，用于归档已手动下载的 CNKI 文件。
- 新增受控 live 下载 smoke：MCP/CLI 支持 `live=true/--live` + `confirm_live_access=true/--confirm-live-access`，只在可见浏览器中打开用户指定 CNKI 详情页并触发一次页面已有下载链接。
- CNKI 本地 artifact 归档支持单次 `filename_policy/filename_template` 覆盖；显式参数优先于配置默认值。
- 本地 CNKI PDF 归档时会尝试提取全文；CAJ/CAJX/NH/KDH 继续只保存原文件并标注 `text_extracted=false`。
- seed preview/paper-search-pro 适配器已保留 CNKI 字段：`cnki_id/source_url/download_format/local_file/result_type`。
- 新增默认 dry-run 的 CNKI 可见浏览器 smoke 脚手架：MCP `cnki_visible_smoke` 与 CLI `cnki-smoke`；真实访问需要 `confirm_live_access`。
- 新增 CNKI 详情页离线解析入口：MCP `get_cnki_paper_detail` 与 CLI `cnki-detail --html-file ...`。
- 新增 CNKI 搜索结果页离线解析入口：MCP `search_cnki_from_html` 与 CLI `cnki-search-html --html-file ...`，解析后保存标准 `SearchSession`。
- 新增 CNKI 批量下载保守控制：CLI `cnki-batch-download` 与 MCP `download_cnki_batch_artifacts` 支持逐篇串行、站点级最小间隔、每 N 篇长冷却、连续失败停止、状态 JSON 与 `--resume`。
- 新增默认关闭的 CNKI CAJ/CAJX 外部转换器配置：`cnki_convert_caj_to_pdf` 与 `cnki_caj_converter_command`；转换成功会增加 `converted_pdf` artifact。
- 报告桥接 metadata / full-workflow handoff 已标注 CNKI seed：`seed_source=cnki` 与 `cnki_fields` 保留状态。
- 多源 seed 会标记 `seed_source=mixed`，同时保留 `cnki_fields` 审计信息。
- `site_policy.py` 新增 CNKI experimental 策略和保守限制常量。
- CLI `search --backend cnki` 现在会保存 gated `SearchSession`，输出 `live_access_not_enabled`，但仍不访问 CNKI。
- CNKI visible-browser 目标拒绝 `fsso.cnki.net` / `login.cnki.net` 等登录入口，避免自动化触碰登录抓取边界。

## 安全边界

- 离线实现阶段不访问 CNKI 真实站点；真实 smoke 必须由用户显式授权。
- 不做 CNKI 登录自动化、验证码绕过、账号密码采集、DRM/付费墙/下载限制绕过。
- `cnki-smoke` 默认 dry-run；真实可见浏览器 smoke 只做页面快照解析，不下载。
- `cnki-detail` 只解析用户提供的 HTML/page source；未提供 HTML 时不会联网。
- `cnki-search-html` 只解析用户提供的搜索页 HTML/page source；遇登录/验证码返回分类错误。
- CAJ/CAJX 转 PDF 不内置、不自动安装第三方工具，默认关闭；转换失败不影响原始文件保存。
- `backend=cnki` 当前只保存 experimental/gated SearchSession 并返回提示；`cnki-download --local-file` 只读取本地文件；`cnki-download --live --confirm-live-access` 只允许单次可见浏览器下载 smoke；`cnki-batch-download --live --confirm-live-access` 仅把单次下载串行编排并保守节流/冷却/状态恢复，仍不绕过登录、验证码、DRM 或付费限制。
- CNKI 下载链路可能频繁触发 `bar.cnki.net` 拼图/滑块验证码，尤其是连续下载、机构共享出口 IP、CAJ/硕博大文件或自动化点击场景；CDP/Selenium 只能辅助打开页面、点击、设置下载目录和检测落盘，不能稳定、合规地越过服务端风控验证码。
- 本项目不会接入验证码破解、打码平台或滑块绕过方案；后续优化方向仅限“检测到验证码后暂停/等待用户人工完成，再自动继续归档”，并配合节流、冷却和 `--resume` 降低重复触发。
- CNKI live 下载命令开始前会主动提示：下载过程可能触发验证码/安全验证，需要保持可见浏览器打开并准备人工处理；未触发验证码时，PDF/CAJ 链路可自动点击、等待落盘并归档。点击下载后若触发 `bar.cnki.net` 验证页，会等待人工完成并自动继续检测落盘；成功 note 标注 `resumed_after_captcha`，超时返回 `captcha_timeout`。

## 第三方参考与许可证

- 参考了计划中记录的公开工具生态和流程边界，包括 `cookjohn/cnki-skills`、`h-lu/cnki-mcp`、`caj2pdf/caj2pdf`。
- 本阶段未复制、vendor 或运行第三方 CNKI 项目代码。
- CAJ 转 PDF 未内置；后续如接外部 converter，需要用户显式配置。

## 验证

```bash
python -m unittest tests.test_cnki tests.test_cli_cnki tests.test_mcp_server tests.test_models_artifacts tests.test_file_naming tests.test_fetcher_phase2 tests.test_search_models -v
python -m unittest tests.test_paper_search_cnki_fields tests.test_paper_search_pro_adapter -v
python -m unittest tests.test_cnki tests.test_cli_cnki tests.test_mcp_server tests.test_site_policy tests.test_backend_routing -v
python -m compileall vpnsci_sustech tests
python -m unittest discover -s tests -v
```

## 2026-06-01 CNKI PDF live smoke follow-up

- 使用关键词 量子计算 冷原子 完成真实 PDF 链路验证。
- 样本：基于光学芯片的中性原子量子计算系统 / 陈梁。
- 归档：cnki/基于光学芯片的中性原子量子计算系统 - 陈梁_4d0d873d.pdf。
- 验证：127 页，13520400 bytes，SHA256 `b917d24b0e550c22bdc0be037bf98f0d79bdc02ee716dca17455482e4f7be3b8`，正文文本可提取并包含 陈梁、冷原子、量子计算。
- 修复：下载等待逻辑可识别同名文件覆盖/更新；点击逻辑增加滚动和 JS click fallback。

## 2026-06-01 CNKI CAJ live smoke follow-up

- 用户确认后补充真实 CAJ 下载 smoke。
- 样本：基于光学芯片的中性原子量子计算系统 / 陈梁。
- 第一次 CAJ 触发 `bar.cnki.net` 拼图校验并超时；用户关闭校验页后重试成功。
- 归档：cnki/基于光学芯片的中性原子量子计算系统 - 陈梁.caj。
- 验证：12899642 bytes，SHA256 `cb3a4d4bc400850ceec85486843346b3c7b9dd9c1cb4744c6ace1239a5f42625`，文件头 `KDH 2.00 Copyright`，`text_extracted=false`。
- 说明：CAJ 原文保存成功；当前默认不解析 CAJ 全文，不内置转换器。
- 文件后续已由用户整理到 `C:\Users\SUSTech\.vpnsci-sustech\papers\cnki`；仓库内不再保留 `cnki/` 下载目录。

## 待真实 smoke 验证项

- 计划 A：验证码等待与人工完成后自动 resume 已有 fake-driver/单元测试覆盖，但尚未单独做一次“点击下载后触发 `bar.cnki.net` 验证页、用户人工完成、工具自动继续归档”的真实 CNKI smoke。
- 计划 B：`cnki-batch-download` / `download_cnki_batch_artifacts` 的节流、冷却、连续失败停止与 `--resume` 已有单元测试覆盖，但尚未做真实小批量 CNKI 下载 smoke。
- 以上 smoke 仍需用户再次显式授权；执行时应限制小样本，建议 2 篇以内，输出目录仍使用 `C:\Users\SUSTech\.vpnsci-sustech\papers\cnki` 或用户指定目录。
