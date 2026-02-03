"""
AI学术文章摘要与邮件推送系统 - MCP版本

使用Chrome DevTools MCP获取文章内容，绕过反爬虫限制
"""
import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import yaml
from openai import OpenAI

# Import local modules
from modules.html_parser import HTMLParser, Article
from modules.html_generator import HTMLGenerator
from modules.email_sender import EmailSender


class ArticleFetcherMCP:
    """
    文章内容获取器 - 使用MCP工具

    注意: 实际MCP工具调用需要通过Claude Code界面执行
    此类提供完整的JavaScript代码和执行流程
    """

    def __init__(self, config: Dict):
        self.config = config

    def get_extraction_js(self) -> str:
        """返回用于提取文章内容的JavaScript代码"""
        return r"""
        () => {
            const results = {};

            // 获取标题
            const titleElem = document.querySelector('h1, .title-text, [class*="title"]');
            results.title = titleElem ? titleElem.innerText.trim() : document.title;

            // 获取摘要
            let abstract = '';

            // INFORMS特定选择器
            const informsAbstract = document.querySelector('.abstractSection p');
            if (informsAbstract) {
                abstract = informsAbstract.innerText.trim();
            }

            // ScienceDirect特定选择器
            if (!abstract) {
                const sdAbstract = document.querySelector('.abstract p, #abstract p');
                if (sdAbstract) {
                    abstract = sdAbstract.innerText.trim();
                }
            }

            // 通用选择器
            if (!abstract) {
                const selectors = [
                    '[class*="abstract"] p',
                    '#abstract p',
                    'h2:contains("Abstract") + p',
                    'h3:contains("Abstract") + p'
                ];
                for (const sel of selectors) {
                    try {
                        const elem = document.querySelector(sel);
                        if (elem && elem.innerText.length > 50) {
                            abstract = elem.innerText.trim();
                            break;
                        }
                    } catch(e) {}
                }
            }

            // 从页面文本中提取（最后手段）
            if (!abstract || abstract.length < 50) {
                const bodyText = document.body.innerText;
                const abstractMatch = bodyText.match(/Abstract\s+([\s\S]*?)(?=\n\s*(?:Keywords|Introduction|1\.|©|DOI|Received))/i);
                if (abstractMatch && abstractMatch[1]) {
                    abstract = abstractMatch[1].trim();
                }
            }

            results.abstract = abstract;
            results.url = window.location.href;
            results.hasContent = abstract.length > 50;

            return JSON.stringify(results);
        }
        """

    async def fetch_article(self, url: str) -> Dict[str, str]:
        """
        获取文章内容

        注意: 此方法需要通过Claude Code的MCP工具执行
        返回的success=false表示需要在Claude Code中执行
        """
        return {
            'success': False,
            'content': '',
            'error': '请使用Claude Code执行MCP工具',
            'js_code': self.get_extraction_js()
        }


class AISummarizer:
    """AI摘要生成器"""

    def __init__(self, config: Dict):
        self.config = config
        ai_config = config.get('ai', {})

        api_key = ai_config.get('api_key') or os.getenv('DASHSCOPE_API_KEY')
        if not api_key:
            raise ValueError("未设置DASHSCOPE_API_KEY")

        self.client = OpenAI(
            api_key=api_key,
            base_url=ai_config.get('api_base', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
        )
        self.model = ai_config.get('model', 'qwen-max')

    async def summarize_articles(self, articles: List[Article]) -> List[Article]:
        """批量生成文章摘要"""
        for i, article in enumerate(articles, 1):
            if not article.content or len(article.content) < 50:
                article.summary = "内容不足，无法生成摘要"
                continue

            try:
                prompt = f"""请分析以下学术论文文章，提供结构化摘要（中文）：

标题：{article.title}
内容：{article.content[:4000]}

请按以下格式输出：
## 研究问题
（简要描述文章要解决的核心问题）

## 研究方法
（描述文章使用的研究方法、数据来源、分析方法等）

## 主要发现
（列出文章的主要研究发现，每条用•开头）

## 贡献与启示
（描述文章的理论/实践贡献和对未来研究的启示）
"""

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "你是一个学术研究助手，擅长分析学术论文并提取关键信息。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.config['ai'].get('temperature', 0.7),
                    max_tokens=self.config['ai'].get('max_tokens', 2000),
                    timeout=self.config['ai'].get('timeout', 120)
                )

                article.summary = response.choices[0].message.content
                print(f"  [{i}/{len(articles)}] ✓ 摘要完成")

            except Exception as e:
                article.summary = f"摘要失败: {str(e)}"
                print(f"  [{i}/{len(articles)}] ✗ 摘要失败: {e}")

            await asyncio.sleep(0.5)

        return articles


