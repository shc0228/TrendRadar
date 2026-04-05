"""
解析TrendRadar生成的HTML文件，提取RSS文章信息
"""
import json
import re
from datetime import datetime, timedelta

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
        """从配置和动态黑名单文件中加载黑名单"""
        # 静态黑名单（config.yaml）
        static = self.config.get('filter', {}).get('jfe_blacklist', [])
        blacklist = set(static) if static else set()
        # 动态黑名单（JSON文件）
        blacklist.update(self._load_dynamic_blacklist())
        return blacklist

    def _dynamic_blacklist_path(self) -> Path:
        """获取动态黑名单文件路径"""
        # 与 config.yaml 同目录
        if self.config.get('_config_path'):
            return Path(self.config['_config_path']).parent / 'dynamic_blacklist.json'
        return Path(__file__).parent.parent / 'dynamic_blacklist.json'

    def _load_dynamic_blacklist(self) -> Set[str]:
        """从JSON文件加载动态黑名单"""
        path = self._dynamic_blacklist_path()
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return set(data) if isinstance(data, list) else set()
            except Exception:
                return set()
        return set()

    def _save_dynamic_blacklist(self, titles: Set[str]):
        """保存动态黑名单到JSON文件"""
        path = self._dynamic_blacklist_path()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(sorted(titles), f, ensure_ascii=False, indent=2)

    def _reload_blacklist(self):
        """重新加载黑名单（合并静态+动态）"""
        self.jfe_blacklist = self._load_blacklist()
        self.jfe_blacklist_normalized = {self._normalize_title(t) for t in self.jfe_blacklist}

    def update_dynamic_blacklist(self, current_file: str):
        """检测重复文章并更新动态黑名单

        比较当前文件与前2天的文件，找出重复出现的文章标题，
        将其加入动态黑名单（已加入的不会被移除）。

        Args:
            current_file: 当前要处理的HTML文件路径
        """
        # 1. 从文件路径提取日期
        match = re.search(r'(\d{4}-\d{2}-\d{2})', str(current_file))
        if not match:
            return
        current_date = datetime.strptime(match.group(1), '%Y-%m-%d').date()

        # 2. 获取监控目录
        watch_dir = self.config.get('monitor', {}).get('watch_dir', '')
        if not watch_dir:
            return
        watch_path = Path(watch_dir)

        # 3. 解析当前文件的所有标题（不过滤黑名单）
        current_articles = self.parse_file(current_file, filter_blacklist=False)
        current_titles = {a.title for a in current_articles}
        current_titles_normalized = {self._normalize_title(t): t for t in current_titles}

        # 4. 查找前2天的HTML文件并提取标题
        previous_titles_normalized = set()
        for days_ago in range(1, 3):
            prev_date = current_date - timedelta(days=days_ago)
            prev_dir = watch_path / prev_date.strftime('%Y-%m-%d')
            if not prev_dir.exists():
                continue
            for html_file in prev_dir.glob('*.html'):
                try:
                    prev_articles = self.parse_file(str(html_file), filter_blacklist=False)
                    for a in prev_articles:
                        previous_titles_normalized.add(self._normalize_title(a.title))
                except Exception:
                    continue

        if not previous_titles_normalized:
            return

        # 5. 找出重复标题（当前文件中也在前2天出现过的）
        repeating = set()
        for norm_title, orig_title in current_titles_normalized.items():
            if norm_title in previous_titles_normalized:
                repeating.add(orig_title)

        if not repeating:
            return

        # 6. 加载已有动态黑名单，合并新条目，保存
        dynamic_blacklist = self._load_dynamic_blacklist()
        new_count = 0
        for title in repeating:
            # 检查是否已存在（用标准化匹配）
            already_exists = any(
                self._normalize_title(t) == self._normalize_title(title)
                for t in dynamic_blacklist
            )
            if not already_exists:
                dynamic_blacklist.add(title)
                new_count += 1

        self._save_dynamic_blacklist(dynamic_blacklist)

        if new_count > 0:
            print(f"   动态黑名单新增 {new_count} 篇重复文章")
            self._reload_blacklist()

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
