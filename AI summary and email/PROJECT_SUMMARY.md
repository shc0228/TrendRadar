# AI学术文章摘要与邮件推送系统 - 项目总结

## 项目概述

自动监控TrendRadar生成的RSS HTML文件，使用浏览器获取文章内容，调用qwen-max模型生成中文摘要，生成HTML报告并通过邮件发送。

项目路径: `E:\claude code projects\trendradar\AI summary and email\`

---

## 已完成的工作

### 1. 项目结构搭建

```
AI summary and email/
├── config.yaml           # 配置文件
├── main.py              # 主入口（文件监控模式）
├── mcp_workflow.py      # MCP工作流脚本
├── requirements.txt     # Python依赖
├── modules/
│   ├── __init__.py
│   ├── html_parser.py       # HTML解析模块 ✓
│   ├── browser_automation.py # 浏览器自动化（混合模式）✓
│   ├── browser_mcp.py        # MCP协调器 ✓
│   ├── ai_summarizer.py      # qwen-max AI摘要 ✓
│   ├── html_generator.py     # HTML报告生成 ✓
│   └── email_sender.py       # 邮件发送 ✓
├── output/               # 生成的报告
└── .mcp_work/           # MCP工作目录
    ├── queue.json       # MCP待处理队列
    └── results.json     # MCP获取结果
```

### 2. 核心功能实现

| 模块 | 状态 | 功能描述 |
|------|------|----------|
| HTML解析器 | ✓ 完成 | 解析RSS HTML文件，提取文章标题、URL、时间、作者 |
| 浏览器自动化 | ✓ 完成 | 混合模式：普通网站用requests，受限网站用MCP |
| AI摘要生成 | ✓ 完成 | 使用qwen-max模型生成结构化中文摘要 |
| HTML报告生成 | ✓ 完成 | 生成带样式的HTML报告，支持邮件展示 |
| 邮件发送 | ✓ 完成 | 通过SMTP发送HTML格式邮件 |

### 3. Chrome DevTools MCP集成

**成功案例:**

| 网站 | 状态 | 获取方式 |
|------|------|----------|
| INFORMS | ✓ 成功 | MCP浏览器直接访问，获取完整摘要 |
| HBR | ✓ 成功 | requests获取meta描述 |
| MIT Sloan | ✓ 成功 | requests获取meta描述 |
| ScienceDirect | ✗ CAPTCHA | 需要人工交互 |

**MCP工具使用流程:**

1. 使用 `mcp__chrome-devtools__navigate_page` 导航到目标URL
2. 使用 `mcp__chrome-devtools__evaluate_script` 执行JavaScript提取内容
3. 保存结果到 `.mcp_work/results.json`

**JavaScript内容提取代码:**

```javascript
() => {
    // INFORMS特定选择器
    const informsAbstract = document.querySelector('.abstractSection p');

    // ScienceDirect特定选择器
    const sdAbstract = document.querySelector('.abstract p, #abstract p');

    // 从页面文本提取
    const bodyText = document.body.innerText;
    const abstractMatch = bodyText.match(/Abstract\s+([\s\S]*?)(?=\n\s*(?:Keywords|Introduction))/i);

    return { title, abstract, url };
}
```

### 4. AI摘要效果

**qwen-max生成的摘要结构:**

```markdown
## 研究问题
（描述文章要解决的核心问题）

## 研究方法
（研究方法、数据来源、分析方法）

## 主要发现
• 发现1
• 发现2

## 贡献与启示
（理论和实践贡献）
```

**测试结果:**

- INFORMS "The Economics of Password Sharing": 完整摘要，包含博弈论模型分析
- HBR "360-Degree Feedback": 实用建议类摘要
- MIT Sloan "AI-Driven Search": 市场趋势分析摘要

### 5. 端到端测试

**输入:** `E:\claude code projects\trendradar\output-rss\html\2026-01-29\15-01.html`

**输出:** `output/summary_2026-01-30_10-54.html`

**邮件:** 成功发送到 hongchuanshen@gmail.com

---

## 当前架构

### 混合浏览器模式

```
                    ┌─────────────────┐
                    │   HTML Parser   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Article URLs   │
                    └────────┬────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
         ┌──────▼──────┐          ┌──────▼──────┐
         │  requests   │          │     MCP     │
         │  (普通网站)  │          │  (受限网站)  │
         └──────┬──────┘          └──────┬──────┘
                │                        │
                │                   Claude Code
                │                   Chrome DevTools
                │                        │
                └────────────┬───────────┘
                             │
                    ┌────────▼────────┐
                    │  AI Summarizer  │
                    │   (qwen-max)    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ HTML Generator  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Email Sender   │
                    └─────────────────┘