async def process_articles_from_html(html_file: str, mcp_fetched_contents: Dict[str, str], config: Dict):
    """
    处理HTML文件中的文章

    Args:
        html_file: HTML文件路径
        mcp_fetched_contents: 通过MCP获取的内容字典 {url: content}
        config: 配置字典
    """
    print(f"\n{'='*60}")
    print(f"处理文件: {Path(html_file).name}")
    print(f"{'='*60}")

    # 1. 解析HTML
    parser = HTMLParser()
    articles = parser.parse_file(html_file)
    print(f"找到 {len(articles)} 篇文章")

    if not articles:
        return

    # 2. 关联MCP获取的内容
    for article in articles:
        if article.url in mcp_fetched_contents:
            article.content = mcp_fetched_contents[article.url]

    # 3. 生成AI摘要
    summarizer = AISummarizer(config)
    print("\n生成AI摘要...")
    articles = await summarizer.summarize_articles(articles)

    # 4. 生成HTML报告
    generator = HTMLGenerator(config)
    html_content = generator.generate(articles, html_file)
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
    output_file = generator.save(html_content, f"summary_{timestamp}.html")
    print(f"\n✓ 报告已保存: {output_file}")

    # 5. 发送邮件
    sender = EmailSender(config)
    sender.send(output_file)

    print("\n✅ 处理完成!")


# MCP工作流程说明
MCP_WORKFLOW_INSTRUCTIONS = """
# MCP工作流程使用说明

由于Chrome DevTools MCP工具只能在Claude Code环境中使用，
请按以下步骤操作：

## 步骤1: 准备文章URL列表

首先运行HTML解析器获取文章URL:

```python
from modules.html_parser import HTMLParser

parser = HTMLParser()
articles = parser.parse_file("path/to/html/file")
urls = [a.url for a in articles]
print(urls)
```

## 步骤2: 使用Chrome DevTools MCP获取内容

在Claude Code中执行以下操作:

1. 打开每个URL:
   - 使用 `mcp__chrome-devtools__navigate_page` 工具

2. 提取内容:
   - 使用 `mcp__chrome-devtools__evaluate_script` 工具
   - 执行以下JavaScript:

```javascript
() => {
    const titleElem = document.querySelector('h1, .title-text');
    const title = titleElem ? titleElem.innerText.trim() : '';

    let abstract = '';
    const informsAbstract = document.querySelector('.abstractSection p');
    if (informsAbstract) {
        abstract = informsAbstract.innerText.trim();
    }

    if (!abstract) {
        const sdAbstract = document.querySelector('.abstract p, #abstract p');
        if (sdAbstract) {
            abstract = sdAbstract.innerText.trim();
        }
    }

    if (!abstract) {
        const bodyText = document.body.innerText;
        const abstractMatch = bodyText.match(/Abstract\\s+([\\s\\S]*?)(?=\\n\\s*(?:Keywords|Introduction))/i);
        if (abstractMatch && abstractMatch[1]) {
            abstract = abstractMatch[1].trim();
        }
    }

    return {
        title: title,
        abstract: abstract,
        url: window.location.href
    };
}
```

## 步骤3: 整合内容并生成摘要

将获取的内容保存为JSON,然后运行:

```python
python mcp_workflow.py
```
"""


def main():
    """主入口"""
    print("=" * 60)
    print("AI学术文章摘要系统 - MCP版本")
    print("=" * 60)
    print(MCP_WORKFLOW_INSTRUCTIONS)

    # 加载配置
    config_path = Path(__file__).parent / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 设置API key
    if config.get('ai', {}).get('api_key'):
        os.environ['DASHSCOPE_API_KEY'] = config['ai']['api_key']

    print("\n配置已加载。请按照上述说明使用MCP工具获取文章内容。")


if __name__ == '__main__':
    main()
