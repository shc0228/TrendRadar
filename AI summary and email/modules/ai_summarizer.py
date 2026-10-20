"""
使用Kimi (kimi-k3) 模型生成文章摘要
"""
import os
import asyncio
from pathlib import Path
from typing import Dict, List

from anthropic import Anthropic
from dotenv import load_dotenv

# Import Article from html_parser
from modules.html_parser import Article

load_dotenv(Path(__file__).parent.parent / '.env')


class AISummarizer:
    """AI摘要生成器 - 使用Kimi (kimi-k3) 模型"""

    def __init__(self, config: Dict):
        self.config = config
        ai_config = config.get('ai', {})

        # 从配置或环境变量获取API key
        api_key = ai_config.get('api_key') or os.getenv('KIMI_API_KEY')
        if not api_key:
            raise ValueError("未设置KIMI_API_KEY，请在本地.env文件中配置或设置环境变量")

        self.client = Anthropic(
            api_key=api_key,
            base_url=ai_config.get('api_base', 'https://api.kimi.com/coding/')
        )
        self.model = ai_config.get('model', 'kimi-k3')

    async def summarize_articles(self, articles: List[Article]) -> List[Article]:
        """批量生成文章摘要"""
        results = []

        for i, article in enumerate(articles, 1):
            print(f"  [{i}/{len(articles)}] 处理: {article.title[:50]}...")

            # 跳过无法获取内容的文章
            if not article.content or len(article.content) < 50:
                print(f"      ⚠ 内容不足，跳过AI摘要")
                article.summary = ""
                results.append(article)
                continue

            try:
                summary = await self._summarize_single(article)
                article.summary = summary
                print(f"      ✓ 摘要完成")
            except Exception as e:
                print(f"      ✗ 摘要失败: {e}")
                article.summary = ""

            results.append(article)

            # 避免API限流
            await asyncio.sleep(0.5)

        return results

    async def _summarize_single(self, article: Article) -> str:
        """生成单篇文章摘要"""
        ai_config = self.config.get('ai', {})

        prompt = ai_config.get('summary_prompt',
            """请分析以下学术论文文章，提供结构化摘要（中文）：

标题：{title}
内容：{content}

请按以下格式输出：
## 文章概要
（用两句话概括文章的核心内容）

## 研究问题
（简要描述文章要解决的核心问题）

## 研究方法
（描述文章使用的研究方法、数据来源、分析方法等）

## 主要发现
（列出文章的主要研究发现，每条用•开头）
""").format(title=article.title, content=article.content[:5000])

        # 同步调用Anthropic兼容客户端
        response = self.client.messages.create(
            model=self.model,
            system="你是一个学术研究助手，擅长分析学术论文并提取关键信息。请用中文输出结构化的学术摘要。",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=ai_config.get('temperature', 0.7),
            max_tokens=ai_config.get('max_tokens', 8192),
            timeout=ai_config.get('timeout', 120)
        )

        # kimi-k3默认开启thinking，content含thinking和text两种块，只取text
        return "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()


# Test the module directly
if __name__ == '__main__':
    import yaml

    # Load config
    config_path = Path(__file__).parent.parent / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    async def test():
        # Create test article
        test_article = Article(
            title="Deep Learning for Natural Language Processing: A Survey",
            url="https://arxiv.org/abs/2401.00001",
            content="""This paper provides a comprehensive survey of deep learning approaches
            for natural language processing. We cover various architectures including
            Transformers, RNNs, and CNNs applied to NLP tasks. The paper discusses
            pre-training methods like BERT and GPT, fine-tuning strategies, and recent
            advances in large language models. We also analyze challenges and future
            directions in the field."""
        )

        summarizer = AISummarizer(config)
        print("测试AI摘要生成...")

        test_article.summary = await summarizer._summarize_single(test_article)
        print(f"\n原始标题: {test_article.title}")
        print(f"\nAI摘要:\n{test_article.summary}")

    from pathlib import Path
    import asyncio
    asyncio.run(test())
