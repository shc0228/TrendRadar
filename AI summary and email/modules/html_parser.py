"""
解析TrendRadar生成的HTML文件，提取RSS文章信息
"""
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from typing import List, Optional, Set, Dict
from pathlib import Path
import unicodedata


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

    def __init__(self, config: Optional[Dict] = None):
        """初始化解析器

        Args:
            config: 配置字典，包含黑名单等过滤规则
        """
        self.config = config or {}
        self.jfe_blacklist: Set[str] = self._load_blacklist()
        # 标准化黑名单中的标题（处理特殊字符）
        self.jfe_blacklist_normalized = {self._normalize_title(t) for t in self.jfe_blacklist}

    def _normalize_title(self, title: str) -> str:
        """标准化标题，用于模糊匹配

        处理特殊字符、大小写等问题
        """
        # 标准化Unicode字符
        normalized = unicodedata.normalize('NFKC', title)
        # 转换智能引号为普通ASCII字符
        # U+2018 LEFT SINGLE QUOTATION MARK -> '
        # U+2019 RIGHT SINGLE QUOTATION MARK -> '
        # U+201C LEFT DOUBLE QUOTATION MARK -> "
        # U+201D RIGHT DOUBLE QUOTATION MARK -> "
        # U+2013 EN DASH -> -
        # U+2014 EM DASH -> -
        char_map = {
            '\u2018': "'",
            '\u2019': "'",
            '\u201c': '"',
            '\u201d': '"',
            '\u2013': '-',
            '\u2014': '--',
        }
        for old, new in char_map.items():
            normalized = normalized.replace(old, new)
        # 转小写
        normalized = normalized.lower()
        # 去除首尾空格
        normalized = normalized.strip()
        return normalized

    def _load_blacklist(self) -> Set[str]:
        """从配置中加载JFE黑名单"""
        blacklist = self.config.get('filter', {}).get('jfe_blacklist', [])
        return set(blacklist) if blacklist else set()

    def is_blacklisted(self, title: str) -> bool:
        """检查文章标题是否在黑名单中

        使用标准化后的标题进行匹配，可以处理特殊字符差异

        Args:
            title: 文章标题

        Returns:
            bool: 如果在黑名单中返回True
        """
        # 先尝试精确匹配
        if title in self.jfe_blacklist:
            return True

        # 再尝试标准化后的匹配
        normalized_title = self._normalize_title(title)
        # 需要检查标准化后的黑名单中是否有匹配
        # 为此，我们需要比较标准化后的标题
        for blacklist_title in self.jfe_blacklist:
            if self._normalize_title(blacklist_title) == normalized_title:
                return True

        return False

    def parse_file(self, file_path: str, filter_blacklist: bool = True) -> List[Article]:
        """解析HTML文件，提取文章列表

        Args:
            file_path: HTML文件路径
            filter_blacklist: 是否过滤黑名单文章，默认为True

        Returns:
            List[Article]: 文章列表
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            html = f.read()

        soup = BeautifulSoup(html, 'html.parser')
        articles = []
        filtered_count = 0

        # 查找所有RSS项
        rss_items = soup.select('.rss-item')

        for item in rss_items:
            link = item.select_one('.rss-link')
            if not link:
                continue

            # 提取标题
            title = link.get_text(strip=True)

            # 黑名单过滤
            if filter_blacklist and self.is_blacklisted(title):
                filtered_count += 1
                continue

            # 提取元数据
            time_elem = item.select_one('.rss-time')
            author_elem = item.select_one('.rss-author')

            article = Article(
                title=title,
                url=link.get('href', ''),
                time=time_elem.get_text(strip=True) if time_elem else '',
                author=author_elem.get_text(strip=True) if author_elem else ''
            )
            articles.append(article)

        if filtered_count > 0:
            print(f"   已过滤 {filtered_count} 篇黑名单文章")

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
