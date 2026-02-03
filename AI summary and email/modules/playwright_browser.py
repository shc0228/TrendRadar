"""
Playwright浏览器自动化 - 直接调用Chrome DevTools

用于需要真实浏览器环境的网站（如INFORMS等有机器人验证的网站）
"""
import asyncio
from pathlib import Path
from typing import Dict
from urllib.parse import urlparse

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class PlaywrightBrowser:
    """
    Playwright浏览器自动化

    直接控制Chrome/Chromium浏览器，无需MCP接口
    """

    # 默认提取内容的JavaScript代码
    EXTRACTION_JS = """
    () => {
        const results = {};

        // 获取标题
        const titleElem = document.querySelector('h1, .title-text, [class*="title"], .article-title');
        results.title = titleElem ? titleElem.innerText.trim() : document.title;

        // 获取摘要 - INFORMS专用
        let abstract = '';
        const informsAbstract = document.querySelector('.abstractSection p, .abstract p');
        if (informsAbstract) {
            abstract = informsAbstract.innerText.trim();
        }

        // ScienceDirect格式
        if (!abstract) {
            const sdAbstract = document.querySelector('.abstract p, #abstract p');
            if (sdAbstract) {
                abstract = sdAbstract.innerText.trim();
            }
        }

        // 通用选择器
        if (!abstract || abstract.length < 50) {
            const selectors = [
                '[class*="abstract"] p',
                '#abstract p',
                '.article-abstract p'
            ];
            for (const sel of selectors) {
                try {
                    const elem = document.querySelector(sel);
                    if (elem && elem.innerText.length > 50) {
                        abstract = elem.innerText.trim();
                        break;
                    }
                } catch(e) {}
            }
        }

        results.abstract = abstract;
        results.url = window.location.href;
        results.hasContent = abstract.length > 50;

        return JSON.stringify(results);
    }
    """

    def __init__(self, config: Dict):
        self.config = config
        self.browser_config = config.get('browser', {})
        self.headless = self.browser_config.get('headless', True)
        self.timeout = self.browser_config.get('timeout', 30000)

    async def initialize(self):
        """初始化浏览器"""
        return True

    async def get_article_content(self, url: str) -> Dict[str, str]:
        """
        使用Playwright获取文章内容

        Returns:
            Dict: {
                'success': bool,
                'content': str,
                'error': str,
                'source': 'playwright'
            }
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {
                'success': False,
                'content': '',
                'error': 'Playwright未安装，请运行: pip install playwright',
                'source': 'playwright'
            }

        try:
            async with async_playwright() as p:
                # 启动浏览器
                browser = await p.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox'
                    ]
                )

                # 创建新的浏览器上下文
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )

                page = await context.new_page()

                # 导航到URL
                await page.goto(url, timeout=self.timeout, wait_until='domcontentloaded')

                # 等待一下让页面加载
                await asyncio.sleep(2)

                # 执行JavaScript提取内容
                result = await page.evaluate(self.EXTRACTION_JS)

                # 关闭浏览器
                await browser.close()

                if result:
                    import json
                    data = json.loads(result)
                    abstract = data.get('abstract', '')

                    if abstract and len(abstract) > 50:
                        return {
                            'success': True,
                            'content': abstract,
                            'error': '',
                            'source': 'playwright'
                        }

                return {
                    'success': False,
                    'content': '',
                    'error': '未能提取到摘要内容',
                    'source': 'playwright'
                }

        except Exception as e:
            return {
                'success': False,
                'content': '',
                'error': f'Playwright执行失败: {str(e)}',
                'source': 'playwright'
            }


class PlaywrightManager:
    """Playwright管理器 - 处理需要浏览器才能访问的URL"""

    # 需要使用Playwright的域名
    PLAYWRIGHT_DOMAINS = {
        'informs.org',
        'pubsonline.informs.org',
        # 注意：journals.uchicago.edu (JPE)有Cloudflare Turnstile保护，Playwright无法绕过，已移至MCP模式
    }

    def __init__(self, config: Dict):
        self.config = config
        self.browser = PlaywrightBrowser(config)
        self._initialized = False

    def can_handle(self, url: str) -> bool:
        """判断URL是否需要使用Playwright"""
        domain = urlparse(url).netloc.lower()
        return any(playwright_domain in domain for playwright_domain in self.PLAYWRIGHT_DOMAINS)

    async def get_article_content(self, url: str) -> Dict[str, str]:
        """获取文章内容"""
        return await self.browser.get_article_content(url)


# Test
if __name__ == '__main__':
    import sys
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    async def test():
        config = {
            'browser': {
                'timeout': 30000,
                'headless': True
            }
        }

        manager = PlaywrightManager(config)

        # 测试INFORMS URL
        test_url = 'https://pubsonline.informs.org/doi/abs/10.1287/isre.2024.1313'

        print(f'Testing Playwright with INFORMS URL:')
        print(f'URL: {test_url}')
        print('-' * 60)

        result = await manager.get_article_content(test_url)

        print(f'Success: {result["success"]}')
        print(f'Source: {result["source"]}')

        if result['success']:
            content = result['content']
            print(f'Content length: {len(content)} chars')
            print(f'Preview: {content[:200]}...')
        else:
            print(f'Error: {result["error"]}')

    asyncio.run(test())
