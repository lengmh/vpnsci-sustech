# FAQ / 常见问题

## 1. 主流期刊都有反爬虫功能，会不会受影响？

基本不会。搜索走的是 Semantic Scholar、Unpaywall、arXiv 的**官方 API**，不是爬网页。获取付费论文走的是学校 WebVPN 代理，从出版商角度看就是一个正常用户在浏览器里打开论文。代码里还做了 2-5 秒随机延迟限速，不会触发风控。

## 2. 支持哪些学校？

内置 100+ 中国高校配置，包括清华、北大、复旦、浙大、上海交大、大连理工、东北大学、吉林大学等。运行 `vpnsci-sustech schools` 查看完整列表。大部分学校使用默认加密密钥，少数学校（如大连理工、东北大学）使用自定义密钥，已内置支持。

## 3. 如何切换学校？

```bash
vpnsci-sustech config-cmd --school 大连理工大学
```

会自动设置 WebVPN 地址和加密密钥。用 `vpnsci-sustech schools` 查看可选学校。

## 4. Elsevier 网站经常提示人机验证，能顺利跳过吗？

Elsevier 的反爬比较严格，通过 WebVPN 获取 Elsevier 论文可能会遇到 403。建议优先尝试 Unpaywall 的 OA 版本（程序会自动尝试）。如果 OA 没有，可以手动在浏览器中通过 WebVPN 下载 PDF。

对于 SUSTech 当前验证结论更保守：

- ScienceDirect 检索可以做
- 正文提取当前可以做
- 原版 publisher PDF 当前不保证成功

也就是：能帮你找到论文、拿到正文，并可在必要时生成本地可解析 fallback PDF；但不承诺自动拿到 ScienceDirect 原版 publisher PDF。

## 4.1 Wiley 现在算“已支持自动下载”吗？

暂时不要这样理解。

当前更准确的说法是：

- 已有一条 **browser-direct PDF** 后备路径
- 对固定样本 `10.1002/anie.201410454` 已验证可拿到真实 PDF
- Wiley 的站内搜索执行层当前容易被 challenge；当前实现会退回 Crossref 元数据搜索来闭合 search→fetch 链路

所以当前产品状态应理解为：

- Wiley 已可搜索并自动获取固定样本全文
- 搜索结果在站内执行受限时会回退到元数据搜索
- 从产品可用性看，当前 search→fetch→pdf 已可闭环

## 4.2 不传 `backend` 时默认怎么搜索？

默认走 **标准检索**。

当前默认策略是：

1. 先用 OpenAlex 做元数据检索
2. 根据配置和结果情况用 Semantic Scholar 做补充 / fallback
3. 对中文学术 query 生成最多 3 个轻量 query variants，并保留原 query
4. 保存 Search Session，便于后续全文获取或显式升级报告

这时**不会**自动切到 Springer / Wiley / ScienceDirect / IEEE Xplore 的 publisher-native search。

如果你想显式验证当前 Phase 2 路线，建议在 MCP / CLI 中明确指定：

- `backend="springerlink"`
- `backend="wiley"`
- `backend="sciencedirect"`
- `backend="ieee"`

也就是说：

- **默认搜索**：OpenAlex-first 标准检索
- **显式指定 backend**：走对应 publisher-native search

IEEE Xplore 的显式搜索走站内 `/rest/search` 元数据结果；后续全文/PDF 获取仍沿用现有 IEEE article/PDF 路径。

## 4.3 为什么搜索后会建议“专业调研”？

这是 **升级建议**，不是自动升级。

它只在标准检索已经拿到足够结构化结果、query 不是 DOI/URL/单篇精确题名、且没有 rate limit / backend blocked / request failed 等严重错误时出现。

出现建议后，你可以继续普通全文获取，也可以显式调用：

```python
generate_search_report(search_session_id="search-...", mode="full")
```

## 4.4 “最新”“高引”“尽量全面”会直接触发专业调研吗？

