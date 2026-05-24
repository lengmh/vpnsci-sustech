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

默认仍然先走 **Semantic Scholar**。

当前默认策略是：

1. 先尝试 Semantic Scholar 匿名搜索
2. 如果匿名搜索遇到 `429`，且你已配置 `semantic_scholar_api_key`
3. 则自动退回到 API key 搜索

这时**不会**自动切到 Springer / Wiley / ScienceDirect 的 publisher-native search。

如果你想显式验证当前 Phase 2 路线，建议在 MCP / CLI 中明确指定：

- `backend="springerlink"`
- `backend="wiley"`
- `backend="sciencedirect"`

也就是说：

- **默认搜索**：Semantic Scholar 优先
- **显式指定 backend**：走对应 publisher-native search

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
