"""
Direct processing script - bypass interactive menu
"""
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml

# Set UTF-8 encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Import modules
from modules.html_parser import HTMLParser
from modules.browser_automation import BrowserAutomation
from modules.ai_summarizer import AISummarizer
from modules.html_generator import HTMLGenerator
from modules.email_sender import EmailSender


async def process_file(file_path: str, config: dict):
    """Process a single HTML file"""
    print(f"\n{'='*60}")
    print(f"Processing: {Path(file_path).name}")
    print(f"{'='*60}")

    # Initialize components
    parser = HTMLParser()
    browser = BrowserAutomation(config)
    summarizer = AISummarizer(config)
    generator = HTMLGenerator(config)

    # 1. Parse HTML
    print("Parsing HTML...")
    articles = parser.parse_file(file_path)
    print(f"   Found {len(articles)} articles")

    if not articles:
        print("   No articles found, skipping")
        return False

    # Print article URLs for debugging
    print("\nArticles:")
    for i, article in enumerate(articles, 1):
        print(f"   {i}. {article.title[:60]}...")
        print(f"      URL: {article.url}")

    # 2. Get article content
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

    # 3. Generate AI summaries
    print(f"\n{'='*60}")
    print(f"Fetch Results: {success_count} success, {fail_count} failed")
    print(f"{'='*60}")

    # Only summarize articles with content
    articles_with_content = [a for a in articles if a.content]

    if not articles_with_content:
        print("\nNo articles with content to summarize")
        return False

    print(f"\nGenerating AI summaries for {len(articles_with_content)} articles...")
    articles = await summarizer.summarize_articles(articles)

    # 4. Generate HTML
    print("\nGenerating summary HTML...")
    html_content = generator.generate(articles, file_path)
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
    output_file = generator.save(html_content, f"summary_{timestamp}.html")
    print(f"   Saved to: {output_file}")

    # 5. Send email (optional - comment out if not needed)
    print("\nSending email...")
    email_sender = EmailSender(config)
    email_result = email_sender.send(output_file)
    print(f"   Email result: {email_result}")

    print(f"\n{'='*60}")
    print("Processing complete!")
    print(f"{'='*60}")

    return True


def main():
    """Main entry point"""
    print("=" * 60)
    print("AI Academic Article Summary System")
    print("=" * 60)

    # Load config
    config_path = Path(__file__).parent / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Set AI API key
    ai_api_key = config.get('ai', {}).get('api_key', '')
    if ai_api_key:
        os.environ['DASHSCOPE_API_KEY'] = ai_api_key

    # Get HTML files from watch directory
    watch_dir = Path(config['monitor']['watch_dir'])

    if not watch_dir.exists():
        print(f"Watch directory does not exist: {watch_dir}")
        return 1

    # Find all HTML files
    html_files = sorted(watch_dir.rglob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]

    if not html_files:
        print("No HTML files found")
        return 0

    print(f"\nFound {len(html_files)} HTML files (showing latest 5)")
    for i, f in enumerate(html_files, 1):
        print(f"  {i}. {f.relative_to(watch_dir)}")

    # Process the latest file
    latest_file = html_files[0]
    print(f"\nProcessing latest file: {latest_file.name}")

    asyncio.run(process_file(str(latest_file), config))

    return 0


if __name__ == '__main__':
    sys.exit(main())