不会。

这些词只说明你希望标准检索排序或覆盖更好，不足以直接进入重流程。直接触发专业调研的强信号只保留很小白名单，例如：

- 文献综述
- 系统综述
- 调研报告
- HTML 报告
- systematic review
- research report
- PRISMA

## 4.5 报告桥接会影响 `fetch_paper` 吗？

不会。

`paper-search-pro` 只通过报告桥接显式调用。桥接未配置或报告生成失败时，标准检索结果和 `fetch_paper` 都不受影响。

## 4.5.0 下载的 PDF 怎么改成“标题 + 作者”命名？

默认仍是旧版兼容的 DOI/identifier 命名。需要友好文件名时显式传：

```bash
vpnsci-sustech fetch "10.xxxx/xxxx" --filename-policy title_author
```

可选策略：

- `identifier`：稳定 DOI/arXiv/URL stem，默认值。
- `title_author`：`文献标题 - 第一作者.pdf`。
- `title_year_author`：`文献标题 (年份) - 第一作者.pdf`。
- `custom`：配合 `--filename-template`。

MCP `fetch_paper` 也支持 `filename_policy`；如果客户端支持 elicitation，可用 `ask_rename=true` 让客户端询问一次。配置里的 `paper_filename_ask=true` 时，支持 elicitation 的 MCP 客户端也会在未显式指定策略时主动询问一次；不想被问可运行：

```bash
vpnsci-sustech config-cmd --paper-filename-ask false
```

CLI `batch` 保存的结果 sidecar（JSON / Markdown / TXT）也会使用同一套命名规则；默认仍是兼容旧行为的 `identifier`。

长文件名和冲突策略也可配置：

```bash
vpnsci-sustech config-cmd --paper-filename-max-length 180 --paper-filename-collision hash
```

`--paper-filename-policy` 只接受 `identifier/title_author/title_year_author/custom`；
`--paper-filename-max-length` 必须为正整数；
`--paper-filename-collision` 只接受 `hash` 或 `increment`。
如果 `title_author` / `custom` 因缺少标题、作者等元数据只能生成空白、纯符号或纯下划线，会自动回退到稳定 `identifier` stem，避免出现 `-.pdf` / `_.pdf` 这类文件名。

## 4.5.0.1 CNKI / 中国知网现在会自动搜索或下载吗？

不会自动触发。当前 CNKI 路径必须显式调用：

- 普通中文 query 不会自动访问 CNKI。
- 只有显式 `backend=cnki` 或明确“知网 / CNKI / 硕博论文 / 中文核心”等意图才进入 CNKI 路由。
- 当前实现不会自动登录、不会抓取 robots 禁止的登录入口、不会绕过验证码/DRM/付费墙/下载限制。
- CLI `search --backend cnki` 会保存一个带 `live_access_not_enabled` 的 SearchSession，便于后续报告桥接或人工追踪；仍不会访问 CNKI。
- 可见浏览器 smoke 拒绝 `fsso.cnki.net` / `login.cnki.net` 等登录入口；登录和验证码只能由用户在可见浏览器里手动完成。

如果你已经在浏览器里手动下载了 CNKI 文件，可以用本地归档命令纳入统一命名和 artifact 输出：

```bash
vpnsci-sustech cnki-download --local-file "./paper.caj" --title "文献标题" --first-author "张三" --cnki-id "CNKIID" --filename-policy title_author
```

该命令只读取本地文件，不访问 CNKI。PDF 会尝试提取全文，成功时标记为 `text_extracted=true`；如果 PDF 无法解析，会保留文件并标记未提取全文。CAJ/CAJX/NH/KDH 会保存为 `source_file`，并标记 `text_extracted=false`。

MCP 也有对应的 `download_cnki_artifact(local_file=...)` 工具，并支持 `filename_policy/filename_template` 覆盖本次归档命名。

