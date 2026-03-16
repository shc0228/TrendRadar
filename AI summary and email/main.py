"""
AI学术文章摘要与邮件推送系统
监控RSS输出目录，自动获取文章内容、生成摘要并发送邮件
"""
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set

import yaml

# Import modules
from modules.html_parser import HTMLParser, Article
from modules.browser_automation import BrowserAutomation
from modules.ai_summarizer import AISummarizer
from modules.html_generator import HTMLGenerator
from modules.email_sender import EmailSender


class SummaryProcessor:
    """摘要处理器 - 主处理逻辑"""

    def __init__(self, config: Dict):
        self.config = config
        self.parser = HTMLParser(config)
        self.browser = BrowserAutomation(config)
        self.summarizer = AISummarizer(config)
        self.generator = HTMLGenerator(config)
        self.email_sender = EmailSender(config)
        self.processed_files: Set[str] = set()
        self._load_processed_files()
        self._browser_initialized = False

    def _load_processed_files(self):
        """加载已处理文件记录"""
        db_path = Path(self.config['monitor']['processed_files_db'])
        if db_path.exists():
            try:
                with open(db_path, 'r', encoding='utf-8') as f:
                    self.processed_files = set(json.load(f))
                print(f"✓ 加载已处理文件记录: {len(self.processed_files)} 个文件")
            except Exception as e:
                print(f"⚠ 加载已处理文件记录失败: {e}")
                self.processed_files = set()

    def _save_processed_files(self):
        """保存已处理文件记录"""
        db_path = Path(self.config['monitor']['processed_files_db'])
        try:
            with open(db_path, 'w', encoding='utf-8') as f:
                json.dump(list(self.processed_files), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"✗ 保存已处理文件记录失败: {e}")

    def mark_processed(self, file_path: str):
        """标记文件为已处理"""
        self.processed_files.add(file_path)
        self._save_processed_files()

    def is_processed(self, file_path: str) -> bool:
        """检查文件是否已处理"""
        return file_path in self.processed_files

    async def process_file(self, file_path: str) -> bool:
        """处理单个HTML文件"""
        try:
            print(f"\n{'='*60}")
            print(f"📄 处理文件: {Path(file_path).name}")
            print(f"{'='*60}")

            # 1. 解析HTML，获取文章列表
            print("🔍 解析HTML文件...")
            articles = self.parser.parse_file(file_path)
            print(f"   找到 {len(articles)} 篇文章")

            if not articles:
                print("   ⚠ 未找到文章，跳过处理")
                return False

            # 2. 初始化浏览器（仅第一次）
            if not self._browser_initialized:
                print("🌐 初始化浏览器...")
                success = await self.browser.initialize()
                if not success:
                    print("   ✗ 浏览器初始化失败")
                    return False
                self._browser_initialized = True
                print("   ✓ 浏览器就绪")

            # 3. 使用浏览器获取文章内容
            print("🌐 获取文章内容...")
            for i, article in enumerate(articles, 1):
                print(f"   [{i}/{len(articles)}] {article.title[:50]}...")
                result = await self.browser.get_article_content(article.url)
                if result['success']:
                    article.content = result['content']
                    print(f"      ✓ 获取内容 ({len(result['content'])} 字符)")
                else:
                    article.content = ""
                    print(f"      ✗ 获取失败: {result['error']}")

                # 避免请求过快
                await asyncio.sleep(0.5)

            # 4. AI生成摘要
            print("\n🤖 生成AI摘要...")
            articles = await self.summarizer.summarize_articles(articles)

            # 5. 生成新HTML
            print("\n📝 生成摘要HTML...")
            html_content = self.generator.generate(articles, file_path)
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
            output_file = self.generator.save(html_content, f"summary_{timestamp}.html")
            print(f"   ✓ 保存到: {output_file}")

            # 6. 发送邮件
            print("\n📧 发送邮件...")
            email_result = self.email_sender.send(output_file)

            print(f"\n{'='*60}")
            print("✅ 处理完成!")
            print(f"{'='*60}")

            return True

        except Exception as e:
            print(f"\n❌ 处理失败: {e}")
            import traceback
            traceback.print_exc()
            return False


def scan_existing_files(processor: SummaryProcessor):
    """扫描并处理已存在的文件（首次运行时）"""
    watch_dir = Path(processor.config['monitor']['watch_dir'])

    if not watch_dir.exists():
        print(f"⚠ 监控目录不存在: {watch_dir}")
        return

    print(f"\n🔍 扫描现有文件...")

    # 查找所有HTML文件
    html_files = list(watch_dir.rglob("*.html"))

    if not html_files:
        print("   未找到HTML文件")
        return

    # 过滤已处理的文件
    new_files = [str(f) for f in html_files if not processor.is_processed(str(f))]

    if not new_files:
        print(f"   所有文件已处理 ({len(html_files)} 个)")
        return

    print(f"   发现 {len(new_files)} 个新文件")

    # 询问是否处理
    print("\n是否处理这些文件? (y/n)")
    response = input("> ").strip().lower()

    if response == 'y':
        for file_path in new_files:
            asyncio.run(processor.process_file(file_path))
            processor.mark_processed(file_path)


def monitor_new_files(processor: SummaryProcessor):
    """监控新文件（循环检查模式）"""
    watch_dir = Path(processor.config['monitor']['watch_dir'])
    check_interval = processor.config['monitor'].get('check_interval', 300)

    print(f"\n🚀 开始监控新文件...")
    print(f"   目录: {watch_dir}")
    print(f"   间隔: {check_interval} 秒")
    print("   按 Ctrl+C 停止\n")

    # 记录已知的文件
    known_files = {str(f) for f in watch_dir.rglob("*.html")}

    try:
        while True:
            # 检查新文件
            current_files = {str(f) for f in watch_dir.rglob("*.html")}
            new_files = current_files - known_files

            if new_files:
                for file_path in new_files:
                    if not processor.is_processed(file_path):
                        print(f"\n🔔 检测到新文件: {Path(file_path).name}")
                        asyncio.run(processor.process_file(file_path))
                        processor.mark_processed(file_path)

                known_files = current_files

            # 等待下次检查
            time.sleep(check_interval)

    except KeyboardInterrupt:
        print("\n\n👋 监控已停止")


def main():
    """主入口"""
    print("=" * 60)
    print("🤖 AI学术文章摘要与邮件推送系统")
    print("=" * 60)

    # 加载配置
    config_path = Path(__file__).parent / 'config.yaml'
    if not config_path.exists():
        print(f"\n❌ 配置文件不存在: {config_path}")
        print("请先创建config.yaml配置文件")
        return 1

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 设置环境变量
    ai_api_key = config.get('ai', {}).get('api_key', '')
    if ai_api_key:
        os.environ['DASHSCOPE_API_KEY'] = ai_api_key

    # 创建处理器
    processor = SummaryProcessor(config)

    # 选择运行模式
    print("\n请选择运行模式:")
    print("  1. 处理现有文件")
    print("  2. 监控新文件 (持续运行)")
    print("  3. 处理现有文件 + 监控新文件")

    mode = input("\n请输入选项 (1/2/3): ").strip()

    if mode == '1':
        scan_existing_files(processor)
    elif mode == '2':
        monitor_new_files(processor)
    elif mode == '3':
        scan_existing_files(processor)
        monitor_new_files(processor)
    else:
        print("无效选项")
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