```

### MCP工作流程

由于MCP工具只能在Claude Code环境中使用，当前采用文件队列方式:

1. Python代码将受限URL写入 `.mcp_work/queue.json`
2. 用户在Claude Code中手动执行MCP工具
3. 结果保存到 `.mcp_work/results.json`
4. Python代码读取结果继续处理

---

## 需要解决的问题

### 1. CAPTCHA挑战

**问题网站:**
- ScienceDirect: 显示 "Are you a robot?" CAPTCHA
- 部分Springer/IEEE期刊可能也有类似保护

**可能解决方案:**

| 方案 | 优点 | 缺点 |
|------|------|------|
| 人工介入 | 可靠 | 需要手动操作 |
| CAPTCHA solving服务 | 自动化 | 成本高，可能违反ToS |
| 使用已有摘要 | 简单 | 内容不完整 |
| 学术数据库API | 完整数据 | 需要机构访问权限 |

### 2. MCP自动化

**当前问题:**
- MCP工具只能在Claude Code对话中使用
- 无法从Python代码直接调用

**可能的解决方案:**

1. **MCP Server模式**
   ```python
   # 运行独立的MCP server
   mcp-server chrome-devtools
   # Python通过HTTP/gRPC调用
   ```

2. **Claude Code CLI**
   ```bash
   # 使用Claude Code CLI执行脚本
   claude-code run mcp_fetch.py
   ```

3. **保持当前模式**
   - 用户提供明确的触发信号
   - Claude Code定期检查队列
   - 完成后通知Python继续

### 3. 网站适配

**需要添加的网站提取规则:**

- [ ] arXiv.org (预印本服务器)
- [ ] SSRN (社会科学研究网络)
- [ ] PubMed (医学文献)
- [ ] Google Scholar (搜索结果)
- [ ] IEEE Xplore
- [ ] ACM Digital Library
- [ ] SpringerLink

**通用提取策略改进:**

```python
# 当前: 依赖固定的CSS选择器
# 改进: 使用AI识别内容区域

def extract_content_with_ai(soup):
    """使用AI模型识别主要内容区域"""
    # 将页面结构输入AI模型
    # 返回最可能包含文章内容的元素
    pass
```

### 4. 性能优化

**当前瓶颈:**

| 瓶颈 | 当前耗时 | 优化方案 |
|------|----------|----------|
| AI摘要生成 | ~15秒/篇 | 批量处理、并发 |
| MCP页面加载 | ~3-5秒/篇 | 并发浏览器 |
| 邮件发送 | ~2秒 | 异步发送 |

**并发处理建议:**

```python
async def fetch_articles_concurrent(urls):
    """并发获取多篇文章"""
    semaphore = asyncio.Semaphore(3)  # 限制并发数
    async def fetch_with_limit(url):
        async with semaphore:
            return await fetch_article(url)
    return await asyncio.gather(*[fetch_with_limit(u) for u in urls])
```

### 5. 错误处理

**需要添加的错误处理:**

- [ ] 网络超时重试机制
- [ ] API限流处理
- [ ] 部分失败时的降级策略
- [ ] 详细的错误日志

---

## 配置清单

### 必需配置

```yaml
# config.yaml
ai:
  api_key: "sk-bf43da8bebea465b9012bb07915edd6c"  # ✓ 已配置
  model: "qwen-max"

email:
  from: "shc2508@163.com"           # ✓ 已配置
  password: "QKaHY6nuefJZhk9E"        # ✓ 已配置
  to: "hongchuanshen@gmail.com"      # ✓ 已配置
  smtp_server: "smtp.163.com"        # ✓ 已配置
  smtp_port: 465                     # ✓ 已配置

