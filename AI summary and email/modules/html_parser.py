"""
解析TrendRadar生成的HTML文件，提取RSS文章信息
"""
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path


@dataclass
class Article:
    """文章数据类"""
    title: str
    url: str
    time: str = ""
    author: str = ""
    content: str = ""  # 浏览器获取的原始内容
    summary: str = ""  # AI生成的摘要


class HTMLParser:
    """HTML解析器"""

    def parse_file(self, file_path: str) -> List[Article]:
        """解析HTML文件，提取文章列表"""
        with open(file_path, 'r', encoding='utf-8') as f:
            html = f.read()

        soup = BeautifulSoup(html, 'html.parser')
        articles = []

        # 查找所有RSS项
        rss_items = soup.select('.rss-item')

        for item in rss_items:
            link = item.select_one('.rss-link')
            if not link:
                continue

            # 提取元数据
            time_elem = item.select_one('.rss-time')
            author_elem = item.select_one('.rss-author')

            article = Article(
                title=link.get_text(strip=True),
                url=link.get('href', ''),
                time=time_elem.get_text(strip=True) if time_elem else '',
                author=author_elem.get_text(strip=True) if author_elem else ''
            )
            articles.append(article)

        return articles


# Test the module directly
if __name__ == '__main__':
    import os

    # Test with actual file
    watch_dir = r"E:\claude code projects\trendradar\output-rss\html"
    test_date = "2026-01-29"

    test_path = Path(watch_dir) / test_date
    html_files = list(test_path.glob("*.html"))

    if html_files:
        parser = HTMLParser()
        for html_file in html_files:
            print(f"\n解析文件: {html_file.name}")
            articles = parser.parse_file(str(html_file))
            print(f"找到 {len(articles)} 篇文章:")
            for i, article in enumerate(articles[:5], 1):
                print(f"  {i}. {article.title[:60]}...")
                print(f"     URL: {article.url}")
    else:
        print(f"未找到HTML文件，请检查路径: {test_path}")
