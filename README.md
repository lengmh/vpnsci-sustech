# vpnsci-sustech

学术论文全文获取工具，支持 100+ 中国高校。通过 MCP 协议接入 AI Agent，用自然语言搜索和获取论文。当前仓库地址：

- GitHub: https://github.com/lengmh/vpnsci-sustech

**获取原理**：
1. 先找免费来源（Unpaywall、arXiv）
2. 找不到则通过学校代理访问机构订阅资源（支持 WebVPN、EZproxy、EasyConnect、aTrust 四种方式）
3. 都不行则返回元数据（标题、摘要、引用数）

## 使用方式

### 通过 AI Agent（推荐）

vpnsci-sustech 通过 [MCP](https://modelcontextprotocol.io/) 协议接入 AI Agent，直接用自然语言交互即可。

**安装**：

对你的 AI Agent 说：

> 帮我安装这个 MCP 包：https://github.com/lengmh/vpnsci-sustech

**使用示例**：

> 帮我搜几篇钙钛矿太阳能电池的最新论文

> 这篇论文的全文是什么？DOI: 10.1038/s41566-024-01234-5

> 帮我找 2023 年以后关于有机光伏的高引论文，下载 PDF

首次使用时 Agent 会询问你的学校，告诉它即可自动配置。

### MCP 手动安装 / 配置

普通用户如果希望不手动 clone 源码仓，可以用 Git URL `uvx` 启动 MCP 入口：

```toml
[mcp_servers.vpnsci_sustech]
type = "stdio"
command = "uvx"
args = ["--from", "git+https://github.com/lengmh/vpnsci-sustech.git", "vpnsci-sustech-mcp"]
```

开发者源码 checkout 或本地可编辑安装时，也可以使用：

```toml
[mcp_servers.vpnsci_sustech]
type = "stdio"
command = "python"
args = ["-m", "vpnsci_sustech.mcp_server"]
```

如果你是从源码仓库安装，也可先执行：

```bash
pip install git+https://github.com/lengmh/vpnsci-sustech.git
```

安装后通常会得到两个命令：

- `vpnsci-sustech`
- `vpnsci-sustech-mcp`

也可以直接手动验证 MCP 入口是否可启动：

```bash
python -m vpnsci_sustech.mcp_server
```

### 安装后最小验证

建议至少验证以下四组检索：

- Springer: `support-vector networks`
- Wiley: `synergetic spin crossover fluorescence one-dimensional hybrid complexes`
- ScienceDirect: `filtering antenna with radiation and filtering functions for wireless applications`
- IEEE Xplore: `Network Anomaly Detection Using a Graph Neural Network`

如果宿主支持为 MCP 工具传参，建议分别指定：

- `backend="springerlink"`
- `backend="wiley"`
- `backend="sciencedirect"`
- `backend="ieee"`

这样可以直接验证当前 Phase 2 的 publisher-native search 路线，而不是只测默认标准检索路线。

### 搜索模式

`search_papers` 默认走 **标准检索**：

- OpenAlex-first 元数据检索
- Semantic Scholar 补充 / fallback
- 少量中英 query variants（原始 query 永远保留）
- 多源去重后的结构化结果
- 返回可复用的 Search Session id

标准检索不会默认生成报告，也不会默认启动 citation chasing、PRISMA、复杂布尔检索式或 `paper-search-pro` 重流程。

当标准检索结果质量足够时，工具可能给出升级建议：

> 如果你想要更全面覆盖、去重整合和 HTML 综合报告，我可以基于这次检索继续进入“专业调研”模式。

这只是提示，不会自动进入专业调研。需要 HTML 综合报告时，显式调用：

```python
generate_search_report(search_session_id="search-...", mode="full")
```

专业调研使用标准检索会话作为种子结果，分两种模式：

- `mode="full"`：完整专业调研，目标是多源扩展检索、检索式规划、相关性分级、RCS / PRISMA / 多格式导出。
- `mode="seed_preview"`：快速 HTML 预览，只整理当前 `SearchSession` 里的已有结果，适合先浏览结果概貌。

`seed_preview` 会自动补齐 HTML 报告需要的主题图景和轻量 PRISMA-S disclosure，但它仍不是完整专业调研。`full` 模式需要支持完整调研执行环境；如果当前 Agent 不支持并行分类，会明确询问你是否改走快速预览、主 Agent 串行分类，或稍后重试。

### Search Session / 恢复 / continuation

当前主链已经统一到 `SearchSession`：

- 标准检索会保存 Search Session
- CNKI HTML 导入会保存带 `html_import` provenance 的 Search Session
- 下载工作流会额外保存 **report recovery sidecar**
- 从单条结果继续全文获取，优先走 **session hit continuation**

当前约定：

- `SearchHit.hit_key` 是单条结果的稳定持久化标识
- 报告、派生、恢复、continuation 不再依赖数组序号
- `original_query / display_query / recovered_label` 必须区分

CNKI 下载 sidecar 默认保存到：

```text
~/.vpnsci-sustech/cache/download-workflows/
```

它和批量下载 `state_file` 不是一个东西：

- `state_file`：mutable resume state
- `download-workflows/*.json`：报告恢复 sidecar

HTML 报告顶部会保留你的原始查询，并在下方用小标签展示实际执行的检索 query，便于区分“我输入了什么”和“各数据源实际搜了什么”。

仓库内包含 `paper-search-pro` 报告能力，并会在用户目录准备本地运行副本。报告、缓存和个人 API key 保存在用户本地，不进入源码仓库。

### OpenAlex 配置

可选配置 OpenAlex API key：

```bash
vpnsci-sustech config-cmd --openalex-api-key YOUR_KEY
```

不配置 key 也可尝试搜索，但 OpenAlex 仍可能遇到额度或频率限制。限流会被报告为 rate limit，不会被伪装成 “No results found”。

### paper-search-pro 报告桥接配置

报告桥接是可选项，不影响标准检索和 `fetch_paper`。推荐使用内置安装命令：

```bash
vpnsci-sustech report-tools install
```

或在配置命令中顺带安装：

```bash
vpnsci-sustech config-cmd --install-report-tools
```

安装后会自动配置报告工具位置、生成命令和报告输出目录。默认命令用于 `seed_preview` 快速 HTML 预览；`mode="full"` 会按完整调研流程继续执行，或在当前 Agent 环境不满足时给出明确选择。

当前仓库边界：Git URL `uvx` 路径可以启动 MCP 入口；但报告前端运行时仍依赖源码仓 `tools/paper-search-pro` 或本地已准备好的 bundled runtime。若 `report-tools install` 在安装态找不到 bundled 资源，应视为配置/打包能力缺口，不要把 `seed_preview` 或 `seed_classified` 说成 `full` 报告。

如果你改的是源码仓里的报告前端（`tools/paper-search-pro/assets/webartifacts_app/paper-report/src/**`），推荐用下面的 repo 维护脚本刷新构建产物和本地 bundled runtime：

```powershell
pwsh -File scripts/refresh_report_frontend.ps1
```

这是源码仓维护动作，不是普通终端用户 / MCP 工具能力。

如果你要改成自己的外部 `paper-search-pro`，也可以手动设置：

```bash
vpnsci-sustech config-cmd \
  --paper-search-pro-root "F:\AI playground\paper-search-pro" \
  --paper-search-pro-command "python -m paper_search_pro --seed {seed_json} --output {output_dir}" \
  --paper-search-pro-output-dir "F:\AI playground\TempFiles\paper-search-reports"
```

命令模板可使用：

- `{seed_json}`：标准检索会话导出的种子结果 JSON
- `{output_dir}`：报告输出目录
- `{session_id}`：检索会话 id

### 通过命令行

```bash
# 安装
pip install git+https://github.com/lengmh/vpnsci-sustech.git

# 配置学校
vpnsci-sustech config-cmd --school 你的学校

# 搜索论文
vpnsci-sustech search "perovskite solar cells"

# 显式 CNKI backend 当前只保存 gated SearchSession，不访问 CNKI
vpnsci-sustech search "钙钛矿" --backend cnki

# 获取论文全文
vpnsci-sustech fetch "10.1038/s41566-024-01234-5"

# 用“标题 + 第一作者”保存 PDF
vpnsci-sustech fetch "10.1038/s41566-024-01234-5" --filename-policy title_author

# 批量获取
vpnsci-sustech batch dois.txt --output ./papers --filename-policy title_year_author
# 批量结果 sidecar（json/markdown/text）也会使用同一套命名策略

# 将已手动下载的 CNKI 文件纳入统一命名/artifact 输出；不会访问 CNKI
vpnsci-sustech cnki-download --local-file ./paper.caj --title "文献标题" --first-author "张三" --filename-policy title_author

# 受控 CNKI 可见浏览器下载 smoke；必须显式确认，会先提示可能需要人工验证码；无验证码时自动下载，点击后如触发验证码会等待人工完成并自动继续归档，超时返回 `captcha_timeout`
vpnsci-sustech cnki-download --detail-url "https://kns.cnki.net/kcms2/article/abstract?filename=..." --live --confirm-live-access --output ~/.vpnsci-sustech/papers/cnki --prefer pdf --filename-policy title_author

# 受控 CNKI 批量下载；逐篇串行，支持最小间隔、每 N 篇冷却、连续失败停止和 --resume 状态恢复
vpnsci-sustech cnki-batch-download cnki-items.jsonl --live --confirm-live-access --output ~/.vpnsci-sustech/papers/cnki --filename-policy title_author --min-interval 20 --cooldown-every 5 --cooldown-seconds 120 --max-consecutive-failures 1 --state-file ~/.vpnsci-sustech/cache/cnki/batch/state.json --resume

# 规划 CNKI 可见浏览器 smoke；默认 dry-run，不打开浏览器、不访问 CNKI
vpnsci-sustech cnki-smoke --query "钙钛矿" --limit 1

# 从已捕获的 CNKI 详情页 HTML 离线解析元数据；不会访问 CNKI
vpnsci-sustech cnki-detail --url-or-id ABC123 --html-file ./detail.html

# 从已捕获的 CNKI 搜索结果 HTML 离线解析并保存 SearchSession；不会访问 CNKI
vpnsci-sustech cnki-search-html --query "钙钛矿" --html-file ./search.html --limit 3

# 从下载 sidecar 恢复 SearchSession 并启动报告（A 恢复）
vpnsci-sustech report-recover --sidecar ~/.vpnsci-sustech/cache/download-workflows/download-xxxx.json --mode seed_preview

# 显式从旧 materialized/report JSON 恢复 SearchSession 并启动报告（B 恢复）
vpnsci-sustech report-recover --report-json ~/.vpnsci-sustech/cache/search/reports/search-xxxx/materialized/report_data.json --prefer B --mode seed_preview

# 从 SearchSession 的单条 hit 继续全文获取
vpnsci-sustech fetch-hit search-xxxx cnki:ABC123 --confirm-live-access

# 可选：配置外部 CAJ/CAJX 转 PDF 命令，默认关闭、不内置转换器
vpnsci-sustech config-cmd --cnki-convert-caj-to-pdf true --cnki-caj-converter-command "caj2pdf convert {input} -o {output}"

# 查看支持的学校
vpnsci-sustech schools
```

### 文献文件命名

默认仍使用兼容旧版本的 `identifier` 策略，例如 `10.1038_nphys1509.pdf`。如果想保存为更友好的文件名，可用：

- `--filename-policy title_author`：`文献标题 - 第一作者.pdf`
- `--filename-policy title_year_author`：`文献标题 (年份) - 第一作者.pdf`
- `--filename-policy custom --filename-template "{title} - {first_author} - {year}"`

也可修改默认配置：

```bash
vpnsci-sustech config-cmd --paper-filename-policy title_author
vpnsci-sustech config-cmd --paper-filename-ask false  # 关闭 MCP 主动询问
vpnsci-sustech config-cmd --paper-filename-max-length 180 --paper-filename-collision hash
```

`--paper-filename-policy` 只接受 `identifier/title_author/title_year_author/custom`；
`--paper-filename-max-length` 必须为正整数；冲突策略只接受 `hash/increment`。
当标题/作者等元数据不足以生成有效友好文件名时，会自动回退到稳定 `identifier` stem。

## SUSTech / CARSI 特殊支持

这个 fork 针对 SUSTech 做了独立适配，支持直接配置 CARSI 学校名，适合 Southern University of Science and Technology 场景。

如果通过 MCP 使用，Agent 可以调用对应配置工具完成初始化；如果通过命令行使用，可先完成登录，再执行搜索和获取操作。

## 当前站点支持说明

- IEEE Xplore：可站内检索，可获取全文，支持 PDF 下载；下载仍沿用现有 IEEE article/PDF 路径
- Springer：可获取全文，搜索和 PDF 下载已验证可用
- Nature：可获取全文
- Wiley Online Library：当前已可做检索并获取全文；搜索在站内执行受限时会回退到元数据搜索
- ScienceDirect：当前已可做检索、全文提取，并可生成本地可解析 PDF；原版 publisher PDF 仍可能失败
- CNKI / 中国知网：当前加入显式路由、会话/DOM 状态探针骨架、离线搜索/详情页解析、`cnki-download --local-file` 本地 artifact 归档、默认 dry-run 的 `cnki-smoke` 可见浏览器 smoke、显式 `cnki-download --live --confirm-live-access` 的受控可见浏览器下载 smoke，以及 `cnki-batch-download` 的保守串行批量下载控制；本地 PDF 会尝试提取全文，CAJ/CAJX/NH/KDH 只保存原文件并标注未提取全文。不会因为普通中文 query 自动访问 CNKI，也不会绕过登录、验证码、DRM、付费墙或下载限制

CNKI 当前额外支持：

- `search_cnki_from_html(...)` 作为正式 `html_import` provenance 并入主链
- 批量下载后自动产出恢复 sidecar
- `report-recover` / `generate_recovery_report(...)` 通过统一 recovery resolver 恢复报告输入
  - A：默认优先使用 download-workflows sidecar
  - B：支持显式传入 legacy `report_data.json`，以及基于 materialized bundle 的兼容恢复
- `fetch-hit` / `fetch_search_hit(...)` 从 session hit 继续获取全文

但仍保持以下边界：

- 普通中文 query 不默认访问 CNKI
- `fetch_paper(cnki_url)` **没有**并入通用 DOI/URL fetch 主内核
- CNKI URL 继续走专用 continuation / download 路线，而不是通用主 fetch 内核
- A/B 自动比较目前保持**保守裁决**：auto 仍优先 A，但会记录 identity/freshness 比较信息

CNKI 的 CAJ/CAJX 转 PDF 默认关闭，不随包安装或捆绑第三方转换器。用户可显式配置外部命令模板；转换失败时仍保留原始 CAJ/CAJX artifact。

ScienceDirect 在人工浏览器访问下可能可用，但自动化原版 PDF 抓取链路仍可能遇到人机验证或 `403/CPE00001`。当前版本对有效样本已可返回：

- live search API 结果（必要时保留 browser fallback）
- 浏览器文章页正文提取
- 明确标注的本地 generated PDF fallback

对于 Wiley，当前版本已有 browser-direct PDF 路径；搜索层在站内执行受限时会退回 Crossref 元数据搜索，以闭合 search→fetch→pdf 链路。

## 支持的学校

内置 100+ 高校配置，包括清华、北大、复旦、浙大、上海交大等。大部分学校可直接使用。

少数学校需要额外配置 VPN 代理，首次使用时 Agent 会自动提示。支持 WebVPN、EZproxy、EasyConnect、aTrust 四种接入方式。

## 环境要求

- Python >= 3.10
- Chrome 浏览器（首次校园网登录需要）
- Docker（仅部分学校需要，Agent 会自动提示）

## 免责声明

本项目是学术论文获取工具，帮助高校师生合法访问机构已订阅的学术资源。不包含任何 VPN 协议实现，不提供 VPN 连接功能。使用者应遵守相关法律法规和学校网络使用规范。

## 致谢

- [paper-search-pro](https://github.com/O0000-code/paper-search-pro) — Apache-2.0 专业文献检索与 HTML 报告工作流
- [webvpn-converter](https://github.com/lcandy2/webvpn-converter) — 学校配置数据
- [Tuna-Erha-Bot](https://github.com/Konano/Tuna-Erha-Bot) — WebVPN 加密算法
- [ZJUWebVPN](https://github.com/eWloYW8/ZJUWebVPN) — 动态密钥方案
- [CASPaperTunneling](https://github.com/qiyang-ustc/CASPaperTunneling) — CAS 认证流程

## License

[MIT](LICENSE)
