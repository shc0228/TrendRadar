"""
定时任务调度器 - 每天16:10自动处理当天的新HTML文件
"""
import asyncio
import json
import os
import sys
import io
from pathlib import Path
from datetime import datetime, timedelta
import time

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    import schedule
except ImportError:
    print("请先安装schedule库: pip install schedule")
    sys.exit(1)

import yaml

from modules.html_parser import HTMLParser
from modules.browser_automation import BrowserAutomation
from modules.ai_summarizer import AISummarizer
from modules.html_generator import HTMLGenerator
from modules.email_sender import EmailSender


async def process_file(file_path: str, config: dict):
    """处理单个HTML文件的完整流程"""
    print(f"\n{'='*60}")
    print(f"Processing: {Path(file_path).name}")
    print(f"{'='*60}")

    # 初始化组件
    parser = HTMLParser()
    browser = BrowserAutomation(config)
    summarizer = AISummarizer(config)
    generator = HTMLGenerator(config)

    # 1. 解析HTML
    print("Parsing HTML...")
    articles = parser.parse_file(file_path)
    print(f"   Found {len(articles)} articles")

    if not articles:
        print("   No articles found, skipping")
        return False

    # 打印文章列表
    print("\nArticles:")
    for i, article in enumerate(articles, 1):
        print(f"   {i}. {article.title[:60]}...")
        print(f"      URL: {article.url}")

    # 2. 获取文章内容
    print("\nFetching article content...")
    success_count = 0
    fail_count = 0

    for i, article in enumerate(articles, 1):
        print(f"\n[{i}/{len(articles)}] {article.title[:50]}...")
        result = await browser.get_article_content(article.url)

        if result['success']:
            article.content = result['content']
            source = result.get('source', 'unknown')
            api_name = result.get('api_name', '')
            print(f"   Success! Source: {source}", end='')
            if api_name:
                print(f", API: {api_name}")
            else:
                print()
            print(f"   Content length: {len(result['content'])} chars")
            success_count += 1
        else:
            article.content = ""
            error = result.get('error', 'Unknown error')
            print(f"   Failed: {error[:80]}")
            fail_count += 1

        await asyncio.sleep(0.3)

    # 3. 生成AI摘要
    print(f"\n{'='*60}")
    print(f"Fetch Results: {success_count} success, {fail_count} failed")
    print(f"{'='*60}")

    # 只总结有内容的文章
    articles_with_content = [a for a in articles if a.content]

    if not articles_with_content:
        print("\nNo articles with content to summarize")
        return False

    print(f"\nGenerating AI summaries for {len(articles_with_content)} articles...")
    articles = await summarizer.summarize_articles(articles)

    # 4. 生成HTML
    print("\nGenerating summary HTML...")
    html_content = generator.generate(articles, file_path)
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
    output_file = generator.save(html_content, f"summary_{timestamp}.html")
    print(f"   Saved to: {output_file}")

    # 5. 发送邮件
    print("\nSending email...")
    email_sender = EmailSender(config)
    email_result = email_sender.send(output_file)
    print(f"   Email result: {email_result}")

    print(f"\n{'='*60}")
    print("Processing complete!")
    print(f"{'='*60}")

    # 标记为已处理
    mark_as_processed(file_path, config)

    return True


def mark_as_processed(file_path: str, config: dict):
    """标记文件为已处理"""
    processed_db = Path(config['monitor']['processed_files_db'])

    # 读取已处理的文件列表
    processed = set()
    if processed_db.exists():
        try:
            with open(processed_db, 'r', encoding='utf-8') as f:
                processed = set(json.load(f))
        except:
            pass

    # 添加当前文件
    processed.add(str(file_path))

    # 保存
    with open(processed_db, 'w', encoding='utf-8') as f:
        json.dump(list(processed), f, ensure_ascii=False, indent=2)


def is_processed(file_path: str, config: dict) -> bool:
    """检查文件是否已处理"""
    processed_db = Path(config['monitor']['processed_files_db'])

    if not processed_db.exists():
        return False

    try:
        with open(processed_db, 'r', encoding='utf-8') as f:
            processed = set(json.load(f))
            return str(file_path) in processed
    except:
        return False


def get_todays_html_files(watch_dir: Path) -> list[Path]:
    """获取今天生成的HTML文件（递归查找子目录）"""
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    html_files = []

    if watch_dir.exists():
        # 递归查找所有HTML文件
        for file in watch_dir.rglob('*.html'):
            # 获取文件修改时间
            mod_time = datetime.fromtimestamp(file.stat().st_mtime).date()

            # 包括今天和昨天晚些时候的文件（处理跨日情况）
            if mod_time >= yesterday:
                html_files.append(file)

    return sorted(html_files, key=lambda x: x.stat().st_mtime, reverse=True)


