"""
找出每天重复的JFE文章 - 简化版
"""
from pathlib import Path
from bs4 import BeautifulSoup

def extract_jfe_articles(file_path):
    """从HTML文件提取JFE文章"""
    with open(file_path, 'r', encoding='utf-8') as f:
        html = f.read()

    soup = BeautifulSoup(html, 'html.parser')
    articles = []

    for item in soup.select('.rss-item'):
        author = item.select_one('.rss-author')
        link = item.select_one('.rss-link')

        if author and 'JFE' in author.get_text():
            title = link.get_text(strip=True)
            url = link.get('href', '')
            articles.append({'title': title, 'url': url})

    return articles

def main():
    watch_dir = Path(r"E:\claude code projects\trendradar\output-rss\html")

    # 获取最近几天的数据
    date_dirs = sorted([d for d in watch_dir.iterdir() if d.is_dir()])

    # 存储每天的文章
    daily_articles = {}
    all_titles = {}

    for date_dir in date_dirs[-10:]:  # 只看最近10天
        html_file = date_dir / "16-00.html"
        if html_file.exists():
            articles = extract_jfe_articles(html_file)
            if articles:
                daily_articles[date_dir.name] = articles
                for art in articles:
                    title = art['title']
                    if title not in all_titles:
                        all_titles[title] = []
                    all_titles[title].append(date_dir.name)

    # 找出在多天都出现的文章
    print(f"分析了 {len(daily_articles)} 天的数据\n")

    duplicates = {title: days for title, days in all_titles.items() if len(days) > 1}

    # 按出现次数排序
    sorted_duplicates = sorted(duplicates.items(), key=lambda x: len(x[1]), reverse=True)

    print("="*80)
    print("重复出现的JFE文章:")
    print("="*80)

    blacklist = []

    for i, (title, days) in enumerate(sorted_duplicates, 1):
        print(f"\n{i}. {title}")
        print(f"   出现天数: {len(days)}")
        print(f"   URL: {daily_articles[days[0]][[a['title'] for a in daily_articles[days[0]]].index(title)]['url']}")

        # 如果在所有天都出现，加入黑名单
        if len(days) == len(daily_articles):
            blacklist.append(title)
            print("   *** 在所有天都出现，建议加入黑名单 ***")

    print("\n" + "="*80)
    print(f"建议加入黑名单的文章 ({len(blacklist)} 篇):")
    print("="*80)

    for i, title in enumerate(blacklist, 1):
        print(f"{i}. {title}")

    # 生成配置文件内容
    print("\n" + "="*80)
    print("config.yaml 中添加以下配置:")
    print("="*80)
    print("\n# JFE文章黑名单 - 每天重复出现的文章\njfe_blacklist:")
    for title in blacklist:
        escaped = title.replace('"', '\\"')
        print(f'  - "{escaped}"')

if __name__ == '__main__':
    main()
