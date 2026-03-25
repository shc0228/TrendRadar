"""
测试黑名单匹配逻辑
"""
import yaml
import unicodedata
from pathlib import Path
from modules.html_parser import HTMLParser

# 加载配置
with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 创建解析器
parser = HTMLParser(config)

# 测试标题（来自HTML）
html_title = "Market feedback: Evidence from the horse's mouth"
config_title = "Market feedback: Evidence from the horse's mouth"

print("="*60)
print("测试黑名单匹配:")
print("="*60)
print(f"\nHTML标题: {html_title}")
quote_chars = [hex(ord(c)) for c in html_title if c == "'" or ord(c) > 127]
print(f"字符码: {quote_chars}")
print(f"标准化后: {parser._normalize_title(html_title)}")

print(f"\nConfig标题: {config_title}")
quote_chars2 = [hex(ord(c)) for c in config_title if c == "'" or ord(c) > 127]
print(f"字符码: {quote_chars2}")
print(f"标准化后: {parser._normalize_title(config_title)}")

print(f"\n标准化后是否相等: {parser._normalize_title(html_title) == parser._normalize_title(config_title)}")

print(f"\nis_blacklisted结果: {parser.is_blacklisted(html_title)}")

print(f"\n黑名单标准化集合: {parser.jfe_blacklist_normalized}")
print(f"标题是否在标准化集合中: {parser._normalize_title(html_title) in parser.jfe_blacklist_normalized}")
