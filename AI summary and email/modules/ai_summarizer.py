"""
使用qwen-max模型生成文章摘要
"""
import os
import asyncio
from typing import Dict, List
from openai import OpenAI

# Import Article from html_parser
from modules.html_parser import Article


class AISummarizer:
    """AI摘要生成器 - 使用qwen-max模型"""

    def __init__(self, config: Dict):
        self.config = config
        ai_config = config.get('ai', {})

        # 从配置或环境变量获取API key
        api_key = ai_config.get('api_key') or os.getenv('DASHSCOPE_API_KEY')
        if not api_key:
            raise ValueError("未设置DASHSCOPE_API_KEY，请在config.yaml中配置或设置环境变量")

        self.client = OpenAI(
            api_key=api_key,
            base_url=ai_config.get('api_base', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
        )
        self.model = ai_config.get('model', 'qwen-max')

    async def summarize_articles(self, articles: List[Article]) -> List[Article]:
        """批量生成文章摘要"""
        results = []

        for i, article in enumerate(articles, 1):
            print(f"  [{i}/{len(articles)}] 处理: {article.title[:50]}...")

            try:
                summary = await self._summarize_single(article)
                article.summary = summary
                print(f"      ✓ 摘要完成")
            except Exception as e:
                print(f"      ✗ 摘要失败: {e}")
                article.summary = f"摘要生成失败: {str(e)}"

            results.append(article)

            # 避免API限流
            await asyncio.sleep(0.5)

        return results

    async def _summarize_single(self, article: Article) -> str:
        """生成单篇文章摘要"""
        ai_config = self.config.get('ai', {})

        # 准备内容
        content = article.content[:5000] if article.content else article.title
        if not content or len(content) < 20:
            content = f"标题: {article.title}\n无法获取文章详细内容。"

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
""").format(title=article.title, content=content)

        # 同步调用OpenAI客户端
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个学术研究助手，擅长分析学术论文并提取关键信息。请用中文输出结构化的学术摘要。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=ai_config.get('temperature', 0.7),
            max_tokens=ai_config.get('max_tokens', 2000),
            timeout=ai_config.get('timeout', 120)
        )

        return response.choices[0].message.content


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