def process_daily_files():
    """处理当天的新文件"""
    print("=" * 60)
    print(f"定时任务执行: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 加载配置
    config_path = Path(__file__).parent / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 设置AI API密钥
    ai_api_key = config.get('ai', {}).get('api_key', '')
    if ai_api_key:
        os.environ['DASHSCOPE_API_KEY'] = ai_api_key

    watch_dir = Path(config['monitor']['watch_dir'])

    # 获取今天的HTML文件
    html_files = get_todays_html_files(watch_dir)

    if not html_files:
        print("没有发现今天的新HTML文件")
        return

    print(f"发现 {len(html_files)} 个HTML文件:")

    # 显示文件列表
    for i, file in enumerate(html_files, 1):
        mod_time = datetime.fromtimestamp(file.stat().st_mtime)
        print(f"  {i}. {file.name} (修改于: {mod_time.strftime('%H:%M:%S')})")

    # 检查是否已处理过
    unprocessed_files = []
    for file in html_files:
        if not is_processed(str(file), config):
            unprocessed_files.append(file)

    if not unprocessed_files:
        print("\n所有文件都已处理过")
        return

    print(f"\n需要处理 {len(unprocessed_files)} 个文件")

    # 处理文件
    for i, file in enumerate(unprocessed_files, 1):
        print(f"\n{'=' * 60}")
        print(f"处理文件 {i}/{len(unprocessed_files)}: {file.name}")
        print(f"{'=' * 60}")

        try:
            asyncio.run(process_file(str(file), config))
            print(f"✅ 文件处理完成: {file.name}")

        except Exception as e:
            print(f"❌ 文件处理失败: {file.name}")
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 60}")
    print("定时任务执行完成")
    print(f"{'=' * 60}")


def run_scheduler():
    """运行调度器"""
    print("=" * 60)
    print("AI学术文章摘要与邮件推送系统 - 定时调度器")
    print("=" * 60)
    print()

    # 设置每天16:10执行
    schedule_time = "16:10"
    schedule.every().day.at(schedule_time).do(process_daily_files)

    print(f"定时任务已设置: 每天 {schedule_time} 执行")
    print(f"监控目录: {Path(__file__).parent.parent / 'output-rss' / 'html'}")
    print()
    print("调度器运行中... (按 Ctrl+C 停止)")
    print()

    # 显示下次执行时间
    next_run = schedule.next_run()
    print(f"下次执行: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 启动时检查是否需要执行今天的任务
    now = datetime.now()
    scheduled_time = now.replace(hour=16, minute=10, second=0, microsecond=0)

    # 如果当前时间在16:10之后且今天还没执行过，立即执行一次
    if now.time() >= scheduled_time.time():
        print("当前时间已过今天的调度时间，立即执行一次...")
        print()
        process_daily_files()
        print()

    # 持续运行
    try:
        while True:
            schedule.run_pending()

            # 每分钟显示一次下次执行时间
            if schedule.next_run():
                next_run = schedule.next_run()
                time_until = (next_run - datetime.now()).total_seconds()
                hours = int(time_until // 3600)
                minutes = int((time_until % 3600) // 60)

                # 每小时输出一次
                if minutes == 0:
                    print(f"[{datetime.now().strftime('%H:%M')}] 下次执行: {next_run.strftime('%Y-%m-%d %H:%M')} (还有 {hours} 小时)")

            time.sleep(60)

    except KeyboardInterrupt:
        print("\n\n调度器已停止")


def run_once():
    """立即执行一次（用于测试）"""
    print("立即执行模式")
    print()
    process_daily_files()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='AI学术文章摘要定时调度器')
    parser.add_argument('--once', action='store_true', help='立即执行一次后退出')
    parser.add_argument('--test', action='store_true', help='测试模式：显示今天的文件但不处理')

    args = parser.parse_args()

    if args.test:
        # 测试模式：只显示文件列表
        config_path = Path(__file__).parent / 'config.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        watch_dir = Path(config['monitor']['watch_dir'])

        print("测试模式 - 检查今天的HTML文件")
        print("=" * 60)
        print(f"监控目录: {watch_dir}")
        print()

        html_files = get_todays_html_files(watch_dir)

        if not html_files:
            print("没有发现今天的HTML文件")
        else:
            print(f"发现 {len(html_files)} 个HTML文件:")
            for i, file in enumerate(html_files, 1):
                mod_time = datetime.fromtimestamp(file.stat().st_mtime)
                print(f"  {i}. {file.name}")
                print(f"     修改时间: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"     文件大小: {file.stat().st_size} bytes")
                print(f"     已处理: {'是' if is_processed(str(file), config) else '否'}")

    elif args.once:
        run_once()
    else:
        run_scheduler()
