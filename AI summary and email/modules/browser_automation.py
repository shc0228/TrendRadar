"""
浏览器自动化模块 - 混合模式 + API优先

支持三种模式:
1. API模式: 优先使用官方API（arXiv, Springer, etc.）
2. requests模式: 用于普通网站
3. MCP模式: 使用Chrome DevTools MCP处理受限网站

MCP工具通过Claude Code界面调用，此模块提供接口定义
"""
import asyncio
import json
import re
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse, unquote

import requests
from bs4 import BeautifulSoup

from .api_router import APIRouter, CAPTCHADetector
from .playwright_browser import PlaywrightManager


class BrowserAutomation:
    """
    浏览器自动化 - 混合模式

    - 普通网站使用requests
    - 受限网站(403)通过MCP处理
    """

    # 需要使用MCP的域名（注意：有API或Playwright支持的域名已移除）
    MCP_DOMAINS = {
        'ieee.org',  # 需要IEEE API
        'dl.acm.org',  # 需要ACM API
        'journals.uchicago.edu',  # JPE等，Cloudflare Turnstile保护
        'academic.oup.com',  # OUP (QJE等)，Cloudflare保护
    }

    def __init__(self, config: Dict):
        self.config = config
        self.browser_config = config.get('browser', {})
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age-0'
        })

        # MCP工作目录
        self.mcp_work_dir = Path('.mcp_work')
        self.mcp_work_dir.mkdir(exist_ok=True)
        self.mcp_queue_file = self.mcp_work_dir / 'queue.json'
        self.mcp_results_file = self.mcp_work_dir / 'results.json'

        # API路由器（优先级最高）
        self.api_router = APIRouter(config) if config.get('api_priority', {}).get('enabled', True) else None

        # Playwright浏览器（用于INFORMS等需要真实浏览器的网站）
        self.playwright_manager = PlaywrightManager(config) if config.get('browser', {}).get('use_playwright', True) else None

    async def initialize(self):
        """初始化浏览器"""
        return True

    def _needs_mcp(self, url: str) -> bool:
        """检查URL是否需要使用MCP"""
        domain = urlparse(url).netloc.lower()
        return any(mcp_domain in domain for mcp_domain in self.MCP_DOMAINS)

    async def get_article_content(self, url: str) -> Dict[str, str]:
        """
        获取文章内容 - API优先

        优先级:
        1. 官方API (Elsevier, arXiv, Springer)
        2. Playwright模式 (INFORMS等需要真实浏览器的网站)
        3. MCP模式 (其他受限网站)
        4. requests模式 (普通网站)

        Returns:
            Dict: {
                'success': bool,
                'content': str,
                'error': str,
                'source': str,  # 'api', 'playwright', 'mcp', 'requests'
                'api_name': str  # API名称（如果是API获取）
            }
        """
        # 1. 优先尝试API（如果启用）
        if self.api_router:
            api_result = await self.api_router.fetch_via_api(url)
            if api_result.get('success'):
                return {
                    'success': True,
                    'content': api_result['content'],
                    'error': '',
                    'source': 'api',
                    'api_name': api_result.get('api_name', 'Unknown')
                }

        # 2. 检查是否需要Playwright (INFORMS等)
        if self.playwright_manager and self.playwright_manager.can_handle(url):
            return await self.playwright_manager.get_article_content(url)

        # 3. 检查是否需要MCP
        if self._needs_mcp(url):
            return await self._get_via_mcp(url)

        # 4. 使用requests获取
        result = await self._get_via_requests(url)

        # 5. 检测CAPTCHA
        if not result['success'] and self._is_captcha_related(result.get('error', '')):
            return self._handle_captcha_detected(url, result)

        return result

    def _is_captcha_related(self, error: str) -> bool:
        """判断错误是否与CAPTCHA相关"""
        return CAPTCHADetector.is_captcha_error(error)

    def _handle_captcha_detected(self, url: str, original_result: Dict) -> Dict:
        """处理检测到的CAPTCHA"""
        fallback = self.config.get('api_priority', {}).get('on_captcha', 'skip')

        if fallback == 'manual':
            return {
                'success': False,
                'content': '',
                'error': 'CAPTCHA detected - 需要人工处理',
                'source': 'captcha',
                'requires_manual': True,
                'suggestion': self._get_api_suggestion(url)
            }
        else:  # skip
            return {
                'success': False,
                'content': '',
                'error': 'CAPTCHA detected - 文章已跳过',
                'source': 'captcha',
                'requires_api': True,
                'suggestion': self._get_api_suggestion(url)
            }

    def _get_api_suggestion(self, url: str) -> str:
        """返回API访问建议"""
        if self.api_router:
            return self.api_router._get_api_suggestion(url)
        return "检查出版商是否提供官方API访问"

    async def _get_via_mcp(self, url: str) -> Dict[str, str]:
        """
        通过MCP获取内容

        由于MCP工具只能在Claude Code环境中使用，
        此方法将URL加入队列，返回特殊状态
        """
        # 检查是否已有结果
        if self.mcp_results_file.exists():
            try:
                with open(self.mcp_results_file, 'r', encoding='utf-8') as f:
                    results = json.load(f)
                    if url in results:
                        result = results[url]
                        if result.get('success') and result.get('content'):
                            return {
                                'success': True,
                                'content': result['content'],
                                'error': '',
                                'mcp_mode': True
                            }
            except:
                pass

        # 将URL加入MCP队列
        self._add_to_mcp_queue(url)

        return {
            'success': False,
            'content': '',
            'error': 'MCP_QUEUE: URL已加入MCP处理队列，请在Claude Code中执行MCP工具',
            'mcp_mode': True
        }

    def _add_to_mcp_queue(self, url: str):
        """将URL添加到MCP处理队列"""
        queue = []
        if self.mcp_queue_file.exists():
            try:
                with open(self.mcp_queue_file, 'r', encoding='utf-8') as f:
                    queue = json.load(f)
            except:
                pass

        if url not in queue:
            queue.append(url)
            with open(self.mcp_queue_file, 'w', encoding='utf-8') as f:
                json.dump(queue, f, ensure_ascii=False, indent=2)

    @staticmethod
    def get_mcp_extraction_js() -> str:
        """
        返回用于MCP工具的JavaScript代码

        在Claude Code中使用:
        1. mcp__chrome-devtools__navigate_page 到目标URL
        2. mcp__chrome-devtools__evaluate_script 执行此JS
        """
        return r"""() => {
    const results = {};

    // 获取标题
    const titleElem = document.querySelector('h1, .title-text, [class*="title"]');
    results.title = titleElem ? titleElem.innerText.trim() : document.title;

    // 获取摘要 - INFORMS
    let abstract = '';
    const informsAbstract = document.querySelector('.abstractSection p');
    if (informsAbstract) {
        abstract = informsAbstract.innerText.trim();
    }

    // 获取摘要 - ScienceDirect
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

    // 从页面文本提取
    if (!abstract || abstract.length < 50) {
        const bodyText = document.body.innerText;
        const abstractMatch = bodyText.match(/Abstract\s+([\s\S]*?)(?=\n\s*(?:Keywords|Introduction|1\.|©|DOI|Received))/i);
        if (abstractMatch && abstractMatch[1]) {
            abstract = abstractMatch[1].trim();
        }
    }

    results.abstract = abstract;
    results.url = window.location.href;
    results.hasContent = abstract.length > 50;

    return JSON.stringify(results);
}"""

    async def _get_via_requests(self, url: str) -> Dict[str, str]:
        """使用requests获取内容"""
        try:
            response = self.session.get(
                url,
                timeout=self.browser_config.get('timeout', 30000) / 1000,
                allow_redirects=True
            )

            if response.status_code == 403:
                # 降级到MCP模式
                return await self._get_via_mcp(url)

            response.raise_for_status()
            response.encoding = response.apparent_encoding or 'utf-8'

            soup = BeautifulSoup(response.text, 'html.parser')
            content = self._extract_content(soup, url)

            if content and len(content) > 50:
                return {
                    'success': True,
                    'content': content,
                    'error': '',
                    'mcp_mode': False
                }
            else:
                return {
                    'success': False,
                    'content': '',
                    'error': '提取内容为空或过短',
                    'mcp_mode': False
                }

        except requests.RequestException as e:
            return {
                'success': False,
                'content': '',
                'error': f'网络请求失败: {str(e)}',
                'mcp_mode': False
            }

    def _extract_content(self, soup: BeautifulSoup, url: str) -> str:
        """从BeautifulSoup对象中提取内容"""
        strategies = [
            self._try_meta_description,
            self._try_abstract_sections,
            self._try_article_content,
            self._try_visible_text
        ]

        for strategy in strategies:
            try:
                content = strategy(soup, url)
                if content and len(content) > 100:
                    return content
            except Exception:
                continue

        return ""

    def _try_meta_description(self, soup: BeautifulSoup, url: str) -> str:
        """尝试获取meta描述"""
        meta_selectors = [
            'meta[name="description"]',
            'meta[property="og:description"]',
            'meta[name="twitter:description"]'
        ]

        for selector in meta_selectors:
            meta = soup.select_one(selector)
            if meta and meta.get('content'):
                return meta.get('content').strip()

        return ""

    def _try_abstract_sections(self, soup: BeautifulSoup, url: str) -> str:
        """尝试获取摘要部分"""
        abstract_selectors = [
            '.abstract',
            '#abstract',
            '[class*="abstract"]',
            '[id*="abstract"]',
            '.article-abstract'
        ]

        for selector in abstract_selectors:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text(separator=' ', strip=True)
                if len(text) > 50:
                    return text

        return ""

    def _try_article_content(self, soup: BeautifulSoup, url: str) -> str:
        """尝试获取文章正文"""
        domain = urlparse(url).netloc.lower()

        if 'hbr.org' in domain:
            return self._extract_hbr(soup)
        elif 'sloanreview.mit.edu' in domain:
            return self._extract_mit_sloan(soup)
        else:
            return self._extract_generic_article(soup)

    def _extract_hbr(self, soup: BeautifulSoup) -> str:
        """提取HBR文章内容"""
        selectors = [
            '.article-body',
            '.post-content',
            '[class*="article-content"]',
            'article'
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                for unwanted in elem.select('.ad, .newsletter, .related, .author-bio'):
                    unwanted.decompose()
                text = elem.get_text(separator='\n', strip=True)
                return self._clean_text(text)

        return ""

    def _extract_mit_sloan(self, soup: BeautifulSoup) -> str:
        """提取MIT Sloan文章内容"""
        selectors = [
            '.article-content',
            '.entry-content',
            'article'
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text(separator='\n', strip=True)
                return self._clean_text(text)

        return ""

    def _extract_generic_article(self, soup: BeautifulSoup) -> str:
        """通用文章内容提取"""
        selectors = [
            'article',
            '[role="article"]',
            '.article-content',
            '.main-content',
            'main',
            '.content',
            '.post-content'
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                for unwanted in elem.select('nav, header, footer, aside, .sidebar, .ad, .comments'):
                    unwanted.decompose()
                text = elem.get_text(separator='\n', strip=True)
                cleaned = self._clean_text(text)
                if len(cleaned) > 100:
                    return cleaned

        return ""

    def _try_visible_text(self, soup: BeautifulSoup, url: str) -> str:
        """获取页面主要可见文本"""
        for script in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            script.decompose()
        text = soup.get_text(separator='\n', strip=True)
        return self._clean_text(text)

    def _clean_text(self, text: str) -> str:
        """清理文本"""
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)

        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if len(line) > 30]

        result = '\n\n'.join(lines)
        if len(result) > 8000:
            result = result[:8000]

        return result.strip()


# MCP队列处理工具
def process_mcp_queue():
    """
    处理MCP队列

    在Claude Code中运行的说明:
    1. 读取.mcp_work/queue.json获取待处理URL列表
    2. 对每个URL使用Chrome DevTools MCP:
       - mcp__chrome-devtools__navigate_page
       - mcp__chrome-devtools__evaluate_script (使用get_mcp_extraction_js())
    3. 将结果保存到.mcp_work/results.json
    """
    work_dir = Path('.mcp_work')
    queue_file = work_dir / 'queue.json'
    results_file = work_dir / 'results.json'

    if not queue_file.exists():
        print("队列为空")
        return

    with open(queue_file, 'r') as f:
        queue = json.load(f)

    print(f"MCP队列中有 {len(queue)} 个URL待处理")
    print("\nJavaScript代码:")
    print(BrowserAutomation.get_mcp_extraction_js())


# Test
if __name__ == '__main__':
    import asyncio

    async def test():
        config = {'browser': {'timeout': 30000}}
        browser = BrowserAutomation(config)

        # 测试不同类型的URL
        test_urls = [
            "https://hbr.org/2026/01/new-to-the-executive-team-start-here",  # 普通网站
            "https://pubsonline.informs.org/doi/abs/10.1287/isre.2024.1313",  # 需要MCP
        ]

        for url in test_urls:
            print(f"\n{'='*60}")
            print(f"测试: {url}")
            print(f"{'='*60}")

            result = await browser.get_article_content(url)
            print(f"成功: {result['success']}")
            print(f"MCP模式: {result.get('mcp_mode', False)}")

            if result['success']:
                print(f"内容长度: {len(result['content'])} 字符")
                print(f"\n内容预览:\n{result['content'][:400]}...")
            else:
                print(f"错误: {result['error']}")

    asyncio.run(test())