如果要做真实下载 smoke，必须显式给 `--live --confirm-live-access`，并建议限制输出目录：

```bash
vpnsci-sustech cnki-download --detail-url "https://kns.cnki.net/kcms2/article/abstract?filename=..." --live --confirm-live-access --output ~/.vpnsci-sustech/papers/cnki --prefer pdf --filename-policy title_author
```

该路径只在可见浏览器中打开用户指定的 CNKI 详情页，从当前页面已有下载链接触发一次下载，并等待 `.pdf/.caj/.cajx/.nh/.kdh` 文件完成。命令开始时会提示下载过程可能触发验证码/安全验证。无验证码时可自动点击下载、等待落盘并归档；如果点击下载后跳到 `bar.cnki.net` 验证页，会进入等待窗口，用户在可见浏览器中人工完成后自动继续检测落盘并归档，成功 note 会标注 `resumed_after_captcha`；超时返回 `captcha_timeout`。若页面是登录页、未知页，或没有可用下载链接，会停止或报错；不会自动处理账号、验证码、DRM、付费限制。

批量 CNKI 下载必须同样显式确认，并默认走逐篇串行保守控制：

```bash
vpnsci-sustech cnki-batch-download "./cnki-items.jsonl" --live --confirm-live-access \
  --output ~/.vpnsci-sustech/papers/cnki \
  --min-interval 20 --cooldown-every 5 --cooldown-seconds 120 \
  --max-consecutive-failures 1 --state-file ~/.vpnsci-sustech/cache/cnki/batch/state.json --resume
```

输入文件可用 JSONL，每行包含 `detail_url/title/first_author/cnki_id`，也可每行只放一个详情页 URL。批量过程会写状态 JSON；`--resume` 会跳过已成功或已失败条目，从 pending 条目继续。连续验证码超时或下载失败达到阈值时停止本轮，避免继续刷请求。MCP 对应 `download_cnki_batch_artifacts(items=[...], live=true, confirm_live_access=true, ...)`。

如果只是想检查 CNKI smoke 将做什么，可先跑 dry-run：

```bash
vpnsci-sustech cnki-smoke --query "钙钛矿" --limit 1
```

默认 dry-run 不打开浏览器、不访问 CNKI。真实可见浏览器 smoke 需要显式 `--live --confirm-live-access`；`cnki-smoke` 仍只做搜索页/详情页快照解析，不下载文件、不提交账号密码、不绕过验证码，遇登录/验证码会暂停并返回状态。

如果已经保存了 CNKI 详情页 HTML/page source，可离线解析元数据：

```bash
vpnsci-sustech cnki-detail --url-or-id ABC123 --html-file "./detail.html"
```

MCP 对应 `get_cnki_paper_detail(url_or_id, html=.../html_file=...)`。未提供 HTML 时返回 `live_access_not_enabled`，不会主动访问 CNKI。

如果保存的是 CNKI 搜索结果页 HTML，可离线解析并保存标准 `SearchSession`：

```bash
vpnsci-sustech cnki-search-html --query "钙钛矿" --html-file "./search.html" --limit 3
```

MCP 对应 `search_cnki_from_html(query, html=.../html_file=...)`。该路径只读本地 HTML，遇登录/验证码页会返回分类错误，不会自动重试或联网。

CAJ/CAJX 转 PDF 是可选外部命令，默认关闭：

```bash
vpnsci-sustech config-cmd --cnki-convert-caj-to-pdf true \
  --cnki-caj-converter-command "caj2pdf convert {input} -o {output}"
```

项目不会安装或捆绑第三方转换器。转换成功时会增加 `converted_pdf` artifact；转换失败时保留原始 CAJ/CAJX，并在 note 中标注失败。

## 4.5.1 完整 `paper-search-pro` 和 seed-only HTML 预览有什么区别？

区别很大：

