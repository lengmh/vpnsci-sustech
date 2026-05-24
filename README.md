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

如果你的 MCP 宿主支持直接填写 `command` / `args`，推荐使用：

```toml
[mcp_servers.vpnsci_sustech]
type = "stdio"
command = "python"
args = ["-m", "vpnsci_sustech.mcp_server"]
```

如果你是从源码仓库安装，推荐先执行：

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

建议至少验证以下三组检索：

- Springer: `support-vector networks`
- Wiley: `synergetic spin crossover fluorescence one-dimensional hybrid complexes`
- ScienceDirect: `filtering antenna with radiation and filtering functions for wireless applications`

如果宿主支持为 MCP 工具传参，建议分别指定：

- `backend="springerlink"`
- `backend="wiley"`
- `backend="sciencedirect"`

这样可以直接验证当前 Phase 2 的 publisher-native search 路线，而不是只测默认 Semantic Scholar 路线。

### 通过命令行

```bash
# 安装
pip install git+https://github.com/lengmh/vpnsci-sustech.git

# 配置学校
vpnsci-sustech config-cmd --school 你的学校

# 搜索论文
vpnsci-sustech search "perovskite solar cells"

# 获取论文全文
vpnsci-sustech fetch "10.1038/s41566-024-01234-5"

# 批量获取
vpnsci-sustech batch dois.txt --output ./papers

# 查看支持的学校
vpnsci-sustech schools
```

## SUSTech / CARSI 特殊支持

这个 fork 针对 SUSTech 做了独立适配，支持直接配置 CARSI 学校名，适合 Southern University of Science and Technology 场景。

如果通过 MCP 使用，Agent 可以调用对应配置工具完成初始化；如果通过命令行使用，可先完成登录，再执行搜索和获取操作。

## 当前站点支持说明

- IEEE Xplore：可获取全文，支持 PDF 下载
- Springer：可获取全文，搜索和 PDF 下载已验证可用
- Nature：可获取全文
- Wiley Online Library：当前已可做检索并获取全文；搜索在站内执行受限时会回退到元数据搜索
- ScienceDirect：当前已可做检索、全文提取，并可生成本地可解析 PDF；原版 publisher PDF 仍可能失败

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

- [webvpn-converter](https://github.com/lcandy2/webvpn-converter) — 学校配置数据
- [Tuna-Erha-Bot](https://github.com/Konano/Tuna-Erha-Bot) — WebVPN 加密算法
- [ZJUWebVPN](https://github.com/eWloYW8/ZJUWebVPN) — 动态密钥方案
- [CASPaperTunneling](https://github.com/qiyang-ustc/CASPaperTunneling) — CAS 认证流程

## License

[MIT](LICENSE)
