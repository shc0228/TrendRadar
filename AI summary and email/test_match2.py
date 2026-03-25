"""
测试黑名单匹配逻辑 - 使用正确的字符
"""
import yaml
import unicodedata
from pathlib import Path
from modules.html_parser import HTMLParser
from bs4 import BeautifulSoup

# 加载配置
with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 创建解析器
parser = HTMLParser(config)

# 从HTML读取实际标题
html_file = Path(r"E:\claude code projects\trendradar\output-rss\html\2026-03-16\16-00.html")
with open(html_file, 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

print("="*60)
print("测试实际的HTML标题与黑名单匹配:")
print("="*60)

for item in soup.select('.rss-item'):
    author = item.select_one('.rss-author')
    if author and 'JFE' in author.get_text():
        link = item.select_one('.rss-link')
        title = link.get_text(strip=True)

        is_blacklisted = parser.is_blacklisted(title)
        normalized = parser._normalize_title(title)

        print(f"\n标题: {title}")
        print(f"是否在黑名单中: {is_blacklisted}")
        print(f"标准化后: {normalized}")
        print(f"在标准化集合中: {normalized in parser.jfe_blacklist_normalized}")
