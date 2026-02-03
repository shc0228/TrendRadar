"""
生成带摘要的HTML文件
"""
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from modules.html_parser import Article


class HTMLGenerator:
    """HTML生成器 - 生成带摘要的HTML报告"""

    def __init__(self, config: Dict):
        self.config = config
        self.template = self._get_template()

    def _get_template(self) -> str:
        """获取HTML模板"""
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI学术文章摘要 - {{ date_str }}</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            margin: 0;
            padding: 16px;
            background: #f5f7fa;
            color: #333;
            line-height: 1.5;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 1px 8px rgba(0,0,0,0.08);
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 16px;
            text-align: center;
        }
        .header h1 {
            margin: 0 0 6px 0;
            font-size: 20px;
        }
        .header .meta {
            font-size: 13px;
            opacity: 0.9;
        }
        .content {
            padding: 16px;
        }
        .article {
            margin-bottom: 16px;
            padding: 14px;
            background: #fafafa;
            border-radius: 6px;
            border-left: 3px solid #667eea;
        }
        .article:last-child {
            margin-bottom: 0;
        }
        .article-title {
            font-size: 16px;
            font-weight: 600;
            margin: 0 0 8px 0;
            color: #1a1a1a;
            line-height: 1.3;
        }
        .article-title a {
            color: inherit;
            text-decoration: none;
        }
        .article-title a:hover {
            text-decoration: underline;
        }
        .article-meta {
            display: flex;
            gap: 10px;
            margin-bottom: 8px;
            font-size: 12px;
            color: #666;
            flex-wrap: wrap;
        }
        .article-meta a {
            color: #667eea;
            text-decoration: none;
        }
        .article-meta a:hover {
            text-decoration: underline;
        }
        .summary-section {
            margin-top: 10px;
        }
        .summary-content {
            font-size: 13px;
            color: #444;
            white-space: pre-wrap;
            line-height: 1.6;
        }
        .summary-content h4 {
            margin: 8px 0 4px 0;
            font-size: 13px;
            color: #333;
            font-weight: 600;
        }
        .summary-content p {
            margin: 0 0 8px 0;
        }
        .footer {
            padding: 12px 16px;
            background: #f8f9fa;
            text-align: center;
            font-size: 12px;
            color: #666;
            border-top: 1px solid #e5e7eb;
        }
        .error-message {
            color: #dc3545;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📚 AI学术文章摘要</h1>
            <div class="meta">{{ date_str }} | {{ articles|length }} 篇文章</div>
        </div>

        <div class="content">
            {% for article in articles %}
            <div class="article">
                <h2 class="article-title">
                    <a href="{{ article.url }}" target="_blank">{{ loop.index }}. {{ article.title }}</a>
                </h2>
                <div class="article-meta">
                    {% if article.author %}{{ article.author }} | {% endif %}
                    <a href="{{ article.url }}" target="_blank">查看原文</a>
                </div>
                {% if article.summary %}
                <div class="summary-section">
                    <div class="summary-content">{{ article.summary }}</div>
                </div>
                {% else %}
                <div class="summary-section">
                    <div class="summary-content error-message">摘要生成中或失败，请稍后查看</div>
                </div>
                {% endif %}
            </div>
            {% endfor %}
        </div>

        <div class="footer">
            由 TrendRadar AI 摘要系统生成 | 基于 qwen-max 模型
        </div>
    </div>
</body>
</html>
"""

    def generate(self, articles: List[Article], source_file: str = "") -> str:
        """生成HTML内容"""
        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d %H:%M')

        # Simple template rendering without Jinja2 dependency
        html_content = self._render_template(
            date_str=date_str,
            articles=articles
        )

        return html_content

    def _render_template(self, date_str: str, articles: List[Article]) -> str:
        """简单的模板渲染"""
        template = self.template

        # Replace date and count
        template = template.replace('{{ date_str }}', date_str)
        template = template.replace('{{ articles|length }}', str(len(articles)))

        # Generate articles HTML
        articles_html = ""
        for i, article in enumerate(articles, 1):
            # Build meta line
            meta_parts = []
            if article.author:
                meta_parts.append(self._escape_html(article.author))
            meta_parts.append(f'<a href="{article.url}" target="_blank">查看原文</a>')
            meta_line = ' | '.join(meta_parts)

            # Build summary section
            if article.summary:
                processed_summary = self._process_summary(article.summary)
                summary_html = f'<div class="summary-section"><div class="summary-content">{processed_summary}</div></div>'
            else:
                summary_html = '<div class="summary-section"><div class="summary-content error-message">摘要生成中或失败，请稍后查看</div></div>'

            article_html = f"""<div class="article">
                <h2 class="article-title">
                    <a href="{article.url}" target="_blank">{i}. {self._escape_html(article.title)}</a>
                </h2>
                <div class="article-meta">{meta_line}</div>
                {summary_html}
            </div>"""

            articles_html += article_html

        # Replace articles placeholder
        start_marker = '<div class="content">'
        end_marker = '</div>\n\n        <div class="footer">'

        start_idx = template.find(start_marker) + len(start_marker)
        end_idx = template.find(end_marker)

        template = template[:start_idx] + articles_html + template[end_idx:]

        return template

    def _process_summary(self, summary: str) -> str:
        """处理摘要内容，转换markdown标记"""
        lines = summary.split('\n')
        result = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Convert ## headers to h4
            if line.startswith('## '):
                content = line[3:].strip()
                result.append(f'<h4>{self._escape_html(content)}</h4>')
            # Convert bullet points
            elif line.startswith('•') or line.startswith('-') or line.startswith('*'):
                content = line[1:].strip()
                result.append(f'<p>• {self._escape_html(content)}</p>')
            else:
                result.append(f'<p>{self._escape_html(line)}</p>')

        return '\n'.join(result)

    def _escape_html(self, text: str) -> str:
        """简单的HTML转义"""
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&#x27;')
        return text

    def save(self, html_content: str, filename: str) -> str:
        """保存HTML文件"""
        output_dir = Path(self.config['output']['dir'])
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return str(output_path)


# Test the module directly
if __name__ == '__main__':
    from pathlib import Path
    import yaml

    # Load config
    config_path = Path(__file__).parent.parent / 'config.yaml'
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    else:
        config = {'output': {'dir': 'output'}}

    # Test articles
    test_articles = [
        Article(
            title="Deep Learning for NLP: A Comprehensive Survey",
            url="https://example.com/paper1",
            time="2024-01-15",
            author="Zhang et al.",
            summary="""## 研究问题
本文系统性地回顾了深度学习在自然语言处理领域的应用和发展。

## 研究方法
通过文献调研，分析了Transformer、RNN、CNN等架构在NLP任务中的应用。

## 主要发现
• Transformer架构已成为主流
• 预训练模型显著提升性能
• 大语言模型展现涌现能力

## 贡献与启示
为NLP研究者提供了全面的技术参考和发展趋势分析。"""
        ),
        Article(
            title="Attention Is All You Need",
            url="https://example.com/paper2",
            time="2017-06-12",
            author="Vaswani et al.",
            summary="""## 研究问题
提出一种全新的神经网络架构Transformer，完全基于注意力机制。

## 研究方法
摒弃循环和卷积，完全使用自注意力机制处理序列数据。

## 主要发现
• 自注意力机制比RNN更高效
• 可以更好地建模长距离依赖
• 在机器翻译任务上取得SOTA结果

## 贡献与启示
Transformer架构成为现代NLP的基石，启发了GPT、BERT等后续工作。"""
        )
    ]

    generator = HTMLGenerator(config)
    html = generator.generate(test_articles)

    output_path = generator.save(html, "test_summary.html")
    print(f"测试HTML已生成: {output_path}")
