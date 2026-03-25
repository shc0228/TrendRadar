"""
测试JFE黑名单功能
"""
import yaml
from pathlib import Path
from modules.html_parser import HTMLParser

def test_blacklist():
    """测试黑名单过滤功能"""
    # 加载配置
    config_path = Path(__file__).parent / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 创建解析器（会自动加载黑名单）
    parser = HTMLParser(config)

    # 显示黑名单内容
    blacklist = parser.jfe_blacklist
    print("="*60)
    print(f"JFE黑名单 ({len(blacklist)} 篇):")
    print("="*60)
    for i, title in enumerate(sorted(blacklist), 1):
        print(f"{i}. {title}")

    # 测试解析
    test_file = Path(r"E:\claude code projects\trendradar\output-rss\html\2026-03-16\16-00.html")

    if not test_file.exists():
        print(f"\n测试文件不存在: {test_file}")
        return

    print("\n" + "="*60)
    print("测试解析HTML文件")
    print("="*60)

    # 不过滤黑名单
    print("\n1. 不过滤黑名单:")
    articles_no_filter = parser.parse_file(str(test_file), filter_blacklist=False)
    print(f"   找到 {len(articles_no_filter)} 篇文章")
    for art in articles_no_filter:
        print(f"   - {art.title[:50]}...")

    # 过滤黑名单
    print("\n2. 过滤黑名单:")
    articles_with_filter = parser.parse_file(str(test_file), filter_blacklist=True)
    print(f"   找到 {len(articles_with_filter)} 篇文章")
    if not articles_with_filter:
        print("   (所有文章都在黑名单中)")
    else:
        for art in articles_with_filter:
            print(f"   - {art.title[:50]}...")

    print("\n" + "="*60)
    print("测试结果:")
    print(f"  原始文章数: {len(articles_no_filter)}")
    print(f"  过滤后文章数: {len(articles_with_filter)}")
    print(f"  过滤掉文章数: {len(articles_no_filter) - len(articles_with_filter)}")
    print(f"  黑名单文章数: {len(blacklist)}")
    print("="*60)

if __name__ == '__main__':
    test_blacklist()