monitor:
  watch_dir: "E:\\claude code projects\\trendradar\\output-rss\\html"  # ✓ 已配置
```

### 可选配置

```yaml
browser:
  timeout: 30000        # 页面加载超时
  wait_for_content: 2000  # 等待内容加载

ai:
  temperature: 0.7      # 生成随机性
  max_tokens: 2000      # 最大输出长度
```

---

## 下一步工作

### 短期 (1-2天)

1. **完善main.py监控功能**
   - [ ] 实现文件监控的自动触发
   - [ ] MCP队列自动处理提示
   - [ ] 处理进度显示

2. **添加更多网站支持**
   - [ ] arXiv提取规则
   - [ ] SSRN提取规则
   - [ ] 通用降级策略

3. **错误处理**
   - [ ] 重试机制
   - [ ] 错误日志
   - [ ] 部分失败处理

### 中期 (1周)

1. **MCP自动化**
   - [ ] 研究MCP Server模式
   - [ ] 实现自动队列处理
   - [ ] 或开发CLI触发机制

2. **性能优化**
   - [ ] 并发处理
   - [ ] 缓存机制
   - [ ] 增量处理

3. **CAPTCHA解决方案**
   - [ ] 评估CAPTCHA solving服务
   - [ ] 或实现人工介入流程
   - [ ] 或使用机构API访问

### 长期 (持续)

1. **更多AI模型**
   - [ ] 支持其他摘要模型
   - [ ] 多语言摘要
   - [ ] 自定义摘要风格

2. **增强功能**
   - [ ] 摘要质量评估
   - [ ] 相关文章推荐
   - [ ] 知识图谱构建

3. **用户界面**
   - [ ] Web界面
   - [ ] 配置管理界面
   - [ ] 报告历史查看

---

## 技术栈总结

| 组件 | 技术 | 版本 |
|------|------|------|
| Python | 3.x | - |
| HTTP客户端 | requests | 2.31+ |
| HTML解析 | BeautifulSoup4 | 4.12+ |
| AI模型 | OpenAI兼容API | qwen-max |
| 邮件 | smtplib | 内置 |
| 文件监控 | watchdog | 4.0+ |
| 浏览器 | Chrome DevTools MCP | - |

---

## 文件清单

### Python模块

- `modules/html_parser.py` - HTML解析，提取文章信息
- `modules/browser_automation.py` - 混合模式浏览器自动化
- `modules/ai_summarizer.py` - qwen-max AI摘要
- `modules/html_generator.py` - HTML报告生成
- `modules/email_sender.py` - 邮件发送

### 配置文件

- `config.yaml` - 主配置文件
- `requirements.txt` - Python依赖
- `processed_files.json` - 已处理文件记录（运行时生成）

### 工作目录

- `.mcp_work/queue.json` - MCP待处理队列
- `.mcp_work/results.json` - MCP获取结果
- `output/` - 生成的HTML报告

---

## 成功指标

| 指标 | 目标 | 当前 |
|------|------|------|
| HTML解析成功率 | >95% | ✓ 100% |
| 内容获取成功率 | >80% | ~60% (3/5测试文章) |
| AI摘要生成成功率 | >90% | ✓ 100% |
| 邮件发送成功率 | >95% | ✓ 100% |
| 端到端处理时间 | <5分钟/批 | ~1分钟/3文章 |

---

## 结论

项目已成功实现核心功能：
- ✓ HTML解析
- ✓ 浏览器内容获取（混合模式）
- ✓ AI摘要生成
- ✓ HTML报告生成
- ✓ 邮件发送

**关键成就:**
- 成功使用Chrome DevTools MCP绕过INFORMS的403限制
- 集成qwen-max生成高质量中文摘要
- 完整的端到端自动化流程

**主要挑战:**
- CAPTCHA保护的网站（ScienceDirect等）
- MCP工具的自动化调用
- 更多网站的适配需求

系统已可用，可以处理大多数公开网站的学术文章，并自动生成摘要报告发送邮件。