- **完整专业调研 / `mode="full"`**：目标是上游 `paper-search-pro` 的完整工作流，包含多源扩展检索、query planning、source routing、相关性分级、RCS / PRISMA / 多格式导出。
- **seed-only 预览 / `mode="seed_preview"`**：把当前 `SearchSession` 里的已有结果渲染成 HTML，适合“先扫一眼刚才这批结果”。

seed preview 会生成主题图景和轻量 PRISMA-S disclosure，避免报告页面空白；但它不会做完整多源扩展、完整 PRISMA-S 审计或并行相关性分级。

## 4.5.2 完整专业调研什么时候需要我选择？

完整专业调研需要 Agent 环境支持相关性分级。若当前 Agent 不支持并行分类，工具会让你明确选择：

1. 改走 `seed_preview` 快速 HTML 报告；
2. 由主 Agent 串行分类（更慢，报告会说明没有使用并行分类）；
3. 暂停，等支持并行分类的环境再继续。

不会把 seed preview 当作完整专业调研交付。

## 4.6 报告工具的数据和配置保存在哪里？

报告工具会在用户目录准备本地运行副本：

```text
~/.vpnsci-sustech/tools/paper-search-pro
```

可以用下面命令安装 / 刷新：

```bash
vpnsci-sustech report-tools install --force
```

这样做有两个目的：

- 源码仓不产生报告、缓存、临时文件；
- API key 只进入用户本地配置，不进入 git

## 5. WebVPN session 会过期吗？

会过期，通常几小时到一天（取决于学校设置）。过期后需要重新登录：

```bash
vpnsci-sustech login --force
```

可以在出门前运行 `vpnsci-sustech login` 预先登录保存 cookies。如果 session 过期，Open Access 和 arXiv 的论文仍然可以正常获取。

## 6. 浙大为什么不在列表里？

浙大的 WebVPN 使用动态密钥方案（登录后从 `/user/info` API 获取密钥），与其他学校的静态密钥不同。目前 vpnsci-sustech 只支持静态密钥的学校，动态密钥支持计划在未来版本中添加。

## 7. 加密密钥是怎么来的？

大部分学校使用默认密钥 `wrdvpnisthebest!`。部分学校使用自定义密钥，这些数据来自开源项目 `lcandy2/webvpn-converter`。如果你的学校不在列表中但你知道它的密钥，可以手动编辑 `~/.vpnsci-sustech/config.json` 设置 `webvpn_base_url`。

## 8. 需要安装什么环境？

- Python >= 3.10
- Chrome 浏览器（WebVPN CAS 登录需要）
- 安装命令：`pip install -e .`
- 注册到 Claude Code：`claude mcp add vpnsci-sustech -- vpnsci-sustech-mcp`

## 9. 这个 fork 和上游 `vpnsci` 有什么区别？

当前仓库是独立 fork，发布名和包名已区分：

- 项目名：`vpnsci-sustech`
- Python 包名：`vpnsci_sustech`
- CLI 命令：`vpnsci-sustech`
- MCP 命令：`vpnsci-sustech-mcp`

它主要用于保留 fork 内的站点适配和 SUSTech / CARSI 相关行为，不影响上游 `vpnsci` 的命名空间。

## 10. Phase 2 不是已经加了 browser / CDP / `curl_cffi` 吗，为什么还不直接说“全面打通”？

因为当前仓库区分：

1. **代码里已有适配骨架**
2. **固定样本已验证**
3. **产品层真实可稳定可用**

这三件事不是一回事。

目前更准确的状态是：

- Springer：已验证 working，且当前 direct path 已可保存固定样本 PDF
- Wiley：搜索与获取已可闭环，但搜索层当前依赖 fallback
- ScienceDirect：search 与 article HTML/fulltext 已可用，并可生成本地可解析 PDF；但原版 publisher PDF 仍未打通

也就是说，当前不会因为“代码里有后备路径”就把 README 写成“站点已全面支持”。
