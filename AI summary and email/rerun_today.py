"""
重新生成并发送今天的邮件（使用新格式）
"""
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

import yaml

from modules.html_parser import HTMLParser
from modules.browser_automation import BrowserAutomation
from modules.ai_summarizer import AISummarizer
from modules.html_generator import HTMLGenerator
from modules.email_sender import EmailSender


async def main():
    # 加载配置
    config_path = Path(__file__).parent / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 设置API key
    ai_api_key = config.get('ai', {}).get('api_key', '')
    if ai_api_key:
        os.environ['KIMI_API_KEY'] = ai_api_key

    today_file = r'E:\claude code projects\trendradar\output-rss\html\2026-05-10\16-00.html'

    print('=' * 60)
    print('重新生成今天邮件（新格式）')
    print('=' * 60)

    # 1. 解析HTML
    parser = HTMLParser(config)
    parser.update_dynamic_blacklist(today_file)
    articles = parser.parse_file(today_file)
    print(f'\n找到 {len(articles)} 篇文章')

    if not articles:
        print('未找到文章，退出')
        return

    # 2. 初始化浏览器
    browser = BrowserAutomation(config)
    print('\n初始化浏览器...')
    await browser.initialize()
    print('浏览器就绪')

    # 3. 获取文章内容
    print('\n获取文章内容...')
    for i, article in enumerate(articles, 1):
        print(f'   [{i}/{len(articles)}] {article.title[:50]}...')
        result = await browser.get_article_content(article.url)
        if result['success']:
            article.content = result['content']
            article.authors = result.get('authors', '')
            print(f'      内容: {len(result["content"])} 字符')
            if article.authors:
                print(f'      作者: {article.authors[:80]}')
        else:
            article.content = ""
            article.authors = ""
            print(f'      获取失败: {result["error"]}')
        await asyncio.sleep(0.5)

    # 4. AI生成摘要
    summarizer = AISummarizer(config)
    print('\n生成AI摘要...')
    articles = await summarizer.summarize_articles(articles)

    # 5. 生成HTML
    generator = HTMLGenerator(config)
    html_content = generator.generate(articles, today_file)
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
    output_file = generator.save(html_content, f"summary_{timestamp}.html")
    print(f'\nHTML已保存: {output_file}')

    # 6. 发送邮件
    sender = EmailSender(config)
    print('\n发送邮件...')
    result = sender.send(output_file)

    print('\n' + '=' * 60)
    if result:
        print('邮件发送成功')
    else:
        print('邮件发送失败')
    print('=' * 60)


if __name__ == '__main__':
    asyncio.run(main())
