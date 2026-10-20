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
        .section-header {
            font-size: 15px;
            font-weight: 600;
            color: #555;
            margin: 20px 0 12px 0;
            padding: 8px 12px;
            background: #f0f2f5;
            border-radius: 4px;
            border-left: 3px solid #667eea;
        }
        .article.academic {
            border-left-color: #667eea;
        }
        .article.non-academic {
            border-left-color: #10b981;
        }
        .article.minimal {
            padding: 10px 14px;
            opacity: 0.85;
        }
        .article.minimal .article-title {
            font-size: 14px;
            font-weight: 500;
            margin: 0;
        }
        .article-authors {
            font-size: 12px;
            color: #555;
            margin-bottom: 6px;
            line-height: 1.5;
        }
        .article-abstract {
            font-size: 12px;
            color: #444;
            margin-bottom: 10px;
            line-height: 1.5;
            padding: 8px;
            background: #f8f9fa;
            border-radius: 4px;
            border-left: 2px solid #ddd;
        }
        .abstract-text {
            color: #555;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AI学术文章摘要</h1>
            <div class="meta">{{ date_str }} | {{ articles|length }} 篇文章</div>
        </div>

        <div class="content">
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

        # 排序：学术期刊优先，HBS/MIT放最后
        sorted_articles = self._sort_articles(articles)

        # Simple template rendering without Jinja2 dependency
        html_content = self._render_template(
            date_str=date_str,
            articles=sorted_articles
        )

        return html_content

    def _sort_articles(self, articles: List[Article]) -> List[Article]:
        """排序文章：学术期刊在前，HBS/MIT在后"""
        academic = []
        non_academic = []

        for article in articles:
            source = (article.author or '').strip()
            if source in ('HBS Review', 'MIT SMR'):
                non_academic.append(article)
            else:
                academic.append(article)

        return academic + non_academic

    def _is_academic(self, article: Article) -> bool:
        """判断是否为学术期刊文章"""
        source = (article.author or '').strip()
        return source not in ('HBS Review', 'MIT SMR')

    def _render_template(self, date_str: str, articles: List[Article]) -> str:
        """简单的模板渲染"""
        template = self.template

        # Replace date and count
        template = template.replace('{{ date_str }}', date_str)
        template = template.replace('{{ articles|length }}', str(len(articles)))

        # Generate articles HTML
        articles_html = ""

        # 学术期刊部分
        academic_articles = [a for a in articles if self._is_academic(a)]
        non_academic_articles = [a for a in articles if not self._is_academic(a)]

        if academic_articles:
            full_count = sum(1 for a in academic_articles if a.content and len(a.content) >= 50)
            minimal_count = len(academic_articles) - full_count
            header_text = '学术期刊'
            if minimal_count > 0:
                header_text += f' ({full_count}篇完整 / {minimal_count}篇仅标题)'
            articles_html += f'<div class="section-header">{header_text}</div>'
            for i, article in enumerate(academic_articles, 1):
                articles_html += self._render_academic_article(article, i)

        if non_academic_articles:
            articles_html += '<div class="section-header" style="margin-top: 24px;">商业评论</div>'
            for i, article in enumerate(non_academic_articles, 1):
                articles_html += self._render_non_academic_article(article, i)

        # Replace articles placeholder
        start_marker = '<div class="content">'
        end_marker = '</div>\n\n        <div class="footer">'

        start_idx = template.find(start_marker) + len(start_marker)
        end_idx = template.find(end_marker)

        template = template[:start_idx] + articles_html + template[end_idx:]

        return template

    def _render_minimal_article(self, article: Article, index: int) -> str:
        """极简渲染：只有标题和链接（用于无法获取内容的文章）"""
        return f"""<div class="article academic minimal">
            <h2 class="article-title">
                <a href="{article.url}" target="_blank">{index}. {self._escape_html(article.title)}</a>
            </h2>
            <div class="article-meta">{self._escape_html(article.author) if article.author else ''} | <a href="{article.url}" target="_blank">查看原文</a></div>
        </div>"""

    def _render_academic_article(self, article: Article, index: int) -> str:
        """渲染学术期刊文章：标题 -> authors -> abstract -> AI总结"""
        # 判断是否有足够内容
        has_content = article.content and len(article.content) >= 50
        has_summary = article.summary and len(article.summary) > 20

        # 如果既没有content也没有summary，简化为只显示标题和链接
        if not has_content and not has_summary:
            return self._render_minimal_article(article, index)

        # 构建AI总结部分
        summary_html = ''
        if article.summary:
            processed_summary = self._process_summary(article.summary)
            summary_html = f'<div class="summary-section"><div class="summary-content">{processed_summary}</div></div>'

        # Authors行
        authors_html = ''
        if article.authors:
            authors_html = f'<div class="article-authors"><strong>Authors:</strong> {self._escape_html(article.authors)}</div>'

        # Abstract行（原始内容，通常是英文摘要）
        abstract_html = ''
        if article.content and len(article.content) > 50:
            # 取前2000字符作为abstract显示，避免过长
            abstract_text = article.content[:2000]
            if len(article.content) > 2000:
                abstract_text += '...'
            abstract_html = f'<div class="article-abstract"><strong>Abstract:</strong> <span class="abstract-text">{self._escape_html(abstract_text)}</span></div>'

        # Meta行：来源 + 原文链接
        meta_parts = []
        if article.author:
            meta_parts.append(self._escape_html(article.author))
        meta_parts.append(f'<a href="{article.url}" target="_blank">查看原文</a>')
        meta_line = ' | '.join(meta_parts)

        return f"""<div class="article academic">
            <h2 class="article-title">
                <a href="{article.url}" target="_blank">{index}. {self._escape_html(article.title)}</a>
            </h2>
            <div class="article-meta">{meta_line}</div>
            {authors_html}
            {abstract_html}
            {summary_html}
        </div>"""

    def _render_non_academic_article(self, article: Article, index: int) -> str:
        """渲染非学术文章（HBS/MIT）：保持原有格式"""
        has_summary = article.summary and len(article.summary) > 20

        # Build meta line
        meta_parts = []
        if article.author:
            meta_parts.append(self._escape_html(article.author))
        meta_parts.append(f'<a href="{article.url}" target="_blank">查看原文</a>')
        meta_line = ' | '.join(meta_parts)

        # Build summary section
        if has_summary:
            processed_summary = self._process_summary(article.summary)
            summary_html = f'<div class="summary-section"><div class="summary-content">{processed_summary}</div></div>'
        else:
            summary_html = ''

        return f"""<div class="article non-academic">
            <h2 class="article-title">
                <a href="{article.url}" target="_blank">{index}. {self._escape_html(article.title)}</a>
            </h2>
            <div class="article-meta">{meta_line}</div>
            {summary_html}
        </div>"""

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

    # Test articles with mixed sources
    test_articles = [
        Article(
            title="Deep Learning for NLP: A Comprehensive Survey",
            url="https://example.com/paper1",
            time="2024-01-15",
            author="JFE",
            authors="Zhang, Y., Wang, X., Li, M.",
            content="This paper provides a comprehensive survey of deep learning approaches for natural language processing. We cover various architectures including Transformers, RNNs, and CNNs applied to NLP tasks.",
            summary="""## 研究问题
本文系统性地回顾了深度学习在自然语言处理领域的应用和发展。

## 研究方法
通过文献调研，分析了Transformer、RNN、CNN等架构在NLP任务中的应用。

## 主要发现
• Transformer架构已成为主流
• 预训练模型显著提升性能
• 大语言模型展现涌现能力"""
        ),
        Article(
            title="How to Move from AI Experimentation to AI Transformation",
            url="https://hbr.org/article",
            time="2024-01-15",
            author="HBS Review",
            authors="",
            content="",
            summary="""## 文章概要
本文探讨了企业如何从AI实验走向AI转型。

## 主要发现
• 需要高层支持
• 数据基础设施是关键
• 人才战略决定成败"""
        ),
        Article(
            title="Attention Is All You Need",
            url="https://example.com/paper2",
            time="2017-06-12",
            author="ISR",
            authors="Vaswani, A., Shazeer, N., Parmar, N.",
            content="The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder.",
            summary="""## 研究问题
提出一种全新的神经网络架构Transformer，完全基于注意力机制。

## 主要发现
• 自注意力机制比RNN更高效
• 可以更好地建模长距离依赖
• 在机器翻译任务上取得SOTA结果"""
        ),
        Article(
            title="Audit Yourself to Get More From GenAI",
            url="https://sloanreview.mit.edu/article",
            time="2024-01-15",
            author="MIT SMR",
            authors="",
            content="",
            summary="""## 文章概要
本文讨论了如何通过自我审计来更好地利用生成式AI。

## 主要发现
• 审计流程需要重新设计
• 人机协作是关键"""
        ),
    ]

    generator = HTMLGenerator(config)
    html = generator.generate(test_articles)

    output_path = generator.save(html, "test_summary.html")
    print(f"测试HTML已生成: {output_path}")
