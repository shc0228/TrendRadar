"""
调试字符编码问题
"""
import yaml
import unicodedata
from pathlib import Path
from modules.html_parser import HTMLParser
from bs4 import BeautifulSoup

# 读取HTML获取实际标题
html_file = Path(r"E:\claude code projects\trendradar\output-rss\html\2026-03-16\16-00.html")
with open(html_file, 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

print("="*60)
print("HTML中实际的JFE文章标题:")
print("="*60)

for item in soup.select('.rss-item'):
    author = item.select_one('.rss-author')
    if author and 'JFE' in author.get_text():
        link = item.select_one('.rss-link')
        title = link.get_text(strip=True)
        print(f"\n标题: {title}")
        print(f"字符编码:")
        for char in title:
            if char == "'" or ord(char) > 127:
                print(f"  '{char}' = U+{ord(char):04X} ({unicodedata.name(char, 'UNKNOWN')})")

# 读取配置中的黑名单
with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

print("\n" + "="*60)
print("config.yaml中的黑名单标题:")
print("="*60)

for title in config['filter']['jfe_blacklist']:
    if 'horse' in title.lower():
        print(f"\n标题: {title}")
        print(f"字符编码:")
        for char in title:
            if char == "'" or ord(char) > 127:
                print(f"  '{char}' = U+{ord(char):04X} ({unicodedata.name(char, 'UNKNOWN')})")

# 测试标准化
print("\n" + "="*60)
print("标准化测试:")
print("="*60)

# HTML中的标题
html_title = "Market feedback: Evidence from the horse's mouth"
config_title = "Market feedback: Evidence from the horse's mouth"

import unicodedata

print(f"\nHTML标题: {html_title}")
print(f"标准化后: {unicodedata.normalize('NFKC', html_title)}")

print(f"\nConfig标题: {config_title}")
print(f"标准化后: {unicodedata.normalize('NFKC', config_title)}")

print(f"\n是否相等: {unicodedata.normalize('NFKC', html_title) == unicodedata.normalize('NFKC', config_title)}")
